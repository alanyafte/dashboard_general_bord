import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import datetime

# Configuración para Google Sheets
SCOPE = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

def conectar_google_sheets():
    """Conectar con Google Sheets usando credenciales"""
    try:
        # Cargar credenciales desde secrets de Streamlit
        creds_dict = st.secrets["gcp_service_account"]
        creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPE)
        client = gspread.authorize(creds)
        
        # Abrir la hoja de cálculo (ajusta el nombre según tu Sheets)
        spreadsheet = client.open("Sistema de Ordenes de Bordado")
        sheet = spreadsheet.worksheet("OrdenesBordado")
        return sheet
    except Exception as e:
        st.error(f"Error conectando con Google Sheets: {e}")
        return None

def obtener_ordenes():
    """Obtener todas las órdenes del Google Sheets"""
    sheet = conectar_google_sheets()
    if sheet:
        try:
            # Obtener todos los datos
            data = sheet.get_all_records()
            if data:
                df = pd.DataFrame(data)
                return df
            else:
                return pd.DataFrame()
        except Exception as e:
            st.error(f"Error obteniendo órdenes: {e}")
            return pd.DataFrame()
    return pd.DataFrame()

def actualizar_estado_orden(numero_orden, nuevo_estado):
    """Actualizar el estado de una orden específica"""
    sheet = conectar_google_sheets()
    if sheet:
        try:
            # Encontrar la fila por número de orden
            data = sheet.get_all_records()
            for i, row in enumerate(data, start=2):  # start=2 porque la fila 1 son headers
                if row['Número Orden'] == numero_orden:
                    # Actualizar estado (columna 25 - índice 24 en base 0)
                    sheet.update_cell(i, 25, nuevo_estado)
                    st.success(f"✅ Estado de {numero_orden} actualizado a: {nuevo_estado}")
                    return True
            st.error(f"❌ No se encontró la orden: {numero_orden}")
            return False
        except Exception as e:
            st.error(f"Error actualizando orden: {e}")
            return False

def mostrar_dashboard_ordenes():
    """Dashboard principal de gestión de órdenes"""
    st.title("🏭 Gestión de Órdenes de Bordado")
    
    # Cargar órdenes
    with st.spinner("Cargando órdenes..."):
        df_ordenes = obtener_ordenes()
    
    if df_ordenes.empty:
        st.info("📭 No hay órdenes registradas aún.")
        return
    
    # Filtros
    col1, col2, col3 = st.columns(3)
    with col1:
        estados = ["Todos"] + list(df_ordenes['Estado'].unique())
        estado_filtro = st.selectbox("Filtrar por Estado:", estados)
    
    with col2:
        vendedores = ["Todos"] + list(df_ordenes['Vendedor'].unique())
        vendedor_filtro = st.selectbox("Filtrar por Vendedor:", vendedores)
    
    with col3:
        clientes = ["Todos"] + list(df_ordenes['Cliente'].unique())
        cliente_filtro = st.selectbox("Filtrar por Cliente:", clientes)
    
    # Aplicar filtros
    df_filtrado = df_ordenes.copy()
    if estado_filtro != "Todos":
        df_filtrado = df_filtrado[df_filtrado['Estado'] == estado_filtro]
    if vendedor_filtro != "Todos":
        df_filtrado = df_filtrado[df_filtrado['Vendedor'] == vendedor_filtro]
    if cliente_filtro != "Todos":
        df_filtrado = df_filtrado[df_filtrado['Cliente'] == cliente_filtro]
    
    # Mostrar estadísticas rápidas
    st.subheader("📊 Resumen")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Órdenes", len(df_filtrado))
    with col2:
        pendientes = len(df_filtrado[df_filtrado['Estado'] == 'Pendiente'])
        st.metric("Pendientes", pendientes)
    with col3:
        en_proceso = len(df_filtrado[df_filtrado['Estado'] == 'En Proceso'])
        st.metric("En Proceso", en_proceso)
    with col4:
        completadas = len(df_filtrado[df_filtrado['Estado'] == 'Completado'])
        st.metric("Completadas", completadas)
    
    # Vista Kanban
    st.subheader("📋 Tablero Kanban")
    
    # Definir columnas del Kanban
    estados_kanban = ['Pendiente', 'En Proceso', 'Completado']
    columns = st.columns(len(estados_kanban))
    
    for i, estado in enumerate(estados_kanban):
        with columns[i]:
            st.subheader(f"{estado}")
            ordenes_estado = df_filtrado[df_filtrado['Estado'] == estado]
            
            for _, orden in ordenes_estado.iterrows():
                with st.expander(f"📦 {orden['Número Orden']} - {orden['Cliente']}"):
                    st.write(f"**Vendedor:** {orden['Vendedor']}")
                    st.write(f"**Diseño:** {orden['Nombre Diseño']}")
                    st.write(f"**Entrega:** {orden['Fecha Entrega']}")
                    st.write(f"**Prendas:** {orden['Prendas']}")
                    
                    # Selector para cambiar estado
                    nuevo_estado = st.selectbox(
                        "Cambiar Estado:",
                        estados_kanban,
                        index=estados_kanban.index(orden['Estado']),
                        key=f"estado_{orden['Número Orden']}"
                    )
                    
                    if nuevo_estado != orden['Estado']:
                        if st.button("💾 Actualizar", key=f"btn_{orden['Número Orden']}"):
                            if actualizar_estado_orden(orden['Número Orden'], nuevo_estado):
                                st.rerun()
    
    # Vista de tabla detallada
    st.subheader("📋 Vista de Tabla Detallada")
    
    # Seleccionar columnas para mostrar
    columnas_mostrar = [
        'Número Orden', 'Cliente', 'Vendedor', 'Fecha Entrega', 
        'Estado', 'Prendas', 'Nombre Diseño', 'Medidas Bordado'
    ]
    
    df_vista = df_filtrado[columnas_mostrar]
    st.dataframe(
        df_vista,
        use_container_width=True,
        hide_index=True
    )
    
    # Botones de acción rápida
    st.subheader("🚀 Acciones Rápidas")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("🔄 Actualizar Datos", use_container_width=True):
            st.rerun()
    
    with col2:
        if st.button("📊 Exportar a Excel", use_container_width=True):
            # Código para exportar
            st.info("⏳ Funcionalidad de exportación en desarrollo")
    
    with col3:
        if st.button("🎯 Nueva Orden", use_container_width=True):
            st.info("🔗 Usa el formulario web para crear nuevas órdenes")

def mostrar_formulario_rapido():
    """Formulario rápido para crear órdenes (opcional)"""
    st.subheader("📝 Crear Orden Rápida")
    
    with st.form("orden_rapida"):
        col1, col2 = st.columns(2)
        
        with col1:
            cliente = st.text_input("Cliente*")
            vendedor = st.text_input("Vendedor*")
            fecha_entrega = st.date_input("Fecha Entrega*")
        
        with col2:
            prendas = st.text_area("Prendas*")
            nombre_diseno = st.text_input("Nombre del Diseño*")
        
        medidas_bordado = st.text_input("Medidas del Bordado*")
        tipo_hilos = st.text_input("Tipo de Hilos*")
        posicion_bordado = st.selectbox(
            "Posición del Bordado*",
            ["Frente Izquierdo", "Frente Derecho", "Centro Pecho", "Espalda Completa", "Manga Izquierda", "Manga Derecha", "Otra"]
        )
        
        if st.form_submit_button("💾 Crear Orden"):
            if cliente and vendedor and prendas and nombre_diseno:
                st.success("✅ Orden creada (esta es una demo - integra con Google Sheets)")
            else:
                st.error("❌ Completa todos los campos obligatorios")
