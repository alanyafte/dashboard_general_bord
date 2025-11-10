import gspread
import pandas as pd
import matplotlib.pyplot as plt
import plotly.express as px
import numpy as np
import streamlit as st
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
from datetime import timedelta

# ✅ FUNCIONES ESENCIALES (backend)
def limpiar_dataframe(df_raw):
    """Limpiar y procesar el dataframe"""
    df = df_raw.copy()
    
    if "Dirección de correo electrónico" in df.columns:
        df = df.drop("Dirección de correo electrónico", axis=1)
    
    df.columns = df.columns.str.strip()
    for col in df.columns:
        if df[col].dtype == 'object':
            df[col] = df[col].str.strip()
    
    if "Marca temporal" in df.columns:
        df["Marca temporal"] = pd.to_datetime(df["Marca temporal"], format='%d/%m/%Y %H:%M:%S', errors='coerce')
    
    if "CANTIDAD" in df.columns:
        df["CANTIDAD"] = pd.to_numeric(df["CANTIDAD"], errors='coerce')
    
    if "PUNTADAS" in df.columns:
        df["PUNTADAS"] = pd.to_numeric(df["PUNTADAS"], errors='coerce')
        df["PUNTADAS"] = df["PUNTADAS"].fillna(0)
    
    if "MULTIPLOS" in df.columns:
        df["MULTIPLOS"] = pd.to_numeric(df["MULTIPLOS"], errors='coerce')
    
    return df

def aplicar_filtros(df):
    """Aplicar filtros interactivos"""
    df_filtrado = df.copy()
    
    st.sidebar.header("🔍 Filtros")
    
    if "OPERADOR" in df.columns:
        operadores = sorted(df["OPERADOR"].unique())
        operadores_seleccionados = st.sidebar.multiselect(
            "Operadores:",
            options=operadores,
            default=operadores
        )
        if operadores_seleccionados:
            df_filtrado = df_filtrado[df_filtrado["OPERADOR"].isin(operadores_seleccionados)]
    
    if "Marca temporal" in df.columns and not df_filtrado["Marca temporal"].isna().all():
        fechas_disponibles = df_filtrado["Marca temporal"].dropna()
        if not fechas_disponibles.empty:
            fecha_min = fechas_disponibles.min().to_pydatetime().date()
            fecha_max = fechas_disponibles.max().to_pydatetime().date()
            
            rango_fechas = st.sidebar.date_input(
                "Rango de Fechas:",
                value=(fecha_min, fecha_max),
                min_value=fecha_min,
                max_value=fecha_max
            )
            
            if len(rango_fechas) == 2:
                fecha_inicio, fecha_fin = rango_fechas
                fecha_inicio_dt = pd.to_datetime(fecha_inicio)
                fecha_fin_dt = pd.to_datetime(fecha_fin) + timedelta(days=1)
                
                mask = (df_filtrado["Marca temporal"] >= fecha_inicio_dt) & \
                       (df_filtrado["Marca temporal"] < fecha_fin_dt)
                df_filtrado = df_filtrado[mask]
    
    st.sidebar.info(f"📊 Registros filtrados: {len(df_filtrado)}")
    return df_filtrado

def calcular_puntadas_automaticamente(df):
    """Calcular automáticamente las puntadas"""
    CONFIG_MAQUINAS = {
        "Susi": 6, "Juan": 6, "Esmeralda": 6, "Rigoberto": 2, "Maricela": 2
    }
    CABEZAS_POR_DEFECTO = 6
    
    if df.empty or "OPERADOR" not in df.columns:
        return pd.DataFrame()
    
    resultados = []
    df_con_fecha = df.copy()
    df_con_fecha['Fecha'] = df_con_fecha['Marca temporal'].dt.date
    grupos = df_con_fecha.groupby(['OPERADOR', 'Fecha'])
    
    for (operador, fecha), grupo in grupos:
        for idx, (indice_fila, fila) in enumerate(grupo.iterrows()):
            if pd.isna(fila.get("CANTIDAD")) or pd.isna(fila.get("PUNTADAS")):
                continue
                
            piezas = fila["CANTIDAD"]
            puntadas_base = fila["PUNTADAS"]
            
            cabezas = None
            posibles_nombres_columnas = ["CABEZAS", "NO_DE_CABEZAS", "NUMERO_CABEZAS", "NO CABEZAS"]
            
            for nombre_columna in posibles_nombres_columnas:
                if nombre_columna in fila and not pd.isna(fila[nombre_columna]):
                    try:
                        cabezas = float(fila[nombre_columna])
                        break
                    except (ValueError, TypeError):
                        continue
            
            if cabezas is None:
                cabezas = CONFIG_MAQUINAS.get(operador, CABEZAS_POR_DEFECTO)
            
            pasadas = np.ceil(piezas / cabezas)
            multiplo = pasadas * cabezas
            puntadas_ajustadas = max(puntadas_base, 4000)
            puntadas_multiplos = multiplo * puntadas_ajustadas
            
            if idx == 0:
                puntadas_cambios = 36000 + 18000
            else:
                puntadas_cambios = 18000
            
            total_puntadas = puntadas_multiplos + puntadas_cambios
            
            resultados.append({
                'OPERADOR': operador,
                'FECHA': fecha,
                'PEDIDO': fila.get('#DE PEDIDO', 'N/A'),
                'TIPO_PRENDA': fila.get('TIPO DE PRENDA', 'N/A'),
                'DISEÑO': fila.get('DISEÑO', 'N/A'),
                'CANTIDAD': piezas,
                'PUNTADAS_BASE': puntadas_base,
                'CABEZAS': cabezas,
                'PASADAS': pasadas,
                'MULTIPLO': multiplo,
                'PUNTADAS_MULTIPLOS': puntadas_multiplos,
                'PUNTADAS_CAMBIOS': puntadas_cambios,
                'TOTAL_PUNTADAS': total_puntadas,
                'FECHA_CALCULO': datetime.now().date()
            })
    
    return pd.DataFrame(resultados)

# ✅ DASHBOARD PRINCIPAL - SIMPLIFICADO
def mostrar_dashboard_principal(df, df_calculado=None):
    """Dashboard principal optimizado"""
    
    # Métricas principales
    st.subheader("📈 Métricas de Producción")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_pedidos = len(df)
        st.metric("Total Pedidos", f"{total_pedidos:,}")
    
    with col2:
        if "CANTIDAD" in df.columns:
            total_unidades = df["CANTIDAD"].sum()
            st.metric("Total Unidades", f"{total_unidades:,}")
        else:
            st.metric("Operadores", df["OPERADOR"].nunique())
    
    with col3:
        if "OPERADOR" in df.columns:
            operadores_activos = df["OPERADOR"].nunique()
            st.metric("Operadores", operadores_activos)
    
    with col4:
        if df_calculado is not None and not df_calculado.empty and "TOTAL_PUNTADAS" in df_calculado.columns:
            total_puntadas = df_calculado["TOTAL_PUNTADAS"].sum()
            st.metric("Total Puntadas", f"{total_puntadas:,.0f}")
    
    # Análisis por operador en pestañas
    tab1, tab2, tab3 = st.tabs(["👥 Operadores", "📊 Tendencias", "📋 Datos"])
    
    with tab1:
        mostrar_analisis_operadores_simplificado(df, df_calculado)
    
    with tab2:
        mostrar_tendencias_compactas(df, df_calculado)
    
    with tab3:
        with st.expander("📊 Ver datos detallados de producción", expanded=False):
            st.dataframe(df, use_container_width=True, height=400)

def mostrar_analisis_operadores_simplificado(df, df_calculado=None):
    """Análisis de operadores simplificado"""
    if df.empty or "OPERADOR" not in df.columns:
        return
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Top operadores por puntadas calculadas
        if df_calculado is not None and not df_calculado.empty:
            puntadas_operador = df_calculado.groupby("OPERADOR")["TOTAL_PUNTADAS"].sum()\
                .sort_values(ascending=False).head(10).reset_index()
            puntadas_operador.columns = ['Operador', 'Total Puntadas']
            
            st.write("**🏆 Top Operadores por Puntadas:**")
            st.dataframe(puntadas_operador, use_container_width=True)
    
    with col2:
        # Métricas básicas por operador
        metricas_operador = df.groupby("OPERADOR").agg({
            '#DE PEDIDO': 'count',
            'CANTIDAD': 'sum' if 'CANTIDAD' in df.columns else None
        }).reset_index()
        
        if 'CANTIDAD' in df.columns:
            metricas_operador.columns = ['Operador', 'Total Pedidos', 'Total Unidades']
        else:
            metricas_operador.columns = ['Operador', 'Total Pedidos']
        
        st.write("**📊 Desempeño por Operador:**")
        st.dataframe(metricas_operador, use_container_width=True)

def mostrar_tendencias_compactas(df, df_calculado=None):
    """Tendencias temporales en formato compacto"""
    if df.empty or "Marca temporal" not in df.columns:
        st.info("No hay datos temporales disponibles.")
        return
    
    try:
        df_temporal = df.copy()
        df_temporal['Fecha'] = df_temporal['Marca temporal'].dt.date
        
        tendencias = df_temporal.groupby('Fecha').agg({
            '#DE PEDIDO': 'count',
            'CANTIDAD': 'sum' if 'CANTIDAD' in df.columns else None
        }).reset_index()
        
        if len(tendencias) > 1:
            # Gráfico combinado compacto
            fig = px.line(
                tendencias, 
                x='Fecha', 
                y=['#DE PEDIDO', 'CANTIDAD'] if 'CANTIDAD' in tendencias.columns else ['#DE PEDIDO'],
                title="Tendencias de Producción",
                markers=True
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Se necesitan datos de más de un día para mostrar tendencias.")
            
    except Exception as e:
        st.error(f"Error al generar tendencias: {str(e)}")

# ✅ CONSULTA DE OPERADORES - SIMPLIFICADA
def mostrar_consultas_operadores(df_calculado, df_resumen):
    """Interfaz simplificada para consulta de operadores"""
    
    if df_calculado is None or df_calculado.empty:
        st.info("ℹ️ No hay cálculos disponibles.")
        return
    
    # Selección de operador
    operadores = sorted(df_calculado["OPERADOR"].unique())
    if not operadores:
        st.info("No hay operadores con cálculos disponibles.")
        return
        
    operador_seleccionado = st.selectbox(
        "Selecciona tu operador:", 
        [""] + operadores,
        index=0
    )
    
    if not operador_seleccionado:
        st.info("👆 Selecciona tu nombre para ver tus puntadas y comisiones")
        return
    
    # Filtrar datos del operador
    df_operador = df_calculado[df_calculado["OPERADOR"] == operador_seleccionado].copy()
    
    if df_operador.empty:
        st.warning("No hay datos para el operador seleccionado.")
        return
    
    # Resumen de puntadas
    st.subheader(f"📊 Resumen de {operador_seleccionado}")
    
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
    
    # Gráfico opcional
    with st.expander("📈 Ver evolución de puntadas", expanded=False):
        if 'FECHA' in df_operador.columns and len(df_operador['FECHA'].unique()) > 1:
            puntadas_por_fecha = df_operador.groupby("FECHA")["TOTAL_PUNTADAS"].sum().reset_index()
            puntadas_por_fecha = puntadas_por_fecha.sort_values("FECHA")
            
            fig = px.line(
                puntadas_por_fecha,
                x="FECHA",
                y="TOTAL_PUNTADAS",
                title=f"Puntadas de {operador_seleccionado}",
                markers=True
            )
            st.plotly_chart(fig, use_container_width=True)
    
    # Detalle de pedidos
    st.subheader("📋 Detalle de Pedidos")
    columnas_mostrar = ['FECHA', 'PEDIDO', 'TIPO_PRENDA', 'DISEÑO', 'CANTIDAD', 'TOTAL_PUNTADAS']
    columnas_disponibles = [col for col in columnas_mostrar if col in df_operador.columns]
    
    df_mostrar = df_operador[columnas_disponibles].copy()
    
    if 'FECHA' in df_mostrar.columns:
        df_mostrar['FECHA'] = df_mostrar['FECHA'].astype(str)
    
    if 'TOTAL_PUNTADAS' in df_mostrar.columns:
        df_mostrar['TOTAL_PUNTADAS'] = df_mostrar['TOTAL_PUNTADAS'].apply(lambda x: f"{x:,.0f}")
    
    if 'CANTIDAD' in df_mostrar.columns:
        df_mostrar['CANTIDAD'] = df_mostrar['CANTIDAD'].apply(lambda x: f"{x:,.0f}")
    
    st.dataframe(df_mostrar, use_container_width=True)
    
    # Comisiones (simplificado)
    mostrar_comisiones_simplificadas(df_resumen, operador_seleccionado)

def mostrar_comisiones_simplificadas(df_resumen, operador_seleccionado):
    """Comisiones simplificadas"""
    
    if df_resumen is None or df_resumen.empty:
        return
    
    df_comisiones = df_resumen[df_resumen['OPERADOR'] == operador_seleccionado].copy()
    
    if df_comisiones.empty:
        st.info("💰 No hay comisiones registradas aún.")
        return
    
    st.subheader("💰 Comisiones y Bonificaciones")
    
    # Selector de vista
    vista_seleccionada = st.radio(
        "Tipo de vista:",
        ["Todo el Historial", "Períodos de Corte"],
        horizontal=True
    )
    
    # Aplicar filtro simple de períodos
    if vista_seleccionada == "Períodos de Corte" and 'FECHA' in df_comisiones.columns:
        try:
            if df_comisiones['FECHA'].dtype == 'object':
                df_comisiones['FECHA'] = pd.to_datetime(df_comisiones['FECHA'], errors='coerce')
            
            if pd.api.types.is_datetime64_any_dtype(df_comisiones['FECHA']):
                df_comisiones['DIA'] = df_comisiones['FECHA'].dt.day
                df_comisiones = df_comisiones[
                    ((df_comisiones['DIA'] >= 1) & (df_comisiones['DIA'] <= 10)) |
                    ((df_comisiones['DIA'] >= 11) & (df_comisiones['DIA'] <= 25))
                ]
        except:
            pass
    
    # Métricas de comisiones
    total_comision = 0
    total_puntadas = 0
    
    if not df_comisiones.empty:
        if 'COMISION_TOTAL' in df_comisiones.columns:
            total_comision = pd.to_numeric(df_comisiones['COMISION_TOTAL'], errors='coerce').sum()
        if 'TOTAL_PUNTADAS' in df_comisiones.columns:
            total_puntadas = pd.to_numeric(df_comisiones['TOTAL_PUNTADAS'], errors='coerce').sum()
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Puntadas", f"{total_puntadas:,.0f}")
    with col2:
        st.metric("Total Comisión", f"${total_comision:,.2f}" if total_comision > 0 else "Por calcular")
    with col3:
        if total_puntadas > 0 and total_comision > 0:
            tasa = (total_comision / total_puntadas) * 1000
            st.metric("Tasa x 1000", f"${tasa:.2f}")
    
    # Tabla simplificada
    columnas_comisiones = ['FECHA', 'TOTAL_PUNTADAS', 'COMISION_TOTAL']
    columnas_disponibles = [col for col in columnas_comisiones if col in df_comisiones.columns]
    
    if columnas_disponibles:
        df_mostrar = df_comisiones[columnas_disponibles].copy()
        
        if 'FECHA' in df_mostrar.columns:
            df_mostrar['FECHA'] = df_mostrar['FECHA'].dt.strftime('%Y-%m-%d')
        
        if 'TOTAL_PUNTADAS' in df_mostrar.columns:
            df_mostrar['TOTAL_PUNTADAS'] = df_mostrar['TOTAL_PUNTADAS'].apply(lambda x: f"{x:,.0f}")
        
        if 'COMISION_TOTAL' in df_mostrar.columns:
            df_mostrar['COMISION_TOTAL'] = df_mostrar['COMISION_TOTAL'].apply(
                lambda x: f"${x:,.2f}" if pd.notna(x) and x != 0 else "Por calcular"
            )
        
        st.dataframe(df_mostrar, use_container_width=True)

# ✅ FUNCIONES PRINCIPALES (backend necesario)
def cargar_datos():
    """Cargar datos desde Google Sheets"""
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
        worksheet = gc.open_by_key(sheet_id).worksheet("reporte_de_trabajo")
        data = worksheet.get_all_values()
        df_raw = pd.DataFrame(data[1:], columns=data[0])
        
        df = limpiar_dataframe(df_raw)
        df_calculado = calcular_puntadas_automaticamente(df)
        
        # Cargar resumen ejecutivo si existe
        try:
            worksheet_resumen = gc.open_by_key(sheet_id).worksheet("resumen_ejecutivo")
            datos_resumen = worksheet_resumen.get_all_values()
            if len(datos_resumen) > 1:
                df_resumen = pd.DataFrame(datos_resumen[1:], columns=datos_resumen[0])
                # Conversiones básicas
                if 'TOTAL_PUNTADAS' in df_resumen.columns:
                    df_resumen['TOTAL_PUNTADAS'] = pd.to_numeric(df_resumen['TOTAL_PUNTADAS'], errors='coerce')
                if 'COMISION_TOTAL' in df_resumen.columns:
                    df_resumen['COMISION_TOTAL'] = pd.to_numeric(df_resumen['COMISION_TOTAL'], errors='coerce')
            else:
                df_resumen = pd.DataFrame()
        except:
            df_resumen = pd.DataFrame()
        
        return df, df_calculado, df_resumen
        
    except Exception as e:
        st.error(f"❌ Error al cargar datos: {str(e)}")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

# ✅ INTERFAZ PRINCIPAL
def main():
    st.set_page_config(page_title="Dashboard Producción", layout="wide")
    st.title("🏭 Dashboard de Producción")
    
    # Botón de actualización
    if st.sidebar.button("🔄 Actualizar Datos", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
    
    # Cargar datos
    df, df_calculado, df_resumen = cargar_datos()
    
    if df.empty:
        st.error("No se pudieron cargar los datos. Verifica la conexión.")
        return
    
    # Info resumen
    st.sidebar.info(f"📊 Registros: {len(df)}")
    if not df_calculado.empty:
        st.sidebar.success(f"🧵 Cálculos: {len(df_calculado)}")
    
    # Pestañas principales
    tab1, tab2 = st.tabs(["📊 Dashboard Principal", "👤 Mis Puntadas y Comisiones"])
    
    with tab1:
        df_filtrado = aplicar_filtros(df)
        mostrar_dashboard_principal(df_filtrado, df_calculado)
    
    with tab2:
        st.info("🔍 Consulta tus puntadas calculadas y comisiones")
        mostrar_consultas_operadores(df_calculado, df_resumen)

if __name__ == "__main__":
    main()
