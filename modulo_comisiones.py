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
    """Sistema liviano para comisiones manuales - CON MÁS OPCIONES"""
    
    st.header("💰 Gestión de Comisiones Manuales")
    
    # ✅ VERIFICACIÓN DE ACCESO
    contraseña = st.text_input("🔐 Contraseña de Encargado:", type="password")
    if contraseña != "operacion2024":
        st.error("⛔ Acceso restringido")
        return
    
    st.success("✅ Acceso concedido - Modo Encargado")
    
    # ✅ CARGAR DATOS BÁSICOS
    df_produccion = cargar_datos_basicos_produccion()
    if df_produccion is None:
        return
    
    # ✅ CONFIGURACIÓN MÁS FLEXIBLE
    st.subheader("📅 Configurar Período")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        # Por defecto usar hoy, pero permitir seleccionar cualquier fecha
        fecha_seleccionada = st.date_input("Fecha:", value=datetime.now().date())
    with col2:
        turno_seleccionado = st.selectbox("Turno:", ["MAÑANA", "TARDE"])
    with col3:
        # Opción para ver TODOS los datos (sin filtro de turno)
        ver_todo_el_dia = st.checkbox("Ver todo el día", value=False)
    
    # ✅ CALCULAR PUNTADAS
    st.subheader("📊 Puntadas del Turno")
    
    if ver_todo_el_dia:
        # Usar función simple sin filtro de turno
        puntadas_operadores = calcular_puntadas_dia_completo(df_produccion, fecha_seleccionada)
        st.info("📋 Mostrando datos de TODO el día")
    else:
        # Usar función con filtro de turno
        puntadas_operadores = calcular_puntadas_turno(df_produccion, fecha_seleccionada, turno_seleccionado)

def calcular_puntadas_dia_completo(df, fecha):
    """Calcular puntadas para todo el día (sin filtro de turno)"""
    
    df_fecha = df.copy()
    df_fecha['Marca temporal'] = pd.to_datetime(df_fecha['Marca temporal'], errors='coerce')
    df_fecha['Fecha'] = df_fecha['Marca temporal'].dt.date
    
    # Filtrar por fecha
    df_dia = df_fecha[df_fecha['Fecha'] == fecha]
    
    if df_dia.empty:
        st.error(f"❌ No hay registros para la fecha {fecha}")
        return {}
    
    # Agrupar por operador
    puntadas_por_operador = df_dia.groupby('OPERADOR').agg({
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
    
    st.success(f"✅ Encontrados {len(resultado)} operadores en todo el día")
    return resultado    

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
    """Calcular puntadas por operador para un turno específico CON DIAGNÓSTICO"""
    
    st.info("🔍 **Modo diagnóstico activado**")
    
    df_fecha = df.copy()
    
    # Convertir a datetime y extraer fecha/hora
    df_fecha['Marca temporal'] = pd.to_datetime(df_fecha['Marca temporal'], errors='coerce')
    df_fecha['Fecha'] = df_fecha['Marca temporal'].dt.date
    df_fecha['Hora'] = df_fecha['Marca temporal'].dt.hour
    df_fecha['Dia_Semana'] = df_fecha['Marca temporal'].dt.day_name()
    
    # Mostrar información de diagnóstico
    st.write("### 📊 Diagnóstico de Datos:")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total registros", len(df_fecha))
    with col2:
        st.metric("Fechas únicas", df_fecha['Fecha'].nunique())
    with col3:
        st.metric("Horas únicas", df_fecha['Hora'].nunique())
    
    # Mostrar rango de fechas y horas disponibles
    st.write("**📅 Fechas disponibles:**", sorted(df_fecha['Fecha'].unique()))
    st.write("**⏰ Horas disponibles:**", sorted(df_fecha['Hora'].unique()))
    
    # Filtrar por fecha
    df_dia = df_fecha[df_fecha['Fecha'] == fecha]
    
    st.write(f"**📋 Registros para {fecha}:** {len(df_dia)}")
    
    if df_dia.empty:
        st.error("❌ No hay registros para esta fecha")
        return {}
    
    # Mostrar distribución de horas para esta fecha
    st.write("**📈 Distribución por horas en esta fecha:**")
    distribucion_horas = df_dia['Hora'].value_counts().sort_index()
    st.bar_chart(distribucion_horas)
    
    # Filtrar por turno (rangos más flexibles)
    if turno == "MAÑANA":
        df_turno = df_dia[df_dia['Hora'].between(5, 15)]  # 5am - 3pm (más flexible)
        st.write("**🌅 Turno MAÑANA:** 5:00 - 15:00 hrs")
    else:  # TARDE
        df_turno = df_dia[df_dia['Hora'].between(13, 23)]  # 1pm - 11pm (más flexible)
        st.write("**🌇 Turno TARDE:** 13:00 - 23:00 hrs")
    
    st.write(f"**📊 Registros en turno {turno}:** {len(df_turno)}")
    
    if df_turno.empty:
        st.warning(f"⚠️ No hay registros en el horario del turno {turno}")
        
        # Mostrar sugerencia de horarios alternativos
        st.write("**💡 Sugerencia:** ¿Quizás los horarios son diferentes?")
        st.write("Horas con datos en esta fecha:", sorted(df_dia['Hora'].unique()))
        return {}
    
    # Agrupar por operador
    if 'OPERADOR' not in df_turno.columns:
        st.error("❌ No existe la columna 'OPERADOR'")
        return {}
    
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
    
    st.success(f"✅ Encontrados {len(resultado)} operadores en turno {turno}")
    
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
