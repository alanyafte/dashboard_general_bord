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
                # Normalizar nombres de estado para el Kanban
                if 'Estado' in df.columns:
                    df['Estado_Kanban'] = df['Estado'].apply(normalizar_estado_kanban)
                return df
            else:
                return pd.DataFrame()
        except Exception as e:
            st.error(f"❌ Error obteniendo órdenes: {e}")
            return pd.DataFrame()
    return pd.DataFrame()

# ============================================================================
# FUNCIONES AUXILIARES PARA KANBAN
# ============================================================================
def normalizar_estado_kanban(estado_original):
    """Normalizar estados a las 4 categorías del Kanban"""
    if pd.isna(estado_original):
        return 'Pendiente'
    
    estado = str(estado_original).strip().lower()
    
    # Mapeo de estados
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

def get_config_estado(estado):
    """Configuración completa para cada estado del Kanban"""
    configs = {
        'Pendiente': {
            'color': '#6C757D',
            'bg_color': '#F8F9FA',
            'icon': '⏱️',
            'border': '3px solid #6C757D'
        },
        'En Proceso': {
            'color': '#0D6EFD',
            'bg_color': '#E8F4FD',
            'icon': '⚙️',
            'border': '3px solid #0D6EFD'
        },
        'Listo': {
            'color': '#198754',
            'bg_color': '#E8F5E9',
            'icon': '✅',
            'border': '3px solid #198754'
        },
        'Entregado': {
            'color': '#6F42C1',
            'bg_color': '#F3E8FF',
            'icon': '📦',
            'border': '3px solid #6F42C1'
        }
    }
    return configs.get(estado, configs['Pendiente'])

# ============================================================================
# CSS PARA EL KANBAN - CORREGIDO
# ============================================================================
def inject_kanban_css():
    """Inyectar CSS correctamente para Streamlit"""
    css = """
    <style>
    /* Contenedor principal del Kanban */
    .kanban-container {
        display: flex !important;
        gap: 20px !important;
        padding: 20px 0 !important;
        overflow-x: auto !important;
        min-height: calc(100vh - 200px) !important;
        background-color: #f0f2f6 !important;
        border-radius: 10px !important;
    }
    
    /* Columnas del Kanban */
    .kanban-column {
        flex: 1 !important;
        min-width: 320px !important;
        background: #F8F9FA !important;
        border-radius: 12px !important;
        padding: 0 !important;
        display: flex !important;
        flex-direction: column !important;
        max-height: 75vh !important;
        overflow-y: auto !important;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1) !important;
    }
    
    /* Cabecera de columna */
    .column-header {
        padding: 15px 20px !important;
        border-bottom: 1px solid #DEE2E6 !important;
        background: white !important;
        border-radius: 12px 12px 0 0 !important;
        position: sticky !important;
        top: 0 !important;
        z-index: 10 !important;
    }
    
    .column-title {
        font-size: 16px !important;
        font-weight: 600 !important;
        display: flex !important;
        justify-content: space-between !important;
        align-items: center !important;
        margin-bottom: 8px !important;
    }
    
    .column-count {
        background: #E9ECEF !important;
        color: #495057 !important;
        padding: 4px 12px !important;
        border-radius: 20px !important;
        font-size: 14px !important;
        font-weight: 600 !important;
    }
    
    .column-subtitle {
        font-size: 12px !important;
        color: #6C757D !important;
        margin-top: 4px !important;
    }
    
    /* Contenedor de tarjetas */
    .cards-container {
        padding: 15px !important;
        flex-grow: 1 !important;
    }
    
    /* Tarjetas individuales */
    .kanban-card {
        background: white !important;
        border-radius: 10px !important;
        padding: 15px !important;
        margin-bottom: 15px !important;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08) !important;
        transition: all 0.3s ease !important;
        cursor: default !important;
        height: 180px !important;
        display: flex !important;
        flex-direction: column !important;
        justify-content: space-between !important;
        border-top: 3px solid !important;
    }
    
    .kanban-card:hover {
        transform: translateY(-3px) !important;
        box-shadow: 0 5px 15px rgba(0,0,0,0.1) !important;
    }
    
    /* Estilos para tarjetas vacías */
    .empty-column {
        text-align: center !important;
        padding: 40px 20px !important;
        color: #ADB5BD !important;
        font-style: italic !important;
        background: white !important;
        border-radius: 8px !important;
        border: 2px dashed #DEE2E6 !important;
        margin: 10px !important;
    }
    
    /* Scrollbar styling */
    .kanban-column::-webkit-scrollbar {
        width: 6px !important;
    }
    
    .kanban-column::-webkit-scrollbar-track {
        background: #F1F3F5 !important;
        border-radius: 10px !important;
    }
    
    .kanban-column::-webkit-scrollbar-thumb {
        background: #ADB5BD !important;
        border-radius: 10px !important;
    }
    
    .kanban-column::-webkit-scrollbar-thumb:hover {
        background: #6C757D !important;
    }
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)

# ============================================================================
# FUNCIONES PARA CREAR TARJETAS Y KANBAN
# ============================================================================
def crear_tarjeta_kanban(orden):
    """Crear tarjeta HTML estilizada para el Kanban"""
    config = get_config_estado(orden['Estado_Kanban'])
    
    # Formatear fecha si existe
    fecha_entrega = orden.get('Fecha Entrega', '')
    fecha_str = 'Sin fecha'
    if pd.notna(fecha_entrega) and fecha_entrega != '':
        try:
            if isinstance(fecha_entrega, datetime):
                fecha_str = fecha_entrega.strftime('%d/%m')
            elif isinstance(fecha_entrega, str) and len(fecha_entrega) >= 10:
                fecha_str = fecha_entrega[:10]
            else:
                fecha_str = str(fecha_entrega)
        except:
            fecha_str = str(fecha_entrega)
    
    # Truncar texto largo
    cliente = str(orden.get('Cliente', 'Cliente no especificado'))[:30]
    cliente = cliente + "..." if len(str(orden.get('Cliente', ''))) > 30 else cliente
    
    diseño = str(orden.get('Nombre Diseño', 'Sin nombre'))[:40]
    diseño = diseño + "..." if len(str(orden.get('Nombre Diseño', ''))) > 40 else diseño
    
    vendedor = str(orden.get('Vendedor', 'Sin vendedor'))[:20]
    
    # Crear HTML de la tarjeta
    html = f"""
    <div class="kanban-card" style="border-top-color: {config['color'].replace('3px solid ', '')};">
        <!-- Header -->
        <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 10px;">
            <div>
                <div style="font-family: 'Courier New', monospace; font-weight: 700; font-size: 14px; color: {config['color']}; margin-bottom: 4px;">
                    {config['icon']} {orden.get('Número Orden', 'N/A')}
                </div>
                <div style="font-size: 12px; color: #6C757D; background: {config['bg_color']}; padding: 2px 8px; border-radius: 12px; display: inline-block;">
                    {orden['Estado_Kanban']}
                </div>
            </div>
            <div style="font-size: 12px; color: #495057; background: #F1F3F5; padding: 4px 8px; border-radius: 6px; font-weight: 500;">
                {fecha_str}
            </div>
        </div>
        
        <!-- Cliente -->
        <div style="font-weight: 600; font-size: 16px; color: #212529; margin: 5px 0; line-height: 1.3;">
            {cliente}
        </div>
        
        <!-- Diseño -->
        <div style="font-size: 13px; color: #495057; margin: 8px 0; line-height: 1.4;">
            <span style="color: #868E96; font-weight: 500;">Diseño:</span><br>
            {diseño}
        </div>
        
        <!-- Footer -->
        <div style="display: flex; justify-content: space-between; align-items: center; margin-top: auto; padding-top: 10px; border-top: 1px solid #E9ECEF;">
            <div style="font-size: 11px; color: #868E96;">
                {vendedor}
            </div>
            <div style="font-size: 11px; color: #868E96;">
                {orden.get('Prendas', '0')} prendas
            </div>
        </div>
    </div>
    """
    return html

def mostrar_kanban_horizontal(df):
    """Mostrar el Kanban mejorado con diseño horizontal"""
    
    # Asegurarnos de que tenemos la columna Estado_Kanban
    if 'Estado_Kanban' not in df.columns:
        df['Estado_Kanban'] = df['Estado'].apply(normalizar_estado_kanban)
    
    # Definir el orden de las columnas
    estados_orden = ['Pendiente', 'En Proceso', 'Listo', 'Entregado']
    
    # Inyectar CSS primero
    inject_kanban_css()
    
    # Crear columnas usando st.columns() de Streamlit para mejor control
    st.markdown('<div class="kanban-container">', unsafe_allow_html=True)
    
    # Usar st.columns para crear el layout horizontal
    columns = st.columns(4)
    
    for idx, estado in enumerate(estados_orden):
        with columns[idx]:
            # Filtrar órdenes para este estado
            ordenes_estado = df[df['Estado_Kanban'] == estado]
            config = get_config_estado(estado)
            
            # Crear la cabecera de la columna
            col_html_header = f"""
            <div class="column-header" style="border-top: {config['border']};">
                <div class="column-title">
                    <span style="color: {config['color']};">
                        {config['icon']} {estado}
                    </span>
                    <span class="column-count">{len(ordenes_estado)}</span>
                </div>
                <div class="column-subtitle">
                    {len(ordenes_estado)} orden{'' if len(ordenes_estado) == 1 else 'es'}
                </div>
            </div>
            """
            
            st.markdown(col_html_header, unsafe_allow_html=True)
            
            # Contenedor para las tarjetas
            st.markdown('<div class="cards-container">', unsafe_allow_html=True)
            
            if ordenes_estado.empty:
                st.markdown('<div class="empty-column">Sin órdenes en este estado</div>', unsafe_allow_html=True)
            else:
                # Ordenar por fecha de entrega (más urgente primero)
                if 'Fecha Entrega' in ordenes_estado.columns:
                    try:
                        ordenes_estado = ordenes_estado.sort_values('Fecha Entrega', na_position='last')
                    except:
                        pass
                
                # Mostrar cada tarjeta
                for _, orden in ordenes_estado.iterrows():
                    tarjeta_html = crear_tarjeta_kanban(orden)
                    st.markdown(tarjeta_html, unsafe_allow_html=True)
            
            st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)

# ============================================================================
# FUNCIONES ORIGINALES (MANTENIDAS)
# ============================================================================
def get_color_estado(estado):
    """Devuelve colores para cada estado (para compatibilidad)"""
    colores = {
        'Pendiente Confirmación': {'color': '#FF6B6B', 'bg_color': '#FFE8E8'},
        'Pendiente': {'color': '#D63031', 'bg_color': '#FFE8E8'},
        'Confirmado': {'color': '#00A085', 'bg_color': '#E8F6F3'},
        'En Proceso': {'color': '#E17055', 'bg_color': '#FFF8E1'},
        'Completado': {'color': '#00A085', 'bg_color': '#E8F6F3'}
    }
    return colores.get(estado, colores['Pendiente'])

def mostrar_kanban_visual(df_filtrado):
    """Versión original del Kanban - mantenida por compatibilidad"""
    st.subheader("🎯 Tablero Kanban Visual")
    
    # Estadísticas rápidas
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        total = len(df_filtrado)
        st.metric("Total", total)
    with col2:
        pendientes = len(df_filtrado[df_filtrado['Estado'] == 'Pendiente'])
        st.metric("Pendientes", pendientes)
    with col3:
        en_proceso = len(df_filtrado[df_filtrado['Estado'] == 'En Proceso'])
        st.metric("En Proceso", en_proceso)
    with col4:
        completadas = len(df_filtrado[df_filtrado['Estado'] == 'Completado'])
        st.metric("Completadas", completadas)
    
    # Definir columnas del Kanban
    estados_kanban = ['Pendiente', 'En Proceso', 'Completado']
    columns = st.columns(len(estados_kanban))
    
    for i, estado in enumerate(estados_kanban):
        with columns[i]:
            color_estado = get_color_estado(estado)
            
            # Header de la columna
            st.markdown(
                f"<div style='background-color: {color_estado['color']}; color: white; padding: 12px; border-radius: 8px; text-align: center; margin-bottom: 15px; font-weight: bold; font-size: 16px;'>"
                f"{estado} ({len(df_filtrado[df_filtrado['Estado'] == estado])})"
                f"</div>", 
                unsafe_allow_html=True
            )
            
            # Ordenes en este estado
            ordenes_estado = df_filtrado[df_filtrado['Estado'] == estado]

def mostrar_vista_tabla(df_filtrado):
    """Muestra la vista de tabla tradicional"""
    st.subheader("📋 Vista de Tabla Detallada")
    
    columnas_mostrar = [
        'Número Orden', 'Cliente', 'Vendedor', 'Fecha Entrega', 
        'Estado', 'Prendas', 'Nombre Diseño', 'Medidas Bordado', 'Tipo Hilos'
    ]
    
    columnas_existentes = [col for col in columnas_mostrar if col in df_filtrado.columns]
    df_vista = df_filtrado[columnas_existentes]
    
    st.dataframe(
        df_vista,
        use_container_width=True,
        hide_index=True
    )

def mostrar_estadisticas(df_filtrado):
    """Muestra gráficas y estadísticas avanzadas"""
    st.subheader("📊 Estadísticas Avanzadas")
    
    col1, col2 = st.columns(2)
    
    with col1:
        conteo_estados = df_filtrado['Estado'].value_counts()
        if not conteo_estados.empty:
            fig_estados = px.pie(
                values=conteo_estados.values,
                names=conteo_estados.index,
                title="Distribución de Estados",
                color=conteo_estados.index,
                color_discrete_map={
                    'Pendiente': '#FF6B6B',
                    'En Proceso': '#FDCB6E',
                    'Completado': '#00B894'
                }
            )
            st.plotly_chart(fig_estados, use_container_width=True)
    
    with col2:
        if 'Vendedor' in df_filtrado.columns:
            conteo_vendedores = df_filtrado['Vendedor'].value_counts().head(10)
            if not conteo_vendedores.empty:
                fig_vendedores = px.bar(
                    x=conteo_vendedores.values,
                    y=conteo_vendedores.index,
                    orientation='h',
                    title="Órdenes por Vendedor (Top 10)",
                    color=conteo_vendedores.values,
                    color_continuous_scale='Blues'
                )
                fig_vendedores.update_layout(showlegend=False)
                st.plotly_chart(fig_vendedores, use_container_width=True)

# ============================================================================
# DASHBOARD PRINCIPAL - VERSIÓN SIMPLIFICADA
# ============================================================================
def mostrar_dashboard_ordenes():
    """Dashboard principal enfocado en el Kanban mejorado"""
    
    st.title("🏭 Tablero de Producción - Órdenes de Bordado")
    
    # Estado de conexión
    with st.expander("🔗 Estado del Sistema", expanded=False):
        if "gsheets" in st.secrets and "ordenes_bordado_sheet_id" in st.secrets["gsheets"]:
            st.success("✅ Conectado a Google Sheets")
        else:
            st.error("❌ Configuración incompleta")
    
    # Cargar órdenes
    with st.spinner("🔄 Cargando órdenes desde Google Sheets..."):
        df_ordenes = obtener_ordenes()
    
    if df_ordenes.empty:
        st.info("📭 No hay órdenes registradas aún.")
        return
    
    # Resumen de estadísticas
    st.subheader("📊 Resumen General")
    
    # Asegurar que tenemos Estado_Kanban
    if 'Estado_Kanban' not in df_ordenes.columns:
        df_ordenes['Estado_Kanban'] = df_ordenes['Estado'].apply(normalizar_estado_kanban)
    
    # Mostrar métricas por estado
    cols = st.columns(4)
    estados = ['Pendiente', 'En Proceso', 'Listo', 'Entregado']
    
    for idx, estado in enumerate(estados):
        with cols[idx]:
            count = len(df_ordenes[df_ordenes['Estado_Kanban'] == estado])
            config = get_config_estado(estado)
            
            # Usar st.metric para mejor integración con Streamlit
            st.metric(
                label=f"{config['icon']} {estado}",
                value=count,
                delta=None
            )
    
    # Filtros simples
    st.markdown("---")
    st.subheader("🎛️ Filtros")
    
    col1, col2 = st.columns(2)
    with col1:
        # Filtro por estado
        estados_disponibles = ["Todos"] + list(df_ordenes['Estado_Kanban'].unique())
        filtro_estado = st.selectbox(
            "Filtrar por estado:",
            estados_disponibles,
            key="filtro_estado_kanban"
        )
    
    with col2:
        # Filtro por vendedor
        vendedores = ["Todos"] + list(df_ordenes['Vendedor'].dropna().unique())
        filtro_vendedor = st.selectbox(
            "Filtrar por vendedor:",
            vendedores,
            key="filtro_vendedor_kanban"
        )
    
    # Aplicar filtros
    df_filtrado = df_ordenes.copy()
    if filtro_estado != "Todos":
        df_filtrado = df_filtrado[df_filtrado['Estado_Kanban'] == filtro_estado]
    if filtro_vendedor != "Todos":
        df_filtrado = df_filtrado[df_filtrado['Vendedor'] == filtro_vendedor]
    
    # Mostrar Kanban mejorado
    st.markdown("---")
    st.markdown(f"### 🎯 Tablero Kanban ({len(df_filtrado)} órdenes)")
    
    # Mostrar el Kanban horizontal
    mostrar_kanban_horizontal(df_filtrado)
    
    # Opciones adicionales
    st.markdown("---")
    col_btn1, col_btn2, col_btn3 = st.columns(3)
    
    with col_btn1:
        if st.button("🔄 Actualizar Datos", use_container_width=True):
            st.rerun()
    
    with col_btn2:
        with st.expander("📋 Ver Datos en Tabla", expanded=False):
            columnas_simples = ['Número Orden', 'Cliente', 'Estado_Kanban', 'Fecha Entrega', 'Vendedor', 'Prendas']
            columnas_existentes = [c for c in columnas_simples if c in df_ordenes.columns]
            st.dataframe(df_ordenes[columnas_existentes], use_container_width=True)
    
    with col_btn3:
        if st.button("📊 Mostrar Estadísticas", use_container_width=True):
            with st.expander("📈 Estadísticas Detalladas", expanded=True):
                mostrar_estadisticas(df_filtrado)
