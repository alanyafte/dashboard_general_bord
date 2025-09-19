import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns
from datetime import datetime
try:
    import gspread
    from google.oauth2 import service_account
    GSHEETS_AVAILABLE = True
except ImportError:
    GSHEETS_AVAILABLE = False
    st.warning("⚠️ Librerías de Google Sheets no instaladas")

# --- FUNCIÓN PARA CONECTAR A GOOGLE SHEETS ---
@st.cache_resource
def conectar_google_sheets():
    if not GSHEETS_AVAILABLE:
        return None
    try:
        if 'gcp_service_account' not in st.secrets:
            st.error("❌ No se encontraron credenciales en Secrets")
            return None
            
        creds = service_account.Credentials.from_service_account_info(
            st.secrets["gcp_service_account"],
            scopes=['https://www.googleapis.com/auth/spreadsheets']
        )
        gc = gspread.authorize(creds)
        st.sidebar.success("✅ Conectado a Google Sheets")
        return gc
    except Exception as e:
        st.error(f"❌ Error de conexión: {e}")
        return None

# --- FUNCIÓN PARA OBTENER DATOS REALES ---
@st.cache_data(ttl=3600)
def obtener_datos_reales():
    gc = conectar_google_sheets()
    if gc is None:
        return None
    
    try:
        url = "https://docs.google.com/spreadsheets/d/1dBubiABkbfpCGxn3b7eLC12DyM-R9N0XdxI93gL2Bv0/edit#gid=0"
        sh = gc.open_by_url(url)
        
        # Leer las pestañas
        ventas_b = pd.DataFrame(sh.worksheet("Ventas").get_all_records())
        produccion_b = pd.DataFrame(sh.worksheet("Produccion").get_all_records())
        ventas_c = pd.DataFrame(sh.worksheet("Ventas_c").get_all_records())
        produccion_c = pd.DataFrame(sh.worksheet("Produccion_c").get_all_records())
        
        st.sidebar.success("✅ Datos reales cargados")
        return {
            'ventas_b': ventas_b,
            'produccion_b': produccion_b,
            'ventas_c': ventas_c,
            'produccion_c': produccion_c
        }
    except Exception as e:
        st.error(f"❌ Error leyendo datos: {e}")
        return None

# --- CONFIGURACIÓN STREAMLIT ---
st.set_page_config(page_title="Dashboard Clima Laboral", layout="wide")
st.title("📊 Dashboard de Clima Laboral")
st.markdown("**Datos en tiempo real desde Google Sheets**")

# --- OBTENER DATOS (reales o de prueba) ---
datos_reales = obtener_datos_reales() if GSHEETS_AVAILABLE else None

if datos_reales:
    st.sidebar.success("📊 Usando datos REALES de Google Sheets")
    # Aquí procesarás los datos reales como en tu código original
    # Por ahora solo mostramos que se conectó
    st.info("✅ ¡Conexión a Google Sheets exitosa!")
    st.write("Dimensión de los datos cargados:")
    for key, df in datos_reales.items():
        st.write(f"{key}: {df.shape[0]} filas x {df.shape[1]} columnas")
else:
    st.sidebar.warning("📋 Usando datos de PRUEBA")
    # --- TUS DATOS DE PRUEBA ACTUALES ---
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

st.header("🌊 Gráfico con Seaborn (Avanzado)")
try:
    fig, ax = plt.subplots(figsize=(12, 6))
    
    # Prepara datos para el heatmap
    heatmap_data = datos_prueba[['Ventas B', 'Producción B', 'Promedio General']]
    
    # Crea heatmap con seaborn
    sns.heatmap(heatmap_data.T, annot=True, fmt='.2f', cmap='RdYlGn', 
                center=3.0, ax=ax)
    ax.set_title('Mapa de Calor - Prueba Seaborn')
    
    st.pyplot(fig)
    st.success("✅ ¡Seaborn funciona perfectamente!")
    
except Exception as e:
    st.warning(f"Seaborn no disponible todavía: {e}")

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
