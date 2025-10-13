import gspread
import pandas as pd
import matplotlib.pyplot as plt
import plotly.express as px
import numpy as np
import streamlit as st
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
from datetime import timedelta

# ✅ FUNCIONES DE LIMPIEZA Y ANÁLISIS (las que ya tenías)
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
    
    # ✅ CORREGIDO: Filtro por fecha (Marca temporal)
    if "Marca temporal" in df.columns and not df_filtrado["Marca temporal"].isna().all():
        fechas_disponibles = df_filtrado["Marca temporal"].dropna()
        if not fechas_disponibles.empty:
            # Convertir a fecha sin hora para el date_input
            fecha_min = fechas_disponibles.min().to_pydatetime().date()
            fecha_max = fechas_disponibles.max().to_pydatetime().date()
            
            rango_fechas = st.sidebar.date_input(
                "Rango de Fechas:",
                value=(fecha_min, fecha_max),
                min_value=fecha_min,
                max_value=fecha_max
            )
            
            # ✅ CORREGIDO: Verificar que se seleccionaron 2 fechas
            if len(rango_fechas) == 2:
                fecha_inicio, fecha_fin = rango_fechas
                # Convertir a datetime para comparación
                fecha_inicio_dt = pd.to_datetime(fecha_inicio)
                fecha_fin_dt = pd.to_datetime(fecha_fin) + timedelta(days=1)  # Incluir todo el día final
                
                mask = (df_filtrado["Marca temporal"] >= fecha_inicio_dt) & \
                       (df_filtrado["Marca temporal"] < fecha_fin_dt)
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

# ✅ NUEVA FUNCIÓN: Métricas con cálculos automáticos
def mostrar_metricas_principales(df, df_calculado=None):
    """Mostrar métricas principales de producción INCLUYENDO CÁLCULOS AUTOMÁTICOS"""
    
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
        # ✅ MÉTRICA MEJORADA: Usar cálculos automáticos si están disponibles
        if df_calculado is not None and not df_calculado.empty and "TOTAL_PUNTADAS" in df_calculado.columns:
            total_puntadas_calculadas = df_calculado["TOTAL_PUNTADAS"].sum()
            st.metric("Total Puntadas Calculadas", f"{total_puntadas_calculadas:,.0f}")
        elif "PUNTADAS" in df.columns:
            total_puntadas = df["PUNTADAS"].sum()
            st.metric("Total Puntadas Base", f"{total_puntadas:,.0f}")
        else:
            st.metric("Pedidos Únicos", df["#DE PEDIDO"].nunique())

# ✅ NUEVA FUNCIÓN: Análisis con cálculos automáticos
def mostrar_analisis_puntadas_calculadas(df_calculado):
    """Análisis específico de puntadas CALCULADAS"""
    
    if df_calculado is None or df_calculado.empty or "TOTAL_PUNTADAS" not in df_calculado.columns:
        st.info("No hay cálculos de puntadas disponibles para mostrar.")
        return
    
    st.subheader("🪡 Análisis de Puntadas Calculadas")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Top operadores por puntadas calculadas
        puntadas_por_operador = df_calculado.groupby("OPERADOR")["TOTAL_PUNTADAS"].sum().sort_values(ascending=False).reset_index()
        puntadas_por_operador.columns = ['Operador', 'Total Puntadas Calculadas']
        
        st.write("**🏆 Ranking por Puntadas Calculadas:**")
        st.dataframe(puntadas_por_operador, use_container_width=True)
    
    with col2:
        # Distribución de puntadas calculadas por tipo de prenda
        if "TIPO_PRENDA" in df_calculado.columns:
            puntadas_por_prenda = df_calculado.groupby("TIPO_PRENDA")["TOTAL_PUNTADAS"].sum().reset_index()
            puntadas_por_prenda.columns = ['Tipo de Prenda', 'Total Puntadas Calculadas']
            
            if len(puntadas_por_prenda) > 0:
                fig = px.pie(
                    puntadas_por_prenda, 
                    values='Total Puntadas Calculadas', 
                    names='Tipo de Prenda',
                    title="Distribución de Puntadas Calculadas por Tipo de Prenda"
                )
                st.plotly_chart(fig, use_container_width=True)

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
    
    st.subheader("🪡 Análisis de Puntadas Base")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Top operadores por puntadas
        puntadas_por_operador = df.groupby("OPERADOR")["PUNTADAS"].sum().sort_values(ascending=False).reset_index()
        puntadas_por_operador.columns = ['Operador', 'Total Puntadas']
        
        st.write("**🏆 Ranking por Puntadas Base:**")
        st.dataframe(puntadas_por_operador, use_container_width=True)
    
    with col2:
        # Distribución de puntadas por tipo de prenda
        if "TIPO DE PRENDA" in df.columns:
            puntadas_por_prenda = df.groupby("TIPO DE PRENDA")["PUNTADAS"].sum().reset_index()
            puntadas_por_prenda.columns = ['Tipo de Prenda', 'Total Puntadas']
            
            if len(puntadas_por_prenda) > 0:
                fig = px.pie(
                    puntadas_por_prenda, 
                    values='Total Puntadas', 
                    names='Tipo de Prenda',
                    title="Distribución de Puntadas Base por Tipo de Prenda"
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
            
            if len(tipos_prenda) > 0:
                fig = px.pie(
                    tipos_prenda, 
                    values='Cantidad', 
                    names='Tipo de Prenda',
                    title="Distribución por Tipo de Prenda"
                )
                st.plotly_chart(fig, use_container_width=True)

# ✅ CORREGIDO COMPLETAMENTE: Función de tendencias temporales
def mostrar_tendencias_temporales(df, df_calculado=None):
    """Mostrar tendencias a lo largo del tiempo INCLUYENDO CÁLCULOS"""
    
    if df.empty or "Marca temporal" not in df.columns:
        st.info("No hay datos temporales disponibles para mostrar tendencias.")
        return
    
    st.subheader("📈 Tendencias Temporales")
    
    try:
        # ✅ CORREGIDO: Crear columna de fecha correctamente
        df_temporal = df.copy()
        df_temporal['Fecha'] = df_temporal['Marca temporal'].dt.date
        
        # Agrupar por fecha
        tendencias = df_temporal.groupby('Fecha').agg({
            '#DE PEDIDO': 'count',
            'CANTIDAD': 'sum' if 'CANTIDAD' in df.columns else None,
            'PUNTADAS': 'sum' if 'PUNTADAS' in df.columns else None
        }).reset_index()
        
        # ✅ CORREGIDO: AGREGAR TENDENCIAS DE CÁLCULOS SI ESTÁN DISPONIBLES
        if df_calculado is not None and not df_calculado.empty and "TOTAL_PUNTADAS" in df_calculado.columns:
            df_calc_temporal = df_calculado.copy()
            if 'FECHA' in df_calc_temporal.columns:
                # Asegurar que FECHA sea tipo fecha
                if df_calc_temporal['FECHA'].dtype == 'object':
                    df_calc_temporal['FECHA'] = pd.to_datetime(df_calc_temporal['FECHA']).dt.date
                
                # Agrupar cálculos por fecha
                tendencias_calc = df_calc_temporal.groupby('FECHA')['TOTAL_PUNTADAS'].sum().reset_index()
                tendencias_calc.columns = ['Fecha', 'TOTAL_PUNTADAS']  # Renombrar para merge
                
                # Hacer merge con las tendencias principales
                tendencias = tendencias.merge(tendencias_calc, on='Fecha', how='left')
        
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
                    title="Evolución de Puntadas Base por Día",
                    markers=True,
                    color_discrete_sequence=['red']
                )
                st.plotly_chart(fig2, use_container_width=True)
            
            # ✅ NUEVO GRÁFICO: Puntadas calculadas por día
            if "TOTAL_PUNTADAS" in tendencias.columns and not tendencias["TOTAL_PUNTADAS"].isna().all():
                fig3 = px.line(
                    tendencias, 
                    x='Fecha', 
                    y='TOTAL_PUNTADAS',
                    title="Evolución de Puntadas Calculadas por Día",
                    markers=True,
                    color_discrete_sequence=['green']
                )
                st.plotly_chart(fig3, use_container_width=True)
        else:
            st.info("Se necesitan datos de más de un día para mostrar tendencias.")
            
    except Exception as e:
        st.error(f"Error al generar tendencias temporales: {str(e)}")
        # Mostrar información de debug
        st.info("Columnas disponibles en los datos:")
        st.info(f"{list(df.columns)}")

# ✅ NUEVAS FUNCIONES PARA CÁLCULOS AUTOMÁTICOS
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
        
        # Limpiar la hoja existente
        worksheet.clear()
        
        # ✅ CONVERTIR FECHAS A STRING ANTES DE GUARDAR
        df_para_guardar = df_calculado.copy()
        
        # Convertir columnas de fecha a string
        date_columns = ['FECHA', 'FECHA_CALCULO']
        for col in date_columns:
            if col in df_para_guardar.columns:
                df_para_guardar[col] = df_para_guardar[col].astype(str)
        
        # Convertir DataFrame a lista de listas
        datos_para_guardar = [df_para_guardar.columns.tolist()] + df_para_guardar.values.tolist()
        
        # Escribir todos los datos
        worksheet.update('A1', datos_para_guardar)
        
        return True
    except Exception as e:
        st.error(f"❌ Error al guardar cálculos: {str(e)}")
        return False

def calcular_puntadas_automaticamente(df):
    """Calcular automáticamente las puntadas cuando se cargan los datos"""
    
    # CONFIGURACIÓN FIJA DE MÁQUINAS (puedes ajustar estos valores)
    CONFIG_MAQUINAS = {
        "Susi": 6,
        "Juan": 6,
        "Esmeralda": 6,
        "Rigoberto": 6,
        "Maricela": 2,
        # Agrega más operadores según necesites
    }
    
    # Valor por defecto si el operador no está en la configuración
    CABEZAS_POR_DEFECTO = 6
    
    if df.empty or "OPERADOR" not in df.columns:
        return pd.DataFrame()
    
    resultados = []
    
    # ✅ CORREGIDO: Primero agrupar por operador y fecha para calcular correctamente los cambios
    df_con_fecha = df.copy()
    df_con_fecha['Fecha'] = df_con_fecha['Marca temporal'].dt.date
    
    # Agrupar por operador y fecha
    grupos = df_con_fecha.groupby(['OPERADOR', 'Fecha'])
    
    for (operador, fecha), grupo in grupos:
        cabezas = CONFIG_MAQUINAS.get(operador, CABEZAS_POR_DEFECTO)
        ordenes_dia = len(grupo)
        
        # ✅ CORREGIDO: Calcular cambios de color por ORDEN (no por día completo)
        for idx, (indice_fila, fila) in enumerate(grupo.iterrows()):
            # Verificar que tenemos los datos necesarios
            if pd.isna(fila.get("CANTIDAD")) or pd.isna(fila.get("PUNTADAS")):
                continue
                
            piezas = fila["CANTIDAD"]
            puntadas_base = fila["PUNTADAS"]
            
            # Calcular múltiplos
            pasadas = np.ceil(piezas / cabezas)
            multiplo = pasadas * cabezas
            puntadas_ajustadas = max(puntadas_base, 4000)
            puntadas_multiplos = multiplo * puntadas_ajustadas
            
            # ✅ CORREGIDO: Calcular cambios de color
            # Primera orden del día: 36,000 (inicio turno) + 18,000 (primera orden) = 54,000
            # Órdenes adicionales: 18,000 cada una
            if idx == 0:  # Primera orden del día
                puntadas_cambios = 36000 + 18000  # Inicio turno + primera orden
            else:  # Órdenes adicionales
                puntadas_cambios = 18000  # Solo cambio de color
            
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
                'FECHA_CALCULO': datetime.now().date(),
                'HORA_CALCULO': datetime.now().strftime("%H:%M:%S"),
                'ORDEN_DEL_DIA': idx + 1  # Para debugging: ver el número de orden en el día
            })
    
    return pd.DataFrame(resultados)

def crear_hoja_resumen_ejecutivo():
    """Crear la hoja de resumen ejecutivo si no existe"""
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
        
        # Intentar acceder a la hoja de resumen ejecutivo, o crearla si no existe
        try:
            worksheet = spreadsheet.worksheet("resumen_ejecutivo")
        except:
            worksheet = spreadsheet.add_worksheet(title="resumen_ejecutivo", rows="1000", cols="10")
            
            # Crear encabezados
            encabezados = [
                "FECHA", 
                "OPERADOR", 
                "TOTAL_PUNTADAS", 
                "COMISION", 
                "BONIFICACION", 
                "COMISION_TOTAL",
                "FECHA_ACTUALIZACION",
                "ACTUALIZADO_POR"
            ]
            worksheet.update('A1', [encabezados])
        
        return True
    except Exception as e:
        st.error(f"❌ Error al crear hoja de resumen ejecutivo: {str(e)}")
        return False

def guardar_resumen_ejecutivo(df_calculado):
    """Guardar resumen ejecutivo automáticamente en Google Sheets"""
    try:
        if df_calculado.empty:
            return False
            
        # Crear hoja si no existe
        crear_hoja_resumen_ejecutivo()
        
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
        worksheet = spreadsheet.worksheet("resumen_ejecutivo")
        
        # Obtener datos existentes
        try:
            datos_existentes = worksheet.get_all_values()
            if len(datos_existentes) > 1:
                df_existente = pd.DataFrame(datos_existentes[1:], columns=datos_existentes[0])
            else:
                df_existente = pd.DataFrame()
        except:
            df_existente = pd.DataFrame()
        
        # Calcular resumen por operador y fecha
        resumen = df_calculado.groupby(['OPERADOR', 'FECHA']).agg({
            'TOTAL_PUNTADAS': 'sum'
        }).reset_index()
        
        # Preparar datos para guardar
        nuevos_registros = []
        for _, fila in resumen.iterrows():
            operador = fila['OPERADOR']
            fecha = fila['FECHA']
            total_puntadas = fila['TOTAL_PUNTADAS']
            
            # Verificar si ya existe este registro
            existe = False
            if not df_existente.empty:
                mask = (df_existente['OPERADOR'] == operador) & (df_existente['FECHA'] == str(fecha))
                existe = not df_existente[mask].empty
            
            # Solo agregar si no existe
            if not existe:
                nuevos_registros.append([
                    str(fecha),
                    operador,
                    total_puntadas,
                    "",  # COMISION (vacío para que lo llene el encargado)
                    "",  # BONIFICACION (vacío)
                    "",  # COMISION_TOTAL (vacío)
                    "",  # FECHA_ACTUALIZACION (vacío)
                    ""   # ACTUALIZADO_POR (vacío)
                ])
        
        # Agregar nuevos registros
        if nuevos_registros:
            # Encontrar la última fila con datos
            if datos_existentes:
                ultima_fila = len(datos_existentes) + 1
            else:
                ultima_fila = 2  # Después de los encabezados
            
            # Escribir nuevos registros
            worksheet.update(f'A{ultima_fila}', nuevos_registros)
        
        return True
    except Exception as e:
        st.error(f"❌ Error al guardar resumen ejecutivo: {str(e)}")
        return False

def cargar_resumen_ejecutivo():
    """Cargar datos del resumen ejecutivo desde Google Sheets"""
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
        
        try:
            worksheet = spreadsheet.worksheet("resumen_ejecutivo")
            datos = worksheet.get_all_values()
            
            if len(datos) > 1:
                df_resumen = pd.DataFrame(datos[1:], columns=datos[0])
                
                # Convertir tipos de datos
                if 'TOTAL_PUNTADAS' in df_resumen.columns:
                    df_resumen['TOTAL_PUNTADAS'] = pd.to_numeric(df_resumen['TOTAL_PUNTADAS'], errors='coerce')
                if 'COMISION' in df_resumen.columns:
                    df_resumen['COMISION'] = pd.to_numeric(df_resumen['COMISION'], errors='coerce')
                if 'BONIFICACION' in df_resumen.columns:
                    df_resumen['BONIFICACION'] = pd.to_numeric(df_resumen['BONIFICACION'], errors='coerce')
                if 'COMISION_TOTAL' in df_resumen.columns:
                    df_resumen['COMISION_TOTAL'] = pd.to_numeric(df_resumen['COMISION_TOTAL'], errors='coerce')
                
                return df_resumen
            else:
                return pd.DataFrame()
                
        except:
            return pd.DataFrame()
            
    except Exception as e:
        st.error(f"❌ Error al cargar resumen ejecutivo: {str(e)}")
        return pd.DataFrame()

def mostrar_comisiones_operador(df_resumen, operador_seleccionado):
    """Mostrar comisiones y bonificaciones del operador"""
    
    if df_resumen.empty or operador_seleccionado is None:
        return
    
    # Filtrar comisiones del operador seleccionado
    df_comisiones = df_resumen[df_resumen['OPERADOR'] == operador_seleccionado].copy()
    
    if df_comisiones.empty:
        st.info("💰 **Comisiones**: No hay comisiones registradas para este operador.")
        return
    
    # Ordenar por fecha (más reciente primero)
    df_comisiones = df_comisiones.sort_values('FECHA', ascending=False)
    
    st.subheader("💰 Comisiones y Bonificaciones")
    
    # Mostrar resumen de comisiones
    total_comision = df_comisiones['COMISION_TOTAL'].sum() if 'COMISION_TOTAL' in df_comisiones.columns else 0
    total_puntadas = df_comisiones['TOTAL_PUNTADAS'].sum() if 'TOTAL_PUNTADAS' in df_comisiones.columns else 0
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Puntadas Acumuladas", f"{total_puntadas:,.0f}")
    with col2:
        st.metric("Total Comisión", f"${total_comision:,.2f}" if total_comision > 0 else "Por calcular")
    with col3:
        if total_puntadas > 0:
            tasa_comision = (total_comision / total_puntadas) * 1000 if total_comision > 0 else 0
            st.metric("Tasa por 1000 puntadas", f"${tasa_comision:.2f}")
    
    # Mostrar tabla detallada de comisiones
    st.write("**📋 Detalle de Comisiones por Fecha:**")
    
    columnas_comisiones = ['FECHA', 'TOTAL_PUNTADAS', 'COMISION', 'BONIFICACION', 'COMISION_TOTAL', 'FECHA_ACTUALIZACION']
    columnas_disponibles = [col for col in columnas_comisiones if col in df_comisiones.columns]
    
    df_mostrar_comisiones = df_comisiones[columnas_disponibles].copy()
    
    # Formatear columnas numéricas
    if 'TOTAL_PUNTADAS' in df_mostrar_comisiones.columns:
        df_mostrar_comisiones['TOTAL_PUNTADAS'] = df_mostrar_comisiones['TOTAL_PUNTADAS'].apply(lambda x: f"{x:,.0f}" if pd.notna(x) else "N/A")
    if 'COMISION' in df_mostrar_comisiones.columns:
        df_mostrar_comisiones['COMISION'] = df_mostrar_comisiones['COMISION'].apply(lambda x: f"${x:,.2f}" if pd.notna(x) and x != "" else "Por calcular")
    if 'BONIFICACION' in df_mostrar_comisiones.columns:
        df_mostrar_comisiones['BONIFICACION'] = df_mostrar_comisiones['BONIFICACION'].apply(lambda x: f"${x:,.2f}" if pd.notna(x) and x != "" else "Por calcular")
    if 'COMISION_TOTAL' in df_mostrar_comisiones.columns:
        df_mostrar_comisiones['COMISION_TOTAL'] = df_mostrar_comisiones['COMISION_TOTAL'].apply(lambda x: f"${x:,.2f}" if pd.notna(x) and x != "" else "Por calcular")
    
    st.dataframe(df_mostrar_comisiones, use_container_width=True)
    
    # Opción para descargar comisiones
    csv_comisiones = df_comisiones[columnas_disponibles].to_csv(index=False)
    st.download_button(
        label="📥 Descargar Mis Comisiones",
        data=csv_comisiones,
        file_name=f"comisiones_{operador_seleccionado}.csv",
        mime="text/csv"
    )

# ✅ MODIFICAR la función mostrar_consultas_operadores para incluir comisiones
def mostrar_consultas_operadores(df_calculado, df_resumen):
    """Interfaz para que los operadores consulten sus puntadas calculadas Y comisiones"""
    
    if df_calculado is None or df_calculado.empty:
        st.info("ℹ️ No hay cálculos disponibles. Los cálculos se generan automáticamente.")
        return
    
    st.header("👤 Consulta de Puntadas y Comisiones por Operador")
    
    # ✅ CORREGIDO: Convertir FECHA de string a date si es necesario
    df_consulta = df_calculado.copy()
    if 'FECHA' in df_consulta.columns and df_consulta['FECHA'].dtype == 'object':
        df_consulta['FECHA'] = pd.to_datetime(df_consulta['FECHA']).dt.date
    
    # Selección de operador
    operadores = sorted(df_consulta["OPERADOR"].unique())
    
    if not operadores:
        st.info("No hay operadores con cálculos disponibles.")
        return
        
    # ✅ SOLUCIÓN CORRECTA: Agregar opción vacía al inicio
    operador_seleccionado = st.selectbox(
        "Selecciona tu operador:", 
        [""] + operadores,  # ✅ Opción vacía primero
        index=0  # ✅ Esto selecciona la opción vacía
    )
    
    # ✅ Verificar si se ha seleccionado un operador válido
    if not operador_seleccionado:
        st.info("👆 **Por favor, selecciona tu nombre de la lista para ver tus puntadas y comisiones**")
        st.warning("💡 _Si no encuentras tu nombre, verifica que hayas registrado producción hoy_")
        return
    
    if operador_seleccionado:
        # Filtrar datos del operador
        df_operador = df_consulta[df_consulta["OPERADOR"] == operador_seleccionado].copy()
        
        # Filtros adicionales
        col1, col2 = st.columns(2)
        with col1:
            fechas = sorted(df_operador["FECHA"].unique()) if 'FECHA' in df_operador.columns else []
            fecha_seleccionada = st.selectbox("Filtrar por fecha:", ["Todas"] + fechas)
        with col2:
            pedidos = sorted(df_operador["PEDIDO"].unique())
            pedido_seleccionado = st.selectbox("Filtrar por pedido:", ["Todos"] + pedidos)
        
        # Aplicar filtros
        if fecha_seleccionada != "Todas" and 'FECHA' in df_operador.columns:
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
            if 'FECHA' in df_operador.columns and len(df_operador['FECHA'].unique()) > 1:
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
            
            # ✅ SOLO UN dataframe, no dos
            df_mostrar = df_operador[columnas_disponibles].copy()
            if 'FECHA' in df_mostrar.columns:
                df_mostrar['FECHA'] = df_mostrar['FECHA'].astype(str)
            
            st.dataframe(df_mostrar, use_container_width=True)
            
            # Opción para descargar puntadas
            csv = df_mostrar.to_csv(index=False)
            st.download_button(
                label="📥 Descargar Mis Puntadas",
                data=csv,
                file_name=f"puntadas_{operador_seleccionado}.csv",
                mime="text/csv"
            )
            
            # ✅ NUEVO: Mostrar comisiones del operador
            mostrar_comisiones_operador(df_resumen, operador_seleccionado)
            
        else:
            st.warning("No hay datos para los filtros seleccionados")

# ✅ MODIFICAR la función principal para incluir el resumen ejecutivo
def mostrar_dashboard_produccion():
    try:
        # ✅ BOTÓN DE REFRESH EN SIDEBAR
        st.sidebar.header("🔄 Actualizar Datos")
        if st.sidebar.button("🔄 Actualizar Datos en Tiempo Real", use_container_width=True):
            # Limpiar cache de datos para forzar recarga
            st.cache_data.clear()
            st.rerun()
        
        # ✅ AUTENTICACIÓN CON CACHE
        @st.cache_data(ttl=300)  # Cache de 5 minutos
        def cargar_y_calcular_datos():
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
            
            # ✅ LIMPIAR DATOS
            df = limpiar_dataframe(df_raw)
            
            # ✅ CALCULAR PUNTADAS AUTOMÁTICAMENTE
            df_calculado = calcular_puntadas_automaticamente(df)
            
            # ✅ GUARDAR CÁLCULOS EN SHEETS (si hay datos)
            if not df_calculado.empty:
                try:
                    guardar_calculos_en_sheets(df_calculado)
                    # ✅ NUEVO: Guardar resumen ejecutivo automáticamente
                    guardar_resumen_ejecutivo(df_calculado)
                except Exception as e:
                    st.sidebar.warning(f"⚠️ No se pudieron guardar los cálculos: {e}")
            
            # ✅ NUEVO: Cargar resumen ejecutivo
            df_resumen = cargar_resumen_ejecutivo()
            
            return df, df_calculado, df_resumen
        
        # Cargar y calcular datos automáticamente
        df, df_calculado, df_resumen = cargar_y_calcular_datos()
        
        st.sidebar.info(f"Última actualización: {datetime.now().strftime('%H:%M:%S')}")
        st.sidebar.info(f"📊 Registros: {len(df)}")
        if not df_calculado.empty:
            st.sidebar.success(f"🧵 Cálculos: {len(df_calculado)}")
        if not df_resumen.empty:
            st.sidebar.success(f"💰 Comisiones: {len(df_resumen)} registros")
        
        # ✅ MOSTRAR DASHBOARD
        mostrar_interfaz_dashboard(df, df_calculado, df_resumen)
        
    except Exception as e:
        st.error(f"❌ Error al cargar los datos: {str(e)}")
        st.info("⚠️ Verifica que la hoja de cálculo esté accesible y la estructura sea correcta")

# ✅ MODIFICAR la función de interfaz para incluir el resumen
def mostrar_interfaz_dashboard(df, df_calculado=None, df_resumen=None):
    """Interfaz principal del dashboard"""
    
    st.title("🏭 Dashboard de Producción")
    
    # Mostrar resumen rápido
    st.info(f"**Base de datos cargada:** {len(df)} registros de producción")
    if df_calculado is not None and not df_calculado.empty:
        st.success(f"**Cálculos automáticos:** {len(df_calculado)} registros calculados")
    if df_resumen is not None and not df_resumen.empty:
        st.success(f"**Resumen ejecutivo:** {len(df_resumen)} registros de comisiones")
    
    # ✅ FILTROS
    df_filtrado = aplicar_filtros(df)
    
    # ✅ PESTAÑAS PRINCIPALES
    tab1, tab2 = st.tabs(["📊 Dashboard Principal", "👤 Consultar Mis Puntadas y Comisiones"])
    
    with tab1:
        # ... (mantén todo el contenido del dashboard principal igual)
        mostrar_metricas_principales(df_filtrado, df_calculado)
        mostrar_analisis_puntadas_calculadas(df_calculado)
        mostrar_analisis_operadores(df_filtrado)
        mostrar_analisis_puntadas(df_filtrado)
        mostrar_analisis_pedidos(df_filtrado)
        mostrar_tendencias_temporales(df_filtrado, df_calculado)
        
        st.subheader("📋 Datos Detallados de Producción")
        st.dataframe(df_filtrado, use_container_width=True, height=400)
    
    with tab2:
        # ✅ ACTUALIZADO: Consulta para operadores INCLUYENDO COMISIONES
        st.info("🔍 **Consulta tus puntadas calculadas automáticamente y tus comisiones**")
        mostrar_consultas_operadores(df_calculado, df_resumen)
