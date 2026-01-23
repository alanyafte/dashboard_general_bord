# modulo_capacitacion.py
import streamlit as st
import pandas as pd
from datetime import datetime
import plotly.graph_objects as go
from google.oauth2 import service_account
from googleapiclient.discovery import build
import hashlib

# Configuración de Google Drive API (si quieres mostrar archivos reales)
SCOPES = ['https://www.googleapis.com/auth/drive.readonly']

def obtener_hash_modulo():
    """Devuelve el hash para el módulo de capacitación"""
    return "3a7bd3e2360a3d29eea436fcfb7e44c735d117c42d1c1835420b6b9942dd4f1b"  # Hash para "capacitacion2024"

def mostrar_dashboard_capacitacion():
    """Dashboard principal del módulo de capacitación"""
    
    st.title("🎓 Sistema de Gestión de Capacitación - Mantenimiento")
    
    # Tabs para diferentes secciones
    tab1, tab2, tab3, tab4 = st.tabs([
        "📁 Estructura del Sistema", 
        "📊 Métricas", 
        "🔍 Buscar Documentos",
        "🚀 Acceso Rápido"
    ])
    
    with tab1:
        mostrar_estructura_sistema()
    
    with tab2:
        mostrar_metricas()
    
    with tab3:
        mostrar_buscador_documentos()
    
    with tab4:
        mostrar_acceso_rapido()

def mostrar_estructura_sistema():
    """Muestra la estructura jerárquica del sistema"""
    
    st.subheader("🏗️ Estructura del Sistema de Capacitación")
    
    # Crear estructura en formato árbol
    estructura_html = """
    <div style="font-family: 'Courier New', monospace; line-height: 1.8; background: #f8f9fa; padding: 20px; border-radius: 10px;">
        <strong>📁 [RAIZ_COMPAÑIA]/</strong><br>
        │<br>
        ├── 📁 <strong>SOPS/</strong> (Procedimientos Estandarizados)<br>
        │   │<br>
        │   ├── 📄 PLN-GEN-01_Plan_General.pdf<br>
        │   │<br>
        │   ├── 📁 <strong>SOP-MNT/</strong> (Mantenimiento)<br>
        │   │   ├── SOP-MNT-01_Procedimiento_Mantenimiento_Preventivo.pdf<br>
        │   │   ├── SOP-MNT-02_Procedimiento_Mantenimiento_Correctivo.pdf<br>
        │   │   └── <strong>SOP-MNT-03_Procedimiento_Gestion_Competencias.pdf</strong><br>
        │   │<br>
        │   ├── 📁 SOP-PRD/ (Producción)<br>
        │   ├── 📁 SOP-RPT/ (Reportes)<br>
        │   └── 📁 <strong>SOP-SEG/</strong> (Seguridad)<br>
        │       ├── <strong>SOP-SEG-01_Procedimiento_LOTO.pdf</strong><br>
        │       ├── <strong>SOP-SEG-02_Procedimiento_EPP.pdf</strong><br>
        │       └── <strong>SOP-SEG-03_Procedimiento_Trabajo_Seguro.pdf</strong><br>
        │<br>
        ├── 📁 <strong>MANTTO/</strong> (Mantenimiento)<br>
        │   │<br>
        │   ├── 📁 PLN-MNT/ (Planes)<br>
        │   │   ├── PLN-MNT-01_Plan_Mantenimiento_Anual.pdf<br>
        │   │   └── PLN-MNT-02_Cronograma_Mensual.xlsx<br>
        │   │<br>
        │   ├── 📁 FOR-MNT/ (Formatos)<br>
        │   │   ├── FOR-MNT-01_Orden_Trabajo.docx<br>
        │   │   ├── FOR-MNT-02_Checklist_Mantenimiento.docx<br>
        │   │   └── FOR-MNT-03_Reporte_Fallas.docx<br>
        │   │<br>
        │   └── 📁 <strong>COM-MNT/</strong> (Competencias)<br>
        │       ├── 📄 <strong>COM-MNT-01_Matriz_Competencias_General.xlsx</strong><br>
        │       ├── 📄 <strong>COM-MNT-02_Registro_Certificaciones.xlsx</strong><br>
        │       └── 📄 <strong>COM-MNT-03_Lista_Personal_Certificado.pdf</strong><br>
        │<br>
        └── 📁 <strong>CAP-MNT/</strong> (Capacitación Mantenimiento)<br>
            │<br>
            ├── 📄 PLN-CAP-MNT-01_Plan_Anual_Capacitacion.xlsx<br>
            ├── 📄 MAN-CAP-MNT-01_Manual_Sistema_Capacitacion.pdf<br>
            │<br>
            ├── 📁 <strong>FOR-CAP-MNT/</strong> (Formatos de Capacitación)<br>
            │   ├── 📄 FOR-CAP-MNT-01_Matriz_Competencias_Personal.xlsx<br>
            │   ├── 📄 FOR-CAP-MNT-02_Registro_Asistencia.docx<br>
            │   ├── 📄 FOR-CAP-MNT-03_Certificacion_Competencia.docx<br>
            │   ├── 📄 FOR-CAP-MNT-04_Expediente_Individual.docx<br>
            │   ├── 📄 FOR-CAP-MNT-05_Solicitud_Capacitacion.docx<br>
            │   └── 📄 FOR-CAP-MNT-06_Evaluacion_Post_Capacitacion.docx<br>
            │<br>
            ├── 📁 <strong>REG-CAP-MNT/</strong> (Registros Históricos)<br>
            │   ├── 📁 2024/<br>
            │   │   ├── REG-CAP-MNT-2024-001_Induccion_Enero_15.docx<br>
            │   │   ├── REG-CAP-MNT-2024-002_LOTO_Febrero_20.docx<br>
            │   │   └── REG-CAP-MNT-2024-003_EPP_Marzo_10.docx<br>
            │   └── 📁 2025/<br>
            │<br>
            ├── 📁 <strong>EXP-CAP-MNT/</strong> (Expedientes Digitales)<br>
            │   ├── 📁 EXP-CAP-MNT-001_Juan_Perez/<br>
            │   │   ├── 📄 PER-CAP-MNT-001_Ficha_Personal.pdf<br>
            │   │   ├── 📄 HIS-CAP-MNT-001_Historial_Capacitacion.xlsx<br>
            │   │   └── 📁 CER-CAP-MNT-001/<br>
            │   │       ├── CER-CAP-MNT-001-01_Prensa_Hidraulica.pdf<br>
            │   │       └── CER-CAP-MNT-001-02_LOTO.pdf<br>
            │   │<br>
            │   ├── 📁 EXP-CAP-MNT-002_Maria_Garcia/<br>
            │   └── 📁 EXP-CAP-MNT-003_Carlos_Lopez/<br>
            │<br>
            ├── 📁 <strong>PRO-CAP-MNT/</strong> (Programas de Capacitación)<br>
            │   ├── 📄 PRO-CAP-MNT-01_Programa_Induccion.pdf<br>
            │   ├── 📄 PRO-CAP-MNT-02_Programa_LOTO.pdf<br>
            │   ├── 📄 PRO-CAP-MNT-03_Programa_EPP.pdf<br>
            │   └── 📄 PRO-CAP-MNT-04_Programa_Primeros_Auxilios.pdf<br>
            │<br>
            └── 📁 <strong>INF-CAP-MNT/</strong> (Informes y Reportes)<br>
                ├── 📄 INF-CAP-MNT-01_Reporte_Mensual.xlsx<br>
                ├── 📄 INF-CAP-MNT-02_Estadisticas_Anuales.pdf<br>
                └── 📄 INF-CAP-MNT-03_Auditoria_Sistema.docx<br>
    </div>
    """
    
    st.markdown(estructura_html, unsafe_allow_html=True)
    
    # Información adicional
    with st.expander("📋 Nomenclatura del Sistema", expanded=False):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("**📄 Formatos/Plantillas:**")
            st.code("FOR-CAP-MNT-XX")
            st.markdown("**📁 Expedientes:**")
            st.code("EXP-CAP-MNT-XXX")
            
        with col2:
            st.markdown("**📑 Registros:**")
            st.code("REG-CAP-MNT-YYYY-XXX")
            st.markdown("**👤 Personales:**")
            st.code("PER-CAP-MNT-XXX")
            
        with col3:
            st.markdown("**📊 Historiales:**")
            st.code("HIS-CAP-MNT-XXX")
            st.markdown("**🏅 Certificaciones:**")
            st.code("CER-CAP-MNT-XXX")

def mostrar_metricas():
    """Muestra métricas y estadísticas del sistema"""
    
    st.subheader("📊 Métricas del Sistema de Capacitación")
    
    # Métricas en tarjetas
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            label="Total Capacitaciones 2024",
            value="24",
            delta="+3 vs 2023"
        )
    
    with col2:
        st.metric(
            label="Empleados Capacitados",
            value="156",
            delta="+28%"
        )
    
    with col3:
        st.metric(
            label="Certificaciones Activas",
            value="89",
            delta="+12"
        )
    
    with col4:
        st.metric(
            label="Tasa de Cumplimiento",
            value="94%",
            delta="+2%"
        )
    
    # Gráficos
    col_chart1, col_chart2 = st.columns(2)
    
    with col_chart1:
        # Gráfico de tipos de capacitación
        fig1 = go.Figure(data=[
            go.Pie(
                labels=['Inducción', 'Seguridad', 'Técnica', 'Primeros Auxilios'],
                values=[35, 30, 25, 10],
                hole=.3,
                marker_colors=['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728']
            )
        ])
        fig1.update_layout(title='Distribución por Tipo de Capacitación')
        st.plotly_chart(fig1, use_container_width=True)
    
    with col_chart2:
        # Gráfico de tendencia mensual
        meses = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun']
        capacitaciones = [3, 5, 4, 6, 7, 5]
        
        fig2 = go.Figure(data=[
            go.Bar(
                x=meses,
                y=capacitaciones,
                marker_color='#2ca02c',
                text=capacitaciones,
                textposition='auto'
            )
        ])
        fig2.update_layout(
            title='Capacitaciones por Mes (2024)',
            xaxis_title='Mes',
            yaxis_title='Número de Capacitaciones'
        )
        st.plotly_chart(fig2, use_container_width=True)
    
    # Tabla de últimas capacitaciones
    st.subheader("📅 Últimas Capacitaciones Registradas")
    
    ultimas_capacitaciones = pd.DataFrame({
        'Fecha': ['2024-06-15', '2024-06-10', '2024-06-05', '2024-05-28', '2024-05-20'],
        'Capacitación': ['Inducción General', 'Procedimiento LOTO', 'EPP Avanzado', 'Primeros Auxilios', 'Mantenimiento Preventivo'],
        'Instructor': ['Juan Pérez', 'María García', 'Carlos López', 'Ana Martínez', 'Pedro Sánchez'],
        'Participantes': [12, 8, 10, 15, 6],
        'Estado': ['✅ Completada', '✅ Completada', '✅ Completada', '✅ Completada', '✅ Completada']
    })
    
    st.dataframe(ultimas_capacitaciones, use_container_width=True, hide_index=True)

def mostrar_buscador_documentos():
    """Buscador de documentos en el sistema"""
    
    st.subheader("🔍 Buscador de Documentos")
    
    # Barra de búsqueda
    col_search, col_filter = st.columns([3, 1])
    
    with col_search:
        busqueda = st.text_input("Buscar documentos por nombre, tipo o código:")
    
    with col_filter:
        tipo_documento = st.selectbox(
            "Filtrar por tipo:",
            ["Todos", "Formatos", "Registros", "Expedientes", "Certificaciones", "Programas"]
        )
    
    # Base de datos simulada de documentos
    documentos = [
        {"Nombre": "FOR-CAP-MNT-01_Matriz_Competencias_Personal.xlsx", "Tipo": "Formato", "Ubicación": "FOR-CAP-MNT/", "Fecha": "2024-01-15"},
        {"Nombre": "REG-CAP-MNT-2024-001_Induccion_Enero_15.docx", "Tipo": "Registro", "Ubicación": "REG-CAP-MNT/2024/01-Enero/", "Fecha": "2024-01-20"},
        {"Nombre": "PER-CAP-MNT-001_Ficha_Personal.pdf", "Tipo": "Expediente", "Ubicación": "EXP-CAP-MNT-001_Juan_Perez/", "Fecha": "2024-02-10"},
        {"Nombre": "HIS-CAP-MNT-001_Historial_Capacitacion.xlsx", "Tipo": "Expediente", "Ubicación": "EXP-CAP-MNT-001_Juan_Perez/", "Fecha": "2024-02-10"},
        {"Nombre": "CER-CAP-MNT-001-01_Prensa_Hidraulica.pdf", "Tipo": "Certificación", "Ubicación": "EXP-CAP-MNT-001_Juan_Perez/CER-CAP-MNT-001/", "Fecha": "2024-03-05"},
        {"Nombre": "PRO-CAP-MNT-01_Programa_Induccion.pdf", "Tipo": "Programa", "Ubicación": "PRO-CAP-MNT/", "Fecha": "2024-01-10"},
        {"Nombre": "SOP-MNT-03_Procedimiento_Gestion_Competencias.pdf", "Tipo": "SOP", "Ubicación": "SOPS/SOP-MNT/", "Fecha": "2024-01-05"},
        {"Nombre": "COM-MNT-01_Matriz_Competencias_General.xlsx", "Tipo": "Competencia", "Ubicación": "MANTTO/COM-MNT/", "Fecha": "2024-01-08"},
    ]
    
    # Filtrar documentos
    if busqueda:
        documentos_filtrados = [d for d in documentos if busqueda.lower() in d["Nombre"].lower()]
    else:
        documentos_filtrados = documentos
    
    if tipo_documento != "Todos":
        documentos_filtrados = [d for d in documentos_filtrados if d["Tipo"] == tipo_documento]
    
    # Mostrar resultados
    if documentos_filtrados:
        st.write(f"**{len(documentos_filtrados)} documentos encontrados:**")
        
        for doc in documentos_filtrados:
            with st.expander(f"📄 {doc['Nombre']}"):
                col_info, col_action = st.columns([3, 1])
                
                with col_info:
                    st.write(f"**Tipo:** {doc['Tipo']}")
                    st.write(f"**Ubicación:** {doc['Ubicación']}")
                    st.write(f"**Fecha:** {doc['Fecha']}")
                
                with col_action:
                    # Simulación de enlace (en producción sería el enlace real)
                    if st.button("🔗 Ver", key=f"ver_{doc['Nombre']}"):
                        st.info(f"Enlace al documento: https://drive.google.com/file/d/ID_{doc['Nombre']}/view")
    else:
        st.warning("No se encontraron documentos con los criterios de búsqueda.")

def mostrar_acceso_rapido():
    """Acceso rápido a formularios y herramientas"""
    
    st.subheader("🚀 Acceso Rápido al Sistema")
    
    st.info("""
    **💡 Información para Empleados:**
    - Los formularios solo pueden ser llenados por personal autorizado
    - Contacta a tu supervisor si necesitas acceso
    - Todos los documentos generados siguen la nomenclatura estándar
    """)
    
    # Tarjetas de acceso
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("### 📝 Registro de Capacitación")
        st.write("Para instructores - Registrar capacitaciones realizadas")
        if st.button("Acceder al Formulario", key="form1", use_container_width=True):
            st.markdown('[👉 Abrir FORM-CAP-MNT-01](https://forms.gle/XXXXXXX-01)')
    
    with col2:
        st.markdown("### 👤 Alta de Operador")
        st.write("Para RRHH - Crear expediente de nuevo empleado")
        if st.button("Acceder al Formulario", key="form2", use_container_width=True):
            st.markdown('[👉 Abrir FORM-CAP-MNT-02](https://forms.gle/XXXXXXX-02)')
    
    with col3:
        st.markdown("### 📊 Panel de Control")
        st.write("Ver estadísticas y reportes del sistema")
        if st.button("Abrir Hoja de Control", key="control", use_container_width=True):
            st.markdown('[👉 Abrir REG-CAP-MNT_Control_2026](https://docs.google.com/spreadsheets/d/1XivfaS94O4ICyFIy3p0nRt1_uHm65fYv-k5I238S4aI)')
    
    # Sección para empleados ver su información
    st.markdown("---")
    st.subheader("👤 Consulta Tu Información Personal")
    
    col_id, col_action = st.columns([2, 1])
    
    with col_id:
        id_empleado = st.text_input("Ingresa tu ID de empleado (ej: EXP-CAP-MNT-001):")
    
    with col_action:
        if st.button("Buscar Mi Expediente", use_container_width=True):
            if id_empleado:
                # Simulación de búsqueda
                if "001" in id_empleado:
                    st.success(f"✅ Expediente encontrado: {id_empleado}")
                    st.write(f"**Nombre:** Juan Pérez García")
                    st.write(f"**Puesto:** Técnico de Mantenimiento II")
                    st.write(f"**Certificaciones activas:** 3")
                    st.write(f"**Última capacitación:** 2024-06-15 - Inducción General")
                else:
                    st.error("❌ Expediente no encontrado. Verifica tu ID.")
            else:
                st.warning("⚠️ Ingresa tu ID de empleado")

# Función para verificación de contraseña
def verificar_contraseña_capacitacion(input_password):
    return hashlib.sha256(input_password.encode()).hexdigest() == obtener_hash_modulo()
