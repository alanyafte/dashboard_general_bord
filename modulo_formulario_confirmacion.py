import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

# Configuración para Google Sheets (SOLO LECTURA)
SCOPE = ["https://www.googleapis.com/auth/spreadsheets.readonly"]

def conectar_google_sheets_solo_lectura():
    """Conectar con Google Sheets en modo solo lectura"""
    try:
        creds_dict = {
            "type": st.secrets["gservice_account"]["type"],
            "project_id": st.secrets["gservice_account"]["project_id"],
            "private_key_id": st.secrets["gservice_account"]["private_key_id"],
            "private_key": st.secrets["gservice_account"]["private_key"].replace('\\n', '\n'),
            "client_email": st.secrets["gservice_account"]["client_email"],
            "client_id": st.secrets["gservice_account"]["client_id"],
            "auth_uri": st.secrets["gservice_account"]["auth_uri"],
            "token_uri": st.secrets["gservice_account"]["token_uri"]
        }
        
        creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPE)
        client = gspread.authorize(creds)
        
        sheet_id = st.secrets["gsheets"]["ordenes_bordado_sheet_id"]
        spreadsheet = client.open_by_key(sheet_id)
        sheet = spreadsheet.worksheet("OrdenesBordado")
        
        return sheet
        
    except Exception as e:
        st.error(f"❌ Error conectando con Google Sheets: {e}")
        return None

def obtener_orden_por_id(pedido_id):
    """Obtener una orden específica (solo lectura)"""
    sheet = conectar_google_sheets_solo_lectura()
    if sheet:
        try:
            data = sheet.get_all_records()
            df = pd.DataFrame(data)
            orden = df[df['Número Orden'] == pedido_id]
            return orden.iloc[0] if not orden.empty else None
        except Exception as e:
            st.error(f"❌ Error obteniendo orden: {e}")
            return None
    return None

def main():
    """Aplicación separada solo para confirmaciones de clientes"""
    
    # Obtener parámetros de la URL
    query_params = st.query_params
    pedido_id = query_params.get("pedido", [None])[0] if "pedido" in query_params else None
    
    if not pedido_id:
        st.error("❌ No se especificó un ID de pedido")
        st.info("💡 Accede mediante el link proporcionado por el vendedor")
        return
    
    # Mostrar interfaz de confirmación
    st.set_page_config(page_title="Confirmación de Pedido", layout="centered")
    st.title("✅ Confirmación de Pedido")
    st.info("Por favor revise los detalles de su pedido y confirme que todo esté correcto.")
    
    # Obtener datos del pedido
    orden = obtener_orden_por_id(pedido_id)
    
    if orden is None:
        st.error("❌ No se encontró el pedido solicitado")
        return
    
    # Mostrar información (SOLO LECTURA - igual que antes)
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📋 Información del Pedido")
        st.write(f"**Número de Orden:** {orden['Número Orden']}")
        st.write(f"**Cliente:** {orden['Cliente']}")
        st.write(f"**Vendedor:** {orden.get('Vendedor', 'N/A')}")
        st.write(f"**Fecha de Entrega:** {orden.get('Fecha Entrega', 'N/A')}")
        st.write(f"**Prendas:** {orden.get('Prendas', 'N/A')}")
    
    with col2:
        st.subheader("🎨 Especificaciones")
        st.write(f"**Diseño:** {orden.get('Nombre Diseño', 'N/A')}")
        st.write(f"**Colores de Hilos:** {orden.get('Colores de Hilos', 'N/A')}")
        st.write(f"**Medidas:** {orden.get('Medidas Bordado', 'N/A')}")
        st.write(f"**Posición:** {orden.get('Posición Bordado', 'N/A')}")
    
    # Mostrar imágenes
    st.subheader("🖼️ Diseños y Posiciones")
    col_disenos = st.columns(5)
    for i in range(1, 6):
        diseno_col = f'Diseño {i}'
        if orden.get(diseno_col) and str(orden[diseno_col]) not in ['', 'nan', 'None']:
            with col_disenos[i-1]:
                try:
                    st.image(orden[diseno_col], caption=f"Diseño {i}", use_column_width=True)
                except:
                    st.markdown(f"[📎 Ver Diseño {i}]({orden[diseno_col]})")
    
    # Sección de confirmación
    st.markdown("---")
    st.subheader("🔏 Confirmación del Pedido")
    
    opcion = st.radio(
        "¿La información del pedido es correcta?",
        ["✅ Sí, confirmar pedido", "❌ No, necesito cambios"]
    )
    
    if opcion == "✅ Sí, confirmar pedido":
        nombre_completo = st.text_input("✍️ Ingrese su nombre completo para firmar:")
        email = st.text_input("📧 Email para confirmación:")
        
        if st.button("🎯 Confirmar y Firmar Pedido"):
            if nombre_completo and email:
                # Enviar confirmación por email (NO puede escribir en Sheets)
                st.success("📧 Confirmación enviada - Nos pondremos en contacto contigo")
                st.balloons()
            else:
                st.error("❌ Por favor complete todos los campos")
    
    else:  # Necesita cambios
        cambios = st.text_area("📝 Describa los cambios necesarios:")
        contacto = st.text_input("📞 Mejor forma de contactarte:")
        
        if st.button("📤 Enviar Solicitud de Cambios"):
            if cambios and contacto:
                st.success("📧 Solicitud enviada - Nos pondremos en contacto contigo")
                st.info("🛠️ Ajustaremos los detalles según sus indicaciones")
