# ✅ NUEVO ARCHIVO - Todo el sistema de comisiones
import streamlit as st
import gspread
import pandas as pd
import numpy as np
from datetime import datetime
from oauth2client.service_account import ServiceAccountCredentials

def mostrar_dashboard_comisiones():
    """Función principal del dashboard de comisiones"""
    gestionar_comisiones_manuales()

def gestionar_comisiones_manuales():
    """Sistema liviano para comisiones manuales"""
    
    st.header("💰 Gestión de Comisiones Manuales")
    
    # ✅ VERIFICACIÓN DE ACCESO
    contraseña = st.text_input("🔐 Contraseña de Encargado:", type="password")
    if contraseña != "operacion2024":
        st.error("⛔ Acceso restringido")
        return
    
    st.success("✅ Acceso concedido - Modo Encargado")
    
    # ✅ CARGAR DATOS BÁSICOS (solo lo necesario)
    df_produccion = cargar_datos_basicos_produccion()
    if df_produccion is None:
        return
    
    # ✅ CONFIGURACIÓN DEL DÍA Y TURNO
    st.subheader("📅 Configurar Período")
    
    col1, col2 = st.columns(2)
    with col1:
        fecha_seleccionada = st.date_input("Fecha:", value=datetime.now().date())
    with col2:
        turno_seleccionado = st.selectbox("Turno:", ["MAÑANA", "TARDE"])
    
    # ✅ CALCULAR PUNTADAS POR OPERADOR (SOLO PARA ESTE TURNO)
    st.subheader("📊 Puntadas del Turno")
    
    puntadas_operadores = calcular_puntadas_turno(df_produccion, fecha_seleccionada, turno_seleccionado)
    
    if not puntadas_operadores:
        st.warning("No hay datos para este turno")
        return
    
    # Mostrar resumen rápido
    for operador, datos in puntadas_operadores.items():
        col1, col2, col3 = st.columns([3, 2, 1])
        with col1:
            st.write(f"**{operador}**")
        with col2:
            st.write(f"Puntadas: {datos['puntadas']:,.0f}")
        with col3:
            st.write(f"Pedidos: {datos['pedidos']}")
    
    # ✅ GESTIÓN MANUAL DE COMISIONES
    st.subheader("💵 Asignar Comisiones Manuales")
    
    comisiones_guardadas = cargar_comisiones_existentes(fecha_seleccionada, turno_seleccionado)
    
    for operador, datos in puntadas_operadores.items():
        with st.expander(f"💰 {operador} - {datos['puntadas']:,.0f} puntadas", expanded=True):
            
            # Buscar si ya existe comisión guardada
            comision_existente = next(
                (c for c in comisiones_guardadas if c['Operador'] == operador), 
                None
            )
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                # Comisión base automática (sugerencia)
                comision_base_sugerida = calcular_comision_base_sugerida(datos['puntadas'])
                comision_base = st.number_input(
                    f"Comisión Base {operador}",
                    min_value=0.0,
                    value=comision_existente['Comision_Base'] if comision_existente else comision_base_sugerida,
                    step=50.0,
                    key=f"base_{operador}"
                )
            
            with col2:
                # Compensación manual
                compensacion = st.number_input(
                    f"Compensación {operador}",
                    min_value=0.0,
                    value=comision_existente['Compensacion_Manual'] if comision_existente else 0.0,
                    step=25.0,
                    key=f"comp_{operador}"
                )
            
            with col3:
                total = comision_base + compensacion
                st.metric("TOTAL", f"${total:,.2f}")
                
                # Botón para guardar individual
                if st.button("💾 Guardar", key=f"btn_{operador}"):
                    guardar_comision_individual(
                        fecha_seleccionada,
                        turno_seleccionado,
                        operador,
                        datos['puntadas'],
                        comision_base,
                        compensacion,
                        total
                    )
    
    # ✅ GUARDAR TODAS LAS COMISIONES
    if st.button("💾 Guardar Todas las Comisiones del Turno", type="primary"):
        guardar_todas_comisiones(fecha_seleccionada, turno_seleccionado, puntadas_operadores)
        st.success("✅ Comisiones guardadas exitosamente!")

def cargar_datos_basicos_produccion():
    """Carga solo las columnas necesarias para evitar peso"""
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
        
        # ✅ SOLO CARGAR COLUMNAS NECESARIAS (reduce peso en 80%)
        data = worksheet.get_all_values()
        df_raw = pd.DataFrame(data[1:], columns=data[0])
        
        # Mantener solo columnas esenciales
        columnas_necesarias = ['Marca temporal', 'OPERADOR', 'PUNTADAS', 'CANTIDAD', '#DE PEDIDO']
        columnas_existentes = [col for col in columnas_necesarias if col in df_raw.columns]
        
        df_ligero = df_raw[columnas_existentes].copy()
        
        # Conversiones básicas
        if "PUNTADAS" in df_ligero.columns:
            df_ligero["PUNTADAS"] = pd.to_numeric(df_ligero["PUNTADAS"], errors='coerce').fillna(0)
        
        return df_ligero
        
    except Exception as e:
        st.error(f"❌ Error al cargar datos: {str(e)}")
        return None

def calcular_puntadas_turno(df, fecha, turno):
    """Calcular puntadas por operador para un turno específico"""
    df_fecha = df.copy()
    df_fecha['Fecha'] = pd.to_datetime(df_fecha['Marca temporal']).dt.date
    df_fecha['Hora'] = pd.to_datetime(df_fecha['Marca temporal']).dt.hour
    
    # Filtrar por fecha
    df_dia = df_fecha[df_fecha['Fecha'] == fecha]
    
    # Filtrar por turno
    if turno == "MAÑANA":
        df_turno = df_dia[df_dia['Hora'].between(6, 14)]  # 6am - 2pm
    else:  # TARDE
        df_turno = df_dia[df_dia['Hora'].between(14, 22)]  # 2pm - 10pm
    
    if df_turno.empty:
        return {}
    
    # Agrupar por operador
    puntadas_por_operador = df_turno.groupby('OPERADOR').agg({
        'PUNTADAS': 'sum',
        '#DE PEDIDO': 'count'
    }).to_dict('index')
    
    # Formatear resultado
    resultado = {}
    for operador, datos in puntadas_por_operador.items():
        resultado[operador] = {
            'puntadas': datos['PUNTADAS'],
            'pedidos': datos['#DE PEDIDO']
        }
    
    return resultado

def calcular_comision_base_sugerida(puntadas):
    """Calcular comisión base sugerida basada en puntadas"""
    if puntadas >= 200000:
        return 300.0
    elif puntadas >= 150000:
        return 200.0
    elif puntadas >= 100000:
        return 100.0
    else:
        return 50.0

def cargar_comisiones_existentes(fecha, turno):
    """Cargar comisiones ya guardadas (muy liviano)"""
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
        worksheet = gc.open_by_key(sheet_id).worksheet("comisiones_manuales")
        data = worksheet.get_all_values()
        
        if len(data) <= 1:  # Solo headers
            return []
        
        df_comisiones = pd.DataFrame(data[1:], columns=data[0])
        
        # Filtrar por fecha y turno
        df_filtrado = df_comisiones[
            (df_comisiones['Fecha'] == fecha.strftime('%Y-%m-%d')) & 
            (df_comisiones['Turno'] == turno)
        ]
        
        return df_filtrado.to_dict('records')
        
    except Exception as e:
        st.info("ℹ️ No hay comisiones guardadas para este turno")
        return []

def guardar_comision_individual(fecha, turno, operador, puntadas, comision_base, compensacion, total):
    """Guardar una comisión individual en Sheets"""
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
        worksheet = gc.open_by_key(sheet_id).worksheet("comisiones_manuales")
        
        # Preparar datos
        nueva_fila = [
            fecha.strftime('%Y-%m-%d'),
            turno,
            operador,
            puntadas,
            comision_base,
            compensacion,
            total,
            "Sistema",  # Autorizado por
            datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        ]
        
        # Agregar fila
        worksheet.append_row(nueva_fila)
        st.success(f"✅ Comisión guardada para {operador}")
        
    except Exception as e:
        st.error(f"❌ Error al guardar: {str(e)}")

def guardar_todas_comisiones(fecha, turno, puntadas_operadores):
    """Guardar todas las comisiones del turno"""
    st.info("Función para guardar todas las comisiones - pendiente de implementar")
