import streamlit as st
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Dashboard Clima Laboral", layout="wide")
st.title("📊 Dashboard de Clima Laboral")
st.markdown("**Versión inicial - Sin gráficos**")

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

# Gráfico simple con Streamlit nativo (sin matplotlib)
st.header("Gráfico Simple")
st.bar_chart(datos_prueba['Promedio General'])

st.success("✅ ¡App funcionando correctamente! Ahora puedes agregar matplotlib gradualmente.")
