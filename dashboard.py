import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns
from datetime import datetime
import traceback
import json

# --- CONFIGURACIÓN STREAMLIT ---
st.set_page_config(page_title="Dashboard Clima Laboral - DEBUG", layout="wide")
st.title("🔧 Dashboard de Clima Laboral - MODO DEBUG")
st.markdown("**Diagnóstico completo de conexión**")

# --- DIAGNÓSTICO INICIAL COMPLETO ---
st.sidebar.header("🔍 DIAGNÓSTICO COMPLETO")

# Verificar todas las dependencias
try:
    import gspread
    from google.oauth2 import service_account
    GSHEETS_AVAILABLE = True
    st.sidebar.success("✅ gspread y google-auth instalados")
except ImportError as e:
    GSHEETS_AVAILABLE = False
    st.sidebar.error(f"❌ Error imports: {e}")

# Verificar secrets
if 'gcp_service_account' in st.secrets:
    st.sidebar.success("✅ Secrets encontrados")
    
    # Mostrar información del service account
    try:
        creds_info = st.secrets["gcp_service_account"]
        if isinstance(creds_info, str):
            creds_info = json.loads(creds_info)
        
        client_email = creds_info.get("client_email", "No encontrado")
        project_id = creds_info.get("project_id", "No encontrado")
        
        st.sidebar.info(f"📧 **Service Account:** {client_email}")
        st.sidebar.info(f"🏢 **Project ID:** {project_id}")
        
    except Exception as e:
        st.sidebar.error(f"❌ Error leyendo secrets: {e}")
else:
    st.sidebar.error("❌ NO hay secrets configurados")

# --- FUNCIÓN DE CONEXIÓN DETALLADA ---
def debug_conexion():
    if not GSHEETS_AVAILABLE:
        return None
    
    try:
        st.header("🔗 DEBUG DETALLADO DE CONEXIÓN")
        
        # 1. Crear credenciales
        creds = service_account.Credentials.from_service_account_info(
            st.secrets["gcp_service_account"],
            scopes=['https://www.googleapis.com/auth/spreadsheets', 
                   'https://www.googleapis.com/auth/drive']
        )
        st.success("✅ Credenciales creadas correctamente")
        
        # 2. Autorizar
        gc = gspread.authorize(creds)
        st.success("✅ Cliente de Google autorizado")
        
        # 3. Intentar abrir la hoja
        url = "https://docs.google.com/spreadsheets/d/1dBubiABkbfpCGxn3b7eLC12DyM-R9N0XdxI93gL2Bv0/edit#gid=0"
        
        st.write(f"🌐 **Intentando abrir URL:** {url}")
        
        try:
            sh = gc.open_by_url(url)
            st.success("✅ ¡HOJA ENCONTRADA Y ACCESIBLE!")
            
            # 4. Listar todas las hojas
            worksheets = sh.worksheets()
            hojas_disponibles = [ws.title for ws in worksheets]
            
            st.write("📋 **Hojas disponibles en el documento:**")
            for hoja in hojas_disponibles:
                st.write(f"   - {hoja}")
            
            # 5. Verificar hojas requeridas
            hojas_requeridas = ["Ventas", "Produccion", "Ventas_c", "Produccion_c"]
            st.write("🔍 **Buscando hojas requeridas:**")
            
            for hoja in hojas_requeridas:
                if hoja in hojas_disponibles:
                    st.success(f"   ✅ {hoja} - ENCONTRADA")
                    try:
                        worksheet = sh.worksheet(hoja)
                        datos = worksheet.get_all_records()
                        st.success(f"   📊 {hoja}: {len(datos)} filas leídas")
                    except Exception as e:
                        st.error(f"   ❌ Error leyendo {hoja}: {str(e)}")
                else:
                    st.error(f"   ❌ {hoja} - NO ENCONTRADA")
            
            return True
            
        except gspread.SpreadsheetNotFound:
            st.error("❌ HOJA NO ENCONTRADA - Verifica la URL")
            st.warning("""
            **Posibles soluciones:**
            1. Verifica que la URL sea correcta
            2. Asegúrate de haber compartido la hoja con el service account
            3. El service account email es: **{}**
            """.format(client_email))
            
        except gspread.exceptions.APIError as e:
            st.error(f"❌ ERROR DE API: {str(e)}")
            st.warning("""
            **Error de permisos de Google API:**
            1. Verifica que el Service Account tenga habilitadas las APIs
            2. Ve a Google Cloud Console > APIs & Services > Enable APIs
            3. Habilita: Google Sheets API y Google Drive API
            """)
            
        except Exception as e:
            st.error(f"❌ ERROR INESPERADO: {str(e)}")
            st.text(traceback.format_exc())
            
    except Exception as e:
        st.error(f"❌ ERROR EN CONEXIÓN: {str(e)}")
        st.text(traceback.format_exc())
    
    return False

# --- EJECUTAR DEBUG ---
if st.button("🔄 EJECUTAR DIAGNÓSTICO COMPLETO", type="primary"):
    conexion_exitosa = debug_conexion()
    
    if conexion_exitosa:
        st.balloons()
        st.success("🎉 ¡CONEXIÓN EXITOSA! Ahora puedes usar tu código original")
    else:
        st.error("❌ ¡FALLA EN LA CONEXIÓN! Revisa los mensajes arriba")

# --- DATOS DE PRUEBA (como fallback) ---
st.header("📊 Datos de Prueba (Modo Seguro)")

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

st.dataframe(datos_prueba.style.format("{:.2f}"))

# --- INSTRUCCIONES ---
with st.expander("📋 INSTRUCCIONES PASO A PASO"):
    st.write("""
    1. **Haz clic en 'EJECUTAR DIAGNÓSTICO COMPLETO'**
    2. **Revisa cada paso del diagnóstico**
    3. **Si hay errores de permisos:**
       - Ve a Google Cloud Console
       - Habilita Google Sheets API y Google Drive API
       - Comparte tu Sheets con el email del service account
    4. **Si las hojas no se encuentran:**
       - Verifica los nombres exactos de las pestañas
    5. **Una vez funcione el diagnóstico, usa tu código original**
    """)

st.warning("⚠️ Ejecuta el diagnóstico completo para ver el error exacto")
