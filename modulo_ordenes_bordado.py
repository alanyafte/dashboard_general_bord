import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

# ============================================================================
# CONFIGURACIÓN DE GOOGLE SHEETS (igual que antes)
# ============================================================================
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
                if 'Estado' not in df.columns:
                    st.warning("⚠️ Columna 'Estado' no encontrada.")
                    df['Estado'] = 'Pendiente'
                return df
            else:
                return pd.DataFrame()
        except Exception as e:
            st.error(f"❌ Error obteniendo órdenes: {e}")
            return pd.DataFrame()
    return pd.DataFrame()

# ============================================================================
# FUNCIONES DEL KANBAN MEJORADO
# ============================================================================
def get_color_estado(estado):
    """Devuelve colores para cada estado"""
    estado = str(estado).strip()
    colores = {
        'Pendiente Confirmación': {'color': '#FF6B6B', 'bg_header': '#FFE8E8', 'bg_card': '#FFFFFF', 'border': '#FF6B6B'},
        'Pendiente': {'color': '#D63031', 'bg_header': '#FFE8E8', 'bg_card': '#FFFFFF', 'border': '#D63031'},
        'Confirmado': {'color': '#00A085', 'bg_header': '#E8F6F3', 'bg_card': '#FFFFFF', 'border': '#00A085'},
        'En Proceso': {'color': '#E17055', 'bg_header': '#FFF8E1', 'bg_card': '#FFFFFF', 'border': '#E17055'},
        'Completado': {'color': '#00A085', 'bg_header': '#E8F6F3', 'bg_card': '#FFFFFF', 'border': '#00A085'},
        'Listo': {'color': '#198754', 'bg_header': '#E8F5E9', 'bg_card': '#FFFFFF', 'border': '#198754'},
        'Entregado': {'color': '#6F42C1', 'bg_header': '#F3E8FF', 'bg_card': '#FFFFFF', 'border': '#6F42C1'}
    }
    return colores.get(estado, {'color': '#6C757D', 'bg_header': '#F8F9FA', 'bg_card': '#FFFFFF', 'border': '#6C757D'})

def crear_tarjeta_mejorada(orden):
    """Crea una tarjeta mejorada con mejor separación visual"""
    estado = orden.get('Estado', 'Pendiente')
    color_estado = get_color_estado(estado)
    
    # Crear un contenedor con borde y sombra
    with st.container():
        # Encabezado de la tarjeta (color diferente)
        st.markdown(
            f"""<div style='
                background-color: {color_estado['bg_header']};
                padding: 12px;
                border-radius: 8px 8px 0 0;
                border-top: 3px solid {color_estado['border']};
                margin: 0 -1rem;
            '>
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div style="font-weight: bold; font-size: 14px;">📦 {orden.get('Número Orden', 'N/A')}</div>
                    <div style='
                        background-color: {color_estado['color']};
                        color: white;
                        padding: 4px 12px;
                        border-radius: 20px;
                        font-size: 11px;
                        font-weight: bold;
                    '>{estado}</div>
                </div>
            </div>""", 
            unsafe_allow_html=True
        )
        
        # Cuerpo de la tarjeta (fondo blanco)
        st.markdown(
            f"""<div style='
                background-color: {color_estado['bg_card']};
                padding: 15px;
                margin: 0 -1rem;
                border-radius: 0 0 8px 8px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.05);
                margin-bottom: 15px;
            '>""", 
            unsafe_allow_html=True
        )
        
        # Cliente (destacado)
        st.markdown(f"**{orden.get('Cliente', 'Cliente no especificado')}**")
        
        # Información en 2 columnas
        col_info1, col_info2 = st.columns(2)
        with col_info1:
            vendedor = orden.get('Vendedor', 'No especificado')
            st.caption(f"👤 **{vendedor[:20]}{'...' if len(vendedor) > 20 else ''}**")
        with col_info2:
            fecha = orden.get('Fecha Entrega', 'No especificada')
            st.caption(f"📅 **{str(fecha)[:10] if fecha else 'Sin fecha'}**")
        
        # Diseño
        diseño = orden.get('Nombre Diseño', 'Sin nombre')
        st.caption(f"🎨 **Diseño:** {diseño[:30]}{'...' if len(diseño) > 30 else ''}")
        
        # Prendas (en un recuadro)
        prendas = orden.get('Prendas', 'No especificadas')
        st.markdown(
            f"""<div style='
                background-color: #F8F9FA;
                padding: 8px;
                border-radius: 6px;
                margin-top: 10px;
                text-align: center;
                border-left: 3px solid {color_estado['border']};
            '>
                <span style='font-size: 12px; color: #495057; font-weight: bold;'>{prendas}</span>
            </div>""", 
            unsafe_allow_html=True
        )
        
        st.markdown("</div>", unsafe_allow_html=True)

def mostrar_kanban_mejorado(df_filtrado):
    """Muestra el tablero Kanban mejorado"""
    st.subheader("🎯 Tablero Kanban de Producción")
    
    # Estadísticas rápidas
    col_stats1, col_stats2, col_stats3, col_stats4 = st.columns(4)
    
    with col_stats1:
        total = len(df_filtrado)
        st.metric("Total Órdenes", total)
    
    with col_stats2:
        pendientes = len(df_filtrado[df_filtrado['Estado'] == 'Pendiente'])
        st.metric("Pendientes", pendientes, delta=None)
    
    with col_stats3:
        en_proceso = len(df_filtrado[df_filtrado['Estado'] == 'En Proceso'])
        st.metric("En Proceso", en_proceso, delta=None)
    
    with col_stats4:
        completadas = len(df_filtrado[df_filtrado['Estado'].isin(['Completado', 'Listo', 'Entregado'])])
        st.metric("Completadas", completadas, delta=None)
    
    st.markdown("---")
    
    # Definir estados para el Kanban (basado en datos reales)
    estados_posibles = ['Pendiente', 'En Proceso', 'Completado', 'Listo', 'Entregado']
    estados_existentes = [e for e in estados_posibles if e in df_filtrado['Estado'].unique()]
    
    # Si no hay estados de la lista, usar los que existen
    if not estados_existentes:
        estados_existentes = df_filtrado['Estado'].unique().tolist()
    
    # Limitar a máximo 4 columnas
    estados_existentes = estados_existentes[:4]
    
    # Crear columnas del Kanban
    columns = st.columns(len(estados_existentes))
    
    for i, estado in enumerate(estados_existentes):
        with columns[i]:
            color_estado = get_color_estado(estado)
            
            # Header de la columna
            st.markdown(
                f"""<div style='
                    background-color: {color_estado['bg_header']};
                    color: {color_estado['color']};
                    padding: 15px;
                    border-radius: 10px;
                    text-align: center;
                    margin-bottom: 20px;
                    font-weight: bold;
                    font-size: 16px;
                    border-bottom: 3px solid {color_estado['border']};
                '>
                    {estado} ({len(df_filtrado[df_filtrado['Estado'] == estado])})
                </div>""", 
                unsafe_allow_html=True
            )
            
            # Órdenes en este estado
            ordenes_estado = df_filtrado[df_filtrado['Estado'] == estado]
            
            if ordenes_estado.empty:
                st.markdown(
                    """<div style='
                        background-color: #F8F9FA;
                        padding: 30px;
                        border-radius: 8px;
                        text-align: center;
                        color: #6C757D;
                        font-style: italic;
                        border: 2px dashed #DEE2E6;
                        margin: 10px 0;
                    '>
                        No hay órdenes
                    </div>""", 
                    unsafe_allow_html=True
                )
            else:
                # Ordenar por fecha de entrega si existe
                if 'Fecha Entrega' in ordenes_estado.columns:
                    try:
                        ordenes_estado = ordenes_estado.sort_values('Fecha Entrega', na_position='last')
                    except:
                        pass
                
                # Espaciado entre tarjetas
                st.markdown("<div style='margin-bottom: 20px;'></div>", unsafe_allow_html=True)
                
                for _, orden in ordenes_estado.iterrows():
                    crear_tarjeta_mejorada(orden)
                    # Espaciado entre tarjetas
                    st.markdown("<div style='margin-bottom: 15px;'></div>", unsafe_allow_html=True)

# ============================================================================
# DASHBOARD PRINCIPAL - SOLO KANBAN MEJORADO
# ============================================================================
def mostrar_dashboard_ordenes():
    """Dashboard principal - Solo Kanban mejorado"""
    
    st.title("🏭 Tablero de Producción - Órdenes de Bordado")
    
    # Información de conexión (colapsada)
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
    
    # Filtros globales
    st.subheader("🎛️ Filtros")
    col_filtro1, col_filtro2, col_filtro3 = st.columns(3)
    
    with col_filtro1:
        estados = ["Todos"] + list(df_ordenes['Estado'].unique())
        estado_filtro = st.selectbox("Por Estado:", estados, key="filtro_estado")
    
    with col_filtro2:
        vendedores = ["Todos"] + list(df_ordenes['Vendedor'].dropna().unique())
        vendedor_filtro = st.selectbox("Por Vendedor:", vendedores, key="filtro_vendedor")
    
    with col_filtro3:
        clientes = ["Todos"] + list(df_ordenes['Cliente'].dropna().unique())
        cliente_filtro = st.selectbox("Por Cliente:", clientes, key="filtro_cliente")
    
    # Aplicar filtros
    df_filtrado = df_ordenes.copy()
    if estado_filtro != "Todos":
        df_filtrado = df_filtrado[df_filtrado['Estado'] == estado_filtro]
    if vendedor_filtro != "Todos":
        df_filtrado = df_filtrado[df_filtrado['Vendedor'] == vendedor_filtro]
    if cliente_filtro != "Todos":
        df_filtrado = df_filtrado[df_filtrado['Cliente'] == cliente_filtro]
    
    # Mostrar Kanban mejorado
    mostrar_kanban_mejorado(df_filtrado)
    
    # Botón de acción
    st.markdown("---")
    col_btn1, col_btn2 = st.columns([3, 1])
    
    with col_btn1:
        st.info(f"📊 Mostrando {len(df_filtrado)} de {len(df_ordenes)} órdenes")
    
    with col_btn2:
        if st.button("🔄 Actualizar Datos", use_container_width=True):
            st.rerun()
