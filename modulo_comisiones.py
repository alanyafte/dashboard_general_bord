# ✅ SISTEMA COMPLETO DE COMISIONES SEMANALES
import streamlit as st
import gspread
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from oauth2client.service_account import ServiceAccountCredentials

def mostrar_dashboard_comisiones():
    """Función principal del dashboard de comisiones"""
    gestionar_comisiones_semanales()

def gestionar_comisiones_semanales():
    """Sistema para comisiones semanales por operador"""
    
    st.title("💰 Sistema de Comisiones Semanales")
    
    # ✅ MODO SELECCIÓN: ENCARGADO vs OPERADOR
    modo = st.radio("Selecciona el modo:", ["👨‍💼 Modo Encargado", "👷 Modo Operador"], horizontal=True)
    
    if modo == "👨‍💼 Modo Encargado":
        gestionar_comisiones_encargado()
    else:
        mostrar_comisiones_operador()

def gestionar_comisiones_encargado():
    """Interfaz para que el encargado asigne comisiones"""
    
    # ✅ VERIFICACIÓN DE ACCESO
    contraseña = st.text_input("🔐 Contraseña de Encargado:", type="password", key="pass_encargado")
    if contraseña != "encargado123":
        st.error("⛔ Acceso restringido")
        return
    
    st.success("✅ Acceso concedido - Modo Encargado")
    
    # ✅ CONFIGURACIÓN SEMANA
    st.subheader("📅 Configurar Semana")
    
    col1, col2 = st.columns(2)
    with col1:
        # Por defecto: lunes de la semana actual
        hoy = datetime.now().date()
        lunes_actual = hoy - timedelta(days=hoy.weekday())
        fecha_inicio = st.date_input("Fecha inicio de semana (lunes):", value=lunes_actual)
    
    with col2:
        # Mostrar rango de la semana
        fecha_fin = fecha_inicio + timedelta(days=6)
        st.write(f"**Semana completa:** {fecha_inicio} al {fecha_fin}")
        st.write(f"**Días:** Lunes a Domingo")
    
    # ✅ CARGAR DATOS DE PRODUCCIÓN DE LA SEMANA
    with st.spinner("Cargando datos de producción..."):
        df_produccion = cargar_datos_semana_produccion(fecha_inicio, fecha_fin)
    
    if df_produccion is None or df_produccion.empty:
        st.warning(f"⚠️ No hay datos de producción para la semana del {fecha_inicio}")
        return
    
    st.success(f"✅ Datos cargados: {len(df_produccion)} registros de producción")
    
    # ✅ RESUMEN DE PRODUCCIÓN POR OPERADOR
    st.subheader("📊 Resumen de Producción Semanal")
    
    # Agrupar por operador y día
    resumen_operadores = calcular_resumen_semanal(df_produccion, fecha_inicio)
    
    # Mostrar resumen general primero
    st.write("### 📈 Resumen General de la Semana")
    
    total_puntadas_semana = sum(datos['total_puntadas'] for datos in resumen_operadores.values())
    total_pedidos_semana = sum(datos['total_pedidos'] for datos in resumen_operadores.values())
    total_operadores = len(resumen_operadores)
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("👥 Operadores Activos", total_operadores)
    with col2:
        st.metric("📦 Total Pedidos", total_pedidos_semana)
    with col3:
        st.metric("🪡 Total Puntadas", f"{total_puntadas_semana:,}")
    
    # ✅ ASIGNACIÓN DE COMISIONES POR OPERADOR
    st.subheader("💵 Asignación de Comisiones")
    
    # Cargar comisiones ya existentes para esta semana
    comisiones_existentes = cargar_comisiones_existentes_semana(fecha_inicio)
    
    for operador, datos_semana in resumen_operadores.items():
        with st.expander(f"👤 **{operador}** - {datos_semana['total_puntadas']:,} puntadas - {datos_semana['total_pedidos']} pedidos", expanded=True):
            
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.write("**📅 Producción por día:**")
                
                # Crear tabla de producción diaria
                datos_diarios = []
                comision_total = 0
                
                for fecha_str, puntadas in datos_semana['puntadas_por_dia'].items():
                    fecha_obj = datetime.strptime(fecha_str, '%Y-%m-%d').date()
                    dia_semana = fecha_obj.strftime('%A')
                    
                    # Buscar si ya existe comisión asignada
                    comision_existente = 0
                    for comision in comisiones_existentes:
                        if (comision['Operador'] == operador and 
                            comision['Fecha_Dia'] == fecha_str):
                            comision_existente = float(comision['Comision'])
                            break
                    
                    # Input para comisión del día
                    comision_dia = st.number_input(
                        f"{dia_semana} ({fecha_str}) - {puntadas:,} puntadas",
                        min_value=0.0,
                        max_value=1000.0,
                        value=comision_existente if comision_existente > 0 else calcular_comision_sugerida(puntadas),
                        key=f"comision_{operador}_{fecha_str}",
                        step=10.0
                    )
                    
                    datos_diarios.append({
                        'fecha': fecha_str,
                        'dia': dia_semana,
                        'puntadas': puntadas,
                        'comision': comision_dia
                    })
                    
                    comision_total += comision_dia
            
            with col2:
                st.write("**💰 Resumen Comisiones:**")
                st.metric("Comisión Total Semanal", f"${comision_total:,.2f}")
                
                # Mostrar desglose sugerido
                st.write("**💡 Sugerencia automática:**")
                for dato in datos_diarios:
                    sugerido = calcular_comision_sugerida(dato['puntadas'])
                    st.write(f"- {dato['dia'][:3]}: ${sugerido:.0f}")
                
                # Botón para guardar comisiones
                if st.button(f"💾 Guardar Comisiones - {operador}", key=f"guardar_{operador}", use_container_width=True):
                    guardar_comisiones_operador_semana(
                        operador, fecha_inicio, datos_diarios, 
                        datos_semana['total_puntadas'], datos_semana['total_pedidos']
                    )

def mostrar_comisiones_operador():
    """Interfaz para que los operadores vean sus comisiones"""
    
    st.subheader("👷 Consulta de Comisiones - Operador")
    
    # ✅ LISTA DE OPERADORES (actualiza con tus operadores reales)
    operadores = obtener_lista_operadores()
    operador_seleccionado = st.selectbox("Selecciona tu nombre:", operadores)
    
    # ✅ CONSULTAR SEMANA
    col1, col2 = st.columns(2)
    with col1:
        # Por defecto: semana actual
        hoy = datetime.now().date()
        lunes_actual = hoy - timedelta(days=hoy.weekday())
        fecha_consulta = st.date_input("Semana a consultar (lunes):", value=lunes_actual)
    
    fecha_inicio_semana = fecha_consulta
    fecha_fin_semana = fecha_inicio_semana + timedelta(days=6)
    
    with col2:
        st.write(f"**Semana:** {fecha_inicio_semana} al {fecha_fin_semana}")
    
    # ✅ CARGAR COMISIONES DEL OPERADOR
    with st.spinner("Buscando comisiones..."):
        comisiones_operador = cargar_comisiones_operador(operador_seleccionado, fecha_inicio_semana)
    
    if not comisiones_operador:
        st.info(f"ℹ️ No hay comisiones registradas para **{operador_seleccionado}** en la semana del {fecha_inicio_semana}")
        return
    
    # ✅ MOSTRAR DETALLE DE COMISIONES
    st.subheader(f"💵 Comisiones de {operador_seleccionado}")
    st.write(f"**Período:** {fecha_inicio_semana} al {fecha_fin_semana}")
    
    # Crear tabla de comisiones
    datos_tabla = []
    total_comision = 0
    total_puntadas = 0
    
    for fecha_str, datos in comisiones_operador['detalle_diario'].items():
        fecha_obj = datetime.strptime(fecha_str, '%Y-%m-%d').date()
        dia_semana = fecha_obj.strftime('%A')
        
        datos_tabla.append({
            'Día': dia_semana,
            'Fecha': fecha_str,
            'Puntadas': f"{datos['puntadas']:,}",
            'Comisión': f"${datos['comision']:,.2f}",
            'Pedidos': datos['pedidos']
        })
        total_comision += datos['comision']
        total_puntadas += datos['puntadas']
    
    # Mostrar tabla con estilo
    st.dataframe(pd.DataFrame(datos_tabla), use_container_width=True)
    
    # ✅ RESUMEN FINAL
    st.subheader("📊 Resumen Final")
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("📅 Días Trabajados", len(comisiones_operador['detalle_diario']))
    with col2:
        st.metric("📊 Total Puntadas", f"{total_puntadas:,}")
    with col3:
        st.metric("📦 Total Pedidos", comisiones_operador['total_pedidos'])
    with col4:
        st.metric("💰 Comisión Total", f"${total_comision:,.2f}")
    
    # ✅ BOTÓN DE CONFIRMACIÓN
    st.markdown("---")
    col1, col2 = st.columns([3, 1])
    with col2:
        if st.button("✅ Confirmar Visualización", use_container_width=True, type="primary"):
            guardar_confirmacion_operador(operador_seleccionado, fecha_inicio_semana, total_comision)
            st.success("✔️ Comisiones verificadas correctamente")

# ============================================================
# FUNCIONES DE APOYO
# ============================================================

def obtener_lista_operadores():
    """Obtener lista de operadores (actualiza con tus operadores reales)"""
    return ["OPERADOR_A", "OPERADOR_B", "OPERADOR_C", "OPERADOR_D", "OPERADOR_E"]

def cargar_datos_semana_produccion(fecha_inicio, fecha_fin):
    """Cargar datos de producción de una semana específica"""
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        
        service_account_info = {
            "type": st.secrets["gservice_account"]["type"],
            "project_id": st.secrets["gservice_account"]["project_id"],
            "private_key_id": st.secrets["gservice_account"]["private_key_id"],
            "private_key": st.secrets["gservice_account"]["private_key"],
            "client_email": st.secrets["gservice_account"]["client_email"],
            "client_id": st.secrets["gservice_account"]["client_id"],
            "auth_uri": st.secrets["gservice_account"]["auth_uri"],
            "token_uri": st.secrets["gservice_account"]["token_uri"]
        }
        
        creds = ServiceAccountCredentials.from_json_keyfile_dict(service_account_info, scope)
        gc = gspread.authorize(creds)
        
        sheet_id = st.secrets["gsheets"]["produccion_sheet_id"]
        worksheet = gc.open_by_key(sheet_id).worksheet("reporte_de_trabajo")
        
        # Cargar datos
        data = worksheet.get_all_values()
        df_raw = pd.DataFrame(data[1:], columns=data[0])
        
        # Filtrar columnas necesarias
        columnas_necesarias = ['Marca temporal', 'OPERADOR', 'PUNTADAS', 'CANTIDAD', '#DE PEDIDO']
        columnas_existentes = [col for col in columnas_necesarias if col in df_raw.columns]
        df_ligero = df_raw[columnas_existentes].copy()
        
        # Convertir fechas y filtrar por semana
        df_ligero['Marca temporal'] = pd.to_datetime(df_ligero['Marca temporal'], errors='coerce')
        df_ligero['Fecha'] = df_ligero['Marca temporal'].dt.date
        
        # Filtrar por rango de fechas
        mask = (df_ligero['Fecha'] >= fecha_inicio) & (df_ligero['Fecha'] <= fecha_fin)
        df_semana = df_ligero[mask].copy()
        
        # Convertir puntadas a numérico
        if "PUNTADAS" in df_semana.columns:
            df_semana["PUNTADAS"] = pd.to_numeric(df_semana["PUNTADAS"], errors='coerce').fillna(0)
        
        return df_semana
        
    except Exception as e:
        st.error(f"❌ Error al cargar datos: {str(e)}")
        return None

def calcular_resumen_semanal(df_produccion, fecha_inicio):
    """Calcular resumen semanal por operador"""
    
    if df_produccion.empty:
        return {}
    
    # Generar todas las fechas de la semana
    fechas_semana = [fecha_inicio + timedelta(days=i) for i in range(7)]
    fechas_semana_str = [fecha.strftime('%Y-%m-%d') for fecha in fechas_semana]
    
    # Agrupar por operador
    operadores = df_produccion['OPERADOR'].unique()
    resumen = {}
    
    for operador in operadores:
        df_operador = df_produccion[df_produccion['OPERADOR'] == operador]
        
        puntadas_por_dia = {}
        total_puntadas = 0
        total_pedidos = 0
        
        for fecha in fechas_semana:
            fecha_str = fecha.strftime('%Y-%m-%d')
            df_dia = df_operador[df_operador['Fecha'] == fecha]
            puntadas_dia = df_dia['PUNTADAS'].sum() if not df_dia.empty else 0
            pedidos_dia = len(df_dia) if not df_dia.empty else 0
            
            puntadas_por_dia[fecha_str] = puntadas_dia
            total_puntadas += puntadas_dia
            total_pedidos += pedidos_dia
        
        resumen[operador] = {
            'puntadas_por_dia': puntadas_por_dia,
            'total_puntadas': total_puntadas,
            'total_pedidos': total_pedidos
        }
    
    return resumen

def calcular_comision_sugerida(puntadas):
    """Calcular comisión sugerida basada en puntadas"""
    if puntadas >= 200000:
        return 300.0
    elif puntadas >= 150000:
        return 250.0
    elif puntadas >= 100000:
        return 200.0
    elif puntadas >= 50000:
        return 150.0
    elif puntadas >= 25000:
        return 100.0
    else:
        return 50.0

def cargar_comisiones_existentes_semana(fecha_inicio):
    """Cargar comisiones ya existentes para una semana"""
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        
        service_account_info = {
            "type": st.secrets["gservice_account"]["type"],
            "project_id": st.secrets["gservice_account"]["project_id"],
            "private_key_id": st.secrets["gservice_account"]["private_key_id"],
            "private_key": st.secrets["gservice_account"]["private_key"],
            "client_email": st.secrets["gservice_account"]["client_email"],
            "client_id": st.secrets["gservice_account"]["client_id"],
            "auth_uri": st.secrets["gservice_account"]["auth_uri"],
            "token_uri": st.secrets["gservice_account"]["token_uri"]
        }
        
        creds = ServiceAccountCredentials.from_json_keyfile_dict(service_account_info, scope)
        gc = gspread.authorize(creds)
        
        sheet_id = st.secrets["gsheets"]["produccion_sheet_id"]
        worksheet = gc.open_by_key(sheet_id).worksheet("comisiones_semanales")
        
        data = worksheet.get_all_values()
        if len(data) <= 1:
            return []
        
        df_comisiones = pd.DataFrame(data[1:], columns=data[0])
        
        # Filtrar por semana
        fecha_inicio_str = fecha_inicio.strftime('%Y-%m-%d')
        df_filtrado = df_comisiones[df_comisiones['Inicio_Semana'] == fecha_inicio_str]
        
        return df_filtrado.to_dict('records')
        
    except Exception as e:
        st.info("ℹ️ No hay comisiones guardadas para esta semana")
        return []

def guardar_comisiones_operador_semana(operador, fecha_inicio, datos_diarios, total_puntadas, total_pedidos):
    """Guardar comisiones de un operador para la semana"""
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        
        service_account_info = {
            "type": st.secrets["gservice_account"]["type"],
            "project_id": st.secrets["gservice_account"]["project_id"],
            "private_key_id": st.secrets["gservice_account"]["private_key_id"],
            "private_key": st.secrets["gservice_account"]["private_key"],
            "client_email": st.secrets["gservice_account"]["client_email"],
            "client_id": st.secrets["gservice_account"]["client_id"],
            "auth_uri": st.secrets["gservice_account"]["auth_uri"],
            "token_uri": st.secrets["gservice_account"]["token_uri"]
        }
        
        creds = ServiceAccountCredentials.from_json_keyfile_dict(service_account_info, scope)
        gc = gspread.authorize(creds)
        
        sheet_id = st.secrets["gsheets"]["produccion_sheet_id"]
        worksheet = gc.open_by_key(sheet_id).worksheet("comisiones_semanales")
        
        # Preparar datos
        fecha_fin = fecha_inicio + timedelta(days=6)
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Guardar cada día individualmente
        filas_guardadas = 0
        for dato in datos_diarios:
            if dato['comision'] > 0:  # Solo guardar si hay comisión asignada
                nueva_fila = [
                    operador,
                    dato['fecha'],
                    fecha_inicio.strftime('%Y-%m-%d'),
                    fecha_fin.strftime('%Y-%m-%d'),
                    dato['puntadas'],
                    dato['comision'],
                    total_pedidos,
                    "Encargado Operación",
                    timestamp,
                    "ASIGNADO"
                ]
                
                worksheet.append_row(nueva_fila)
                filas_guardadas += 1
        
        st.success(f"✅ Comisiones guardadas para {operador}: {filas_guardadas} días")
        
    except Exception as e:
        st.error(f"❌ Error al guardar comisiones: {str(e)}")

def cargar_comisiones_operador(operador, fecha_inicio_semana):
    """Cargar comisiones de un operador específico para una semana"""
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        
        service_account_info = {
            "type": st.secrets["gservice_account"]["type"],
            "project_id": st.secrets["gservice_account"]["project_id"],
            "private_key_id": st.secrets["gservice_account"]["private_key_id"],
            "private_key": st.secrets["gservice_account"]["private_key"],
            "client_email": st.secrets["gservice_account"]["client_email"],
            "client_id": st.secrets["gservice_account"]["client_id"],
            "auth_uri": st.secrets["gservice_account"]["auth_uri"],
            "token_uri": st.secrets["gservice_account"]["token_uri"]
        }
        
        creds = ServiceAccountCredentials.from_json_keyfile_dict(service_account_info, scope)
        gc = gspread.authorize(creds)
        
        sheet_id = st.secrets["gsheets"]["produccion_sheet_id"]
        worksheet = gc.open_by_key(sheet_id).worksheet("comisiones_semanales")
        
        # Cargar todos los datos
        data = worksheet.get_all_values()
        if len(data) <= 1:
            return None
        
        df_comisiones = pd.DataFrame(data[1:], columns=data[0])
        
        # Filtrar por operador y semana
        fecha_inicio_str = fecha_inicio_semana.strftime('%Y-%m-%d')
        df_operador = df_comisiones[
            (df_comisiones['Operador'] == operador) & 
            (df_comisiones['Inicio_Semana'] == fecha_inicio_str)
        ]
        
        if df_operador.empty:
            return None
        
        # Procesar datos
        detalle_diario = {}
        total_puntadas = 0
        total_pedidos = 0
        
        for _, row in df_operador.iterrows():
            fecha = row['Fecha_Dia']
            puntadas = int(float(row['Puntadas'])) if row['Puntadas'] else 0
            comision = float(row['Comision']) if row['Comision'] else 0
            pedidos = int(row['Pedidos']) if row['Pedidos'] else 0
            
            detalle_diario[fecha] = {
                'puntadas': puntadas,
                'comision': comision,
                'pedidos': pedidos
            }
            
            total_puntadas += puntadas
            total_pedidos += pedidos
        
        return {
            'detalle_diario': detalle_diario,
            'total_puntadas': total_puntadas,
            'total_pedidos': total_pedidos
        }
        
    except Exception as e:
        st.error(f"❌ Error al cargar comisiones: {str(e)}")
        return None

def guardar_confirmacion_operador(operador, fecha_semana, comision_total):
    """Guardar confirmación de visualización del operador"""
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        
        service_account_info = {
            "type": st.secrets["gservice_account"]["type"],
            "project_id": st.secrets["gservice_account"]["project_id"],
            "private_key_id": st.secrets["gservice_account"]["private_key_id"],
            "private_key": st.secrets["gservice_account"]["private_key"],
            "client_email": st.secrets["gservice_account"]["client_email"],
            "client_id": st.secrets["gservice_account"]["client_id"],
            "auth_uri": st.secrets["gservice_account"]["auth_uri"],
            "token_uri": st.secrets["gservice_account"]["token_uri"]
        }
        
        creds = ServiceAccountCredentials.from_json_keyfile_dict(service_account_info, scope)
        gc = gspread.authorize(creds)
        
        sheet_id = st.secrets["gsheets"]["produccion_sheet_id"]
        worksheet = gc.open_by_key(sheet_id).worksheet("confirmaciones_comisiones")
        
        # Guardar confirmación
        nueva_fila = [
            operador,
            fecha_semana.strftime('%Y-%m-%d'),
            comision_total,
            datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "CONFIRMADO"
        ]
        
        worksheet.append_row(nueva_fila)
        
    except Exception as e:
        st.error(f"❌ Error al guardar confirmación: {str(e)}")
