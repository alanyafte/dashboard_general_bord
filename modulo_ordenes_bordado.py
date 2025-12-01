import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import plotly.express as px

# ============================================================================
# CONFIGURACIÓN DE GOOGLE SHEETS
# ============================================================================
SCOPE = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

def conectar_google_sheets():
    """Conectar con Google Sheets usando credenciales existentes"""
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
                return df
            else:
                return pd.DataFrame()
        except Exception as e:
            st.error(f"❌ Error obteniendo órdenes: {e}")
            return pd.DataFrame()
    return pd.DataFrame()

# ============================================================================
# FUNCIONES PARA KANBAN MEJORADO CON STREAMLIT NATIVO
# ============================================================================
def normalizar_estado_kanban(estado_original):
    """Normalizar estados a las 4 categorías del Kanban"""
    if pd.isna(estado_original):
        return 'Pendiente'
    
    estado = str(estado_original).strip().lower()
    
    if 'pendiente' in estado:
        return 'Pendiente'
    elif 'proceso' in estado or 'producción' in estado or 'produccion' in estado:
        return 'En Proceso'
    elif 'listo' in estado or 'completado' in estado or 'terminado' in estado:
        return 'Listo'
    elif 'entregado' in estado or 'finalizado' in estado:
        return 'Entregado'
    else:
        return 'Pendiente'

def get_color_estado(estado):
    """Obtener configuración de colores para cada estado"""
    colores = {
        'Pendiente': {
            'color': '#6C757D',
            'bg_color': '#F8F9FA',
            'border_color': '#6C757D',
            'icon': '⏱️'
        },
        'En Proceso': {
            'color': '#0D6EFD',
            'bg_color': '#E8F4FD',
            'border_color': '#0D6EFD',
            'icon': '⚙️'
        },
        'Listo': {
            'color': '#198754',
            'bg_color': '#E8F5E9',
            'border_color': '#198754',
            'icon': '✅'
        },
        'Entregado': {
            'color': '#6F42C1',
            'bg_color': '#F3E8FF',
            'border_color': '#6F42C1',
            'icon': '📦'
        }
    }
    return colores.get(estado, colores['Pendiente'])

def crear_tarjeta_orden(orden, estado_kanban):
    """Crear una tarjeta de orden usando solo Streamlit nativo"""
    config = get_color_estado(estado_kanban)
    
    # Formatear fecha
    fecha_entrega = orden.get('Fecha Entrega', '')
    fecha_str = 'Sin fecha'
    if pd.notna(fecha_entrega) and fecha_entrega != '':
        try:
            if isinstance(fecha_entrega, datetime):
                fecha_str = fecha_entrega.strftime('%d/%m')
            elif isinstance(fecha_entrega, str):
                fecha_str = fecha_entrega[:10] if len(fecha_entrega) >= 10 else fecha_entrega
            else:
                fecha_str = str(fecha_entrega)
        except:
            fecha_str = str(fecha_entrega)
    
    # Crear contenedor con borde
    with st.container():
        # Borde superior de la tarjeta
        st.markdown(
            f"""<div style='height: 4px; background-color: {config['border_color']}; 
                 border-radius: 2px 2px 0 0; margin: 0 -1rem;'></div>""", 
            unsafe_allow_html=True
        )
        
        # Contenido de la tarjeta
        col_header = st.columns([3, 1])
        with col_header[0]:
            # Número de orden con icono
            st.markdown(f"**{config['icon']} {orden.get('Número Orden', 'N/A')}**")
            # Estado
            st.markdown(
                f"""<div style='background-color: {config['bg_color']}; color: {config['color']}; 
                     padding: 2px 8px; border-radius: 12px; display: inline-block; font-size: 0.8em;'>
                     {estado_kanban}</div>""", 
                unsafe_allow_html=True
            )
        with col_header[1]:
            # Fecha
            st.caption(fecha_str)
        
        # Separador
        st.markdown("---")
        
        # Información principal
        st.markdown(f"**{orden.get('Cliente', 'Cliente no especificado')}**")
        
        # Diseño
        diseño = orden.get('Nombre Diseño', 'Sin nombre')
        if len(str(diseño)) > 40:
            diseño = str(diseño)[:40] + "..."
        st.caption(f"**Diseño:** {diseño}")
        
        # Información adicional
        col_footer = st.columns(2)
        with col_footer[0]:
            vendedor = orden.get('Vendedor', 'Sin vendedor')
            if len(str(vendedor)) > 15:
                vendedor = str(vendedor)[:15] + "..."
            st.caption(f"👤 {vendedor}")
        with col_footer[1]:
            prendas = orden.get('Prendas', '0')
            st.caption(f"👕 {prendas} prendas")
    
    # Espaciado entre tarjetas
    st.markdown("<div style='margin-bottom: 15px;'></div>", unsafe_allow_html=True)

def mostrar_kanban_streamlit(df):
    """Mostrar Kanban usando solo componentes nativos de Streamlit"""
    
    # Agregar columna Estado_Kanban si no existe
    if 'Estado' in df.columns:
        df['Estado_Kanban'] = df['Estado'].apply(normalizar_estado_kanban)
    elif 'Estado_Kanban' not in df.columns:
        df['Estado_Kanban'] = 'Pendiente'
    
    # Estados en orden
    estados = ['Pendiente', 'En Proceso', 'Listo', 'Entregado']
    
    # CSS mínimo pero efectivo
    st.markdown("""
    <style>
    div[data-testid="stVerticalBlock"] > div[data-testid="stVerticalBlock"] {
        background-color: #f8f9fa;
        padding: 10px;
        border-radius: 10px;
        margin-bottom: 20px;
        border-left: 4px solid;
    }
    
    div.stColumn {
        background-color: white;
        padding: 15px;
        border-radius: 10px;
        margin: 5px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    
    .kanban-header {
        font-size: 1.1em;
        font-weight: bold;
        padding: 10px;
        border-radius: 8px;
        margin-bottom: 15px;
        text-align: center;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Crear 4 columnas horizontales
    cols = st.columns(4)
    
    for idx, estado in enumerate(estados):
        with cols[idx]:
            # Filtrar órdenes para este estado
            ordenes_estado = df[df['Estado_Kanban'] == estado]
            config = get_color_estado(estado)
            
            # Cabecera de la columna
            st.markdown(
                f"""<div class='kanban-header' style='background-color: {config['bg_color']}; 
                     color: {config['color']}; border-bottom: 3px solid {config['border_color']};'>
                     {config['icon']} {estado} ({len(ordenes_estado)})</div>""", 
                unsafe_allow_html=True
            )
            
            # Mostrar tarjetas
            if ordenes_estado.empty:
                st.info("No hay órdenes", icon="📭")
            else:
                # Ordenar por fecha si existe
                if 'Fecha Entrega' in ordenes_estado.columns:
                    try:
                        ordenes_estado = ordenes_estado.sort_values('Fecha Entrega', na_position='last')
                    except:
                        pass
                
                # Mostrar cada tarjeta
                for _, orden in ordenes_estado.iterrows():
                    crear_tarjeta_orden(orden, estado)

def mostrar_resumen_estadisticas(df):
    """Mostrar resumen estadístico"""
    if 'Estado_Kanban' not in df.columns:
        df['Estado_Kanban'] = df['Estado'].apply(normalizar_estado_kanban) if 'Estado' in df.columns else 'Pendiente'
    
    col1, col2, col3, col4 = st.columns(4)
    
    estados = ['Pendiente', 'En Proceso', 'Listo', 'Entregado']
    configs = [get_color_estado(e) for e in estados]
    counts = [len(df[df['Estado_Kanban'] == e]) for e in estados]
    
    for i, (estado, config, count) in enumerate(zip(estados, configs, counts)):
        with [col1, col2, col3, col4][i]:
            # Usar st.metric con HTML personalizado
            st.markdown(
                f"""
                <div style='
                    background-color: {config['bg_color']};
                    padding: 15px;
                    border-radius: 10px;
                    border-top: 3px solid {config['border_color']};
                    text-align: center;
                '>
                    <div style='font-size: 24px; font-weight: bold; color: {config['color']};'>
                        {count}
                    </div>
                    <div style='font-size: 14px; color: {config['color']};'>
                        {config['icon']} {estado}
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )

# ============================================================================
# DASHBOARD PRINCIPAL
# ============================================================================
def mostrar_dashboard_ordenes():
    """Dashboard principal enfocado en visualización Kanban"""
    
    st.title("🏭 Tablero de Producción")
    st.markdown("---")
    
    # Estado de conexión
    with st.expander("🔗 Estado de Conexión", expanded=False):
        if "gsheets" in st.secrets and "ordenes_bordado_sheet_id" in st.secrets["gsheets"]:
            st.success("✅ Conectado a Google Sheets")
        else:
            st.error("❌ Configuración incompleta")
    
    # Cargar órdenes
    with st.spinner("🔄 Cargando órdenes..."):
        df_ordenes = obtener_ordenes()
    
    if df_ordenes.empty:
        st.info("📭 No hay órdenes registradas aún.")
        return
    
    # Mostrar resumen
    st.subheader("📊 Resumen por Estado")
    mostrar_resumen_estadisticas(df_ordenes)
    
    # Filtros
    st.markdown("---")
    st.subheader("🎛️ Filtros")
    
    col_f1, col_f2 = st.columns(2)
    with col_f1:
        # Preparar estados para filtro
        if 'Estado' in df_ordenes.columns:
            df_ordenes['Estado_Kanban_temp'] = df_ordenes['Estado'].apply(normalizar_estado_kanban)
        elif 'Estado_Kanban' not in df_ordenes.columns:
            df_ordenes['Estado_Kanban_temp'] = 'Pendiente'
        else:
            df_ordenes['Estado_Kanban_temp'] = df_ordenes['Estado_Kanban']
        
        estados_unicos = ["Todos"] + sorted(df_ordenes['Estado_Kanban_temp'].unique().tolist())
        filtro_estado = st.selectbox(
            "Filtrar por estado:",
            estados_unicos,
            key="filtro_estado_main"
        )
    
    with col_f2:
        # Filtro por vendedor
        vendedores = ["Todos"] + sorted(df_ordenes['Vendedor'].dropna().unique().tolist())
        filtro_vendedor = st.selectbox(
            "Filtrar por vendedor:",
            vendedores,
            key="filtro_vendedor_main"
        )
    
    # Aplicar filtros
    df_filtrado = df_ordenes.copy()
    
    if filtro_estado != "Todos":
        if 'Estado_Kanban_temp' in df_filtrado.columns:
            df_filtrado = df_filtrado[df_filtrado['Estado_Kanban_temp'] == filtro_estado]
    
    if filtro_vendedor != "Todos":
        df_filtrado = df_filtrado[df_filtrado['Vendedor'] == filtro_vendedor]
    
    # Limpiar columna temporal
    if 'Estado_Kanban_temp' in df_filtrado.columns:
        df_filtrado = df_filtrado.drop(columns=['Estado_Kanban_temp'])
    
    # Mostrar Kanban
    st.markdown("---")
    st.subheader(f"🎯 Tablero Kanban ({len(df_filtrado)} órdenes)")
    
    mostrar_kanban_streamlit(df_filtrado)
    
    # Botones de acción
    st.markdown("---")
    
    col_b1, col_b2, col_b3 = st.columns(3)
    
    with col_b1:
        if st.button("🔄 Actualizar Datos", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
    
    with col_b2:
        if st.button("📋 Ver en Tabla", use_container_width=True):
            with st.expander("📋 Vista de Tabla", expanded=True):
                columnas = ['Número Orden', 'Cliente', 'Vendedor', 'Fecha Entrega', 'Estado']
                columnas_existentes = [c for c in columnas if c in df_ordenes.columns]
                if columnas_existentes:
                    st.dataframe(df_ordenes[columnas_existentes], use_container_width=True)
    
    with col_b3:
        if st.button("ℹ️ Información", use_container_width=True):
            st.info("""
            **Información del Tablero:**
            
            • **Pendiente** ⏱️: Órdenes por iniciar
            • **En Proceso** ⚙️: Órdenes en producción
            • **Listo** ✅: Órdenes terminadas
            • **Entregado** 📦: Órdenes finalizadas
            
            Los datos se actualizan automáticamente desde Google Sheets.
            """)
