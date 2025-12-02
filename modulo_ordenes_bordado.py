import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

# Configuración para Google Sheets
SCOPE = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

def conectar_google_sheets():
    """Conectar con Google Sheets usando tus credenciales existentes"""
    try:
        creds_dict = {
            "type": st.secrets["gservice_account"]["type"],
            "project_id": st.secrets["gservice_account"]["project_id"],
            "private_key_id": st.secrets["gservice_account"]["private_key_id"],
            "private_key": st.secrets["gservice_account"]["private_key"].replace('\\n', '\n'),
            "client_email": st.secrets["gservice_account"]["client_email"],
            "client_id": st.secrets["gservice_account"]["client_id"],
            "auth_uri": st.secrets["gservice_account"]["auth_uri"],
            "token_uri": st.secrets["gservice_account"]["token_uri"]
        }
        
        creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPE)
        client = gspread.authorize(creds)
        
        sheet_id = st.secrets["gsheets"]["ordenes_bordado_sheet_id"]
        spreadsheet = client.open_by_key(sheet_id)
        sheet = spreadsheet.worksheet("OrdenesBordado")
        
        return sheet
        
    except Exception as e:
        st.error(f"❌ Error conectando con Google Sheets: {e}")
        return None

def obtener_ordenes():
    """Obtener todas las órdenes del Google Sheets"""
    sheet = conectar_google_sheets()
    if sheet:
        try:
            data = sheet.get_all_records()
            if data:
                df = pd.DataFrame(data)
                # Verificar que las columnas necesarias existen
                if 'Estado Producción' not in df.columns:
                    df['Estado Producción'] = 'Pendiente'
                if 'Estado Aprobación' not in df.columns:
                    df['Estado Aprobación'] = 'Pendiente'
                
                # CREAR ESTADO COMBINADO PARA EL KANBAN
                df['Estado_Kanban'] = df.apply(crear_estado_combinado, axis=1)
                
                return df
            else:
                return pd.DataFrame()
        except Exception as e:
            st.error(f"❌ Error obteniendo órdenes: {e}")
            return pd.DataFrame()
    return pd.DataFrame()

def crear_estado_combinado(row):
    """Crear un estado combinado basado en ambas columnas"""
    aprobacion = str(row.get('Estado Aprobación', '')).strip().lower()
    produccion = str(row.get('Estado Producción', '')).strip().lower()
    
    # Lógica para determinar el estado del Kanban
    if 'entregado' in produccion:
        return 'Entregado'
    elif 'completado' in produccion:
        return 'Completado'
    elif 'proceso' in produccion or 'producción' in produccion:
        return 'En Proceso'
    elif 'espera' in produccion:
        return 'En Espera'
    elif 'aprobado' in aprobacion or 'confirmado' in aprobacion:
        # Si está aprobado pero no ha empezado producción
        return 'Pendiente de Producción'
    elif 'rechazado' in aprobacion:
        return 'Rechazado'
    elif 'revisión' in aprobacion or 'pendiente' in aprobacion:
        return 'Pendiente de Aprobación'
    else:
        return 'Pendiente'

def get_color_estado_kanban(estado):
    """Devuelve colores para cada estado del KANBAN COMBINADO"""
    colores = {
        'Pendiente de Aprobación': {'color': '#95A5A6', 'bg_color': '#F2F4F4', 'icon': '⏳'},
        'Rechazado': {'color': '#E74C3C', 'bg_color': '#FDEDEC', 'icon': '❌'},
        'Pendiente de Producción': {'color': '#F39C12', 'bg_color': '#FEF9E7', 'icon': '📋'},
        'En Espera': {'color': '#E17055', 'bg_color': '#FFF8E1', 'icon': '⏱️'},
        'En Proceso': {'color': '#3498DB', 'bg_color': '#EBF5FB', 'icon': '⚙️'},
        'Completado': {'color': '#27AE60', 'bg_color': '#E8F8F5', 'icon': '✅'},
        'Entregado': {'color': '#6F42C1', 'bg_color': '#F3E8FF', 'icon': '📦'}
    }
    return colores.get(estado, {'color': '#95A5A6', 'bg_color': '#F2F4F4', 'icon': '❓'})

def crear_tarjeta_streamlit(orden):
    """Crea una tarjeta usando solo componentes de Streamlit"""
    estado_kanban = orden.get('Estado_Kanban', 'Pendiente de Aprobación')
    color_estado = get_color_estado_kanban(estado_kanban)
    
    # Información de ambos estados para mostrar en tooltip
    estado_aprobacion = orden.get('Estado Aprobación', 'No especificado')
    estado_produccion = orden.get('Estado Producción', 'No especificado')
    
    # Crear un contenedor con estilo
    with st.container():
        # Header de la tarjeta
        col1, col2 = st.columns([3, 1])
        with col1:
            st.markdown(f"**{color_estado['icon']} {orden['Número Orden']}**")
            st.markdown(f"### {orden['Cliente']}")
        with col2:
            st.markdown(
                f"<div style='background-color: {color_estado['color']}; color: white; padding: 4px 8px; border-radius: 20px; text-align: center; font-size: 10px; font-weight: bold;'>{estado_kanban}</div>", 
                unsafe_allow_html=True
            )
            # Info pequeña de ambos estados
            st.caption(f"✓ {estado_aprobacion}")
            st.caption(f"🛠️ {estado_produccion}")
        
        # Información de la orden
        col_info1, col_info2 = st.columns(2)
        with col_info1:
            st.caption(f"👤 **Vendedor:** {orden.get('Vendedor', 'No especificado')}")
            st.caption(f"🎨 **Diseño:** {orden.get('Nombre del Diseño', 'Sin nombre')}")
        with col_info2:
            st.caption(f"📅 **Entrega:** {orden.get('Fecha Compromiso', 'No especificada')}")
        
        # Prendas y cantidad
        prendas_info = f"{orden.get('Cantidad Total', '0')} unidades - {orden.get('Prendas', 'No especificadas')}"
        st.markdown(
            f"<div style='background-color: {color_estado['bg_color']}; padding: 8px; border-radius: 6px; border-left: 3px solid {color_estado['color']}; margin: 8px 0;'>"
            f"<span style='font-size: 11px; color: #636E72; font-weight: bold;'>{prendas_info}</span>"
            f"</div>", 
            unsafe_allow_html=True
        )
        
        st.markdown("---")

def mostrar_kanban_visual(df_filtrado):
    """Muestra el tablero Kanban con estados combinados"""
    st.subheader("🎯 Tablero Kanban - Flujo Completo")
    
    # Definir el orden del flujo en el Kanban
    estados_kanban = [
        'Pendiente de Aprobación',
        'Rechazado',
        'Pendiente de Producción', 
        'En Espera',
        'En Proceso',
        'Completado',
        'Entregado'
    ]
    
    # Filtrar solo los estados que existen en los datos
    estados_existentes = [e for e in estados_kanban if e in df_filtrado['Estado_Kanban'].unique()]
    
    # Estadísticas rápidas
    st.write("### 📊 Resumen por Estado")
    cols_stats = st.columns(min(len(estados_existentes), 7))
    
    for i, estado in enumerate(estados_existentes[:7]):
        with cols_stats[i]:
            count = len(df_filtrado[df_filtrado['Estado_Kanban'] == estado])
            color_estado = get_color_estado_kanban(estado)
            st.metric(
                label=estado.split()[-1],  # Mostrar solo la última palabra
                value=count,
                delta=None
            )
    
    st.markdown("---")
    
    # Crear columnas del Kanban
    columns = st.columns(len(estados_existentes))
    
    for i, estado in enumerate(estados_existentes):
        with columns[i]:
            color_estado = get_color_estado_kanban(estado)
            
            # Header de la columna
            st.markdown(
                f"<div style='background-color: {color_estado['color']}; color: white; padding: 12px; border-radius: 8px; text-align: center; margin-bottom: 15px; font-weight: bold; font-size: 16px;'>"
                f"{color_estado['icon']} {estado} ({len(df_filtrado[df_filtrado['Estado_Kanban'] == estado])})"
                f"</div>", 
                unsafe_allow_html=True
            )
            
            # Órdenes en este estado
            ordenes_estado = df_filtrado[df_filtrado['Estado_Kanban'] == estado]
            
            if ordenes_estado.empty:
                st.info("No hay órdenes")
            else:
                # Ordenar por fecha de compromiso
                if 'Fecha Compromiso' in ordenes_estado.columns:
                    try:
                        ordenes_estado = ordenes_estado.sort_values('Fecha Compromiso', na_position='last')
                    except:
                        pass
                
                for _, orden in ordenes_estado.iterrows():
                    crear_tarjeta_streamlit(orden)

def mostrar_dashboard_ordenes():
    """Dashboard principal de gestión de órdenes SOLO CON KANBAN"""
    
    st.title("🏭 Tablero de Producción - Órdenes de Bordado")
    
    # Información de conexión
    with st.expander("🔗 Estado de Conexión", expanded=False):
        if "gsheets" in st.secrets and "ordenes_bordado_sheet_id" in st.secrets["gsheets"]:
            st.success("✅ Conectado a Google Sheets")
        else:
            st.error("❌ Sheet ID no configurado")
    
    # Cargar órdenes
    with st.spinner("🔄 Cargando órdenes desde Google Sheets..."):
        df_ordenes = obtener_ordenes()
    
    if df_ordenes.empty:
        st.info("📭 No hay órdenes registradas aún.")
        return
    
    # Filtros globales
    st.subheader("🎛️ Filtros")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        # Filtro por estado del Kanban
        estados_kanban = ["Todos"] + sorted(df_ordenes['Estado_Kanban'].dropna().unique())
        estado_filtro = st.selectbox("Por Estado Kanban:", estados_kanban, key="filtro_estado_kanban")
    
    with col2:
        vendedores = ["Todos"] + sorted(df_ordenes['Vendedor'].dropna().unique())
        vendedor_filtro = st.selectbox("Por Vendedor:", vendedores, key="filtro_vendedor")
    
    with col3:
        clientes = ["Todos"] + sorted(df_ordenes['Cliente'].dropna().unique())
        cliente_filtro = st.selectbox("Por Cliente:", clientes, key="filtro_cliente")
    
    # Aplicar filtros
    df_filtrado = df_ordenes.copy()
    if estado_filtro != "Todos":
        df_filtrado = df_filtrado[df_filtrado['Estado_Kanban'] == estado_filtro]
    if vendedor_filtro != "Todos":
        df_filtrado = df_filtrado[df_filtrado['Vendedor'] == vendedor_filtro]
    if cliente_filtro != "Todos":
        df_filtrado = df_filtrado[df_filtrado['Cliente'] == cliente_filtro]
    
    # Mostrar Kanban
    mostrar_kanban_visual(df_filtrado)
    
    # Botones de acción
    st.markdown("---")
    col_btn1, col_btn2 = st.columns([3, 1])
    
    with col_btn1:
        st.info(f"📊 Mostrando {len(df_filtrado)} de {len(df_ordenes)} órdenes")
    
    with col_btn2:
        if st.button("🔄 Actualizar Datos", use_container_width=True):
            st.rerun()
