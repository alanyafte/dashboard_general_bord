import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import uuid
from datetime import datetime
import pandas as pd
import io
from PIL import Image

# Configuración para Google Sheets y Drive
SCOPE = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/drive"        
]

def conectar_google_sheets():
    """Conectar con Google Sheets"""
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
        
        # ✅ CORRECTO: Usar el nombre de la clave
        sheet_id = st.secrets["gsheets"]["ordenes_bordado_sheet_id"]
        spreadsheet = client.open_by_key(sheet_id)
        sheet = spreadsheet.worksheet("OrdenesBordado")
        
        return sheet
        
    except Exception as e:
        st.error(f"❌ Error conectando con Google Sheets: {e}")
        return None

def generar_numero_orden():
    """Generar número de orden único"""
    sheet = conectar_google_sheets()
    if sheet:
        try:
            data = sheet.get_all_records()
            if data:
                # Buscar el último número de orden
                ultimo_numero = 1
                for fila in data:
                    if 'Número Orden' in fila and fila['Número Orden']:
                        try:
                            num = int(fila['Número Orden'].split('-')[1])
                            ultimo_numero = max(ultimo_numero, num + 1)
                        except:
                            continue
                return f"BORD-{ultimo_numero:03d}"
        except:
            pass
    
    return f"BORD-{int(datetime.now().timestamp()) % 1000:03d}"

def subir_archivo_drive(archivo, tipo_archivo):
    """Subir archivo REAL a Google Drive"""
    try:
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaIoBaseUpload
        import io
        
        # Conectar a Drive API usando tus credenciales existentes
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
        drive_service = build('drive', 'v3', credentials=creds)
        
        # Buscar o crear carpeta para diseños de bordado
        folder_name = "Diseños_Bordado_App"
        folder_id = buscar_o_crear_carpeta_drive(drive_service, folder_name)
        
        # Preparar metadata del archivo
        file_metadata = {
            'name': f"{tipo_archivo}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{archivo.name}",
            'parents': [folder_id]
        }
        
        # Subir archivo
        media = MediaIoBaseUpload(
            io.BytesIO(archivo.getvalue()),
            mimetype=archivo.type,
            resumable=True
        )
        
        file = drive_service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id'
        ).execute()
        
        # Hacer público el archivo
        drive_service.permissions().create(
            fileId=file['id'],
            body={'type': 'anyone', 'role': 'reader'}
        ).execute()
        
        # Retornar URL directa para embedding
        return f"https://drive.google.com/uc?id={file['id']}"
        
    except Exception as e:
        st.error(f"❌ Error subiendo archivo a Drive: {str(e)}")
        return None

def buscar_o_crear_carpeta_drive(drive_service, folder_name):
    """Buscar o crear carpeta en Drive"""
    try:
        # Buscar carpeta existente
        results = drive_service.files().list(
            q=f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false",
            spaces='drive',
            fields='files(id, name)'
        ).execute()
        
        folders = results.get('files', [])
        
        if folders:
            return folders[0]['id']
        else:
            # Crear nueva carpeta
            folder_metadata = {
                'name': folder_name,
                'mimeType': 'application/vnd.google-apps.folder'
            }
            
            folder = drive_service.files().create(body=folder_metadata, fields='id').execute()
            
            # También hacer pública la carpeta
            drive_service.permissions().create(
                fileId=folder['id'],
                body={'type': 'anyone', 'role': 'reader'}
            ).execute()
            
            return folder['id']
            
    except Exception as e:
        st.error(f"❌ Error gestionando carpeta Drive: {str(e)}")
        return None

def subir_archivos_drive(archivos, tipo_archivo):
    """Subir múltiples archivos a Drive"""
    if not archivos:
        return []
    
    urls = []
    for i, archivo in enumerate(archivos):
        with st.spinner(f"Subiendo {tipo_archivo} {i+1}..."):
            url = subir_archivo_drive(archivo, tipo_archivo)
            if url:
                urls.append(url)
            else:
                st.error(f"❌ Error subiendo {archivo.name}")
    
    return urls

def guardar_orden_sheets(datos_orden):
    """Guardar orden completa en Google Sheets"""
    try:
        sheet = conectar_google_sheets()
        if not sheet:
            return False
        
        # Preparar la fila con todas las columnas
        fila = [
            datos_orden.get('Fecha Creación', ''),
            datos_orden.get('Número Orden', ''),
            datos_orden.get('Cliente', ''),
            datos_orden.get('Vendedor', ''),
            datos_orden.get('Fecha Entrega', ''),
            datos_orden.get('Prendas', ''),
            datos_orden.get('Colores de Prendas', ''),
            datos_orden.get('Nombre Diseño', ''),
            datos_orden.get('Colores de Hilos', ''),
            datos_orden.get('Medidas Bordado', ''),
            datos_orden.get('Tipo Hilos', ''),
            datos_orden.get('Posición Bordado', ''),
            datos_orden.get('Detalles Posición', ''),
            datos_orden.get('Notas Generales', ''),
            # Diseños 1-5
            datos_orden.get('Diseño 1', ''),
            datos_orden.get('Diseño 2', ''),
            datos_orden.get('Diseño 3', ''),
            datos_orden.get('Diseño 4', ''),
            datos_orden.get('Diseño 5', ''),
            # Posiciones 1-5
            datos_orden.get('Posición 1', ''),
            datos_orden.get('Posición 2', ''),
            datos_orden.get('Posición 3', ''),
            datos_orden.get('Posición 4', ''),
            datos_orden.get('Posición 5', ''),
            # Firma del cliente (placeholder)
            datos_orden.get('Nombre Aprobador', ''),
            datos_orden.get('Fecha Aprobación', ''),
            datos_orden.get('Firma Cliente', 'Sin firma digital'),
            # Estado y confirmación
            datos_orden.get('Estado', 'Pendiente Confirmación'),
            # Campos adicionales para tracking
            datos_orden.get('Email Cliente', ''),
            datos_orden.get('Telefono Cliente', ''),
            datos_orden.get('Token Confirmacion', ''),
            datos_orden.get('Fecha Confirmación', ''),
            datos_orden.get('IP Confirmación', '')
        ]
        
        sheet.append_row(fila)
        return True
        
    except Exception as e:
        st.error(f"❌ Error guardando en Sheets: {str(e)}")
        return False

def buscar_orden_por_token(token):
    """Buscar orden por token de confirmación"""
    sheet = conectar_google_sheets()
    if sheet:
        try:
            data = sheet.get_all_records()
            for orden in data:
                if orden.get('Token Confirmacion') == token:
                    return orden
        except Exception as e:
            st.error(f"❌ Error buscando orden: {e}")
    return None

def confirmar_orden_token(token):
    """Confirmar orden mediante token"""
    sheet = conectar_google_sheets()
    if sheet:
        try:
            data = sheet.get_all_records()
            for i, orden in enumerate(data, start=2):
                if orden.get('Token Confirmacion') == token:
                    # Actualizar estado a "Confirmado" y fecha
                    sheet.update_cell(i, 28, 'Confirmado')  # Columna Estado
                    sheet.update_cell(i, 33, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))  # Fecha Confirmación
                    return True
        except Exception as e:
            st.error(f"❌ Error confirmando orden: {e}")
    return False

def obtener_ordenes_pendientes_confirmacion():
    """Obtener órdenes pendientes de confirmación"""
    sheet = conectar_google_sheets()
    if sheet:
        try:
            data = sheet.get_all_records()
            pendientes = [orden for orden in data if orden.get('Estado') == 'Pendiente Confirmación']
            return pendientes
        except Exception as e:
            st.error(f"❌ Error obteniendo órdenes pendientes: {e}")
    return []

def generar_enlace_confirmacion(token):
    """Generar enlace de confirmación"""
    # En producción, usar la URL real de tu app
    base_url = "https://tudashboard.streamlit.app"
    return f"{base_url}/?token={token}"

def validar_formulario_completo(form_data):
    """Validar todos los campos del formulario"""
    campos_requeridos = [
        form_data['cliente'], form_data['vendedor'], 
        form_data['prendas'], form_data['colores_prendas'],
        form_data['nombre_diseno'], form_data['colores_hilos'],
        form_data['medidas_bordado'], form_data['tipo_hilos'],
        form_data['posicion_bordado'], form_data['email_cliente']
    ]
    
    if not all(campos_requeridos):
        st.error("❌ Por favor completa todos los campos obligatorios (*)")
        return False
    
    if form_data['fecha_entrega'] <= datetime.today().date():
        st.error("❌ La fecha de entrega debe ser futura")
        return False
    
    return True


def mostrar_formulario_creacion():
    """Formulario para crear nuevas órdenes"""
    
    st.header("🆕 Crear Nueva Orden de Bordado")
    
    with st.form("nueva_orden_form", clear_on_submit=True):
        # Información básica
        col1, col2 = st.columns(2)
        
        with col1:
            cliente = st.text_input("👤 Cliente *", placeholder="Nombre del cliente")
            vendedor = st.text_input("👨‍💼 Vendedor *", placeholder="Nombre del vendedor")
            fecha_entrega = st.date_input("📅 Fecha de Entrega *", min_value=datetime.today())
        
        with col2:
            prendas = st.text_area("👕 Prendas *", placeholder="Ej: 10 playeras, 5 gorras...")
            colores_prendas = st.text_area("🎨 Colores de Prendas *", placeholder="Ej: 5 negras, 3 blancas...")
        
        # Especificaciones técnicas
        st.subheader("📐 Especificaciones Técnicas")
        col_tech1, col_tech2 = st.columns(2)
        
        with col_tech1:
            nombre_diseno = st.text_input("🎨 Nombre del Diseño *", placeholder="Nombre y número de diseño")
            medidas_bordado = st.text_input("📏 Medidas del Bordado *", placeholder="Ej: 10x48 cm")
        
        with col_tech2:
            colores_hilos = st.text_area("🧵 Colores de Hilos *", placeholder="Ej: Rojo #FF0000, Azul #0000FF...")
            tipo_hilos = st.text_input("🪡 Tipo de Hilos *", placeholder="Ej: 9 hilos")
        
        # Posición del bordado
        posicion_bordado = st.selectbox(
            "📍 Posición del Bordado *",
            ["Frente Izquierdo", "Frente Derecho", "Centro Pecho", "Espalda Completa", 
             "Manga Izquierda", "Manga Derecha", "Otra"]
        )
        
        detalles_posicion = st.text_area("📝 Detalles de Posición", placeholder="Especificaciones adicionales sobre la posición...")
        
        # Subida de archivos
        st.subheader("🖼️ Archivos Adjuntos")
        
        col_files1, col_files2 = st.columns(2)
        
        with col_files1:
            st.write("**Diseños (Máx. 5)**")
            disenos_files = st.file_uploader(
                "Subir diseños", 
                type=['jpg', 'png', 'jpeg', 'pdf'],
                accept_multiple_files=True,
                key="disenos_uploader",
                label_visibility="collapsed"
            )
            
            # Mostrar preview de diseños
            if disenos_files:
                st.write("**Vista previa de diseños:**")
                cols = st.columns(min(3, len(disenos_files)))
                for i, archivo in enumerate(disenos_files[:3]):
                    with cols[i]:
                        if archivo.type.startswith('image/'):
                            image = Image.open(archivo)
                            st.image(image, caption=f"Diseño {i+1}", width=100)
                        else:
                            st.info(f"📄 {archivo.name}")
        
        with col_files2:
            st.write("**Imágenes de Posición (Máx. 5)**")
            posiciones_files = st.file_uploader(
                "Subir posiciones", 
                type=['jpg', 'png', 'jpeg'],
                accept_multiple_files=True,
                key="posiciones_uploader",
                label_visibility="collapsed"
            )
            
            # Mostrar preview de posiciones
            if posiciones_files:
                st.write("**Vista previa de posiciones:**")
                cols = st.columns(min(3, len(posiciones_files)))
                for i, archivo in enumerate(posiciones_files[:3]):
                    with cols[i]:
                        image = Image.open(archivo)
                        st.image(image, caption=f"Posición {i+1}", width=100)
        
        # Información de contacto para confirmación
        st.subheader("📧 Información para Confirmación")
        email_cliente = st.text_input("📧 Email del Cliente *", placeholder="email@cliente.com")
        telefono_cliente = st.text_input("📞 Teléfono del Cliente", placeholder="+52 123 456 7890")
        
        notas_generales = st.text_area("📝 Notas Generales", placeholder="Información adicional importante...")
        
        # Botón de envío
        submitted = st.form_submit_button("🚀 Crear Orden y Generar Enlace de Confirmación", use_container_width=True)
        
        if submitted:
            form_data = {
                'cliente': cliente,
                'vendedor': vendedor,
                'fecha_entrega': fecha_entrega,
                'prendas': prendas,
                'colores_prendas': colores_prendas,
                'nombre_diseno': nombre_diseno,
                'medidas_bordado': medidas_bordado,
                'colores_hilos': colores_hilos,
                'tipo_hilos': tipo_hilos,
                'posicion_bordado': posicion_bordado,
                'detalles_posicion': detalles_posicion,
                'email_cliente': email_cliente,
                'telefono_cliente': telefono_cliente,
                'notas_generales': notas_generales,
                'disenos_files': disenos_files,
                'posiciones_files': posiciones_files
            }
            
            if validar_formulario_completo(form_data):
                crear_orden_con_confirmacion(form_data)

def crear_orden_con_confirmacion(form_data):
    """Crear orden en Sheets y generar enlace de confirmación"""
    
    try:
        # Generar token único y número de orden
        token_confirmacion = str(uuid.uuid4())
        numero_orden = generar_numero_orden()
        
        # Subir archivos a Drive
        with st.spinner("📤 Subiendo archivos a Drive..."):
            urls_disenos = subir_archivos_drive(form_data['disenos_files'], "disenos")
            urls_posiciones = subir_archivos_drive(form_data['posiciones_files'], "posiciones")
        
        # Preparar datos para Google Sheets
        datos_orden = {
            'Fecha Creación': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'Número Orden': numero_orden,
            'Cliente': form_data['cliente'],
            'Vendedor': form_data['vendedor'],
            'Fecha Entrega': form_data['fecha_entrega'].strftime("%Y-%m-%d"),
            'Prendas': form_data['prendas'],
            'Colores de Prendas': form_data['colores_prendas'],
            'Nombre Diseño': form_data['nombre_diseno'],
            'Colores de Hilos': form_data['colores_hilos'],
            'Medidas Bordado': form_data['medidas_bordado'],
            'Tipo Hilos': form_data['tipo_hilos'],
            'Posición Bordado': form_data['posicion_bordado'],
            'Detalles Posición': form_data.get('detalles_posicion', ''),
            'Notas Generales': form_data.get('notas_generales', ''),
            'Email Cliente': form_data['email_cliente'],
            'Telefono Cliente': form_data.get('telefono_cliente', ''),
            'Token Confirmacion': token_confirmacion,
            'Estado': 'Pendiente Confirmación',
            'Fecha Confirmación': '',
            'IP Confirmación': ''
        }
        
        # Agregar URLs de diseños
        for i, url in enumerate(urls_disenos[:5], 1):
            datos_orden[f'Diseño {i}'] = url
        
        # Agregar URLs de posiciones  
        for i, url in enumerate(urls_posiciones[:5], 1):
            datos_orden[f'Posición {i}'] = url
        
        # Rellenar diseños faltantes
        for i in range(len(urls_disenos) + 1, 6):
            datos_orden[f'Diseño {i}'] = ''
        
        # Rellenar posiciones faltantes
        for i in range(len(urls_posiciones) + 1, 6):
            datos_orden[f'Posición {i}'] = ''
        
        # Guardar en Google Sheets
        with st.spinner("💾 Guardando orden en base de datos..."):
            if guardar_orden_sheets(datos_orden):
                # Generar enlace de confirmación
                enlace_confirmacion = generar_enlace_confirmacion(token_confirmacion)
                
                # Mostrar resultados
                st.success("🎉 ¡Orden creada exitosamente!")
                
                col1, col2 = st.columns(2)
                with col1:
                    st.info(f"**Número de Orden:** {numero_orden}")
                    st.info(f"**Cliente:** {form_data['cliente']}")
                    st.info(f"**Estado:** Pendiente Confirmación")
                
                with col2:
                    st.info(f"**Enlace de Confirmación:**")
                    st.code(enlace_confirmacion, language="text")
                    
                    # Botón para copiar enlace
                    if st.button("📋 Copiar Enlace al Portapapeles", use_container_width=True):
                        st.code(enlace_confirmacion, language="text")
                        st.success("✅ Enlace copiado - puedes pegarlo en un email o mensaje")
                
                st.markdown("---")
                st.info("""
                **📋 Próximos pasos:**
                1. **Comparte el enlace** de confirmación con el cliente
                2. **El cliente revisará** los detalles y confirmará la orden
                3. **El estado cambiará** automáticamente a "Confirmado"
                4. **Puedes seguir el progreso** en el dashboard de órdenes
                """)
                
                return True
    
    except Exception as e:
        st.error(f"❌ Error al crear orden: {str(e)}")
        return False

def mostrar_interfaz_confirmacion(token):
    """Mostrar interfaz de confirmación para un token específico"""
    
    with st.spinner("🔍 Buscando orden..."):
        orden = buscar_orden_por_token(token)
    
    if not orden:
        st.error("""
        ❌ **Orden no encontrada**
        
        Posibles razones:
        - El enlace ha expirado (válido por 30 días)
        - La orden ya fue confirmada anteriormente
        - El enlace es incorrecto
        """)
        return
    
    if orden.get('Estado') != 'Pendiente Confirmación':
        estado_actual = orden.get('Estado', 'Desconocido')
        st.warning(f"⚠️ Esta orden ya fue **{estado_actual.lower()}**")
        
        if orden.get('Estado') == 'Confirmado':
            st.success("✅ Orden confirmada anteriormente")
            if orden.get('Fecha Confirmación'):
                st.info(f"**Fecha de confirmación:** {orden['Fecha Confirmación']}")
        
        # Mostrar detalles de todos modos
        st.markdown("---")
    
    # Mostrar resumen de la orden
    st.success(f"🔍 Orden encontrada: **{orden.get('Número Orden', 'N/A')}**")
    
    # Mostrar detalles en columnas
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📋 Información General")
        st.write(f"**Cliente:** {orden.get('Cliente', 'N/A')}")
        st.write(f"**Vendedor:** {orden.get('Vendedor', 'N/A')}")
        st.write(f"**Fecha de Entrega:** {orden.get('Fecha Entrega', 'N/A')}")
        st.write(f"**Prendas:** {orden.get('Prendas', 'N/A')}")
        st.write(f"**Colores de Prendas:** {orden.get('Colores de Prendas', 'N/A')}")
    
    with col2:
        st.subheader("🎨 Especificaciones Técnicas")
        st.write(f"**Diseño:** {orden.get('Nombre Diseño', 'N/A')}")
        st.write(f"**Colores de Hilos:** {orden.get('Colores de Hilos', 'N/A')}")
        st.write(f"**Medidas:** {orden.get('Medidas Bordado', 'N/A')}")
        st.write(f"**Tipo de Hilos:** {orden.get('Tipo Hilos', 'N/A')}")
        st.write(f"**Posición:** {orden.get('Posición Bordado', 'N/A')}")
    
    # Mostrar detalles de posición si existen
    if orden.get('Detalles Posición'):
        st.subheader("📍 Detalles de Posición")
        st.info(orden['Detalles Posición'])
    
    # Mostrar archivos adjuntos
    mostrar_archivos_adjuntos = False
    for i in range(1, 6):
        if orden.get(f'Diseño {i}') and 'simulated' not in orden[f'Diseño {i}']:
            mostrar_archivos_adjuntos = True
            break
    
    if mostrar_archivos_adjuntos:
        st.subheader("🖼️ Archivos Adjuntos")
        
        # Diseños
        st.write("**Diseños:**")
        cols_disenos = st.columns(5)
        for i in range(1, 6):
            if orden.get(f'Diseño {i}') and 'simulated' not in orden[f'Diseño {i}']:
                with cols_disenos[i-1]:
                    st.image(orden[f'Diseño {i}'], caption=f"Diseño {i}", use_column_width=True)
        
        # Posiciones
        st.write("**Posiciones:**")
        cols_posiciones = st.columns(5)
        for i in range(1, 6):
            if orden.get(f'Posición {i}') and 'simulated' not in orden[f'Posición {i}']:
                with cols_posiciones[i-1]:
                    st.image(orden[f'Posición {i}'], caption=f"Posición {i}", use_column_width=True)
    
    # Mostrar notas generales si existen
    if orden.get('Notas Generales'):
        st.subheader("📝 Notas Generales")
        st.info(orden['Notas Generales'])
    
    # Solo mostrar sección de confirmación si está pendiente
    if orden.get('Estado') == 'Pendiente Confirmación':
        st.markdown("---")
        st.subheader("✅ Confirmación Final")
        
        st.warning("""
        **⚠️ Por favor verifica que:**
        - ✅ Toda la información sea correcta
        - ✅ Los diseños sean los aprobados  
        - ✅ Las especificaciones técnicas sean las acordadas
        - ✅ La fecha de entrega sea la esperada
        """)
        
        # Checkbox de confirmación
        confirmo_correcto = st.checkbox("🔒 Confirmo que toda la información es correcta y apruebo la orden")
        acepto_terminos = st.checkbox("📝 Acepto los términos y condiciones del servicio")
        
        # Botón de confirmación
        if st.button("🎯 Confirmar Orden Definitivamente", 
                     type="primary", 
                     disabled=not (confirmo_correcto and acepto_terminos),
                     use_container_width=True):
            
            with st.spinner("Confirmando orden..."):
                if confirmar_orden_token(token):
                    st.balloons()
                    st.success("🎉 ¡Orden confirmada exitosamente!")
                    st.info("📞 Nos pondremos en contacto contigo para los siguientes pasos.")
                    
                    # Auto-recargar para mostrar estado actualizado
                    st.rerun()
                else:
                    st.error("❌ Error al confirmar la orden. Por favor intenta nuevamente.")

def mostrar_panel_confirmacion():
    """Panel para que los clientes confirmen órdenes"""
    
    st.header("✅ Confirmación de Órdenes por Clientes")
    
    # Obtener token de URL parameters
    query_params = st.experimental_get_query_params()
    token = query_params.get("token", [None])[0]
    
    if token:
        # Mostrar interfaz de confirmación
        mostrar_interfaz_confirmacion(token)
    else:
        # Mostrar instrucciones
        st.info("""
        ### 📋 Instrucciones para Clientes:
        
        1. **Recibirás un enlace único** por email o mensaje
        2. **Haz clic en el enlace** para ver los detalles de tu orden
        3. **Revisa cuidadosamente** toda la información
        4. **Confirma la orden** si todo está correcto
        
        ### 🔒 Seguridad:
        - Cada enlace es único y personal
        - Válido por 30 días
        - Solo se puede confirmar una vez
        """)
        
        # Opción para ingresar token manualmente
        with st.expander("🔑 Tengo un código de confirmación"):
            token_manual = st.text_input("Ingresa tu token de confirmación:")
            if st.button("🔍 Buscar Orden") and token_manual:
                mostrar_interfaz_confirmacion(token_manual)

def mostrar_gestion_enlaces():
    """Panel para gestionar enlaces de confirmación"""
    
    st.header("🔗 Gestión de Enlaces de Confirmación")
    
    # Obtener órdenes pendientes de confirmación
    with st.spinner("Buscando órdenes pendientes..."):
        ordenes_pendientes = obtener_ordenes_pendientes_confirmacion()
    
    if not ordenes_pendientes:
        st.info("🎉 No hay órdenes pendientes de confirmación")
        return
    
    st.success(f"📊 Se encontraron {len(ordenes_pendientes)} órdenes pendientes de confirmación")
    
    for orden in ordenes_pendientes:
        with st.expander(f"📦 {orden.get('Número Orden', 'N/A')} - {orden.get('Cliente', 'N/A')}", expanded=False):
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.write(f"**Vendedor:** {orden.get('Vendedor', 'N/A')}")
                st.write(f"**Fecha Creación:** {orden.get('Fecha Creación', 'N/A')}")
                st.write(f"**Email:** {orden.get('Email Cliente', 'No registrado')}")
                st.write(f"**Teléfono:** {orden.get('Telefono Cliente', 'No registrado')}")
                st.write(f"**Prendas:** {orden.get('Prendas', 'N/A')}")
            
            with col2:
                enlace = generar_enlace_confirmacion(orden['Token Confirmacion'])
                st.write("**Enlace de confirmación:**")
                st.code(enlace, language="text")
                
                # Botones de acción
                if st.button("📋 Copiar Enlace", key=f"copy_{orden['Token Confirmacion']}"):
                    st.code(enlace, language="text")
                    st.success("✅ Enlace copiado al portapapeles")
                
                st.write("")  # Espacio
                
                if st.button("🔄 Actualizar Estado", key=f"refresh_{orden['Token Confirmacion']}"):
                    st.rerun()

def mostrar_formulario_confirmacion():
    """Módulo principal para crear órdenes y sistema de confirmación"""
    
    st.title("📝 Sistema de Órdenes con Confirmación Automática")
    
    # Pestañas para diferentes funcionalidades
    tab1, tab2, tab3 = st.tabs(["📋 Crear Orden", "✅ Confirmar Orden", "🔗 Gestión de Enlaces"])
    
    with tab1:
        mostrar_formulario_creacion()
    
    with tab2:
        mostrar_panel_confirmacion()
    
    with tab3:
        mostrar_gestion_enlaces()
