import gspread
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import streamlit as st
from google.colab import auth
from google.auth import default

def inicializar_oee():
    """Función para inicializar la conexión y datos OEE"""
    try:
        # Autenticación
        auth.authenticate_user()
        creds, _ = default()
        gc = gspread.authorize(creds)
        
        # Abrir Google Sheet
        sheet_id = "1VEI-eCZBUoAkwWbr8wNmA0fo4zdXXSPEGp5M-qyQD1E"
        worksheet = gc.open_by_key(sheet_id).worksheet("Produccion")
        
        # Obtener datos
        data = worksheet.get_all_values()
        df_raw = pd.DataFrame(data[1:], columns=data[0])
        
        # Convertir columnas numéricas
        columnas_numericas = [
            "cantidad_producida", "unidades_defectuosas", "unidades_buenas",
            "tiempo_planificado_min", "tiempo_paro_planeado_min",
            "tiempo_paro_no_planeado_min", "run_time_min", "tiempo_ciclo_ideal_unit_seg"
        ]
        
        for col in columnas_numericas:
            if col in df_raw.columns:
                df_raw[col] = pd.to_numeric(df_raw[col], errors="coerce")
        
        return df_raw
    except Exception as e:
        st.error(f"Error al cargar datos OEE: {e}")
        return pd.DataFrame()

def calcular_metricas_oee(df_raw):
    """Calcular métricas OEE"""
    if df_raw.empty:
        return df_raw
    
    # Calcular métricas base
    df_raw["tiempo_operativo_min"] = (
        df_raw["tiempo_planificado_min"]
        - df_raw["tiempo_paro_planeado_min"]
        - df_raw["tiempo_paro_no_planeado_min"]
    )
    
    df_raw["availability"] = df_raw["tiempo_operativo_min"] / df_raw["tiempo_planificado_min"]
    
    df_raw["performance"] = (
        (df_raw["cantidad_producida"] * df_raw["tiempo_ciclo_ideal_unit_seg"])
        / (df_raw["tiempo_operativo_min"] * 60)
    )
    
    df_raw["quality"] = df_raw["unidades_buenas"] / df_raw["cantidad_producida"]
    df_raw["OEE"] = df_raw["availability"] * df_raw["performance"] * df_raw["quality"]
    
    return df_raw

def mostrar_dashboard_oee():
    """Función principal para mostrar el dashboard OEE en Streamlit"""
    st.header("🏭 Dashboard OEE - Efectividad General de Equipos")
    
    # Cargar datos
    with st.spinner("Cargando datos de producción..."):
        df_raw = inicializar_oee()
    
    if df_raw.empty:
        st.warning("No se pudieron cargar los datos de OEE")
        return
    
    # Calcular métricas
    df_metricas = calcular_metricas_oee(df_raw)
    
    # Mostrar resumen general
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("OEE Promedio", f"{df_metricas['OEE'].mean():.2%}")
    with col2:
        st.metric("Disponibilidad Promedio", f"{df_metricas['availability'].mean():.2%}")
    with col3:
        st.metric("Rendimiento Promedio", f"{df_metricas['performance'].mean():.2%}")
    with col4:
        st.metric("Calidad Promedio", f"{df_metricas['quality'].mean():.2%}")
    
    # Filtros
    st.subheader("🔍 Filtros")
    col1, col2 = st.columns(2)
    
    with col1:
        maquinas = df_metricas["maquina"].unique()
        maquina_seleccionada = st.selectbox("Seleccionar Máquina", ["Todas"] + list(maquinas))
    
    with col2:
        fechas = df_metricas["fecha_inic"].unique()
        fecha_seleccionada = st.selectbox("Seleccionar Fecha", ["Todas"] + list(fechas))
    
    # Aplicar filtros
    df_filtrado = df_metricas.copy()
    if maquina_seleccionada != "Todas":
        df_filtrado = df_filtrado[df_filtrado["maquina"] == maquina_seleccionada]
    if fecha_seleccionada != "Todas":
        df_filtrado = df_filtrado[df_filtrado["fecha_inic"] == fecha_seleccionada]
    
    # Gráficos
    st.subheader("📊 Métricas OEE")
    
    # OEE por máquina
    oee_por_maquina = df_filtrado.groupby("maquina")[["availability", "performance", "quality", "OEE"]].mean()
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**OEE por Máquina**")
        fig, ax = plt.subplots()
        oee_por_maquina["OEE"].plot(kind="bar", ax=ax, ylabel="OEE", xlabel="Máquina")
        ax.set_ylim(0, 1)
        st.pyplot(fig)
    
    with col2:
        st.write("**Componentes OEE por Máquina**")
        fig, ax = plt.subplots(figsize=(10, 6))
        oee_por_maquina[["availability", "performance", "quality"]].plot(kind="bar", ax=ax)
        ax.set_ylabel("Valor")
        ax.legend(["Disponibilidad", "Rendimiento", "Calidad"])
        st.pyplot(fig)
    
    # Gráfico de radar
    st.subheader("📈 Análisis Comparativo - Gráfico Radar")
    
    oee_componentes = df_filtrado.groupby("maquina")[["availability", "performance", "quality"]].mean() * 100
    
    if len(oee_componentes) > 0:
        categorias = list(oee_componentes.columns)
        N = len(categorias)
        angulos = np.linspace(0, 2 * np.pi, N, endpoint=False).tolist()
        angulos += angulos[:1]
        
        fig, ax = plt.subplots(figsize=(8, 8), subplot_kw=dict(projection='polar'))
        
        for maquina, fila in oee_componentes.iterrows():
            valores = fila.tolist()
            valores += valores[:1]
            ax.plot(angulos, valores, marker="o", label=maquina)
            ax.fill(angulos, valores, alpha=0.1)
        
        ax.set_xticks(angulos[:-1])
        ax.set_xticklabels(categorias)
        ax.set_yticks([20, 40, 60, 80, 100])
        ax.set_yticklabels(["20%", "40%", "60%", "80%", "100%"])
        ax.set_ylim(0, 100)
        ax.legend(loc="upper right", bbox_to_anchor=(1.3, 1.1))
        st.pyplot(fig)
    
    # Tabla de datos
    st.subheader("📋 Datos Detallados")
    st.dataframe(df_filtrado[["maquina", "codigo_pedido", "fecha_inic", "OEE", "availability", "performance", "quality"]])
