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

# --- FUNCIÓN PARA OBTENER DATOS REALES CON DEBUG ---
@st.cache_data(ttl=3600)
def obtener_datos_reales():
    gc = conectar_google_sheets()
    if gc is None:
        return None
    
    try:
        st.sidebar.info("🔗 Intentando conectar con Google Sheets...")
        
        url = "https://docs.google.com/spreadsheets/d/1dBubiABkbfpCGxn3b7eLC12DyM-R9N0XdxI93gL2Bv0/edit#gid=0"
        sh = gc.open_by_url(url)
        st.sidebar.success("✅ Hoja de cálculo encontrada")
        
        # Listar todas las pestañas disponibles para debug
        todas_hojas = [worksheet.title for worksheet in sh.worksheets()]
        st.sidebar.write(f"📋 Hojas disponibles: {', '.join(todas_hojas)}")
        
        # Leer las pestañas con manejo de errores individual
        datos = {}
        hojas_requeridas = ["Ventas", "Produccion", "Ventas_c", "Produccion_c"]
        
        for hoja in hojas_requeridas:
            try:
                if hoja in todas_hojas:
                    worksheet = sh.worksheet(hoja)
                    datos[hoja] = pd.DataFrame(worksheet.get_all_records())
                    st.sidebar.success(f"✅ {hoja}: {datos[hoja].shape[0]} filas")
                else:
                    st.sidebar.error(f"❌ Pestaña '{hoja}' no encontrada")
                    return None
            except Exception as e:
                st.sidebar.error(f"❌ Error leyendo {hoja}: {str(e)}")
                return None
        
        st.sidebar.success("✅ Todas las pestañas leídas correctamente")
        return datos
        
    except Exception as e:
        st.error(f"❌ Error general: {str(e)}")
        # Mostrar más detalles del error
        with st.expander("🔍 Detalles del error"):
            st.write(f"**Tipo de error:** {type(e).__name__}")
            st.write(f"**Mensaje:** {str(e)}")
            st.write("""
            **Posibles soluciones:**
            1. Verifica que la URL de la hoja sea correcta
            2. Asegúrate que el service account tenga acceso a la hoja
            3. Revisa que los nombres de las pestañas sean exactos
            """)
        return None
        
# --- CONFIGURACIÓN STREAMLIT ---
st.set_page_config(page_title="Dashboard Clima Laboral", layout="wide")
st.title("📊 Dashboard de Clima Laboral")
st.markdown("**Datos en tiempo real desde Google Sheets**")

# --- OBTENER DATOS (reales o de prueba) ---
datos_reales = obtener_datos_reales() if GSHEETS_AVAILABLE else None
# --- DIAGNÓSTICO DE CONEXIÓN ---
with st.sidebar:
    st.header("🔧 Diagnóstico de Conexión")
    
    if GSHEETS_AVAILABLE:
        st.success("✅ Librerías de Google instaladas")
        
        if 'gcp_service_account' in st.secrets:
            st.success("✅ Credenciales encontradas en Secrets")
            
            # Mostrar email del service account
            try:
                import json
                creds_info = st.secrets["gcp_service_account"]
                if isinstance(creds_info, str):
                    creds_info = json.loads(creds_info)
                
                client_email = creds_info.get("client_email", "No encontrado")
                st.info(f"📧 **Service Account Email:**")
                st.code(client_email)
                st.warning("🚨 **¡COMPARTE tu Google Sheets con este email!**")
                
            except Exception as e:
                st.error(f"Error leyendo credenciales: {e}")
        else:
            st.error("❌ No hay credenciales en Secrets")
    else:
        st.error("❌ Librerías de Google no instaladas")

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
