import streamlit as st
from modulo_clima_laboral import mostrar_dashboard_clima_laboral
from modulo_produccion import mostrar_dashboard_produccion
from modulo_satisfaccion_cliente import mostrar_dashboard_satisfaccion
#from modulo_general_gastos import...
# Configuración de la página
st.set_page_config(
    page_title="Dashboard Integral",
    page_icon="📊",
    layout="wide"
)
# Cargar contraseñas desde Streamlit Secrets
def cargar_contraseñas_seguras():
    try:
        # Intentar cargar desde secrets
        contraseñas = {
            "🏭 Producción": st.secrets["PASSWORD_PRODUCCION"],
            "👥 Clima Laboral": st.secrets["PASSWORD_CLIMA_LABORAL"], 
            "😊 Satisfacción Cliente": st.secrets["PASSWORD_SATISFACCION_CLIENTE"],
        }
        st.sidebar.success("🔐 Secrets cargados correctamente")
        return contraseñas
    except Exception as e:
        st.error(f"❌ Error cargando secrets: {e}")
        st.stop()  # Detener la app si no hay secrets

CONTRASEÑAS_MODULOS = cargar_contraseñas_seguras()

# Inicializar estado de sesión para cada módulo
for modulo in CONTRASEÑAS_MODULOS.keys():
    if f"acceso_{modulo}" not in st.session_state:
        st.session_state[f"acceso_{modulo}"] = False

# Sidebar para navegación
st.sidebar.title("🌐 Navegación")
modulo_seleccionado = st.sidebar.radio(
    "Seleccionar Módulo:",
    ["🏭 Producción", "👥 Clima Laboral", "😊 Satisfacción Cliente"]
)

# Título principal
st.title("📊 Dashboard Integral de Métricas")

# Verificar si el módulo requiere autenticación
modulo_acceso_key = f"acceso_{modulo_seleccionado}"

if not st.session_state[modulo_acceso_key]:
    # Mostrar interfaz de autenticación
    st.warning(f"🔒 **Acceso Restringido**: {modulo_seleccionado}")
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.write("**Autenticación Requerida**")
        contraseña = st.text_input(
            "Contraseña:",
            type="password",
            key=f"pass_{modulo_seleccionado}"
        )
        
        if st.button("🔑 Verificar Acceso", use_container_width=True):
            if contraseña == CONTRASEÑAS_MODULOS[modulo_seleccionado]:
                st.session_state[modulo_acceso_key] = True
                st.rerun()
            else:
                st.error("❌ Contraseña incorrecta")
    
    with col2:
        st.info("""
        **💡 Información:**
        - Cada módulo tiene su propia contraseña
        - Contacta al administrador si necesitas acceso
        - Las credenciales se mantienen durante la sesión
        """)
    
else:
    # Módulo desbloqueado - mostrar contenido
    if modulo_seleccionado == "🏭 Producción":
        mostrar_dashboard_produccion()
        
    elif modulo_seleccionado == "👥 Clima Laboral":
        mostrar_dashboard_clima_laboral()
        
    elif modulo_seleccionado == "😊 Satisfacción Cliente":
        mostrar_dashboard_satisfaccion()
    
    # Botón para cerrar sesión del módulo actual
    st.sidebar.markdown("---")
    if st.sidebar.button("🔒 Cerrar Sesión de Este Módulo"):
        st.session_state[modulo_acceso_key] = False
        st.rerun()

# Footer del sidebar
st.sidebar.markdown("---")
if st.sidebar.button("🚪 Cerrar Todas las Sesiones"):
    for modulo in CONTRASEÑAS_MODULOS.keys():
        st.session_state[f"acceso_{modulo}"] = False
    st.rerun()
