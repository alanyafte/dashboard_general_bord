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
# 🔐 REEMPLAZA ESTO - HASHS en lugar de contraseñas en texto plano
HASHES_MODULOS = {
    "🏭 Producción": "9c1900c7d367f40b9c7953e96b98c49340e567dbaccc127834956929f963d7b0",
    "👥 Clima Laboral": "ab9335cda699f64ba4dc0307308754ceae1a4caa3b8e0ec539957fe4cef6aaa8",
    "😊 Satisfacción Cliente": "d6a2339d155e81f11349280374b228b27273e8f7725a1d2f0feae84c95caa2f9",
}

# 🔐 AÑADE esta función de verificación
def verificar_contraseña(input_password, stored_hash):
    return hashlib.sha256(input_password.encode()).hexdigest() == stored_hash

# Inicializar estado de sesión para cada módulo
for modulo in HASHES_MODULOS.keys(): 
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
            if contraseña == HASHES_MODULOS[modulo_seleccionado]:
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
