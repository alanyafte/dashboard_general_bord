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
# KANBAN MEJORADO (VERSIÓN HORIZONTAL)
# ============================================================================
def crear_tarjeta_kanban_html(orden):
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
    <div class="kanban-card" style="
        background: white;
        border-radius: 10px;
        padding: 15px;
        margin-bottom: 15px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        border-top: {config['border']};
        transition: all 0.3s ease;
        cursor: default;
        height: 180px;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
    ">
        <!-- Header -->
        <div style="
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            margin-bottom: 10px;
        ">
            <div>
                <div style="
                    font-family: 'Courier New', monospace;
                    font-weight: 700;
                    font-size: 14px;
                    color: {config['color']};
                    margin-bottom: 4px;
                ">
                    {config['icon']} {orden.get('Número Orden', 'N/A')}
                </div>
                <div style="
                    font-size: 12px;
                    color: #6C757D;
                    background: {config['bg_color']};
                    padding: 2px 8px;
                    border-radius: 12px;
                    display: inline-block;
                ">
                    {orden['Estado_Kanban']}
                </div>
            </div>
            <div style="
                font-size: 12px;
                color: #495057;
                background: #F1F3F5;
                padding: 4px 8px;
                border-radius: 6px;
                font-weight: 500;
            ">
                {fecha_str}
            </div>
        </div>
        
        <!-- Cliente -->
        <div style="
            font-weight: 600;
            font-size: 16px;
            color: #212529;
            margin: 5px 0;
            line-height: 1.3;
        ">
            {cliente}
        </div>
        
        <!-- Diseño -->
        <div style="
            font-size: 13px;
            color: #495057;
            margin: 8px 0;
            line-height: 1.4;
        ">
            <span style="color: #868E96; font-weight: 500;">Diseño:</span><br>
            {diseño}
        </div>
        
        <!-- Footer -->
        <div style="
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-top: auto;
            padding-top: 10px;
            border-top: 1px solid #E9ECEF;
        ">
            <div style="
                font-size: 11px;
                color: #868E96;
            ">
                {vendedor}
            </div>
            <div style="
                font-size: 11px;
                color: #868E96;
            ">
                {orden.get('Prendas', '0')} prendas
            </div>
        </div>
    </div>
    """
    return html

def mostrar_kanban_mejorado(df):
    """Mostrar el Kanban mejorado con diseño horizontal"""
    
    # Asegurarnos de que tenemos la columna Estado_Kanban
    if 'Estado_Kanban' not in df.columns:
        df['Estado_Kanban'] = df['Estado'].apply(normalizar_estado_kanban)
    
    # Definir el orden de las columnas
    estados_orden = ['Pendiente', 'En Proceso', 'Listo', 'Entregado']
    
    # CSS personalizado para el Kanban
    kanban_css = """
    <style>
    .kanban-container {
        display: flex;
        gap: 20px;
        padding: 20px 0;
        overflow-x: auto;
        min-height: calc(100vh - 200px);
    }
    
    .kanban-column {
        flex: 1;
        min-width: 300px;
        background: #F8F9FA;
        border-radius: 12px;
        padding: 0;
        display: flex;
        flex-direction: column;
        max-height: calc(100vh - 250px);
        overflow-y: auto;
    }
    
    .column-header {
        padding: 15px;
        border-bottom: 1px solid #DEE2E6;
        background: white;
        border-radius: 12px 12px 0 0;
        position: sticky;
        top: 0;
        z-index: 10;
    }
    
    .column-title {
        font-size: 16px;
        font-weight: 600;
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 8px;
    }
    
    .column-count {
        background: #E9ECEF;
        color: #495057;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 14px;
        font-weight: 600;
    }
    
    .column-subtitle {
        font-size: 12px;
        color: #6C757D;
        margin-top: 4px;
    }
    
    .cards-container {
        padding: 15px;
        flex-grow: 1;
    }
    
    .kanban-card:hover {
        transform: translateY(-3px);
        box-shadow: 0 5px 15px rgba(0,0,0,0.1);
    }
    
    /* Scrollbar styling */
    .kanban-column::-webkit-scrollbar {
        width: 6px;
    }
    
    .kanban-column::-webkit-scrollbar-track {
        background: #F1F3F5;
        border-radius: 10px;
    }
    
    .kanban-column::-webkit-scrollbar-thumb {
        background: #ADB5BD;
        border-radius: 10px;
    }
    
    .kanban-column::-webkit-scrollbar-thumb:hover {
        background: #6C757D;
    }
    </style>
    """
    
    # Inyectar CSS
    st.markdown(kanban_css, unsafe_allow_html=True)
    
    # Contenedor principal del Kanban
    st.markdown('<div class="kanban-container">', unsafe_allow_html=True)
    
    for estado in estados_orden:
        # Filtrar órdenes para este estado
        ordenes_estado = df[df['Estado_Kanban'] == estado]
        config = get_config_estado(estado)
        
        # Crear HTML para la columna
        col_html = f"""
        <div class="kanban-column">
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
            <div class="cards-container">
        """
        
        # Agregar tarjetas
        if ordenes_estado.empty:
            col_html += f"""
            <div style="
                text-align: center;
                padding: 40px 20px;
                color: #ADB5BD;
                font-style: italic;
                background: white;
                border-radius: 8px;
                border: 2px dashed #DEE2E6;
            ">
                Sin órdenes en este estado
            </div>
            """
        else:
            # Ordenar por fecha de entrega (más urgente primero)
            if 'Fecha Entrega' in ordenes_estado.columns:
                try:
                    ordenes_estado = ordenes_estado.sort_values('Fecha Entrega', na_position='last')
                except:
                    pass
            
            for _, orden in ordenes_estado.iterrows():
                col_html += crear_tarjeta_kanban_html(orden)
        
        col_html += """
            </div>
        </div>
        """
        
        st.markdown(col_html, unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)

# ============================================================================
# FUNCIONES ORIGINALES (MANTENIDAS POR COMPATIBILIDAD)
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

def crear_tarjeta_streamlit(orden):
    """Crea una tarjeta usando solo componentes de Streamlit (compatibilidad)"""
    color_estado = get_color_estado(orden['Estado'])
    
    with st.container():
        col1, col2 = st.columns([3, 1])
        with col1:
            st.markdown(f"**📦 {orden['Número Orden']}**")
            st.markdown(f"### {orden['Cliente']}")
        with col2:
            st.markdown(
                f"<div style='background-color: {color_estado['color']}; color: white; padding: 4px 8px; border-radius: 20px; text-align: center; font-size: 10px; font-weight: bold;'>{orden['Estado']}</div>", 
                unsafe_allow_html=True
            )
        
        col_info1, col_info2 = st.columns(2)
        with col_info1:
            st.caption(f"👤 **Vendedor:** {orden.get('Vendedor', 'No especificado')}")
            st.caption(f"🎨 **Diseño:** {orden.get('Nombre Diseño', 'Sin nombre')}")
        with col_info2:
            st.caption(f"📅 **Entrega:** {orden.get('Fecha Entrega', 'No especificada')}")
        
        st.markdown(
            f"<div style='background-color: {color_estado['bg_color']}; padding: 8px; border-radius: 6px; border-left: 3px solid {color_estado['color']}; margin: 8px 0;'>"
            f"<span style='font-size: 11px; color: #636E72; font-weight: bold;'>{orden.get('Prendas', 'No especificadas')}</span>"
            f"</div>", 
            unsafe_allow_html=True
        )
        
        st.markdown("---")

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
# DASHBOARD PRINCIPAL
# ============================================================================
def mostrar_dashboard_ordenes():
    """Dashboard principal de gestión de órdenes con pestañas"""
    
    st.title("🏭 Gestión de Órdenes de Bordado")
    
    # Información de conexión
    with st.expander("🔗 Estado de Conexión", expanded=False):
        if "gsheets" in st.secrets and "ordenes_bordado_sheet_id" in st.secrets["gsheets"]:
            st.success("✅ Sheet ID configurado correctamente")
            st.write(f"**Service Account:** {st.secrets['gservice_account']['client_email']}")
            st.write(f"**Sheet ID:** {st.secrets['gsheets']['ordenes_bordado_sheet_id']}")
        else:
            st.error("❌ Sheet ID no configurado en secrets")
    
    # Cargar órdenes
    with st.spinner("🔄 Cargando órdenes desde Google Sheets..."):
        df_ordenes = obtener_ordenes()
    
    if df_ordenes.empty:
        st.info("📭 No hay órdenes registradas aún.")
        st.info("💡 Usa el formulario web para crear la primera orden.")
        return
    
    # Filtros globales
    st.subheader("🎛️ Filtros Globales")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        estados = ["Todos"] + list(df_ordenes['Estado'].unique())
        estado_filtro = st.selectbox("Filtrar por Estado:", estados, key="filtro_estado")
    
    with col2:
        vendedores = ["Todos"] + list(df_ordenes['Vendedor'].dropna().unique())
        vendedor_filtro = st.selectbox("Filtrar por Vendedor:", vendedores, key="filtro_vendedor")
    
    with col3:
        clientes = ["Todos"] + list(df_ordenes['Cliente'].dropna().unique())
        cliente_filtro = st.selectbox("Filtrar por Cliente:", clientes, key="filtro_cliente")
    
    # Aplicar filtros
    df_filtrado = df_ordenes.copy()
    if estado_filtro != "Todos":
        df_filtrado = df_filtrado[df_filtrado['Estado'] == estado_filtro]
    if vendedor_filtro != "Todos":
        df_filtrado = df_filtrado[df_filtrado['Vendedor'] == vendedor_filtro]
    if cliente_filtro != "Todos":
        df_filtrado = df_filtrado[df_filtrado['Cliente'] == cliente_filtro]
    
    # OPCIÓN 1: Solo Kanban Mejorado (recomendado)
    st.markdown("---")
    st.markdown(f"### 🎯 Tablero Kanban ({len(df_filtrado)} órdenes)")
    mostrar_kanban_mejorado(df_filtrado)
    
    # OPCIÓN 2: Pestañas con todas las vistas (si quieres mantener compatibilidad)
    # tab1, tab2, tab3 = st.tabs(["🎯 Kanban Mejorado", "📋 Vista Tabla", "📊 Estadísticas"])
    
    # with tab1:
    #     mostrar_kanban_mejorado(df_filtrado)
    
    # with tab2:
    #     mostrar_vista_tabla(df_filtrado)
    
    # with tab3:
    #     mostrar_estadisticas(df_filtrado)
    
    # Botones de acción rápida
    st.markdown("---")
    col_btn1, col_btn2, col_btn3 = st.columns(3)
    
    with col_btn1:
        if st.button("🔄 Actualizar Datos", use_container_width=True):
            st.rerun()
    
    with col_btn2:
        # Mostrar vista simple de datos
        with st.expander("📋 Ver Datos en Tabla", expanded=False):
            columnas_simples = ['Número Orden', 'Cliente', 'Estado', 'Fecha Entrega', 'Vendedor']
            columnas_existentes = [c for c in columnas_simples if c in df_ordenes.columns]
            st.dataframe(df_ordenes[columnas_existentes].head(20), use_container_width=True)
    
    with col_btn3:
        if st.button("📊 Ver Estadísticas", use_container_width=True):
            st.session_state.mostrar_estadisticas = True
        
        if st.session_state.get('mostrar_estadisticas', False):
            mostrar_estadisticas(df_filtrado)
