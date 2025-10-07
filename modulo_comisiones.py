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
    modo = st.radio("Selecciona el modo:", ["👨‍💼 Modo Encargado", "👷 Modo Operador"])
    
    if "👨‍💼 Modo Encargado" in modo:
        gestionar_comisiones_encargado()
    else:
        mostrar_comisiones_operador()

def gestionar_comisiones_encargado():
    """Interfaz para que el encargado asigne comisiones"""
    
    # ✅ VERIFICACIÓN DE ACCESO
    contraseña = st.text_input("🔐 Contraseña de Encargado:", type="password")
    if contraseña != "operacion2024":
        st.error("⛔ Acceso restringido")
        return
    
    st.success("✅ Acceso concedido - Modo Encargado")
    
    # ✅ CONFIGURACIÓN SEMANA
    st.subheader("📅 Configurar Semana")
    
    col1, col2 = st.columns(2)
    with col1:
        fecha_inicio = st.date_input("Fecha inicio de semana:", 
                                   value=datetime.now().date() - timedelta(days=datetime.now().weekday()))
    with col2:
        # Mostrar rango de la semana
        fecha_fin = fecha_inicio + timedelta(days=6)
        st.write(f"**Semana:** {fecha_inicio} al {fecha_fin}")
    
    # ✅ CARGAR DATOS DE PRODUCCIÓN DE LA SEMANA
    df_produccion = cargar_datos_semana_produccion(fecha_inicio, fecha_fin)
    if df_produccion is None or df_produccion.empty:
        st.warning("⚠️ No hay datos de producción para esta semana")
        return
    
    # ✅ RESUMEN DE PRODUCCIÓN POR OPERADOR
    st.subheader("📊 Resumen de Producción Semanal")
    
    # Agrupar por operador y día
    resumen_operadores = calcular_resumen_semanal(df_produccion, fecha_inicio)
    
    # Mostrar resumen
    for operador, datos_semana in resumen_operadores.items():
        with st.expander(f"👤 **{operador}** - Total: {datos_semana['total_puntadas']:,} puntadas"):
            col1, col2 = st.columns(2)
            
            with col1:
                st.write("**Producción por día:**")
                for fecha, puntadas in datos_semana['puntadas_por_dia'].items():
                    st.write(f"- {fecha}: {puntadas:,} puntadas")
            
            with col2:
                # Asignación de comisiones
                st.write("**Asignar Comisiones:**")
                comision_total = 0
                
                for fecha, puntadas in datos_semana['puntadas_por_dia'].items():
                    comision_dia = st.number_input(
                        f"Comisión {fecha}",
                        min_value=0.0,
                        max_value=1000.0,
                        value=calcular_comision_sugerida(puntadas),
                        key=f"comision_{operador}_{fecha}"
                    )
                    comision_total += comision_dia
                
                st.metric("💰 Comisión Total Semanal", f"${comision_total:,.2f}")
                
                # Botón para guardar comisiones
                if st.button(f"💾 Guardar Comisiones - {operador}", key=f"guardar_{operador}"):
                    guardar_comisiones_semanales(
                        operador, fecha_inicio, datos_semana['puntadas_por_dia'], 
                        comision_total, datos_semana['total_pedidos']
                    )

def mostrar_comisiones_operador():
    """Interfaz para que los operadores vean sus comisiones"""
    
    st.subheader("👷 Consulta de Comisiones - Operador")
    
    # ✅ LISTA DE OPERADORES (podría venir de una base de datos)
    operadores = ["OPERADOR_A", "OPERADOR_B", "OPERADOR_C", "OPERADOR_D", "OPERADOR_E"]
    operador_seleccionado = st.selectbox("Selecciona tu nombre:", operadores)
    
    # ✅ CONSULTAR SEMANA
    col1, col2 = st.columns(2)
    with col1:
        fecha_consulta = st.date_input("Semana a consultar:", 
                                     value=datetime.now().date() - timedelta(days=datetime.now().weekday()))
    
    fecha_inicio_semana = fecha_consulta
    fecha_fin_semana = fecha_inicio_semana + timedelta(days=6)
    
    # ✅ CARGAR COMISIONES DEL OPERADOR
    comisiones_operador = cargar_comisiones_operador(operador_seleccionado, fecha_inicio_semana)
    
    if not comisiones_operador:
        st.info(f"ℹ️ No hay comisiones registradas para {operador_seleccionado} en la semana del {fecha_inicio_semana}")
        return
    
    # ✅ MOSTRAR DETALLE DE COMISIONES
    st.subheader(f"💵 Comisiones de {operador_seleccionado}")
    st.write(f"**Período:** {fecha_inicio_semana} al {fecha_fin_semana}")
    
    # Crear DataFrame para mostrar
    datos_tabla = []
    total_comision = 0
    
    for fecha, datos in comisiones_operador['detalle_diario'].items():
        datos_tabla.append({
            'Fecha': fecha,
            'Puntadas': f"{datos['puntadas']:,}",
            'Comisión': f"${datos['comision']:,.2f}",
            'Pedidos': datos['pedidos']
        })
        total_comision += datos['comision']
    
    # Mostrar tabla
    df_comisiones = pd.DataFrame(datos_tabla)
    st.dataframe(df_comisiones, use_container_width=True)
    
    # ✅ RESUMEN FINAL
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("📊 Total Puntadas", f"{comisiones_operador['total_puntadas']:,}")
    with col2:
        st.metric("📦 Total Pedidos", comisiones_operador['total_pedidos'])
    with col3:
        st.metric("💰 Comisión Total", f"${total_comision:,.2f}")
    
    # ✅ BOTÓN DE CONFIRMACIÓN
    if st.button("✅ Confirmar Visualización"):
        st.success("✔️ Comisiones verificadas correctamente")
        guardar_confirmacion_operador(operador_seleccionado, fecha_inicio_semana, total_comision)

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
    
    # Agrupar por operador
    operadores = df_produccion['OPERADOR'].unique()
    resumen = {}
    
    for operador in operadores:
        df_operador = df_produccion[df_produccion['OPERADOR'] == operador]
        
        puntadas_por_dia = {}
        total_puntadas = 0
        total_pedidos = 0
        
        for fecha in fechas_semana:
            df_dia = df_operador[df_operador['Fecha'] == fecha]
            puntadas_dia = df_dia['PUNTADAS'].sum() if not df_dia.empty else 0
            pedidos_dia = len(df_dia) if not df_dia.empty else 0
            
            puntadas_por_dia[fecha.strftime('%Y-%m-%d')] = puntadas_dia
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

def guardar_comisiones_semanales(operador, fecha_inicio, puntadas_por_dia, comision_total, total_pedidos):
    """Guardar comisiones semanales en Google Sheets"""
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
        
        # Preparar datos para guardar
        fecha_fin = fecha_inicio + timedelta(days=6)
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Guardar cada día individualmente
        for fecha_str, puntadas in puntadas_por_dia.items():
            comision_dia = calcular_comision_sugerida(puntadas)  # O guardar las asignadas individualmente
            
            nueva_fila = [
                operador,
                fecha_str,  # Fecha específica del día
                fecha_inicio.strftime('%Y-%m-%d'),  # Inicio semana
                fecha_fin.strftime('%Y-%m-%d'),     # Fin semana
                puntadas,
                comision_dia,
                total_pedidos,
                "Encargado Operación",  # Asignado por
                timestamp,
                "PENDIENTE"  # Estado de confirmación
            ]
            
            worksheet.append_row(nueva_fila)
        
        st.success(f"✅ Comisiones guardadas para {operador}")
        
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
        df_operador = df_comisiones[
            (df_comisiones['Operador'] == operador) & 
            (df_comisiones['Inicio_Semana'] == fecha_inicio_semana.strftime('%Y-%m-%d'))
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
        st.error(f"❌ Error al guardar: {str(e)}")

def guardar_todas_comisiones(fecha, turno, puntadas_operadores):
    """Guardar todas las comisiones del turno"""
    st.info("Función para guardar todas las comisiones - pendiente de implementar")
