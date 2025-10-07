import gspread
import pandas as pd
import matplotlib.pyplot as plt
import plotly.express as px
import numpy as np
import streamlit as st
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
from datetime import timedelta

# ✅ PRIMERO: Las funciones de utilidad y limpieza (las que ya tienes)
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

# ✅ LUEGO: Las NUEVAS funciones que te di (con cálculos persistentes)

def guardar_calculos_en_sheets(df_calculado):
    """Guardar los cálculos en una nueva hoja de Google Sheets"""
    try:
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
        
        sheet_id = st.secrets["gsheets"]["produccion_sheet_id"]
        spreadsheet = gc.open_by_key(sheet_id)
        
        # Intentar acceder a la hoja de cálculos, o crearla si no existe
        try:
            worksheet = spreadsheet.worksheet("puntadas_calculadas")
        except:
            worksheet = spreadsheet.add_worksheet(title="puntadas_calculadas", rows="1000", cols="20")
        
        # Limpiar la hoja existente y escribir nuevos datos
        worksheet.clear()
        
        # Convertir DataFrame a lista de listas
        datos_para_guardar = [df_calculado.columns.tolist()] + df_calculado.values.tolist()
        
        # Escribir todos los datos
        worksheet.update('A1', datos_para_guardar)
        
        return True
    except Exception as e:
        st.error(f"❌ Error al guardar cálculos: {str(e)}")
        return False

def calcular_puntadas_automaticas(df, df_calculado_existente=None):
    """Calcular automáticamente las puntadas y guardar en Google Sheets"""
    
    st.header("🧵 Cálculo Automático de Puntadas")
    
    # ✅ CONFIGURACIÓN DE MÁQUINAS POR OPERADOR
    st.subheader("⚙️ Configuración de Máquinas")
    
    if "OPERADOR" not in df.columns or "Marca temporal" not in df.columns:
        st.error("❌ Se necesitan las columnas 'OPERADOR' y 'Marca temporal'")
        return df, df_calculado_existente
    
    operadores = sorted(df["OPERADOR"].unique())
    
    config_maquinas = {}
    for operador in operadores:
        col1, col2 = st.columns([2, 1])
        with col1:
            st.write(f"**{operador}**")
        with col2:
            cabezas = st.number_input(
                f"Cabezas {operador}",
                min_value=1,
                value=6,
                key=f"cabezas_{operador}"
            )
            config_maquinas[operador] = cabezas
    
    # ✅ CONFIGURACIÓN DE FECHAS PARA CÁLCULO
    st.subheader("📅 Configuración de Período")
    
    df_fechas = df.copy()
    df_fechas['Fecha'] = df_fechas['Marca temporal'].dt.date
    fechas_disponibles = sorted(df_fechas['Fecha'].unique())
    
    col1, col2 = st.columns(2)
    with col1:
        fecha_inicio = st.selectbox(
            "Fecha de inicio:",
            options=fechas_disponibles,
            index=0
        )
    with col2:
        fecha_fin = st.selectbox(
            "Fecha de fin:",
            options=fechas_disponibles,
            index=len(fechas_disponibles)-1
        )
    
    # Filtrar datos por rango de fechas seleccionado
    mask = (df_fechas['Fecha'] >= fecha_inicio) & (df_fechas['Fecha'] <= fecha_fin)
    df_periodo = df_fechas[mask]
    
    st.info(f"📊 Datos del período {fecha_inicio} a {fecha_fin}: {len(df_periodo)} registros")
    
    if st.button("🔄 Calcular y Guardar Puntadas", type="primary"):
        
        if "CANTIDAD" not in df_periodo.columns or "PUNTADAS" not in df_periodo.columns:
            st.error("❌ Se necesitan las columnas 'CANTIDAD' y 'PUNTADAS'")
            return df, df_calculado_existente
        
        # ✅ CALCULAR PUNTADAS PARA TODO EL PERÍODO
        resultados = []
        totales_operador = {}
        
        with st.spinner("Calculando puntadas..."):
            for operador in operadores:
                # Filtrar órdenes del operador en el PERÍODO
                df_operador = df_periodo[df_periodo["OPERADOR"] == operador].copy()
                cabezas = config_maquinas[operador]
                
                if len(df_operador) == 0:
                    continue
                
                # Agrupar por fecha para calcular cambios de color por día
                df_operador['Fecha'] = df_operador['Marca temporal'].dt.date
                fechas_operador = df_operador['Fecha'].unique()
                
                for fecha in fechas_operador:
                    df_dia = df_operador[df_operador['Fecha'] == fecha]
                    ordenes_dia = len(df_dia)
                    
                    # Calcular para cada orden del día
                    for idx, orden in df_dia.iterrows():
                        piezas = orden["CANTIDAD"]
                        puntadas_base = orden["PUNTADAS"]
                        
                        # Calcular múltiplos
                        pasadas = np.ceil(piezas / cabezas)
                        multiplo = pasadas * cabezas
                        puntadas_ajustadas = max(puntadas_base, 4000)
                        puntadas_multiplos = multiplo * puntadas_ajustadas
                        
                        # Calcular cambios de color (36,000 por turno + 18,000 por orden)
                        puntadas_cambios = 36000 + (ordenes_dia * 18000)
                        total_puntadas = puntadas_multiplos + puntadas_cambios
                        
                        resultados.append({
                            'OPERADOR': operador,
                            'FECHA': fecha,
                            'PEDIDO': orden.get('#DE PEDIDO', 'N/A'),
                            'TIPO_PRENDA': orden.get('TIPO DE PRENDA', 'N/A'),
                            'DISEÑO': orden.get('DISEÑO', 'N/A'),
                            'CANTIDAD': piezas,
                            'PUNTADAS_BASE': puntadas_base,
                            'CABEZAS': cabezas,
                            'PASADAS': pasadas,
                            'MULTIPLO': multiplo,
                            'PUNTADAS_MULTIPLOS': puntadas_multiplos,
                            'PUNTADAS_CAMBIOS': puntadas_cambios,
                            'TOTAL_PUNTADAS': total_puntadas,
                            'FECHA_CALCULO': datetime.now().date(),
                            'HORA_CALCULO': datetime.now().strftime("%H:%M:%S")
                        })
                    
                    # Acumular totales por operador
                    if operador not in totales_operador:
                        totales_operador[operador] = {
                            'ordenes': 0,
                            'puntadas_multiplos': 0,
                            'puntadas_cambios': 0,
                            'total': 0
                        }
                    
                    totales_operador[operador]['ordenes'] += ordenes_dia
                    totales_operador[operador]['puntadas_multiplos'] += sum(r['PUNTADAS_MULTIPLOS'] for r in resultados if r['OPERADOR'] == operador and r['FECHA'] == fecha)
                    totales_operador[operador]['puntadas_cambios'] += puntadas_cambios
                    totales_operador[operador]['total'] += sum(r['TOTAL_PUNTADAS'] for r in resultados if r['OPERADOR'] == operador and r['FECHA'] == fecha)
        
        # ✅ CREAR DATAFRAME CON RESULTADOS
        df_resultados = pd.DataFrame(resultados)
        
        # ✅ COMBINAR CON CÁLCULOS EXISTENTES (si los hay)
        if df_calculado_existente is not None and not df_calculado_existente.empty:
            # Eliminar duplicados (mantener los cálculos más recientes)
            columnas_comparar = ['OPERADOR', 'FECHA', 'PEDIDO']
            df_combinado = pd.concat([df_calculado_existente, df_resultados]).drop_duplicates(
                subset=columnas_comparar, 
                keep='last'
            )
        else:
            df_combinado = df_resultados
        
        # ✅ GUARDAR EN GOOGLE SHEETS
        if guardar_calculos_en_sheets(df_combinado):
            st.success("✅ Cálculos guardados exitosamente en Google Sheets")
            st.session_state.df_calculado = df_combinado
        else:
            st.error("❌ Error al guardar los cálculos")
        
        # ✅ MOSTRAR RESULTADOS DEL PERÍODO
        st.subheader(f"📊 Resultados del Período {fecha_inicio} a {fecha_fin}")
        
        for operador, datos in totales_operador.items():
            st.write(f"**👤 {operador}** (Máquina de {config_maquinas[operador]} cabezas)")
            
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Órdenes", datos['ordenes'])
            with col2:
                st.metric("Puntadas Múltiplos", f"{datos['puntadas_multiplos']:,.0f}")
            with col3:
                st.metric("Puntadas Cambios", f"{datos['puntadas_cambios']:,.0f}")
            with col4:
                st.metric("**TOTAL**", f"**{datos['total']:,.0f}**")
        
        # ✅ RESUMEN GENERAL DEL PERÍODO
        st.subheader(f"🏆 Resumen General del Período")
        
        total_general = sum(datos['total'] for datos in totales_operador.values())
        total_multiplos_general = sum(datos['puntadas_multiplos'] for datos in totales_operador.values())
        total_cambios_general = sum(datos['puntadas_cambios'] for datos in totales_operador.values())
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Operadores Activos", len(totales_operador))
        with col2:
            st.metric("Total Puntadas Múltiplos", f"{total_multiplos_general:,.0f}")
        with col3:
            st.metric("Total Puntadas Cambios", f"{total_cambios_general:,.0f}")
        with col4:
            st.metric("**TOTAL PERÍODO**", f"**{total_general:,.0f}**")
        
        return df, df_combinado
    
    else:
        st.info("👆 Configura las fechas y haz clic en 'Calcular y Guardar Puntadas'")
        return df, df_calculado_existente

def mostrar_consultas_operadores(df_calculado):
    """Interfaz para que los operadores consulten sus puntadas calculadas"""
    
    if df_calculado is None or df_calculado.empty:
        st.info("ℹ️ No hay cálculos guardados. Ejecuta el cálculo automático primero.")
        return
    
    st.header("👤 Consulta de Puntadas por Operador")
    
    # Selección de operador
    operadores = sorted(df_calculado["OPERADOR"].unique())
    operador_seleccionado = st.selectbox("Selecciona tu operador:", operadores)
    
    if operador_seleccionado:
        # Filtrar datos del operador
        df_operador = df_calculado[df_calculado["OPERADOR"] == operador_seleccionado].copy()
        
        # Filtros adicionales
        col1, col2 = st.columns(2)
        with col1:
            fechas = sorted(df_operador["FECHA"].unique())
            fecha_seleccionada = st.selectbox("Filtrar por fecha:", ["Todas"] + fechas)
        with col2:
            pedidos = sorted(df_operador["PEDIDO"].unique())
            pedido_seleccionado = st.selectbox("Filtrar por pedido:", ["Todos"] + pedidos)
        
        # Aplicar filtros
        if fecha_seleccionada != "Todas":
            df_operador = df_operador[df_operador["FECHA"] == fecha_seleccionada]
        if pedido_seleccionado != "Todos":
            df_operador = df_operador[df_operador["PEDIDO"] == pedido_seleccionado]
        
        # Mostrar métricas del operador
        st.subheader(f"📊 Resumen de {operador_seleccionado}")
        
        if not df_operador.empty:
            total_puntadas = df_operador["TOTAL_PUNTADAS"].sum()
            total_pedidos = len(df_operador)
            promedio_puntadas = total_puntadas / total_pedidos if total_pedidos > 0 else 0
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Pedidos", total_pedidos)
            with col2:
                st.metric("Total Puntadas", f"{total_puntadas:,.0f}")
            with col3:
                st.metric("Promedio por Pedido", f"{promedio_puntadas:,.0f}")
            
            # Gráfico de puntadas por fecha
            st.subheader("📈 Evolución de Puntadas")
            puntadas_por_fecha = df_operador.groupby("FECHA")["TOTAL_PUNTADAS"].sum().reset_index()
            
            fig = px.line(
                puntadas_por_fecha,
                x="FECHA",
                y="TOTAL_PUNTADAS",
                title=f"Puntadas de {operador_seleccionado} por Fecha",
                markers=True
            )
            st.plotly_chart(fig, use_container_width=True)
            
            # Detalle de pedidos
            st.subheader("📋 Detalle de Pedidos")
            columnas_mostrar = ['FECHA', 'PEDIDO', 'TIPO_PRENDA', 'DISEÑO', 'CANTIDAD', 
                               'PUNTADAS_MULTIPLOS', 'PUNTADAS_CAMBIOS', 'TOTAL_PUNTADAS']
            columnas_disponibles = [col for col in columnas_mostrar if col in df_operador.columns]
            
            st.dataframe(df_operador[columnas_disponibles], use_container_width=True)
            
            # Opción para descargar
            csv = df_operador[columnas_disponibles].to_csv(index=False)
            st.download_button(
                label="📥 Descargar Mis Puntadas",
                data=csv,
                file_name=f"puntadas_{operador_seleccionado}.csv",
                mime="text/csv"
            )
        else:
            st.warning("No hay datos para los filtros seleccionados")

# ✅ FINALMENTE: La función principal MODIFICADA

def mostrar_dashboard_produccion():
    try:
        # ✅ BOTÓN DE REFRESH EN SIDEBAR
        st.sidebar.header("🔄 Actualizar Datos")
        if st.sidebar.button("🔄 Actualizar Datos en Tiempo Real", use_container_width=True):
            # Limpiar cache de datos para forzar recarga
            if 'df_produccion' in st.session_state:
                del st.session_state['df_produccion']
            if 'df_calculado' in st.session_state:
                del st.session_state['df_calculado']
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
            
            # ✅ CARGAR DATOS DE PRODUCCIÓN
            sheet_id = st.secrets["gsheets"]["produccion_sheet_id"]
            worksheet = gc.open_by_key(sheet_id).worksheet("reporte_de_trabajo")
            data = worksheet.get_all_values()
            df_raw = pd.DataFrame(data[1:], columns=data[0])
            
            # ✅ INTENTAR CARGAR DATOS CALCULADOS (si existen)
            try:
                worksheet_calculado = gc.open_by_key(sheet_id).worksheet("puntadas_calculadas")
                data_calculado = worksheet_calculado.get_all_values()
                if len(data_calculado) > 1:
                    df_calculado = pd.DataFrame(data_calculado[1:], columns=data_calculado[0])
                else:
                    df_calculado = pd.DataFrame()
            except:
                df_calculado = pd.DataFrame()
            
            return df_raw, df_calculado
        
        # Cargar datos (usando cache)
        df_raw, df_calculado = cargar_datos_desde_sheets()
        
        # ✅ LIMPIAR Y PROCESAR DATOS
        df = limpiar_dataframe(df_raw)
        
        # ✅ MOSTRAR DASHBOARD
        mostrar_interfaz_dashboard(df, df_calculado)
        
    except Exception as e:
        st.error(f"❌ Error al cargar los datos: {str(e)}")
        st.info("⚠️ Verifica que la hoja de cálculo esté accesible y la estructura sea correcta")

def mostrar_interfaz_dashboard(df, df_calculado=None):
    """Interfaz principal del dashboard"""
    
    st.title("🏭 Dashboard de Producción")
    
    # Mostrar resumen rápido
    st.info(f"**Base de datos cargada:** {len(df)} registros de producción")
    if df_calculado is not None and not df_calculado.empty:
        st.success(f"**Cálculos guardados:** {len(df_calculado)} registros calculados")
    
    # ✅ FILTROS
    df_filtrado = aplicar_filtros(df)
    
    # ✅ PESTAÑAS PRINCIPALES
    tab1, tab2, tab3 = st.tabs(["📊 Dashboard Principal", "🧵 Calcular Puntadas", "👤 Consultar Mis Puntadas"])
    
    with tab1:
        # ✅ MÉTRICAS PRINCIPALES
        mostrar_metricas_principales(df_filtrado)
        
        # ✅ ANÁLISIS POR OPERADOR
        mostrar_analisis_operadores(df_filtrado)
        
        # ✅ ANÁLISIS ESPECÍFICO DE PUNTADAS
        mostrar_analisis_puntadas(df_filtrado)
        
        # ✅ ANÁLISIS DE PEDIDOS
        mostrar_analisis_pedidos(df_filtrado)
        
        # ✅ TENDENCIAS TEMPORALES
        mostrar_tendencias_temporales(df_filtrado)
        
        # ✅ DATOS DETALLADOS
        st.subheader("📋 Datos Detallados de Producción")
        st.dataframe(df_filtrado, use_container_width=True, height=400)
    
    with tab2:
        # ✅ CÁLCULO AUTOMÁTICO DE PUNTADAS
        df_actualizado, df_calculado_actualizado = calcular_puntadas_automaticas(df_filtrado, df_calculado)
    
    with tab3:
        # ✅ CONSULTA PARA OPERADORES
        mostrar_consultas_operadores(df_calculado)
