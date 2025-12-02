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
                    df['Estado Producción'] = 'Pendiente Aprobación'
                if 'Estado Aprobación' not in df.columns:
                    df['Estado Aprobación'] = 'Pendiente'
                
                # CREAR ESTADO KANBAN
                df['Estado_Kanban'] = df.apply(crear_estado_kanban, axis=1)
                
                return df, sheet
            else:
                return pd.DataFrame(), None
        except Exception as e:
            st.error(f"❌ Error obteniendo órdenes: {e}")
            return pd.DataFrame(), None
    return pd.DataFrame(), None

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

def actualizar_estado_produccion(sheet, numero_orden, nuevo_estado):
    """Actualizar el estado de producción en Google Sheets"""
    try:
        # Obtener todos los datos para encontrar la fila
        data = sheet.get_all_records()
        
        # Encontrar la columna de "Estado Producción"
        headers = sheet.row_values(1)
        try:
            col_index = headers.index('Estado Producción') + 1
        except ValueError:
            # Si no encuentra el nombre exacto, buscar similar
            for i, header in enumerate(headers):
                if 'producción' in header.lower() or 'produccion' in header.lower():
                    col_index = i + 1
                    break
            else:
                st.error("❌ No se encontró la columna 'Estado Producción'")
                return False
        
        # Buscar la fila con el número de orden
        for i, row in enumerate(data, start=2):
            if str(row.get('Número Orden', '')).strip() == str(numero_orden).strip():
                # Actualizar la celda
                sheet.update_cell(i, col_index, nuevo_estado)
                return True
        
        st.error(f"❌ No se encontró la orden: {numero_orden}")
        return False
        
    except Exception as e:
        st.error(f"❌ Error actualizando orden: {e}")
        return False

def verificar_y_actualizar_aprobados(df, sheet):
    """Verificar órdenes aprobadas y actualizar su estado de producción si es necesario"""
    actualizaciones = []
    
    for _, row in df.iterrows():
        numero_orden = row['Número Orden']
        aprobacion = str(row.get('Estado Aprobación', '')).strip()
        produccion = str(row.get('Estado Producción', '')).strip()
        
        # Si está aprobado y su estado producción NO es "En Espera", "En Proceso", "Completado" o "Entregado"
        if aprobacion == 'Aprobado' and produccion not in ['En Espera', 'En Proceso', 'Completado', 'Entregado']:
            # Verificar que no sea "Pendiente Aprobación" (ese es el estado inicial)
            if produccion != 'Pendiente Aprobación':
                # Actualizar a "En Espera"
                if actualizar_estado_produccion(sheet, numero_orden, 'En Espera'):
                    actualizaciones.append(numero_orden)
    
    return actualizaciones

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

def crear_tarjeta_streamlit(orden, sheet):
    """Crea una tarjeta usando solo componentes de Streamlit"""
    estado_kanban = orden.get('Estado_Kanban', 'Pendiente Aprobación')
    color_estado = get_color_estado_kanban(estado_kanban)
    
    # Información de AMBAS columnas para mostrar
    estado_aprobacion = orden.get('Estado Aprobación', 'No especificado')
    estado_produccion = orden.get('Estado Producción', 'No especificado')
    numero_orden = orden['Número Orden']
    
    # Crear un contenedor con estilo
    with st.container():
        # Header de la tarjeta - Mostrando ambos estados
        col1, col2 = st.columns([3, 1])
        with col1:
            st.markdown(f"**{color_estado['icon']} {numero_orden}**")
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
        
        # BOTÓN PARA FORZAR ACTUALIZACIÓN SI ESTÁ APROBADO PERO NO EN ESPERA
        if estado_aprobacion == 'Aprobado' and estado_produccion not in ['En Espera', 'En Proceso', 'Completado', 'Entregado']:
            if st.button(f"🔄 Mover a 'En Espera'", key=f"btn_{numero_orden}", use_container_width=True):
                with st.spinner(f"Actualizando {numero_orden}..."):
                    if actualizar_estado_produccion(sheet, numero_orden, 'En Espera'):
                        st.success(f"✅ {numero_orden} actualizado a 'En Espera'")
                        st.rerun()
        
        st.markdown("---")

def mostrar_kanban_visual(df_filtrado, sheet):
    """Muestra el tablero Kanban"""
    st.subheader("🎯 Tablero Kanban de Producción")
    
    # BOTÓN PARA ACTUALIZAR TODOS LOS APROBADOS
    if st.button("🔄 Actualizar todos los aprobados a 'En Espera'", use_container_width=True):
        with st.spinner("Verificando órdenes aprobadas..."):
            actualizaciones = verificar_y_actualizar_aprobados(df_filtrado, sheet)
            if actualizaciones:
                st.success(f"✅ {len(actualizaciones)} órdenes actualizadas: {', '.join(actualizaciones[:5])}{'...' if len(actualizaciones) > 5 else ''}")
                st.rerun()
            else:
                st.info("ℹ️ No hay órdenes aprobadas pendientes de actualizar")
    
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
                    crear_tarjeta_streamlit(orden, sheet)

def mostrar_dashboard_ordenes():
    """Dashboard principal de gestión de órdenes SOLO CON KANBAN"""
    
    st.title("🏭 Tablero de Producción - Órdenes de Bordado")
    
    # Información de conexión
    with st.expander("🔗 Estado de Conexión", expanded=False):
        if "gsheets" in st.secrets and "ordenes_bordado_sheet_id" in st.secrets["gsheets"]:
            st.success("✅ Conectado a Google Sheets")
        else:
            st.error("❌ Sheet ID no configurado")
    
    # Cargar órdenes (ahora también devuelve el objeto sheet)
    with st.spinner("🔄 Cargando órdenes desde Google Sheets..."):
        df_ordenes, sheet = obtener_ordenes()
    
    if df_ordenes.empty:
        st.info("📭 No hay órdenes registradas aún.")
        return
    
    if sheet is None:
        st.error("❌ No se pudo conectar a Google Sheets")
        return
    
    # Mostrar información de las columnas para debug (opcional)
    with st.expander("🔍 Ver estructura de datos", expanded=False):
        st.write(f"**Columnas disponibles:** {list(df_ordenes.columns)}")
        st.write(f"**Valores en 'Estado Aprobación':** {df_ordenes['Estado Aprobación'].unique()}")
        st.write(f"**Valores en 'Estado Producción':** {df_ordenes['Estado Producción'].unique()}")
        st.write(f"**Valores en 'Estado_Kanban':** {df_ordenes['Estado_Kanban'].unique()}")
        
        # Mostrar órdenes que necesitan actualización
        aprobados_pendientes = df_ordenes[
            (df_ordenes['Estado Aprobación'] == 'Aprobado') & 
            (~df_ordenes['Estado Producción'].isin(['En Espera', 'En Proceso', 'Completado', 'Entregado']))
        ]
        if not aprobados_pendientes.empty:
            st.warning(f"⚠️ {len(aprobados_pendientes)} órdenes aprobadas necesitan actualización:")
            st.dataframe(aprobados_pendientes[['Número Orden', 'Cliente', 'Estado Aprobación', 'Estado Producción']])
    
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
    
    # Mostrar Kanban (pasar el objeto sheet)
    mostrar_kanban_visual(df_filtrado, sheet)
    
    # Botones de acción
    st.markdown("---")
    col_btn1, col_btn2 = st.columns([3, 1])
    
    with col_btn1:
        st.info(f"📊 Mostrando {len(df_filtrado)} de {len(df_ordenes)} órdenes")
    
    with col_btn2:
        if st.button("🔄 Actualizar Datos", use_container_width=True):
            st.rerun()
