import streamlit as st
from modulo_clima_laboral import mostrar_dashboard_clima_laboral
from modulo_oee import mostrar_dashboard_oee
# from modulo_satisfaccion_cliente import mostrar_dashboard_satisfaccion  # Para el futuro

# Configuración de la página
#st.set_page_config
    #page_title="Dashboard Integral",
    #page_icon="📊",
    #layout="wide"

# Sidebar para navegación
st.sidebar.title("🌐 Navegación")
modulo_seleccionado = st.sidebar.radio(
    "Seleccionar Módulo:",
    ["🏭 OEE - Producción", "👥 Clima Laboral", "😊 Satisfacción Cliente"]
)

# Título principal
st.title("📊 Dashboard Integral de Métricas")

# Navegación entre módulos
if modulo_seleccionado == "🏭 OEE - Producción":
    mostrar_dashboard_oee()
    
elif modulo_seleccionado == "👥 Clima Laboral":
    mostrar_dashboard_clima_laboral()
    
elif modulo_seleccionado == "😊 Satisfacción Cliente":
    st.info("Módulo en desarrollo...")
    # mostrar_dashboard_satisfaccion()

# Footer
st.sidebar.markdown("---")
st.sidebar.info("Dashboard Integral v1.0")
