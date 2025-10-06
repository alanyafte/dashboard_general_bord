import gspread
import pandas as pd
import matplotlib.pyplot as plt
import plotly.express as px
import numpy as np
import streamlit as st
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

def mostrar_dashboard_produccion():
    try:
        # ✅ BOTÓN DE REFRESH EN SIDEBAR
        st.sidebar.header("🔄 Actualizar Datos")
        if st.sidebar.button("🔄 Actualizar Datos en Tiempo Real", use_container_width=True):
            # Limpiar cache de datos para forzar recarga
            if 'df_produccion' in st.session_state:
                del st.session_state['df_produccion']
            st.rerun()
        
        st.sidebar.info("Última actualización: " + datetime.now().strftime("%H:%M:%S"))
        
        # ✅ AUTENTICACIÓN CON CACHE
        @st.cache_data(ttl=300)  # Cache de 5 minutos
        def cargar_datos_desde_sheets():
            scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
            
            service_account_info = {
                "type": st.secrets["gservice_account"]["type"],
                "project_id": st.secrets["gservice_account"]["project_id"],
                "private_key_id": st.secrets["gservice_account"]["private_key_id"],
                "private_key": st.secrets["gservice_account"]["private_key"],
                "client_email": st.secrets["gservice_account"]["client_email"],
                "client_id": st.secrets["gservice_account"]["client_id"],
                "auth_uri": st.secrets["gservice_account"]["auth_uri"],
                "token_uri": st.secrets["gservice_account"]["token_uri"]
            }
            
            creds = ServiceAccountCredentials.from_json_keyfile_dict(service_account_info, scope)
            gc = gspread.authorize(creds)
            
            # ✅ CARGAR DATOS
            sheet_id = st.secrets["gsheets"]["produccion_sheet_id"]
            worksheet = gc.open_by_key(sheet_id).worksheet("reporte_de_trabajo")
            data = worksheet.get_all_values()
            df_raw = pd.DataFrame(data[1:], columns=data[0])
            
            return df_raw
        
        # Cargar datos (usando cache)
        df_raw = cargar_datos_desde_sheets()
        
        # ✅ LIMPIAR Y PROCESAR DATOS
        df = limpiar_dataframe(df_raw)
        
        # ✅ MOSTRAR DASHBOARD
        mostrar_interfaz_dashboard(df)
        
    except Exception as e:
        st.error(f"❌ Error al cargar los datos: {str(e)}")
        st.info("⚠️ Verifica que la hoja de cálculo esté accesible y la estructura sea correcta")

def limpiar_dataframe(df_raw):
    """Limpiar y procesar el dataframe"""
    df = df_raw.copy()
    
    # Eliminar columna de correo electrónico que no interesa
    if "Dirección de correo electrónico" in df.columns:
        df = df.drop("Dirección de correo electrónico", axis=1)
    
    # Limpiar espacios en nombres de columnas y valores
    df.columns = df.columns.str.strip()
    for col in df.columns:
        if df[col].dtype == 'object':
            df[col] = df[col].str.strip()
    
    # Convertir Marca temporal a datetime
    if "Marca temporal" in df.columns:
        df["Marca temporal"] = pd.to_datetime(df["Marca temporal"], errors='coerce')
    
    # Convertir CANTIDAD a numérico
    if "CANTIDAD" in df.columns:
        df["CANTIDAD"] = pd.to_numeric(df["CANTIDAD"], errors='coerce')
    
    # Convertir PUNTADAS a numérico (MUY IMPORTANTE para la suma)
    if "PUNTADAS" in df.columns:
        # Limpiar posibles textos o caracteres no numéricos
        df["PUNTADAS"] = pd.to_numeric(df["PUNTADAS"], errors='coerce')
        # Eliminar NaN para evitar problemas en sumas
        df["PUNTADAS"] = df["PUNTADAS"].fillna(0)
    
    # Convertir MULTIPLOS a numérico (si existe)
    if "MULTIPLOS" in df.columns:
        df["MULTIPLOS"] = pd.to_numeric(df["MULTIPLOS"], errors='coerce')
    
    return df

def aplicar_filtros(df):
    """Aplicar filtros interactivos"""
    df_filtrado = df.copy()
    
    st.sidebar.header("🔍 Filtros Avanzados")
    
    # Filtro por OPERADOR
    if "OPERADOR" in df.columns:
        operadores = sorted(df["OPERADOR"].unique())
        operadores_seleccionados = st.sidebar.multiselect(
            "Operadores:",
            options=operadores,
            default=operadores
        )
        if operadores_seleccionados:
            df_filtrado = df_filtrado[df_filtrado["OPERADOR"].isin(operadores_seleccionados)]
    
    # Filtro por fecha (Marca temporal)
    if "Marca temporal" in df.columns and not df_filtrado["Marca temporal"].isna().all():
        fechas_disponibles = df_filtrado["Marca temporal"].dropna()
        if not fechas_disponibles.empty:
            fecha_min = fechas_disponibles.min().date()
            fecha_max = fechas_disponibles.max().date()
            
            rango_fechas = st.sidebar.date_input(
                "Rango de Fechas:",
                value=(fecha_min, fecha_max),
                min_value=fecha_min,
                max_value=fecha_max
            )
            if len(rango_fechas) == 2:
                mask = (df_filtrado["Marca temporal"].dt.date >= rango_fechas[0]) & \
                       (df_filtrado["Marca temporal"].dt.date <= rango_fechas[1])
                df_filtrado = df_filtrado[mask]
    
    # Filtro por TIPO DE PRENDA
    if "TIPO DE PRENDA" in df.columns:
        tipos_prenda = sorted(df_filtrado["TIPO DE PRENDA"].unique())
        tipos_seleccionados = st.sidebar.multiselect(
            "Tipo de Prenda:",
            options=tipos_prenda,
            default=tipos_prenda
        )
        if tipos_seleccionados:
            df_filtrado = df_filtrado[df_filtrado["TIPO DE PRENDA"].isin(tipos_seleccionados)]
    
    # Filtro por DISEÑO
    if "DISEÑO" in df.columns:
        diseños = sorted(df_filtrado["DISEÑO"].unique())
        diseños_seleccionados = st.sidebar.multiselect(
            "Diseños:",
            options=diseños,
            default=diseños
        )
        if diseños_seleccionados:
            df_filtrado = df_filtrado[df_filtrado["DISEÑO"].isin(diseños_seleccionados)]
    
    st.sidebar.info(f"📊 Registros filtrados: {len(df_filtrado)}")
    
    return df_filtrado

def mostrar_metricas_principales(df):
    """Mostrar métricas principales de producción"""
    
    if df.empty:
        st.warning("No hay datos con los filtros aplicados")
        return
    
    st.subheader("📈 Métricas de Producción")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_pedidos = len(df)
        st.metric("Total de Pedidos", f"{total_pedidos:,}")
    
    with col2:
        if "CANTIDAD" in df.columns:
            total_unidades = df["CANTIDAD"].sum()
            st.metric("Total Unidades", f"{total_unidades:,}")
        else:
            st.metric("Operadores Activos", df["OPERADOR"].nunique())
    
    with col3:
        if "OPERADOR" in df.columns:
            operadores_activos = df["OPERADOR"].nunique()
            st.metric("Operadores Activos", operadores_activos)
        else:
            st.metric("Diseños Únicos", df["DISEÑO"].nunique())
    
    with col4:
        # ✅ NUEVA MÉTRICA: SUMA TOTAL DE PUNTADAS
        if "PUNTADAS" in df.columns:
            total_puntadas = df["PUNTADAS"].sum()
            st.metric("Total Puntadas", f"{total_puntadas:,.0f}")
        elif "Marca temporal" in df.columns and not df["Marca temporal"].isna().all():
            ultima_actualizacion = df["Marca temporal"].max()
            st.metric("Último Registro", ultima_actualizacion.strftime("%d/%m/%Y"))
        else:
            st.metric("Pedidos Únicos", df["#DE PEDIDO"].nunique())

def mostrar_analisis_operadores(df):
    """Análisis detallado por operador INCLUYENDO PUNTADAS"""
    
    if df.empty or "OPERADOR" not in df.columns:
        return
    
    st.subheader("👤 Análisis por Operador")
    
    # ✅ MÉTRICAS POR OPERADOR INCLUYENDO PUNTADAS
    metricas_operador = df.groupby("OPERADOR").agg({
        '#DE PEDIDO': 'count',
        'CANTIDAD': 'sum' if 'CANTIDAD' in df.columns else None,
        'PUNTADAS': 'sum' if 'PUNTADAS' in df.columns else None
    }).reset_index()
    
    # Ajustar nombres de columnas según qué métricas están disponibles
    if 'CANTIDAD' in df.columns and 'PUNTADAS' in df.columns:
        metricas_operador.columns = ['Operador', 'Total Pedidos', 'Total Unidades', 'Total Puntadas']
    elif 'CANTIDAD' in df.columns:
        metricas_operador.columns = ['Operador', 'Total Pedidos', 'Total Unidades']
    elif 'PUNTADAS' in df.columns:
        metricas_operador.columns = ['Operador', 'Total Pedidos', 'Total Puntadas']
    else:
        metricas_operador.columns = ['Operador', 'Total Pedidos']
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**📊 Desempeño por Operador:**")
        st.dataframe(metricas_operador, use_container_width=True)
    
    with col2:
        # ✅ GRÁFICO DE PUNTADAS POR OPERADOR
        if "PUNTADAS" in df.columns and 'Total Puntadas' in metricas_operador.columns:
            fig = px.bar(
                metricas_operador, 
                x='Operador', 
                y='Total Puntadas',
                title="Puntadas Totales por Operador",
                color='Total Puntadas',
                text='Total Puntadas'
            )
            fig.update_traces(texttemplate='%{text:,.0f}', textposition='outside')
            st.plotly_chart(fig, use_container_width=True)
        else:
            # Gráfico de pedidos por operador como fallback
            fig = px.bar(
                metricas_operador, 
                x='Operador', 
                y='Total Pedidos',
                title="Pedidos por Operador",
                color='Total Pedidos',
                text='Total Pedidos'
            )
            fig.update_traces(texttemplate='%{text}', textposition='outside')
            st.plotly_chart(fig, use_container_width=True)

def mostrar_analisis_puntadas(df):
    """✅ NUEVA SECCIÓN: Análisis específico de puntadas"""
    
    if df.empty or "PUNTADAS" not in df.columns:
        return
    
    st.subheader("🪡 Análisis de Puntadas")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Top operadores por puntadas
        puntadas_por_operador = df.groupby("OPERADOR")["PUNTADAS"].sum().sort_values(ascending=False).reset_index()
        puntadas_por_operador.columns = ['Operador', 'Total Puntadas']
        
        st.write("**🏆 Ranking por Puntadas:**")
        st.dataframe(puntadas_por_operador, use_container_width=True)
    
    with col2:
        # Distribución de puntadas por tipo de prenda
        if "TIPO DE PRENDA" in df.columns:
            puntadas_por_prenda = df.groupby("TIPO DE PRENDA")["PUNTADAS"].sum().reset_index()
            puntadas_por_prenda.columns = ['Tipo de Prenda', 'Total Puntadas']
            
            fig = px.pie(
                puntadas_por_prenda, 
                values='Total Puntadas', 
                names='Tipo de Prenda',
                title="Distribución de Puntadas por Tipo de Prenda"
            )
            st.plotly_chart(fig, use_container_width=True)

def mostrar_analisis_pedidos(df):
    """Análisis de pedidos y producción"""
    
    if df.empty:
        return
    
    st.subheader("📦 Análisis de Pedidos")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Top diseños más producidos
        if "DISEÑO" in df.columns:
            top_diseños = df["DISEÑO"].value_counts().head(10).reset_index()
            top_diseños.columns = ['Diseño', 'Cantidad']
            
            st.write("**🎨 Top Diseños:**")
            st.dataframe(top_diseños, use_container_width=True)
    
    with col2:
        # Tipos de prenda más comunes
        if "TIPO DE PRENDA" in df.columns:
            tipos_prenda = df["TIPO DE PRENDA"].value_counts().reset_index()
            tipos_prenda.columns = ['Tipo de Prenda', 'Cantidad']
            
            fig = px.pie(
                tipos_prenda, 
                values='Cantidad', 
                names='Tipo de Prenda',
                title="Distribución por Tipo de Prenda"
            )
            st.plotly_chart(fig, use_container_width=True)

def mostrar_tendencias_temporales(df):
    """Mostrar tendencias a lo largo del tiempo"""
    
    if df.empty or "Marca temporal" not in df.columns:
        return
    
    st.subheader("📈 Tendencias Temporales")
    
    # Agrupar por fecha
    df_temporal = df.copy()
    df_temporal['Fecha'] = df_temporal['Marca temporal'].dt.date
    tendencias = df_temporal.groupby('Fecha').agg({
        '#DE PEDIDO': 'count',
        'CANTIDAD': 'sum' if 'CANTIDAD' in df.columns else None,
        'PUNTADAS': 'sum' if 'PUNTADAS' in df.columns else None
    }).reset_index()
    
    if len(tendencias) > 1:
        # Gráfico de pedidos por día
        fig = px.line(
            tendencias, 
            x='Fecha', 
            y='#DE PEDIDO',
            title="Evolución de Pedidos por Día",
            markers=True
        )
        st.plotly_chart(fig, use_container_width=True)
        
        # Gráfico de puntadas por día (si existen)
        if "PUNTADAS" in df.columns:
            fig2 = px.line(
                tendencias, 
                x='Fecha', 
                y='PUNTADAS',
                title="Evolución de Puntadas por Día",
                markers=True,
                color_discrete_sequence=['red']
            )
            st.plotly_chart(fig2, use_container_width=True)

def calcular_puntadas_automaticas(df):
    """Calcular automáticamente las puntadas para MÚLTIPLES operadores"""
    
    st.header("🧵 Cálculo de Puntadas para Comisiones")
    
    if "OPERADOR" not in df.columns or "Marca temporal" not in df.columns:
        st.error("❌ Se necesitan las columnas 'OPERADOR' y 'Marca temporal'")
        return df
    
    # ✅ CONFIGURACIÓN DE MÁQUINAS POR OPERADOR
    st.subheader("⚙️ Configuración de Máquinas")
    
    operadores = sorted(df["OPERADOR"].unique())
    
    # Mostrar todos los operadores con sus configuraciones
    config_maquinas = {}
    st.write("**Configurar cabezas por operador:**")
    
    cols = st.columns(3)  # 3 columnas para mejor organización
    for i, operador in enumerate(operadores):
        with cols[i % 3]:
            cabezas = st.number_input(
                f"{operador}",
                min_value=1,
                value=6,
                key=f"cabezas_{operador}",
                help=f"Número de cabezas para {operador}"
            )
            config_maquinas[operador] = cabezas
    
    # ✅ SELECTOR MÚLTIPLE DE OPERADORES
    st.subheader("👥 Selección de Operadores")
    
    operadores_seleccionados = st.multiselect(
        "Selecciona los operadores a calcular:",
        options=operadores,
        default=operadores,  # Por defecto selecciona todos
        help="Puedes seleccionar uno o varios operadores para el cálculo"
    )
    
    if not operadores_seleccionados:
        st.warning("⚠️ Por favor selecciona al menos un operador")
        return df
    
    # ✅ FILTRO POR FECHA
    st.subheader("📅 Configuración de Fecha")
    
    df_fechas = df.copy()
    df_fechas['Fecha'] = df_fechas['Marca temporal'].dt.date
    fechas_disponibles = sorted(df_fechas['Fecha'].unique())
    
    col1, col2 = st.columns(2)
    with col1:
        fecha_seleccionada = st.selectbox(
            "Seleccionar fecha para cálculo:",
            options=fechas_disponibles,
            index=len(fechas_disponibles)-1 if fechas_disponibles else 0
        )
    
    with col2:
        # Opción para incluir todos los datos (sin filtro de fecha)
        incluir_todas_fechas = st.checkbox(
            "📊 Incluir todas las fechas", 
            value=False,
            help="Calcular sobre todos los registros sin filtrar por fecha"
        )
    
    # Aplicar filtros
    if incluir_todas_fechas:
        df_turno = df_fechas[df_fechas['OPERADOR'].isin(operadores_seleccionados)].copy()
        st.info(f"📊 {len(operadores_seleccionados)} operadores - TODAS LAS FECHAS: {len(df_turno)} registros")
    else:
        df_turno = df_fechas[
            (df_fechas['Fecha'] == fecha_seleccionada) & 
            (df_fechas['OPERADOR'].isin(operadores_seleccionados))
        ].copy()
        st.info(f"📊 {len(operadores_seleccionados)} operadores - {fecha_seleccionada}: {len(df_turno)} registros")
    
    # ✅ BOTÓN DE CÁLCULO
    if st.button("🔄 Calcular Puntadas para Operadores Seleccionados", type="primary", use_container_width=True):
        
        if df_turno.empty:
            st.error("❌ No hay registros para los operadores y fecha seleccionados")
            return df
        
        if "CANTIDAD" not in df_turno.columns or "PUNTADAS" not in df_turno.columns:
            st.error("❌ Se necesitan las columnas 'CANTIDAD' y 'PUNTADAS'")
            return df
        
        # ✅ CALCULAR PARA CADA OPERADOR SELECCIONADO
        resultados_detalle = []
        totales_operadores = {}
        
        for operador in operadores_seleccionados:
            # Filtrar órdenes del operador
            df_operador = df_turno[df_turno["OPERADOR"] == operador].copy()
            cabezas = config_maquinas[operador]
            
            if len(df_operador) == 0:
                st.warning(f"⚠️ {operador} no tiene registros en el período seleccionado")
                continue
            
            total_multiplos_operador = 0
            
            # Calcular para cada orden del operador
            for idx, orden in df_operador.iterrows():
                piezas = orden["CANTIDAD"]
                puntadas_base = orden["PUNTADAS"]
                
                # Calcular múltiplos
                pasadas = np.ceil(piezas / cabezas)
                multiplo = pasadas * cabezas
                puntadas_ajustadas = max(puntadas_base, 4000)
                puntadas_multiplos = multiplo * puntadas_ajustadas
                total_multiplos_operador += puntadas_multiplos
                
                resultados_detalle.append({
                    'OPERADOR': operador,
                    'FECHA': orden['Fecha'] if 'Fecha' in orden else fecha_seleccionada,
                    'PEDIDO': orden.get('#DE PEDIDO', 'N/A'),
                    'PRENDA': orden.get('TIPO DE PRENDA', 'N/A'),
                    'CANTIDAD': piezas,
                    'PUNTADAS_BASE': puntadas_base,
                    'CABEZAS': cabezas,
                    'PASADAS': pasadas,
                    'MULTIPLO': multiplo,
                    'PUNTADAS_MULTIPLOS': puntadas_multiplos
                })
            
            # ✅ CALCULAR CAMBIOS DE COLOR
            ordenes_operador = len(df_operador)
            puntadas_cambios = 36000 + (ordenes_operador * 18000)
            total_operador = total_multiplos_operador + puntadas_cambios
            
            totales_operadores[operador] = {
                'ordenes': ordenes_operador,
                'cabezas': cabezas,
                'puntadas_multiplos': total_multiplos_operador,
                'puntadas_cambios': puntadas_cambios,
                'total': total_operador
            }
        
        # ✅ MOSTRAR RESUMEN EJECUTIVO
        st.subheader("🏆 Resumen Ejecutivo de Comisiones")
        
        # Métricas generales
        total_general = sum(datos['total'] for datos in totales_operadores.values())
        total_operadores_calculados = len(totales_operadores)
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Operadores Calculados", total_operadores_calculados)
        with col2:
            st.metric("Total Órdenes", sum(datos['ordenes'] for datos in totales_operadores.values()))
        with col3:
            st.metric("Puntadas Cambios", f"{sum(datos['puntadas_cambios'] for datos in totales_operadores.values()):,.0f}")
        with col4:
            st.metric("**TOTAL GENERAL**", f"**{total_general:,.0f}**")
        
        # ✅ TABLA RESUMEN POR OPERADOR
        st.subheader("📊 Resumen por Operador")
        
        resumen_data = []
        for operador, datos in totales_operadores.items():
            resumen_data.append({
                'Operador': operador,
                'Cabezas': datos['cabezas'],
                'Órdenes': datos['ordenes'],
                'Puntadas Múltiplos': f"{datos['puntadas_multiplos']:,.0f}",
                'Puntadas Cambios': f"{datos['puntadas_cambios']:,.0f}",
                'Total Puntadas': f"{datos['total']:,.0f}"
            })
        
        df_resumen = pd.DataFrame(resumen_data)
        st.dataframe(df_resumen, use_container_width=True)
        
        # ✅ GRÁFICO COMPARATIVO
        if len(totales_operadores) > 1:
            st.subheader("📈 Comparativa entre Operadores")
            
            df_grafico = pd.DataFrame([
                {
                    'Operador': operador,
                    'Puntadas Múltiplos': datos['puntadas_multiplos'],
                    'Puntadas Cambios': datos['puntadas_cambios'],
                    'Total': datos['total']
                }
                for operador, datos in totales_operadores.items()
            ])
            
            fig = px.bar(
                df_grafico,
                x='Operador',
                y=['Puntadas Múltiplos', 'Puntadas Cambios'],
                title="Distribución de Puntadas por Operador",
                barmode='stack',
                labels={'value': 'Puntadas', 'variable': 'Tipo'}
            )
            st.plotly_chart(fig, use_container_width=True)
        
        # ✅ DETALLE COMPLETO (OPCIONAL - EN EXPANDER)
        with st.expander("📋 Ver Detalle Completo de Cálculos"):
            if resultados_detalle:
                df_detalle = pd.DataFrame(resultados_detalle)
                st.dataframe(df_detalle, use_container_width=True, height=400)
                
                # Opción para descargar detalle
                csv_detalle = df_detalle.to_csv(index=False, encoding='utf-8')
                st.download_button(
                    label="📥 Descargar Detalle de Cálculos (CSV)",
                    data=csv_detalle,
                    file_name="detalle_puntadas_operadores.csv",
                    mime="text/csv"
                )
        
        # ✅ RESUMEN PARA COPIAR (PARA COMISIONES)
        st.subheader("💵 Resumen para Cálculo de Comisiones")
        
        for operador, datos in totales_operadores.items():
            st.write(f"**{operador}:** {datos['total']:,.0f} puntadas totales")
        
        return df_turno
    
    else:
        st.info("👆 Configura las máquinas, selecciona operadores y haz clic en 'Calcular'")
        return df

def mostrar_interfaz_dashboard(df):
    """Interfaz principal del dashboard"""
    
    st.title("🏭 Dashboard de Producción")
    
    # Mostrar resumen rápido
    st.info(f"**Base de datos cargada:** {len(df)} registros de producción")
    
    # ✅ FILTROS
    df_filtrado = aplicar_filtros(df)
    
    # ✅ NUEVA SECCIÓN: CÁLCULO AUTOMÁTICO DE PUNTADAS (INSERTAR ESTO)
    with st.expander("🧵 CALCULAR PUNTADAS AUTOMÁTICAS (Múltiplos + Cambios de Color)", expanded=True):
        df_calculado = calcular_puntadas_automaticas(df_filtrado)
    
    # ✅ MÉTRICAS PRINCIPALES (las que ya tienes)
    mostrar_metricas_principales(df_filtrado)
    
    # ✅ ANÁLISIS POR OPERADOR (INCLUYE PUNTADAS)
    mostrar_analisis_operadores(df_filtrado)
    
    # ✅ NUEVA SECCIÓN: ANÁLISIS ESPECÍFICO DE PUNTADAS
    mostrar_analisis_puntadas(df_filtrado)
    
    # ✅ ANÁLISIS DE PEDIDOS
    mostrar_analisis_pedidos(df_filtrado)
    
    # ✅ TENDENCIAS TEMPORALES
    mostrar_tendencias_temporales(df_filtrado)
    
    # ✅ DATOS DETALLADOS
    st.subheader("📋 Datos Detallados de Producción")
    st.dataframe(df_filtrado, use_container_width=True, height=400)
    
    # Opción para descargar
    csv = df_filtrado.to_csv(index=False, encoding='utf-8')
    st.download_button(
        label="📥 Descargar Datos Filtrados (CSV)",
        data=csv,
        file_name="produccion_filtrada.csv",
        mime="text/csv"
    )
