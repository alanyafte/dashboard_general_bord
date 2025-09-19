import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime

# --- CONFIGURACIÓN STREAMLIT ---
st.set_page_config(page_title="Dashboard Clima Laboral", layout="wide")
st.title("📊 Dashboard de Clima Laboral")
st.markdown("**Versión inicial para pruebas en Streamlit Cloud**")

# --- DATOS DE PRUEBA ---
@st.cache_data(ttl=3600)
def obtener_datos_prueba():
    try:
        secciones = [
            "Funciones laborales", "Entorno de trabajo", "Relaciones laborales",
            "Compensación y beneficios", "Desarrollo profesional", 
            "Liderazgo", "Cultura organizacional"
        ]
        
        datos_prueba = pd.DataFrame({
            'Ventas B': [4.2, 3.8, 4.5, 3.2, 2.8, 3.5, 4.0],
            'Producción B': [4.0, 3.6, 4.3, 3.0, 2.6, 3.3, 3.8],
            'Ventas C': [4.1, 3.9, 4.4, 3.3, 2.9, 3.6, 4.1],
            'Producción C': [3.9, 3.7, 4.2, 3.1, 2.7, 3.4, 3.9]
        }, index=secciones)
        
        datos_prueba["Promedio General"] = datos_prueba.mean(axis=1)
        datos_prueba['ultima_actualizacion'] = datetime.now()
        
        return datos_prueba
        
    except Exception as e:
        st.error(f"Error: {e}")
        return None

# --- INTERFAZ PRINCIPAL ---
datos = obtener_datos_prueba()

if datos is not None:
    st.sidebar.success(f"✅ Datos de prueba - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Gráfico simple
    st.header("Gráfico de Prueba")
    fig, ax = plt.subplots(figsize=(10, 6))
    datos["Promedio General"].plot(kind='bar', ax=ax, color='lightblue')
    ax.set_title('Promedio General por Sección')
    ax.set_ylabel('Puntuación')
    ax.set_xlabel('Secciones')
    ax.tick_params(axis='x', rotation=45)
    plt.tight_layout()
    st.pyplot(fig)

    # Estadísticas
    st.header("Estadísticas")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Promedio", f"{datos['Promedio General'].mean():.2f}")
    with col2:
        st.metric("Mejor", datos['Promedio General'].idxmax())
    with col3:
        st.metric("Peor", datos['Promedio General'].idxmin())

    # Datos
    st.header("Datos")
    st.dataframe(datos.style.format("{:.2f}"))

else:
    st.error("Error al cargar datos")

# --- SECCIÓN DE CONFIGURACIÓN ---
with st.expander("🚀 Configuración para producción"):
    st.write("""
    **Para conectar con Google Sheets, agrega:**

    1. **Secrets** en Streamlit Cloud (.streamlit/secrets.toml)
    2. **Código de autenticación** gradualmente
    3. **Funciones completas** paso a paso
    """)
