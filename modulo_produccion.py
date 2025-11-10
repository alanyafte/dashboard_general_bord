import gspread
import pandas as pd
import matplotlib.pyplot as plt
import plotly.express as px
import numpy as np
import streamlit as st
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
from datetime import timedelta

# ✅ FUNCIONES DE LIMPIEZA Y CÁLCULO (Backend)
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
        df["Marca temporal"] = pd.to_datetime(df["Marca temporal"], format='%d/%m/%Y %H:%M:%S', errors='coerce')
    
    # Convertir CANTIDAD a numérico
    if "CANTIDAD" in df.columns:
        df["CANTIDAD"] = pd.to_numeric(df["CANTIDAD"], errors='coerce')
    
    # Convertir PUNTADAS a numérico
    if "PUNTADAS" in df.columns:
        df["PUNTADAS"] = pd.to_numeric(df["PUNTADAS"], errors='coerce')
        df["PUNTADAS"] = df["PUNTADAS"].fillna(0)
    
    # Convertir MULTIPLOS a numérico (si existe)
    if "MULTIPLOS" in df.columns:
        df["MULTIPLOS"] = pd.to_numeric(df["MULTIPLOS"], errors='coerce')
    
    return df

def aplicar_filtros(df):
    """Aplicar filtros interactivos"""
    df_filtrado = df.copy()
    
    st.sidebar.header("🔍 Filtros")
    
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
    
    # Filtro por fecha
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
    """Calcular automáticamente las puntadas cuando se cargan los datos"""
    
    CONFIG_MAQUINAS = {
        "Susi": 6,
        "Juan": 6,
        "Esmeralda": 6,
        "Rigoberto": 2,
        "Maricela": 2,
    }
    
    CABEZAS_POR_DEFECTO = 6
    
    if df.empty or "OPERADOR" not in df.columns:
        return pd.DataFrame()
    
    resultados = []
    
    df_con_fecha = df.copy()
    df_con_fecha['Fecha'] = df_con_fecha['Marca temporal'].dt.date
    
    # Agrupar por operador y fecha
    grupos = df_con_fecha.groupby(['OPERADOR', 'Fecha'])
    
    for (operador, fecha), grupo in grupos:
        # Calcular cambios de color por ORDEN
        for idx, (indice_fila, fila) in enumerate(grupo.iterrows()):
            # Verificar que tenemos los datos necesarios
            if pd.isna(fila.get("CANTIDAD")) or pd.isna(fila.get("PUNTADAS")):
                continue
                
            piezas = fila["CANTIDAD"]
            puntadas_base = fila["PUNTADAS"]
            
            # Tomar cabezas de la columna del sheets si existe
            cabezas = None
            posibles_nombres_columnas = ["CABEZAS", "NO_DE_CABEZAS", "NUMERO_CABEZAS", "NO CABEZAS"]
            
            for nombre_columna in posibles_nombres_columnas:
                if nombre_columna in fila and not pd.isna(fila[nombre_columna]):
                    try:
                        cabezas = float(fila[nombre_columna])
                        break
                    except (ValueError, TypeError):
                        continue
            
            # Si no se encontró en columnas, usar configuración manual como respaldo
            if cabezas is None:
                cabezas = CONFIG_MAQUINAS.get(operador, CABEZAS_POR_DEFECTO)
            
            # Calcular múltiplos
            pasadas = np.ceil(piezas / cabezas)
            multiplo = pasadas * cabezas
            puntadas_ajustadas = max(puntadas_base, 4000)
            puntadas_multiplos = multiplo * puntadas_ajustadas
            
            # Calcular cambios de color
            if idx == 0:  # Primera orden del día
                puntadas_cambios = 36000 + 18000
            else:  # Órdenes adicionales
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
                'FECHA_CALCULO': datetime.now().date(),
                'HORA_CALCULO': datetime.now().strftime("%H:%M:%S")
            })
    
    return pd.DataFrame(resultados)

# ✅ FUNCIONES DE GUARDADO EN SHEETS
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
        
        # CONVERTIR FECHAS A STRING ANTES DE GUARDAR
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

def cargar_y_calcular_datos():
    """Cargar y calcular datos desde Google Sheets"""
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
        
        # CARGAR DATOS DE PRODUCCIÓN
        sheet_id = st.secrets["gsheets"]["produccion_sheet_id"]
        worksheet = gc.open_by_key(sheet_id).worksheet("reporte_de_trabajo")
        data = worksheet.get_all_values()
        df_raw = pd.DataFrame(data[1:], columns=data[0])
        
        # LIMPIAR DATOS
        df = limpiar_dataframe(df_raw)
        
        # CALCULAR PUNTADAS AUTOMÁTICAMENTE
        df_calculado = calcular_puntadas_automaticamente(df)
        
        # ✅ GUARDAR CÁLCULOS EN SHEETS (si hay datos)
        if not df_calculado.empty:
            try:
                guardar_calculos_en_sheets(df_calculado)
                # ✅ GUARDAR RESUMEN EJECUTIVO AUTOMÁTICAMENTE
                guardar_resumen_ejecutivo(df_calculado)
            except Exception as e:
                st.sidebar.warning(f"⚠️ No se pudieron guardar los cálculos: {e}")
        
        # CARGAR RESUMEN EJECUTIVO
        try:
            worksheet_resumen = gc.open_by_key(sheet_id).worksheet("resumen_ejecutivo")
            datos_resumen = worksheet_resumen.get_all_values()
            
            if len(datos_resumen) > 1:
                df_resumen = pd.DataFrame(datos_resumen[1:], columns=datos_resumen[0])
                
                # Convertir tipos de datos
                if 'TOTAL_PUNTADAS' in df_resumen.columns:
                    df_resumen['TOTAL_PUNTADAS'] = pd.to_numeric(df_resumen['TOTAL_PUNTADAS'], errors='coerce')
                if 'COMISION_TOTAL' in df_resumen.columns:
                    df_resumen['COMISION_TOTAL'] = pd.to_numeric(df_resumen['COMISION_TOTAL'], errors='coerce')
                if 'BONIFICACION' in df_resumen.columns:
                    df_resumen['BONIFICACION'] = pd.to_numeric(df_resumen['BONIFICACION'], errors='coerce')
                if 'COMISION' in df_resumen.columns:
                    df_resumen['COMISION'] = pd.to_numeric(df_resumen['COMISION'], errors='coerce')
                
                # Convertir fecha
                if 'FECHA' in df_resumen.columns:
                    df_resumen['FECHA'] = pd.to_datetime(df_resumen['FECHA'], errors='coerce')
                    
            else:
                df_resumen = pd.DataFrame()
        except:
            df_resumen = pd.DataFrame()
        
        return df, df_calculado, df_resumen
        
    except Exception as e:
        st.error(f"❌ Error al cargar los datos: {str(e)}")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

# ✅ FUNCIÓN PRINCIPAL QUE EXPORTA EL MÓDULO (CORREGIDA)
def mostrar_dashboard_produccion():
    """Función principal que se llama desde app_principal.py - VERSIÓN CORREGIDA"""
    try:
        # Botón de actualización
        st.sidebar.header("🔄 Actualizar Datos")
        if st.sidebar.button("🔄 Actualizar Datos en Tiempo Real", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
        
        # Cargar datos
        df, df_calculado, df_resumen = cargar_y_calcular_datos()
        
        st.sidebar.info(f"Última actualización: {datetime.now().strftime('%H:%M:%S')}")
        st.sidebar.info(f"📊 Registros: {len(df)}")
        if not df_calculado.empty:
            st.sidebar.success(f"🧵 Cálculos: {len(df_calculado)}")
        if not df_resumen.empty:
            st.sidebar.success(f"💰 Comisiones: {len(df_resumen)} registros")
        
        # INTERFAZ OPTIMIZADA
        st.title("🏭 Dashboard de Producción")
        
        # Mostrar resumen rápido
        st.info(f"**Base de datos cargada:** {len(df)} registros de producción")
        if df_calculado is not None and not df_calculado.empty:
            st.success(f"**Cálculos automáticos:** {len(df_calculado)} registros calculados")
        if df_resumen is not None and not df_resumen.empty:
            st.success(f"**Resumen ejecutivo:** {len(df_resumen)} registros de comisiones")
        
        # FILTROS
        df_filtrado = aplicar_filtros(df)
        
        # PESTAÑAS PRINCIPALES OPTIMIZADAS
        tab1, tab2 = st.tabs(["📊 Dashboard Principal", "👤 Consultar Mis Puntadas y Comisiones"])
        
        with tab1:
            mostrar_dashboard_compacto(df_filtrado, df_calculado)
        
        with tab2:
            st.info("🔍 **Consulta tus puntadas calculadas automáticamente y tus comisiones**")
            mostrar_consultas_operadores_compacto(df_calculado, df_resumen)
        
    except Exception as e:
        st.error(f"❌ Error al cargar los datos: {str(e)}")
        st.info("⚠️ Verifica que la hoja de cálculo esté accesible y la estructura sea correcta")

def mostrar_analisis_puntadas_completo(df, df_calculado=None):
    """Análisis completo de puntadas con todos los gráficos"""
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Análisis de puntadas base
        if "PUNTADAS" in df.columns:
            st.subheader("🪡 Análisis de Puntadas Base")
            
            # Top operadores por puntadas base
            puntadas_por_operador = df.groupby("OPERADOR")["PUNTADAS"].sum().sort_values(ascending=False).reset_index()
            puntadas_por_operador.columns = ['Operador', 'Total Puntadas']
            
            st.write("**🏆 Ranking por Puntadas Base:**")
            st.dataframe(puntadas_por_operador, use_container_width=True)
    
    with col2:
        # Distribución de puntadas por tipo de prenda
        if "TIPO DE PRENDA" in df.columns and "PUNTADAS" in df.columns:
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
    
    # Análisis de puntadas calculadas
    if df_calculado is not None and not df_calculado.empty and "TOTAL_PUNTADAS" in df_calculado.columns:
        st.subheader("🧵 Análisis de Puntadas Calculadas")
        
        col3, col4 = st.columns(2)
        
        with col3:
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
        
        with col4:
            # Top diseños más producidos
            if "DISEÑO" in df.columns:
                top_diseños = df["DISEÑO"].value_counts().head(10).reset_index()
                top_diseños.columns = ['Diseño', 'Cantidad']
                
                st.write("**🎨 Top Diseños:**")
                st.dataframe(top_diseños, use_container_width=True)

def mostrar_tendencias_completas(df, df_calculado=None):
    """Tendencias temporales completas con todos los gráficos"""
    
    if df.empty or "Marca temporal" not in df.columns:
        st.info("No hay datos temporales disponibles.")
        return
    
    try:
        df_temporal = df.copy()
        df_temporal['Fecha'] = df_temporal['Marca temporal'].dt.date
        
        tendencias = df_temporal.groupby('Fecha').agg({
            '#DE PEDIDO': 'count',
            'CANTIDAD': 'sum' if 'CANTIDAD' in df.columns else None,
            'PUNTADAS': 'sum' if 'PUNTADAS' in df.columns else None
        }).reset_index()
        
        # ✅ AGREGAR TENDENCIAS DE CÁLCULOS SI ESTÁN DISPONIBLES
        if df_calculado is not None and not df_calculado.empty and "TOTAL_PUNTADAS" in df_calculado.columns:
            df_calc_temporal = df_calculado.copy()
            if 'FECHA' in df_calc_temporal.columns:
                if df_calc_temporal['FECHA'].dtype == 'object':
                    df_calc_temporal['FECHA'] = pd.to_datetime(df_calc_temporal['FECHA']).dt.date
                
                tendencias_calc = df_calc_temporal.groupby('FECHA')['TOTAL_PUNTADAS'].sum().reset_index()
                tendencias_calc.columns = ['Fecha', 'TOTAL_PUNTADAS']
                tendencias = tendencias.merge(tendencias_calc, on='Fecha', how='left')
        
        if len(tendencias) > 1:
            # Gráfico de pedidos por día
            fig1 = px.line(
                tendencias, 
                x='Fecha', 
                y='#DE PEDIDO',
                title="📦 Evolución de Pedidos por Día",
                markers=True
            )
            st.plotly_chart(fig1, use_container_width=True)
            
            # Gráficos en columnas para ahorrar espacio
            col1, col2 = st.columns(2)
            
            with col1:
                # Gráfico de puntadas base por día
                if "PUNTADAS" in df.columns:
                    fig2 = px.line(
                        tendencias, 
                        x='Fecha', 
                        y='PUNTADAS',
                        title="🪡 Evolución de Puntadas Base por Día",
                        markers=True,
                        color_discrete_sequence=['red']
                    )
                    st.plotly_chart(fig2, use_container_width=True)
            
            with col2:
                # Gráfico de puntadas calculadas por día
                if "TOTAL_PUNTADAS" in tendencias.columns and not tendencias["TOTAL_PUNTADAS"].isna().all():
                    fig3 = px.line(
                        tendencias, 
                        x='Fecha', 
                        y='TOTAL_PUNTADAS',
                        title="🧵 Evolución de Puntadas Calculadas por Día",
                        markers=True,
                        color_discrete_sequence=['green']
                    )
                    st.plotly_chart(fig3, use_container_width=True)
                    
        else:
            st.info("Se necesitan datos de más de un día para mostrar tendencias.")
            
    except Exception as e:
        st.error(f"Error al generar tendencias: {str(e)}")

# ✅ CONSULTA DE OPERADORES OPTIMIZADA
def mostrar_consultas_operadores_compacto(df_calculado, df_resumen):
    """Interfaz compacta para consulta de operadores"""
    
    if df_calculado is None or df_calculado.empty:
        st.info("ℹ️ No hay cálculos disponibles. Los cálculos se generan automáticamente.")
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
        st.info("👆 **Por favor, selecciona tu nombre de la lista para ver tus puntadas y comisiones**")
        return
    
    # Filtrar datos del operador
    df_operador = df_calculado[df_calculado["OPERADOR"] == operador_seleccionado].copy()
    
    if df_operador.empty:
        st.warning("No hay datos para los filtros seleccionados")
        return
    
    # 1. RESUMEN DE PUNTADAS
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
