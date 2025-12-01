import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

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
# KANBAN CORREGIDO - ENFOQUE DIRECTO
# ============================================================================
def normalizar_estado(estado):
    """Normalizar el estado a 4 categorías"""
    if pd.isna(estado):
        return 'Pendiente'
    
    estado_str = str(estado).lower().strip()
    
    if 'pendiente' in estado_str:
        return 'Pendiente'
    elif 'proceso' in estado_str or 'producción' in estado_str or 'produccion' in estado_str:
        return 'En Proceso'
    elif 'listo' in estado_str or 'completado' in estado_str or 'terminado' in estado_str:
        return 'Listo'
    elif 'entregado' in estado_str or 'finalizado' in estado_str:
        return 'Entregado'
    else:
        return 'Pendiente'

def mostrar_kanban_corregido(df):
    """Kanban con HTML bien formado"""
    
    # Agregar estado normalizado
    df['Estado_Kanban'] = df['Estado'].apply(normalizar_estado) if 'Estado' in df.columns else 'Pendiente'
    
    # Estados en orden
    estados = ['Pendiente', 'En Proceso', 'Listo', 'Entregado']
    
    # CSS en bloque separado
    css_html = """
    <style>
    /* Contenedor principal horizontal */
    .kanban-horizontal {
        display: flex;
        gap: 15px;
        overflow-x: auto;
        padding: 10px 0;
        margin-bottom: 20px;
    }
    
    /* Columna individual */
    .kanban-col {
        flex: 1;
        min-width: 300px;
        background: #f8f9fa;
        border-radius: 8px;
        padding: 0;
    }
    
    /* Cabecera de columna */
    .col-header {
        padding: 12px 15px;
        font-weight: bold;
        border-bottom: 2px solid;
        border-radius: 8px 8px 0 0;
        margin-bottom: 10px;
        font-size: 16px;
    }
    
    /* Tarjeta de orden */
    .orden-card {
        background: white;
        margin: 10px 15px;
        padding: 15px;
        border-radius: 6px;
        border-left: 4px solid;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        margin-bottom: 12px;
    }
    
    /* Colores por estado */
    .pendiente { border-left-color: #6c757d; }
    .en-proceso { border-left-color: #0d6efd; }
    .listo { border-left-color: #198754; }
    .entregado { border-left-color: #6f42c1; }
    
    .header-pendiente { background: #f8f9fa; color: #6c757d; border-color: #6c757d; }
    .header-proceso { background: #e8f4fd; color: #0d6efd; border-color: #0d6efd; }
    .header-listo { background: #e8f5e9; color: #198754; border-color: #198754; }
    .header-entregado { background: #f3e8ff; color: #6f42c1; border-color: #6f42c1; }
    </style>
    """
    
    # Inyectar CSS primero
    st.markdown(css_html, unsafe_allow_html=True)
    
    # Construir el HTML completo en una sola variable
    kanban_html = '<div class="kanban-horizontal">'
    
    for estado in estados:
        # Filtrar órdenes para este estado
        ordenes = df[df['Estado_Kanban'] == estado]
        
        # Determinar clase CSS
        estado_class = estado.lower().replace(' ', '-')
        header_class = f"header-{estado_class}"
        
        # Crear columna
        kanban_html += f'''
        <div class="kanban-col">
            <div class="col-header {header_class}">
                {estado} ({len(ordenes)})
            </div>
        '''
        
        # Si no hay órdenes
        if ordenes.empty:
            kanban_html += '''
            <div style="text-align: center; padding: 30px 20px; color: #999; font-style: italic;">
                Sin órdenes
            </div>
            '''
        else:
            # Ordenar por fecha si existe
            if 'Fecha Entrega' in ordenes.columns:
                try:
                    ordenes = ordenes.sort_values('Fecha Entrega', na_position='last')
                except:
                    pass
            
            # Agregar cada tarjeta
            for _, orden in ordenes.iterrows():
                # Formatear información
                num_orden = orden.get('Número Orden', 'N/A')
                cliente = str(orden.get('Cliente', 'Sin cliente'))[:25]
                if len(str(orden.get('Cliente', ''))) > 25:
                    cliente += "..."
                
                diseño = str(orden.get('Nombre Diseño', 'Sin diseño'))[:30]
                if len(str(orden.get('Nombre Diseño', ''))) > 30:
                    diseño += "..."
                
                fecha = orden.get('Fecha Entrega', '')
                fecha_str = 'Sin fecha'
                if pd.notna(fecha) and fecha != '':
                    try:
                        if isinstance(fecha, datetime):
                            fecha_str = fecha.strftime('%d/%m')
                        else:
                            fecha_str = str(fecha)[:10]
                    except:
                        fecha_str = str(fecha)
                
                vendedor = str(orden.get('Vendedor', ''))[:15]
                if vendedor == '':
                    vendedor = 'No asignado'
                
                prendas = orden.get('Prendas', '0')
                
                # Crear tarjeta
                kanban_html += f'''
                <div class="orden-card {estado_class}">
                    <div style="display: flex; justify-content: space-between; align-items: start;">
                        <div style="font-weight: bold; color: #333;">{num_orden}</div>
                        <div style="font-size: 12px; color: #666; background: #f1f3f5; padding: 2px 8px; border-radius: 10px;">{fecha_str}</div>
                    </div>
                    
                    <div style="font-size: 14px; font-weight: 600; margin: 8px 0; color: #212529;">{cliente}</div>
                    
                    <div style="font-size: 12px; color: #495057; margin-bottom: 8px;">
                        <strong>Diseño:</strong> {diseño}
                    </div>
                    
                    <div style="display: flex; justify-content: space-between; font-size: 11px; color: #6c757d;">
                        <div>👤 {vendedor}</div>
                        <div>👕 {prendas} prendas</div>
                    </div>
                </div>
                '''
        
        kanban_html += '</div>'
    
    kanban_html += '</div>'
    
    # Mostrar TODO el HTML de una vez
    st.markdown(kanban_html, unsafe_allow_html=True)

# ============================================================================
# DASHBOARD PRINCIPAL - VERSIÓN FINAL CORREGIDA
# ============================================================================
def mostrar_dashboard_ordenes():
    """Dashboard principal - Solo Kanban limpio"""
    
    st.title("📋 Tablero de Órdenes de Bordado")
    st.markdown("---")
    
    # Cargar datos
    with st.spinner("🔄 Cargando órdenes..."):
        df_ordenes = obtener_ordenes()
    
    if df_ordenes.empty:
        st.info("📭 No hay órdenes registradas.")
        return
    
    # Resumen rápido
    if 'Estado' in df_ordenes.columns:
        df_ordenes['Estado_Simple'] = df_ordenes['Estado'].apply(normalizar_estado)
    else:
        df_ordenes['Estado_Simple'] = 'Pendiente'
    
    # Mostrar contadores
    st.subheader("📊 Resumen")
    
    col1, col2, col3, col4 = st.columns(4)
    
    estados = ['Pendiente', 'En Proceso', 'Listo', 'Entregado']
    colores = ['#6c757d', '#0d6efd', '#198754', '#6f42c1']
    iconos = ['⏱️', '⚙️', '✅', '📦']
    
    for i, (estado, color, icono) in enumerate(zip(estados, colores, iconos)):
        with [col1, col2, col3, col4][i]:
            count = len(df_ordenes[df_ordenes['Estado_Simple'] == estado])
            st.markdown(f"""
            <div style="text-align: center; padding: 15px; background-color: white; 
                        border-radius: 10px; border-top: 3px solid {color}; box-shadow: 0 2px 4px rgba(0,0,0,0.05);">
                <div style="font-size: 28px; font-weight: bold; color: {color};">{count}</div>
                <div style="font-size: 14px; color: #495057;">{icono} {estado}</div>
            </div>
            """, unsafe_allow_html=True)
    
    # Filtro simple
    st.markdown("---")
    
    filtro_col1, filtro_col2 = st.columns(2)
    
    with filtro_col1:
        estado_filtro = st.selectbox(
            "Filtrar por estado:",
            ["Todos"] + estados,
            key="filtro_estado"
        )
    
    with filtro_col2:
        # Solo mostrar filtro de vendedor si hay datos
        if 'Vendedor' in df_ordenes.columns:
            vendedores = ["Todos"] + sorted(df_ordenes['Vendedor'].dropna().unique().tolist())
            vendedor_filtro = st.selectbox(
                "Filtrar por vendedor:",
                vendedores,
                key="filtro_vendedor"
            )
        else:
            vendedor_filtro = "Todos"
    
    # Aplicar filtros
    df_filtrado = df_ordenes.copy()
    
    if estado_filtro != "Todos":
        df_filtrado = df_filtrado[df_filtrado['Estado_Simple'] == estado_filtro]
    
    if vendedor_filtro != "Todos" and 'Vendedor' in df_filtrado.columns:
        df_filtrado = df_filtrado[df_filtrado['Vendedor'] == vendedor_filtro]
    
    # Mostrar Kanban
    st.markdown("---")
    st.subheader(f"🎯 Órdenes ({len(df_filtrado)})")
    
    # Llamar a la función corregida
    mostrar_kanban_corregido(df_filtrado)
    
    # Botón de actualización
    if st.button("🔄 Actualizar Datos", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
    
    # Estado de conexión (al final)
    with st.expander("🔗 Información del Sistema", expanded=False):
        if "gsheets" in st.secrets and "ordenes_bordado_sheet_id" in st.secrets["gsheets"]:
            st.success("✅ Conectado a Google Sheets")
            st.write(f"Órdenes cargadas: {len(df_ordenes)}")
        else:
            st.error("❌ Configuración incompleta")
