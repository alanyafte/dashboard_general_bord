import gspread
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import streamlit as st
from oauth2client.service_account import ServiceAccountCredentials

def mostrar_dashboard_produccion():
    try:
        # ✅ AUTENTICACIÓN
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
    
    # Mostrar información del dataframe crudo
    st.sidebar.info(f"📊 Datos crudos: {len(df)} registros, {len(df.columns)} columnas")
    
    # Limpiar espacios en nombres de columnas
    df.columns = df.columns.str.strip()
    
    # Mostrar columnas disponibles para debugging
    with st.expander("🔍 Ver columnas disponibles y datos crudos"):
        st.write("**Columnas:**", list(df.columns))
        st.write("**Primeras filas:**")
        st.dataframe(df.head(10))
    
    # Aquí puedes agregar más limpieza según tus columnas específicas
    # Por ejemplo: convertir fechas, limpiar valores numéricos, etc.
    
    return df

def mostrar_interfaz_dashboard(df):
    """Interfaz principal del dashboard"""
    
    st.title("🏭 Dashboard de Producción")
    
    # ✅ FILTROS EN SIDEBAR
    st.sidebar.header("🔍 Filtros")
    df_filtrado = aplicar_filtros(df)
    
    # ✅ MÉTRICAS PRINCIPALES
    st.header("📈 Métricas Principales")
    mostrar_metricas_principales(df_filtrado)
    
    # ✅ ANÁLISIS POR OPERADOR
    st.header("👤 Análisis por Operador")
    mostrar_analisis_operadores(df_filtrado)
    
    # ✅ DATOS DETALLADOS
    st.header("📋 Datos Detallados")
    mostrar_datos_detallados(df_filtrado)

def aplicar_filtros(df):
    """Aplicar filtros interactivos"""
    df_filtrado = df.copy()
    
    # Filtro por operador (si existe la columna)
    if 'Operador' in df.columns or 'operador' in df.columns:
        col_operador = 'Operador' if 'Operador' in df.columns else 'operador'
        operadores = sorted(df[col_operador].unique())
        operadores_seleccionados = st.sidebar.multiselect(
            "Seleccionar Operadores:",
            options=operadores,
            default=operadores
        )
        if operadores_seleccionados:
            df_filtrado = df_filtrado[df_filtrado[col_operador].isin(operadores_seleccionados)]
    
    # Filtro por fecha (si existe)
    columnas_fecha = [col for col in df.columns if 'fecha' in col.lower() or 'date' in col.lower()]
    if columnas_fecha:
        col_fecha = columnas_fecha[0]
        # Intentar convertir a datetime
        try:
            df_filtrado[col_fecha] = pd.to_datetime(df_filtrado[col_fecha], errors='coerce')
            fechas_disponibles = df_filtrado[col_fecha].dropna()
            if not fechas_disponibles.empty:
                fecha_min = fechas_disponibles.min()
                fecha_max = fechas_disponibles.max()
                
                rango_fechas = st.sidebar.date_input(
                    "Rango de Fechas:",
                    value=(fecha_min, fecha_max),
                    min_value=fecha_min,
                    max_value=fecha_max
                )
                if len(rango_fechas) == 2:
                    mask = (df_filtrado[col_fecha] >= pd.Timestamp(rango_fechas[0])) & \
                           (df_filtrado[col_fecha] <= pd.Timestamp(rango_fechas[1]))
                    df_filtrado = df_filtrado[mask]
        except:
            pass
    
    st.sidebar.info(f"📊 Registros después de filtros: {len(df_filtrado)}")
    
    return df_filtrado

def mostrar_metricas_principales(df):
    """Mostrar métricas principales"""
    
    if df.empty:
        st.warning("No hay datos con los filtros aplicados")
        return
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_registros = len(df)
        st.metric("Total de Registros", total_registros)
    
    with col2:
        # Ejemplo: contar operadores únicos
        col_operador = next((col for col in df.columns if 'operador' in col.lower()), None)
        if col_operador:
            operadores_unicos = df[col_operador].nunique()
            st.metric("Operadores Únicos", operadores_unicos)
        else:
            st.metric("Registros Únicos", df.iloc[:, 0].nunique())
    
    with col3:
        # Ejemplo: encontrar columna numérica para promediar
        columnas_numericas = df.select_dtypes(include=[np.number]).columns
        if len(columnas_numericas) > 0:
            valor_promedio = df[columnas_numericas[0]].mean()
            st.metric(f"Promedio {columnas_numericas[0]}", f"{valor_promedio:.2f}")
        else:
            st.metric("Datos Disponibles", "✓")
    
    with col4:
        # Última fecha (si existe)
        columnas_fecha = [col for col in df.columns if 'fecha' in col.lower()]
        if columnas_fecha:
            try:
                ultima_fecha = pd.to_datetime(df[columnas_fecha[0]]).max()
                st.metric("Última Actualización", ultima_fecha.strftime("%d/%m/%Y"))
            except:
                st.metric("Actualizado", "Reciente")

def mostrar_analisis_operadores(df):
    """Análisis específico por operador"""
    
    if df.empty:
        return
    
    col_operador = next((col for col in df.columns if 'operador' in col.lower()), None)
    
    if col_operador:
        # Métricas por operador
        st.subheader("Desempeño por Operador")
        
        # Aquí puedes personalizar según tus métricas específicas
        metricas_operador = df[col_operador].value_counts().reset_index()
        metricas_operador.columns = ['Operador', 'Total Registros']
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**Registros por Operador:**")
            st.dataframe(metricas_operador, use_container_width=True)
        
        with col2:
            # Gráfico simple de barras
            if len(metricas_operador) > 0:
                fig, ax = plt.subplots()
                ax.bar(metricas_operador['Operador'], metricas_operador['Total Registros'])
                ax.set_title("Registros por Operador")
                plt.xticks(rotation=45)
                st.pyplot(fig)

def mostrar_datos_detallados(df):
    """Mostrar datos detallados"""
    
    if df.empty:
        return
    
    st.subheader("Tabla de Datos Completa")
    
    # Mostrar dataframe con opción de descarga
    st.dataframe(df, use_container_width=True, height=400)
    
    # Opción para descargar datos filtrados
    csv = df.to_csv(index=False)
    st.download_button(
        label="📥 Descargar Datos Filtrados (CSV)",
        data=csv,
        file_name="datos_produccion_filtrados.csv",
        mime="text/csv"
    )
