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

def obtener_ordenes_con_actualizacion(sheet):
    """Obtener órdenes y actualizar automáticamente si es necesario"""
    try:
        data = sheet.get_all_records()
        if not data:
            return pd.DataFrame()
        
        df = pd.DataFrame(data)
        
        # Verificar que las columnas necesarias existen
        if 'Estado Producción' not in df.columns:
            df['Estado Producción'] = 'Pendiente Aprobación'
        if 'Estado Aprobación' not in df.columns:
            df['Estado Aprobación'] = 'Pendiente'
        
        # ENCONTRAR LA COLUMNA DE ESTADO PRODUCCIÓN
        headers = sheet.row_values(1)
        try:
            col_produccion_index = headers.index('Estado Producción') + 1
        except ValueError:
            # Si no encuentra el nombre exacto, buscar similar
            for i, header in enumerate(headers):
                if 'producción' in header.lower() or 'produccion' in header.lower():
                    col_produccion_index = i + 1
                    break
            else:
                col_produccion_index = None
        
        # VERIFICAR Y ACTUALIZAR ORDENES APROBADAS
        actualizaciones_realizadas = []
        
        for i, row in enumerate(data, start=2):
            numero_orden = str(row.get('Número Orden', '')).strip()
            aprobacion = str(row.get('Estado Aprobación', '')).strip()
            produccion = str(row.get('Estado Producción', '')).strip()
            
            # LOGICA: Si está aprobado Y producción no está en estado avanzado
            if (aprobacion == 'Aprobado' and 
                produccion not in ['En Espera', 'En Proceso', 'Completado', 'Entregado'] and
                col_produccion_index is not None):
                
                # Actualizar a "En Espera"
                sheet.update_cell(i, col_produccion_index, 'En Espera')
                actualizaciones_realizadas.append(numero_orden)
        
        # Si hubo actualizaciones, recargar datos
        if actualizaciones_realizadas:
            st.session_state['ultimas_actualizaciones'] = actualizaciones_realizadas
            data = sheet.get_all_records()
            df = pd.DataFrame(data)
        
        # CREAR ESTADO KANBAN
        df['Estado_Kanban'] = df.apply(crear_estado_kanban, axis=1)
        
        return df
        
    except Exception as e:
        st.error(f"❌ Error obteniendo/actualizando órdenes: {e}")
        return pd.DataFrame()

def crear_estado_kanban(row):
    """Crear estado del Kanban según la lógica especificada"""
    aprobacion = str(row.get('Estado Aprobación', '')).strip()
    produccion = str(row.get('Estado Producción', '')).strip()
    
    # LÓGICA:
    # 1. Si estado aprobación es "Pendiente" → Estado Kanban = "Pendiente Aprobación"
    if aprobacion == 'Pendiente':
        return 'Pendiente Aprobación'
    
    # 2. Si estado aprobación es "Aprobado" → proceder a ver estado producción
    elif aprobacion == 'Aprobado':
        # Ahora sí revisamos el estado de producción
        if produccion == 'En Espera':
            return 'En Espera'
        elif produccion == 'En Proceso':
            return 'En Proceso'
        elif produccion == 'Completado':
            return 'Completado'
        elif produccion == 'Entregado':
            return 'Entregado'
        else:
            # Si está aprobado pero no tiene estado de producción definido
            return 'En Espera'
    
    # 3. Si hay otros valores
    else:
        return 'Pendiente Aprobación'

def get_color_estado_kanban(estado):
    """Devuelve colores para cada estado del KANBAN"""
    colores = {
        'Pendiente Aprobación': {'color': '#D63031', 'bg_color': '#FFE8E8', 'icon': '⏳'},
        'En Espera': {'color': '#E17055', 'bg_color': '#FFF8E1', 'icon': '⏱️'},
        'En Proceso': {'color': '#3498DB', 'bg_color': '#EBF5FB', 'icon': '⚙️'},
        'Completado': {'color': '#27AE60', 'bg_color': '#E8F8F5', 'icon': '✅'},
        'Entregado': {'color': '#6F42C1', 'bg_color': '#F3E8FF', 'icon': '📦'}
    }
    return colores.get(estado, {'color': '#95A5A6', 'bg_color': '#F2F4F4', 'icon': '❓'})

def crear_tarjeta_streamlit(orden):
    """Crea una tarjeta usando solo componentes de Streamlit"""
    estado_kanban = orden.get('Estado_Kanban', 'Pendiente Aprobación')
    color_estado = get_color_estado_kanban(estado_kanban)
    
    # Información de AMBAS columnas para mostrar
    estado_aprobacion = orden.get('Estado Aprobación', 'No especificado')
    estado_produccion = orden.get('Estado Producción', 'No especificado')
    
    # Crear un contenedor con estilo
    with st.container():
        # Header de la tarjeta - Mostrando ambos estados
        col1, col2 = st.columns([3, 1])
        with col1:
            st.markdown(f"**{color_estado['icon']} {orden['Número Orden']}**")
            st.markdown(f"### {orden['Cliente']}")
        with col2:
            # Estado Kanban (combinado)
            st.markdown(
                f"<div style='background-color: {color_estado['color']}; color: white; padding: 4px 8px; border-radius: 20px; text-align: center; font-size: 10px; font-weight: bold;'>{estado_kanban}</div>", 
                unsafe_allow_html=True
            )
            # Detalles de ambas columnas
            st.markdown(
                f"<div style='font-size: 9px; color: #666; text-align: center; margin-top: 2px;'>"
                f"Aprobación: {estado_aprobacion}<br>"
                f"Producción: {estado_produccion}"
                f"</div>", 
                unsafe_allow_html=True
            )
        
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
    """Muestra el tablero Kanban"""
    st.subheader("🎯 Tablero Kanban de Producción")
    
    # Mostrar actualizaciones recientes si las hay
    if 'ultimas_actualizaciones' in st.session_state and st.session_state['ultimas_actualizaciones']:
        actualizaciones = st.session_state['ultimas_actualizaciones']
        if len(actualizaciones) > 0:
            st.success(f"✅ Se actualizaron {len(actualizaciones)} órdenes a 'En Espera': {', '.join(actualizaciones[:3])}{'...' if len(actualizaciones) > 3 else ''}")
            # Limpiar después de mostrar
            st.session_state['ultimas_actualizaciones'] = []
    
    # Información sobre el flujo automático
    with st.expander("ℹ️ Flujo Automático", expanded=False):
        st.info("""
        **Actualización automática:**
        
        Cuando una orden tiene **Estado Aprobación = "Aprobado"** y 
        **Estado Producción** no es uno de los estados avanzados 
        (En Proceso, Completado, Entregado), se actualiza automáticamente a **"En Espera"**.
        
        Esto sucede cada vez que cargas o actualizas el tablero.
        """)
    
    # Definir el orden del flujo en el Kanban (5 estados)
    estados_kanban = [
        'Pendiente Aprobación',
        'En Espera',
        'En Proceso',
        'Completado',
        'Entregado'
    ]
    
    # Estadísticas rápidas - 5 columnas
    st.write("### 📊 Resumen por Estado")
    col1, col2, col3, col4, col5 = st.columns(5)
    
    stats_cols = [col1, col2, col3, col4, col5]
    for i, estado in enumerate(estados_kanban):
        with stats_cols[i]:
            count = len(df_filtrado[df_filtrado['Estado_Kanban'] == estado])
            color_estado = get_color_estado_kanban(estado)
            st.markdown(f"""
            <div style="text-align: center; padding: 10px; background-color: white; 
                        border-radius: 8px; border-top: 3px solid {color_estado['color']}; 
                        box-shadow: 0 1px 3px rgba(0,0,0,0.1);">
                <div style="font-size: 22px; font-weight: bold; color: {color_estado['color']};">{count}</div>
                <div style="font-size: 12px; color: #495057;">{color_estado['icon']} {estado.split()[-1]}</div>
            </div>
            """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Crear 5 columnas del Kanban
    columns = st.columns(5)
    
    for i, estado in enumerate(estados_kanban):
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
    
    # Conectar a Google Sheets
    sheet = conectar_google_sheets()
    if sheet is None:
        st.error("❌ No se pudo conectar a Google Sheets")
        return
    
    # Cargar órdenes CON ACTUALIZACIÓN AUTOMÁTICA
    with st.spinner("🔄 Cargando y verificando órdenes..."):
        df_ordenes = obtener_ordenes_con_actualizacion(sheet)
    
    if df_ordenes.empty:
        st.info("📭 No hay órdenes registradas aún.")
        return
    
    # Mostrar información de las columnas para debug (opcional)
    with st.expander("🔍 Ver estructura de datos", expanded=False):
        st.write(f"**Total de órdenes:** {len(df_ordenes)}")
        st.write(f"**Valores en 'Estado Aprobación':** {df_ordenes['Estado Aprobación'].unique()}")
        st.write(f"**Valores en 'Estado Producción':** {df_ordenes['Estado Producción'].unique()}")
        st.write(f"**Valores en 'Estado_Kanban':** {df_ordenes['Estado_Kanban'].unique()}")
        
        # Mostrar estadísticas
        aprobados = df_ordenes[df_ordenes['Estado Aprobación'] == 'Aprobado']
        st.write(f"**Órdenes aprobadas:** {len(aprobados)}")
    
    # Filtros globales
    st.subheader("🎛️ Filtros")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        # Filtro por estado del Kanban
        estados_kanban = ["Todos"] + ['Pendiente Aprobación', 'En Espera', 'En Proceso', 'Completado', 'Entregado']
        estado_filtro = st.selectbox("Por Estado:", estados_kanban, key="filtro_estado_kanban")
    
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
            # Limpiar cache y recargar
            if 'ultimas_actualizaciones' in st.session_state:
                del st.session_state['ultimas_actualizaciones']
            st.rerun()
