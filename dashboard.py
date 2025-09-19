import streamlit as st
import pandas as pd
from datetime import datetime

# Intenta importar matplotlib pero con respaldo
try:
    import matplotlib.pyplot as plt
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    st.warning("⚠️ Matplotlib no está instalado. Usando gráficos nativos de Streamlit.")

st.set_page_config(page_title="Dashboard Clima Laboral", layout="wide")
st.title("📊 Dashboard de Clima Laboral")
st.markdown("**Versión inicial - Probando matplotlib**")

# Datos de prueba
secciones = [
    "Funciones laborales", "Entorno de trabajo", "Relaciones laborales",
    "Compensación y beneficios", "Desarrollo profesional", 
    "Liderazgo", "Cultura organizacional"
]

datos_prueba = pd.DataFrame({
    'Ventas B': [4.2, 3.8, 4.5, 3.2, 2.8, 3.5, 4.0],
    'Producción B': [4.0, 3.6, 4.3, 3.0, 2.6, 3.3, 3.8],
    'Promedio General': [4.1, 3.7, 4.4, 3.1, 2.7, 3.4, 3.9]
}, index=secciones)

# Interfaz solo con datos tabulares
st.sidebar.success(f"✅ App funcionando - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

st.header("Datos en Tabla")
st.dataframe(datos_prueba.style.format("{:.2f}").highlight_max(axis=0, color='#90EE90').highlight_min(axis=0, color='#FFCCCB'))

st.header("Estadísticas")
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Promedio General", f"{datos_prueba['Promedio General'].mean():.2f}")
with col2:
    st.metric("Máxima Valoración", f"{datos_prueba['Promedio General'].max():.2f}")
with col3:
    st.metric("Mínima Valoración", f"{datos_prueba['Promedio General'].min():.2f}")

# Gráfico simple con Streamlit nativo (siempre funciona)
st.header("Gráfico Simple (Streamlit)")
st.bar_chart(datos_prueba['Promedio General'])

# Gráfico con matplotlib (solo si está disponible)
if MATPLOTLIB_AVAILABLE:
    st.header("Gráfico con Matplotlib")
    try:
        fig, ax = plt.subplots(figsize=(10, 4))
        ax.bar(datos_prueba.index, datos_prueba['Promedio General'], color='lightblue', alpha=0.7)
        ax.set_title('Gráfico con Matplotlib (Si se instala)')
        ax.set_ylabel('Puntuación')
        ax.tick_params(axis='x', rotation=45)
        st.pyplot(fig)
        st.success("✅ ¡Matplotlib funciona perfectamente!")
    except Exception as e:
        st.error(f"Error con matplotlib: {e}")
else:
    st.info("📊 Para ver gráficos con matplotlib, instala la dependencia")

# Diagnóstico
with st.expander("🔍 Diagnóstico de dependencias"):
    st.write(f"**Matplotlib disponible:** {MATPLOTLIB_AVAILABLE}")
    if not MATPLOTLIB_AVAILABLE:
        st.write("""
        **Para instalar matplotlib:**
        1. Crea un archivo `requirements.txt` con:
        ```
        streamlit>=1.28.0
        pandas>=1.5.0
        matplotlib>=3.6.0
        ```
        2. Espera a que Streamlit Cloud reinstale las dependencias
        """)

st.success("✅ ¡App funcionando correctamente! El error era esperado.")
