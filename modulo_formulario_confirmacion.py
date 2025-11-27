import streamlit as st
import requests
import json
import uuid
from datetime import datetime
import pandas as pd
import io
from PIL import Image, ImageDraw
import base64

# =============================================
# 🔗 CONEXIÓN CON APPSCRIPT
# =============================================

def conectar_appscript():
    """Obtener URL de AppScript desde secrets"""
    try:
        return st.secrets["appscript"]["url"]
    except:
        st.error("❌ No se configuró la URL de AppScript en los secrets")
        return None

def guardar_orden_appscript(datos_orden):
    """Guardar orden via AppScript Web App"""
    try:
        appscript_url = conectar_appscript()
        if not appscript_url:
            return False
        
        response = requests.post(
            appscript_url,
            json=datos_orden,
            headers={'Content-Type': 'application/json'}
        )
        
        if response.status_code == 200:
            result = response.json()
            if result.get('status') == 'success':
                return result
            else:
                st.error(f"❌ Error en AppScript: {result.get('message', 'Error desconocido')}")
                return False
        else:
            st.error(f"❌ Error HTTP {response.status_code}")
            return False
            
    except Exception as e:
        st.error(f"❌ Error de conexión: {str(e)}")
        return False

def buscar_orden_appscript(token):
    """Buscar orden por token via AppScript"""
    try:
        appscript_url = conectar_appscript()
        if not appscript_url:
            return None
        
        # AppScript usa GET para búsquedas
        url = f"{appscript_url}?token={token}"
        response = requests.get(url)
        
        if response.status_code == 200:
            result = response.json()
            if result.get('status') == 'success':
                return result.get('orden')
            else:
                st.error(f"❌ {result.get('message', 'Orden no encontrada')}")
                return None
        else:
            st.error("❌ Error buscando orden")
            return None
            
    except Exception as e:
        st.error(f"❌ Error de conexión: {str(e)}")
        return None

def confirmar_orden_appscript(token):
    """Confirmar orden via AppScript"""
    try:
        appscript_url = conectar_appscript()
        if not appscript_url:
            return False
        
        datos = {'accion': 'confirmar_orden', 'token': token}
        response = requests.post(
            appscript_url,
            json=datos,
            headers={'Content-Type': 'application/json'}
        )
        
        if response.status_code == 200:
            result = response.json()
            return result.get('status') == 'success'
        else:
            return False
            
    except Exception as e:
        st.error(f"❌ Error confirmando orden: {str(e)}")
        return False

# =============================================
# 🎯 SISTEMA DE MARCADO DE IMÁGENES
# =============================================

def procesar_marcado_imagen(imagen, puntos_marcados):
    """Procesar imagen y agregar marcas X en las posiciones especificadas"""
    try:
        img = Image.open(imagen)
        width, height = img.size
        
        draw = ImageDraw.Draw(img)
        
        for punto in puntos_marcados:
            x, y = punto['x'], punto['y']
            tamaño_x = max(10, min(width, height) // 30)
            
            # Dibujar X roja
            draw.line([(x - tamaño_x, y - tamaño_x), (x + tamaño_x, y + tamaño_x)], fill='red', width=4)
            draw.line([(x + tamaño_x, y - tamaño_x), (x - tamaño_x, y + tamaño_x)], fill='red', width=4)
            
            # Círculo alrededor para mejor visibilidad
            draw.ellipse([(x - tamaño_x-2, y - tamaño_x-2), (x + tamaño_x+2, y + tamaño_x+2)], outline='red', width=2)
        
        img_bytes = io.BytesIO()
        if imagen.name.lower().endswith('.png'):
            img.save(img_bytes, format='PNG')
        else:
            img.save(img_bytes, format='JPEG', quality=95)
        img_bytes.seek(0)
        
        return img_bytes
        
    except Exception as e:
        st.error(f"❌ Error procesando imagen: {str(e)}")
        return None

def mostrar_interfaz_marcado_simple(archivo, numero_posicion):
    """Interfaz simple de marcado SIN formulario"""
    
    # Inicializar session_state
    key_puntos = f'puntos_{numero_posicion}'
    if key_puntos not in st.session_state:
        st.session_state[key_puntos] = []
    
    # Mostrar imagen original
    imagen = Image.open(archivo)
    st.image(imagen, use_column_width=True, caption=f"Imagen {numero_posicion} - {imagen.width} x {imagen.height} px")
    
    # Controles de coordenadas
    col_coord1, col_coord2, col_coord3 = st.columns([2, 2, 1])
    
    with col_coord1:
        coord_x = st.slider(f"Coordenada X", 0, imagen.width, imagen.width//2, key=f"x_{numero_posicion}")
    
    with col_coord2:
        coord_y = st.slider(f"Coordenada Y", 0, imagen.height, imagen.height//2, key=f"y_{numero_posicion}")
    
    with col_coord3:
        rel_x = coord_x / imagen.width * 100
        rel_y = coord_y / imagen.height * 100
        st.metric("Relativo", f"{rel_x:.1f}%, {rel_y:.1f}%")
    
    # Botones de acción
    col_btn1, col_btn2, col_btn3 = st.columns(3)
    
    with col_btn1:
        if st.button("➕ Agregar", key=f"add_{numero_posicion}", use_container_width=True):
            st.session_state[key_puntos].append({'x': coord_x, 'y': coord_y})
            st.success(f"✅ Marca agregada en X:{coord_x}, Y:{coord_y}")
            st.rerun()
    
    with col_btn2:
        if st.button("🎯 Puntos Comunes", key=f"common_{numero_posicion}", use_container_width=True):
            puntos_comunes = [
                {'x': imagen.width // 2, 'y': imagen.height // 2},  # Centro
                {'x': imagen.width // 4, 'y': imagen.height // 2},  # Izquierda
                {'x': 3 * imagen.width // 4, 'y': imagen.height // 2},  # Derecha
                {'x': imagen.width // 2, 'y': imagen.height // 4},  # Arriba
                {'x': imagen.width // 2, 'y': 3 * imagen.height // 4},  # Abajo
            ]
            st.session_state[key_puntos].extend(puntos_comunes)
            st.success("✅ Marcas comunes agregadas")
            st.rerun()
    
    with col_btn3:
        if st.button("🔄 Limpiar", key=f"clear_{numero_posicion}", use_container_width=True):
            st.session_state[key_puntos] = []
            st.success("✅ Todas las marcas eliminadas")
            st.rerun()
    
    # Mostrar marcas actuales
    puntos = st.session_state[key_puntos]
    if puntos:
        st.write("**📍 Marcas actuales:**")
        for i, punto in enumerate(puntos):
            col_info, col_del = st.columns([4, 1])
            with col_info:
                rel_x = punto['x'] / imagen.width * 100
                rel_y = punto['y'] / imagen.height * 100
                st.write(f"**{i+1}.** X: {punto['x']} ({rel_x:.1f}%), Y: {punto['y']} ({rel_y:.1f}%)")
            with col_del:
                if st.button("🗑️", key=f"del_{numero_posicion}_{i}"):
                    st.session_state[key_puntos].pop(i)
                    st.rerun()
    else:
        st.info("📝 No hay marcas agregadas aún")
    
    # Vista previa con marcas
    if puntos:
        st.subheader("👁️ Vista Previa con Marcas")
        imagen_marcada = procesar_marcado_imagen(archivo, puntos)
        if imagen_marcada:
            st.image(imagen_marcada, use_column_width=True, caption="Vista previa con marcas X rojas")
            
            # Opción para descargar imagen marcada
            st.download_button(
                label="📥 Descargar Imagen Marcada",
                data=imagen_marcada.getvalue(),
                file_name=f"marcada_{archivo.name}",
                mime="image/jpeg" if archivo.name.lower().endswith(('.jpg', '.jpeg')) else "image/png",
                key=f"download_{numero_posicion}"
            )
    
    return st.session_state[key_puntos]

# =============================================
# 📝 FORMULARIO PRINCIPAL
# =============================================

def mostrar_formulario_creacion():
    """Formulario principal para crear órdenes"""
    
    st.header("🆕 Crear Nueva Orden de Bordado")
    
    # Información básica
    st.subheader("📋 Información General")
    col1, col2 = st.columns(2)
    
    with col1:
        cliente = st.text_input("👤 Cliente *", placeholder="Nombre del cliente")
        vendedor = st.text_input("👨‍💼 Vendedor *", placeholder="Nombre del vendedor")
        fecha_entrega = st.date_input("📅 Fecha de Entrega *", min_value=datetime.today().date())
    
    with col2:
        prendas = st.text_area("👕 Prendas *", placeholder="Ej: 10 playeras, 5 gorras, 3 sudaderas...")
        colores_prendas = st.text_area("🎨 Colores de Prendas *", placeholder="Ej: 5 negras, 3 blancas, 2 azules...")
    
    # Especificaciones técnicas
    st.subheader("📐 Especificaciones Técnicas")
    col_tech1, col_tech2 = st.columns(2)
    
    with col_tech1:
        nombre_diseno = st.text_input("🎨 Nombre del Diseño *", placeholder="Nombre y número de diseño")
        medidas_bordado = st.text_input("📏 Medidas del Bordado *", placeholder="Ej: 10x48 cm, 8x8 cm...")
    
    with col_tech2:
        colores_hilos = st.text_area("🧵 Colores de Hilos *", placeholder="Ej: Rojo #FF0000, Azul #0000FF, Negro...")
        tipo_hilos = st.text_input("🪡 Tipo de Hilos *", placeholder="Ej: 9 hilos, 12 hilos, metalizados...")
    
    # Posición del bordado
    st.subheader("📍 Posición del Bordado")
    posicion_bordado = st.selectbox(
        "Selecciona la posición *",
        ["Frente Izquierdo", "Frente Derecho", "Centro Pecho", "Espalda Completa", 
         "Manga Izquierda", "Manga Derecha", "Otro"],
        key="posicion_bordado"
    )
    
    detalles_posicion = st.text_area("📝 Detalles Adicionales de Posición", 
                                   placeholder="Especificaciones adicionales sobre la posición...")
    
    # 🎯 SISTEMA DE MARCADO DE POSICIONES
    st.subheader("🎯 Marcado de Posiciones del Bordado")
    
    st.info("""
    **💡 Instrucciones:**
    1. **Sube imágenes** de las prendas
    2. **Usa los sliders** para marcar posiciones exactas
    3. **Vista en tiempo real** de las marcas X rojas
    4. **Descarga** la imagen final con marcas
    """)
    
    # Subida de imágenes para marcado
    posiciones_files = st.file_uploader(
        "Subir imágenes para marcar posiciones (Máx. 5)", 
        type=['jpg', 'png', 'jpeg'],
        accept_multiple_files=True,
        key="posiciones_uploader"
    )
    
    # Mostrar interfaces de marcado para cada imagen
    puntos_por_imagen = {}
    if posiciones_files:
        st.success(f"📁 {len(posiciones_files)} imagen(es) cargada(s) para marcado")
        
        for i, archivo in enumerate(posiciones_files[:5]):
            with st.expander(f"🎯 Marcando Posición {i+1}: {archivo.name}", expanded=True):
                puntos_marcados = mostrar_interfaz_marcado_simple(archivo, i+1)
                puntos_por_imagen[f'posicion_{i+1}'] = puntos_marcados
    
    # Información de contacto para confirmación
    st.subheader("📧 Información para Confirmación")
    email_cliente = st.text_input("📧 Email del Cliente *", placeholder="email@cliente.com")
    telefono_cliente = st.text_input("📞 Teléfono del Cliente", placeholder="+52 123 456 7890")
    
    notas_generales = st.text_area("📝 Notas Generales", placeholder="Información adicional importante...")
    
    # Botón de envío principal
    st.markdown("---")
    if st.button("🚀 Crear Orden y Generar Enlace de Confirmación", type="primary", use_container_width=True):
        # Validación de campos obligatorios
        campos_requeridos = [
            cliente, vendedor, prendas, colores_prendas, nombre_diseno,
            colores_hilos, medidas_bordado, tipo_hilos, posicion_bordado, email_cliente
        ]
        
        if not all(campos_requeridos):
            st.error("❌ Por favor completa todos los campos obligatorios (*)")
        elif fecha_entrega <= datetime.today().date():
            st.error("❌ La fecha de entrega debe ser futura")
        else:
            # Generar token único
            token_confirmacion = str(uuid.uuid4())
            numero_orden = f"BORD-{int(datetime.now().timestamp()) % 10000:04d}"
            
            # Preparar datos para AppScript
            datos_orden = {
                'accion': 'crear_orden',
                'fecha_creacion': datetime.now().isoformat(),
                'numero_orden': numero_orden,
                'cliente': cliente,
                'vendedor': vendedor,
                'fecha_entrega': fecha_entrega.isoformat(),
                'prendas': prendas,
                'colores_prendas': colores_prendas,
                'nombre_diseno': nombre_diseno,
                'colores_hilos': colores_hilos,
                'medidas_bordado': medidas_bordado,
                'tipo_hilos': tipo_hilos,
                'posicion_bordado': posicion_bordado,
                'detalles_posicion': detalles_posicion,
                'email_cliente': email_cliente,
                'telefono_cliente': telefono_cliente,
                'notas_generales': notas_generales,
                'token_confirmacion': token_confirmacion,
                'estado': 'Pendiente Confirmación'
            }
            
            # Guardar via AppScript
            with st.spinner("💾 Guardando orden en base de datos..."):
                resultado = guardar_orden_appscript(datos_orden)
                
                if resultado:
                    # Generar enlace de confirmación
                    base_url = "https://tudashboard.streamlit.app"  # Cambia por tu URL
                    enlace_confirmacion = f"{base_url}/?token={token_confirmacion}"
                    
                    # Mostrar resultados
                    st.success("🎉 ¡Orden creada exitosamente!")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        st.info(f"**Número de Orden:** {numero_orden}")
                        st.info(f"**Cliente:** {cliente}")
                        st.info(f"**Estado:** Pendiente Confirmación")
                    
                    with col2:
                        st.info(f"**Enlace de Confirmación:**")
                        st.code(enlace_confirmacion, language="text")
                        
                        # Botón para copiar enlace
                        if st.button("📋 Copiar Enlace", key="copy_link"):
                            st.code(enlace_confirmacion, language="text")
                            st.success("✅ Enlace copiado - pégalo en un email o mensaje")
                    
                    st.markdown("---")
                    st.info("""
                    **📋 Próximos pasos:**
                    1. **Comparte el enlace** de confirmación con el cliente
                    2. **El cliente revisará** los detalles y confirmará la orden
                    3. **El estado cambiará** automáticamente a "Confirmado"
                    4. **Puedes seguir el progreso** en el dashboard de órdenes
                    """)

# =============================================
# ✅ PANEL DE CONFIRMACIÓN
# =============================================

def mostrar_interfaz_confirmacion(token):
    """Mostrar interfaz de confirmación para un token específico"""
    
    with st.spinner("🔍 Buscando orden..."):
        orden = buscar_orden_appscript(token)
    
    if not orden:
        st.error("""
        ❌ **Orden no encontrada**
        
        Posibles razones:
        - El enlace ha expirado
        - La orden ya fue confirmada
        - El token es incorrecto
        """)
        return
    
    estado_actual = orden.get('Estado', 'Desconocido')
    
    if estado_actual != 'Pendiente Confirmación':
        st.warning(f"⚠️ Esta orden ya fue **{estado_actual.lower()}**")
        
        if estado_actual == 'Confirmado':
            st.success("✅ Orden confirmada anteriormente")
        
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
    
    # Mostrar detalles adicionales
    if orden.get('Detalles Posición'):
        st.subheader("📍 Detalles de Posición")
        st.info(orden['Detalles Posición'])
    
    if orden.get('Notas Generales'):
        st.subheader("📝 Notas Generales")
        st.info(orden['Notas Generales'])
    
    # Solo mostrar sección de confirmación si está pendiente
    if estado_actual == 'Pendiente Confirmación':
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
                if confirmar_orden_appscript(token):
                    st.balloons()
                    st.success("🎉 ¡Orden confirmada exitosamente!")
                    st.info("📞 Nos pondremos en contacto contigo para los siguientes pasos.")
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

# =============================================
# 🔗 GESTIÓN DE ENLACES
# =============================================

def mostrar_gestion_enlaces():
    """Panel para gestionar enlaces de confirmación"""
    
    st.header("🔗 Gestión de Enlaces de Confirmación")
    
    st.info("""
    **📊 Funcionalidad en desarrollo:**
    - Próximamente podrás ver todas las órdenes pendientes
    - Generar enlaces de confirmación
    - Seguir el estado de las confirmaciones
    
    **Por ahora:** Usa el formulario de creación para generar enlaces individuales.
    """)
    
    # Aquí puedes agregar en el futuro la lista de órdenes pendientes
    st.warning("🚧 Esta funcionalidad estará disponible en la próxima actualización")

# =============================================
# 🎯 MÓDULO PRINCIPAL
# =============================================

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
