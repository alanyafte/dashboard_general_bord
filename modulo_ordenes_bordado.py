import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import plotly.express as px

# Configuración para Google Sheets
SCOPE = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

def conectar_google_sheets():
    """Conectar con Google Sheets usando tus credenciales existentes"""
    try:
        # Usar las credenciales que ya tienes configuradas
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
        
        # Obtener el ID del sheet desde secrets
        sheet_id = st.secrets["gsheets"]["ordenes_bordado_sheet_id"]
        
        # Abrir por ID (más confiable que por nombre)
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
                # Verificar que la columna Estado existe
                if 'Estado' not in df.columns:
                    st.warning("⚠️ Columna 'Estado' no encontrada. Se agregará automáticamente.")
                    df['Estado'] = 'Pendiente'
                return df
            else:
                return pd.DataFrame()
        except Exception as e:
            st.error(f"❌ Error obteniendo órdenes: {e}")
            return pd.DataFrame()
    return pd.DataFrame()

def actualizar_estado_orden(numero_orden, nuevo_estado):
    """Actualizar el estado de una orden específica - CORREGIDO"""
    sheet = conectar_google_sheets()
    if sheet:
        try:
            # Obtener todos los datos para encontrar la fila
            data = sheet.get_all_records()
            
            for i, row in enumerate(data, start=2):  # start=2 porque fila 1 son headers
                if row.get('Número Orden') == numero_orden:
                    # CORRECCIÓN: Estado está en columna 28 (índice 27 en base 0)
                    sheet.update_cell(i, 28, nuevo_estado)
                    st.success(f"✅ Estado de {numero_orden} actualizado a: {nuevo_estado}")
                    return True
            
            st.error(f"❌ No se encontró la orden: {numero_orden}")
            return False
            
        except Exception as e:
            st.error(f"❌ Error actualizando orden: {e}")
            return False

def estilo_tarjeta_kanban(estado):
    """Devuelve el estilo CSS para cada estado del Kanban"""
    estilos = {
        'Pendiente': {
            'border': '2px solid #FF6B6B',
            'background': 'linear-gradient(135deg, #FFE8E8, #FFFFFF)',
            'color': '#D63031'
        },
        'En Proceso': {
            'border': '2px solid #FDCB6E',
            'background': 'linear-gradient(135deg, #FFF8E1, #FFFFFF)',
            'color': '#E17055'
        },
        'Completado': {
            'border': '2px solid #00B894',
            'background': 'linear-gradient(135deg, #E8F6F3, #FFFFFF)',
            'color': '#00A085'
        }
    }
    return estilos.get(estado, estilos['Pendiente'])

def crear_tarjeta_orden(orden):
    """Crea una tarjeta visual para cada orden en el Kanban"""
    estilo = estilo_tarjeta_kanban(orden['Estado'])
    
    # Manejar valores NaN o None
    vendedor = orden.get('Vendedor', 'No especificado')
    nombre_diseno = orden.get('Nombre Diseño', 'Sin nombre')
    fecha_entrega = orden.get('Fecha Entrega', 'No especificada')
    prendas = orden.get('Prendas', 'No especificadas')
    
    tarjeta_html = f"""
    <div style="
        {estilo['background']};
        border: {estilo['border']};
        border-radius: 12px;
        padding: 15px;
        margin: 10px 0;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        transition: transform 0.2s ease;
        font-family: 'Arial', sans-serif;
    " onmouseover="this.style.transform='translateY(-2px)'" onmouseout="this.style.transform='translateY(0)'">
        <div style="display: flex; justify-content: space-between; align-items: start;">
            <div style="flex: 1;">
                <h4 style="margin: 0 0 8px 0; color: {estilo['color']}; font-size: 14px;">
                    📦 {orden['Número Orden']}
                </h4>
                <h3 style="margin: 0 0 10px 0; color: #2D3436; font-size: 16px; font-weight: bold;">
                    {orden['Cliente']}
                </h3>
            </div>
            <div style="
                background: {estilo['color']}; 
                color: white; 
                padding: 4px 8px; 
                border-radius: 20px; 
                font-size: 10px; 
                font-weight: bold;
            ">
                {orden['Estado']}
            </div>
        </div>
        
        <div style="margin: 8px 0;">
            <div style="display: flex; align-items: center; margin: 4px 0;">
                <span style="font-size: 12px; color: #636E72;">👤</span>
                <span style="font-size: 12px; color: #636E72; margin-left: 5px;">{vendedor}</span>
            </div>
            <div style="display: flex; align-items: center; margin: 4px 0;">
                <span style="font-size: 12px; color: #636E72;">🎨</span>
                <span style="font-size: 12px; color: #636E72; margin-left: 5px;">{nombre_diseno}</span>
            </div>
            <div style="display: flex; align-items: center; margin: 4px 0;">
                <span style="font-size: 12px; color: #636E72;">📅</span>
                <span style="font-size: 12px; color: #636E72; margin-left: 5px;">{fecha_entrega}</span>
            </div>
        </div>
        
        <div style="
            background: rgba(255,255,255,0.7); 
            padding: 8px; 
            border-radius: 6px; 
            margin-top: 8px;
            border-left: 3px solid {estilo['color']};
        ">
            <div style="font-size: 11px; color: #636E72; font-weight: bold;">
                {prendas}
            </div>
        </div>
    </div>
    """
    return tarjeta_html

def mostrar_kanban_visual(df_filtrado):
    """Muestra el tablero Kanban con diseño visual mejorado"""
    st.subheader("🎯 Tablero Kanban Visual")
    
    # Estadísticas rápidas
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        total = len(df_filtrado)
        st.metric("Total", total, delta=None)
    with col2:
        pendientes = len(df_filtrado[df_filtrado['Estado'] == 'Pendiente'])
        st.metric("Pendientes", pendientes, delta=None)
    with col3:
        en_proceso = len(df_filtrado[df_filtrado['Estado'] == 'En Proceso'])
        st.metric("En Proceso", en_proceso, delta=None)
    with col4:
        completadas = len(df_filtrado[df_filtrado['Estado'] == 'Completado'])
        st.metric("Completadas", completadas, delta=None)
    
    # Definir columnas del Kanban
    estados_kanban = ['Pendiente', 'En Proceso', 'Completado']
    columns = st.columns(len(estados_kanban))
    
    for i, estado in enumerate(estados_kanban):
        with columns[i]:
            # Header de la columna con estilo
            estilo = estilo_tarjeta_kanban(estado)
            st.markdown(f"""
            <div style="
                background: {estilo['color']};
                color: white;
                padding: 12px;
                border-radius: 8px;
                text-align: center;
                margin-bottom: 15px;
                font-weight: bold;
                font-size: 16px;
            ">
                {estado} ({len(df_filtrado[df_filtrado['Estado'] == estado])})
            </div>
            """, unsafe_allow_html=True)
            
            # Ordenes en este estado
            ordenes_estado = df_filtrado[df_filtrado['Estado'] == estado]
            
            if ordenes_estado.empty:
                st.markdown("""
                <div style="
                    text-align: center;
                    color: #636E72;
                    padding: 20px;
                    font-style: italic;
                ">
                    No hay órdenes en este estado
                </div>
                """, unsafe_allow_html=True)
            else:
                for _, orden in ordenes_estado.iterrows():
                    # Crear y mostrar la tarjeta
                    tarjeta_html = crear_tarjeta_orden(orden)
                    st.markdown(tarjeta_html, unsafe_allow_html=True)  # ✅ CORRECCIÓN AQUÍ
                    
                    # Controles para cambiar estado (en un expander para no saturar)
                    with st.expander("🔄 Cambiar Estado", expanded=False):
                        nuevo_estado = st.selectbox(
                            "Seleccionar nuevo estado:",
                            estados_kanban,
                            index=estados_kanban.index(orden['Estado']),
                            key=f"kanban_{orden['Número Orden']}"
                        )
                        
                        if nuevo_estado != orden['Estado']:
                            if st.button("💾 Actualizar Estado", key=f"update_kanban_{orden['Número Orden']}"):
                                if actualizar_estado_orden(orden['Número Orden'], nuevo_estado):
                                    st.rerun()

def mostrar_vista_tabla(df_filtrado):
    """Muestra la vista de tabla tradicional"""
    st.subheader("📋 Vista de Tabla Detallada")
    
    # Seleccionar columnas para mostrar
    columnas_mostrar = [
        'Número Orden', 'Cliente', 'Vendedor', 'Fecha Entrega', 
        'Estado', 'Prendas', 'Nombre Diseño', 'Medidas Bordado', 'Tipo Hilos'
    ]
    
    # Filtrar columnas que existen
    columnas_existentes = [col for col in columnas_mostrar if col in df_filtrado.columns]
    df_vista = df_filtrado[columnas_existentes]
    
    # Aplicar estilo condicional a la tabla
    def estilo_fila(estado):
        if estado == 'Pendiente':
            return 'background-color: #FFE8E8'
        elif estado == 'En Proceso':
            return 'background-color: #FFF8E1'
        elif estado == 'Completado':
            return 'background-color: #E8F6F3'
        return ''
    
    styled_df = df_vista.style.apply(
        lambda x: [estilo_fila(x['Estado'])] * len(x), 
        axis=1
    )
    
    st.dataframe(
        styled_df,
        use_container_width=True,
        hide_index=True
    )

def mostrar_estadisticas(df_filtrado):
    """Muestra gráficas y estadísticas avanzadas"""
    st.subheader("📊 Estadísticas Avanzadas")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Gráfico de torta de estados
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
        # Gráfico de barras por vendedor
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
    
    # Filtros globales (aparecen en todas las pestañas)
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
    
    # Pestañas
    tab1, tab2, tab3 = st.tabs(["🎯 Kanban Visual", "📋 Vista Tabla", "📊 Estadísticas"])
    
    with tab1:
        mostrar_kanban_visual(df_filtrado)
    
    with tab2:
        mostrar_vista_tabla(df_filtrado)
    
    with tab3:
        mostrar_estadisticas(df_filtrado)
    
    # Botones de acción rápida en el footer
    st.markdown("---")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("🔄 Actualizar Todos los Datos", use_container_width=True):
            st.rerun()
    
    with col2:
        if st.button("📊 Exportar a Excel", use_container_width=True):
            timestamp = pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")
            filename = f"ordenes_bordado_{timestamp}.xlsx"
            df_filtrado.to_excel(filename, index=False)
            st.success(f"✅ Datos exportados a {filename}")
    
    with col3:
        if st.button("🔍 Debug Info", use_container_width=True):
            with st.expander("🔍 Información de Debug"):
                st.write(f"**Columnas encontradas:** {list(df_ordenes.columns)}")
                st.write(f"**Total de órdenes:** {len(df_ordenes)}")
                st.write(f"**Órdenes filtradas:** {len(df_filtrado)}")
                st.write("**Primeras filas:**")
                st.dataframe(df_ordenes.head(2))
