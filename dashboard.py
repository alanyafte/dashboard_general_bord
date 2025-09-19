import streamlit as st
import gspread
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns
from google.oauth2 import service_account
from datetime import datetime

# --- CONFIGURACIÓN STREAMLIT ---
st.set_page_config(page_title="Dashboard Clima Laboral", layout="wide")
st.title("📊 Dashboard de Clima Laboral")
st.markdown("**Datos actualizados desde Google Sheets**")

# --- AUTENTICACIÓN ---
@st.cache_resource
def get_credentials():
    return service_account.Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=['https://www.googleapis.com/auth/spreadsheets']
    )

# --- OBTENER DATOS CON CACHE ---
@st.cache_data(ttl=3600)  # Actualiza cada 1 hora
def obtener_datos_actualizados():
    try:
        creds = get_credentials()
        gc = gspread.authorize(creds)

        url = "https://docs.google.com/spreadsheets/d/1dBubiABkbfpCGxn3b7eLC12DyM-R9N0XdxI93gL2Bv0/edit#gid=0"
        sh = gc.open_by_url(url)

        # Leer las cuatro pestañas
        ventas_b = pd.DataFrame(sh.worksheet("Ventas").get_all_records())
        produccion_b = pd.DataFrame(sh.worksheet("Produccion").get_all_records())
        ventas_c = pd.DataFrame(sh.worksheet("Ventas_c").get_all_records())
        produccion_c = pd.DataFrame(sh.worksheet("Produccion_c").get_all_records())

        # Diccionario de mapeo
        mapeo_preguntas = {
            "Mi trabajo es interesante y significativo": "Funciones laborales",
            "Mi rol aprovecha adecuadamente mis habilidades": "Funciones laborales",
            "Estoy satisfecho/a con mis responsabilidades actuales": "Funciones laborales",
            "Mi carga de trabajo es manejable": "Funciones laborales",
            "Me siento motivado/a cada día para realizar mis tareas": "Funciones laborales",
            "Me siento cómodo/a y seguro/a en mi entorno de trabajo": "Entorno de trabajo",
            "Tengo los recursos y herramientas necesarios para hacer mi trabajo": "Entorno de trabajo",
            "Los espacios comunes son accesibles y adecuados": "Entorno de trabajo",
            "Mi entorno promueve la colaboración": "Entorno de trabajo",
            "Hay un buen equilibrio entre espacio personal y colaborativo": "Entorno de trabajo",
            "Me siento parte de una comunidad en el trabajo": "Relaciones laborales",
            "Tengo una buena relación con mi jefe directo": "Relaciones laborales",
            "Hay un ambiente de respeto entre los empleados": "Relaciones laborales",
            "Mi relación con compañeros es positiva": "Relaciones laborales",
            "Tengo oportunidades de conexión profesional dentro de la empresa": "Relaciones laborales",
            "Los beneficios laborales que recibo son adecuados": "Compensación y beneficios",
            "Mi salario es justo": "Compensación y beneficios",
            "Se reconoce y recompensa mi desempeño": "Compensación y beneficios",
            "Estoy satisfecho/a con las oportunidades de bonificaciones": "Compensación y beneficios",
            "Estoy satisfecho/a con los planes de seguro y atención médica": "Compensación y beneficios",
            "Estoy satisfecho/a con las opciones de capacitación disponibles": "Desarrollo profesional",
            "Recibo retroalimentación constructiva": "Desarrollo profesional",
            "La empresa me motiva a adquirir nuevas habilidades": "Desarrollo profesional",
            "Hay oportunidades de aprendizaje": "Desarrollo profesional",
            "Existen oportunidades de ascenso en mi puesto actual": "Desarrollo profesional",
            "La empresa tiene una visión clara y bien comunicada": "Liderazgo",
            "Los líderes son accesibles y receptivos": "Liderazgo",
            "Los líderes guían eficientemente mi trabajo": "Liderazgo",
            "Mi líder me apoya en mi crecimiento profesional": "Liderazgo",
            "Mi líder inspira y motiva al equipo": "Liderazgo",
            "Los valores de la empresa coinciden con los míos": "Cultura organizacional",
            "Estoy satisfecho/a con mi equilibrio vida-trabajo": "Cultura organizacional",
            "Tengo flexibilidad para gestionar asuntos personales": "Cultura organizacional",
            "La empresa promueve un ambiente inclusivo y diverso": "Cultura organizacional",
            "Estoy satisfecho/a con el clima laboral en general": "Cultura organizacional",
        }

        # Orden de secciones
        orden_secciones = [
            "Funciones laborales", "Entorno de trabajo", "Relaciones laborales",
            "Compensación y beneficios", "Desarrollo profesional", 
            "Liderazgo", "Cultura organizacional"
        ]

        # Funciones de cálculo
        def calcular_metricas(df, grupo):
            columnas_respuestas = [col for col in df.columns if col in mapeo_preguntas]
            df_numerico = df[columnas_respuestas].apply(pd.to_numeric, errors='coerce')
            df_renombrado = df_numerico.rename(columns=mapeo_preguntas)
            promedio_seccion = df_renombrado.T.groupby(level=0).mean().T.mean()
            resultado = promedio_seccion.to_frame(name=grupo)
            resultado = resultado.reindex(orden_secciones)
            return resultado

        def calcular_desviacion(df, grupo):
            columnas_respuestas = [col for col in df.columns if col in mapeo_preguntas]
            df_numerico = df[columnas_respuestas].apply(pd.to_numeric, errors='coerce')
            df_renombrado = df_numerico.rename(columns=mapeo_preguntas)
            desviacion_seccion = df_renombrado.T.groupby(level=0).std().T.mean()
            resultado = desviacion_seccion.to_frame(name=grupo)
            resultado = resultado.reindex(orden_secciones)
            return resultado

        # Calcular promedios
        res_ventas_b = calcular_metricas(ventas_b, "Ventas B")
        res_produccion_b = calcular_metricas(produccion_b, "Producción B")
        res_ventas_c = calcular_metricas(ventas_c, "Ventas C")
        res_produccion_c = calcular_metricas(produccion_c, "Producción C")

        # Unir resultados
        resultado_final = res_ventas_b.join(res_produccion_b).join(res_ventas_c).join(res_produccion_c)
        resultado_final["Promedio Empresa B"] = resultado_final[["Ventas B", "Producción B"]].mean(axis=1)
        resultado_final["Promedio Empresa C"] = resultado_final[["Ventas C", "Producción C"]].mean(axis=1)
        resultado_final["Promedio General"] = resultado_final[["Ventas B", "Producción B", "Ventas C", "Producción C"]].mean(axis=1)

        # Calcular desviaciones estándar
        desv_ventas_b = calcular_desviacion(ventas_b, "Desv. Ventas B")
        desv_produccion_b = calcular_desviacion(produccion_b, "Desv. Producción B")
        desv_ventas_c = calcular_desviacion(ventas_c, "Desv. Ventas C")
        desv_produccion_c = calcular_desviacion(produccion_c, "Desv. Producción C")

        # Unir todo
        resultado_final_total = resultado_final.join(desv_ventas_b).join(desv_produccion_b).join(desv_ventas_c).join(desv_produccion_c)
        resultado_final_total['ultima_actualizacion'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        return resultado_final_total
        
    except Exception as e:
        st.error(f"Error al obtener datos: {e}")
        return None


# --- INTERFAZ PRINCIPAL ---
datos = obtener_datos_actualizados()

if datos is not None:
    # Mostrar última actualización (manejo seguro)
    try:
        ultima_actualizacion = datos.get('ultima_actualizacion')
        if isinstance(ultima_actualizacion, pd.Series):
            ultima_str = ultima_actualizacion.iloc[0]
        else:
            ultima_str = ultima_actualizacion if ultima_actualizacion else datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        st.sidebar.success(f"✅ Última actualización: {ultima_str}")
    except:
        st.sidebar.success(f"✅ Última actualización: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # --- GRÁFICO COMPARATIVO ---
    st.header("Comparación entre Empresas B y C")
    comparativo_empresas = datos[["Promedio Empresa B", "Promedio Empresa C"]].copy()
    
    fig1, ax1 = plt.subplots(figsize=(12, 6))
    comparativo_empresas.plot(kind='bar', ax=ax1)
    ax1.set_title('Comparación de Satisfacción Laboral entre Empresas B y C')
    ax1.set_ylabel('Puntuación Promedio')
    ax1.set_xlabel('Secciones')
    ax1.tick_params(axis='x', rotation=45)
    ax1.legend(title='Empresa')
    plt.tight_layout()
    st.pyplot(fig1)

    # --- FILTROS INTERACTIVOS ---
if datos is not None:
    st.sidebar.header("🔍 Filtros Avanzados")
    
    # 1. Filtro por rango de puntuación
    min_val = float(datos.select_dtypes(include=[np.number]).min().min())
    max_val = float(datos.select_dtypes(include=[np.number]).max().max())
    
    rango_puntuacion = st.sidebar.slider(
        "Rango de Puntuación",
        min_value=min_val,
        max_value=max_val,
        value=(min_val, max_val),
        step=0.1
    )
    
    # 2. Filtro por secciones (multiselect)
    secciones_seleccionadas = st.sidebar.multiselect(
        "Secciones a mostrar",
        options=datos.index.tolist(),
        default=datos.index.tolist()
    )
    
    # 3. Filtro por departamentos
    departamentos = ['Ventas B', 'Producción B', 'Ventas C', 'Producción C', 'Promedio General']
    deptos_seleccionados = st.sidebar.multiselect(
        "Departamentos/Métricas",
        options=departamentos,
        default=departamentos
    )
    
    # Aplicar filtros
    datos_filtrados = datos.copy()
    
    # Filtrar por secciones
    if secciones_seleccionadas:
        datos_filtrados = datos_filtrados.loc[secciones_seleccionadas]
    
    # Filtrar por departamentos
    if deptos_seleccionados:
        datos_filtrados = datos_filtrados[deptos_seleccionados]
    
    # Filtrar por rango de puntuación (para columnas numéricas)
    for col in datos_filtrados.select_dtypes(include=[np.number]).columns:
        datos_filtrados = datos_filtrados[
            (datos_filtrados[col] >= rango_puntuacion[0]) & 
            (datos_filtrados[col] <= rango_puntuacion[1])
        ]
    
    # Usar datos filtrados en los gráficos
    datos = datos_filtrados

    


    
    # --- GRÁFICO DE PROMEDIOS ---
    st.header("Promedio General por Sección")
    
    fig2, ax2 = plt.subplots(figsize=(14, 7))
    bars = ax2.bar(datos.index, datos["Promedio General"],
                   color='lightblue', edgecolor='navy', linewidth=1.2, alpha=0.8)

    ax2.set_title("Clima Laboral por Sección - Promedio General", fontsize=16, fontweight='bold')
    ax2.set_ylabel("Nivel de Satisfacción (1-5)", fontsize=12, fontweight='bold')
    ax2.set_xlabel("Secciones", fontsize=12, fontweight='bold')
    ax2.tick_params(axis='x', rotation=45)

    # Añadir valores en las barras
    for i, v in enumerate(datos["Promedio General"]):
        ax2.text(i, v + 0.05, f'{v:.2f}', ha='center', va='bottom', fontweight='bold', fontsize=10)

    # Línea de referencia
    promedio_general = datos["Promedio General"].mean()
    ax2.axhline(y=promedio_general, color='red', linestyle='--', linewidth=2,
                label=f'Promedio General: {promedio_general:.2f}')
    ax2.grid(axis='y', alpha=0.2, linestyle='-')
    ax2.legend()
    ax2.set_ylim(0, max(datos["Promedio General"]) * 1.15)
    plt.tight_layout()
    st.pyplot(fig2)

    # --- GRÁFICO CON DESVIACIÓN ESTÁNDAR ---
    st.header("Promedio General con Desviación Estándar")
    
    std_of_averages_per_section = datos[['Ventas B', 'Producción B', 'Ventas C', 'Producción C']].std(axis=1)

    fig3, ax3 = plt.subplots(figsize=(14, 7))
    bars = ax3.bar(datos.index, datos["Promedio General"],
                   yerr=std_of_averages_per_section, capsize=5,
                   color='lightblue', edgecolor='navy', linewidth=1.2, alpha=0.8)

    ax3.set_title("Clima Laboral por Sección - Promedio General con Variabilidad", fontsize=16, fontweight='bold')
    ax3.set_ylabel("Nivel de Satisfacción (1-5)", fontsize=12, fontweight='bold')
    ax3.set_xlabel("Secciones", fontsize=12, fontweight='bold')
    ax3.tick_params(axis='x', rotation=45)

    # Añadir valores
    for i, v in enumerate(datos["Promedio General"]):
        ax3.text(i, v + 0.1, f'{v:.2f}', ha='center', va='bottom', fontweight='bold', fontsize=10)

    # Añadir desviaciones
    for i, (promedio, std_val) in enumerate(zip(datos["Promedio General"], std_of_averages_per_section)):
        y_position = promedio + std_val + 0.15
        ax3.text(i, y_position, f'±{std_val:.2f}', ha='center', va='bottom', 
                fontsize=9, fontweight='bold', bbox=dict(boxstyle="round,pad=0.3", 
                facecolor="white", edgecolor="gray", alpha=0.8))

    ax3.grid(axis='y', alpha=0.2, linestyle='-')
    max_value = max(datos["Promedio General"]) + max(std_of_averages_per_section)
    ax3.set_ylim(0, max_value * 1.2)
    plt.tight_layout()
    st.pyplot(fig3)

    # --- GRÁFICO DE PORCENTAJE ---
    st.header("Porcentaje de Satisfacción")
    
    promedio_total_porcentaje = (datos["Promedio General"] - 1) / 4 * 100

    fig4, ax4 = plt.subplots(figsize=(14, 7))
    bars = ax4.bar(promedio_total_porcentaje.index, promedio_total_porcentaje,
                   color='lightblue', edgecolor='navy', linewidth=1.2, alpha=0.8)

    ax4.set_title("Clima Laboral por Sección - Porcentaje de Satisfacción", fontsize=16, fontweight='bold')
    ax4.set_ylabel("Porcentaje de Satisfacción (%)", fontsize=12, fontweight='bold')
    ax4.set_xlabel("Secciones", fontsize=12, fontweight='bold')
    ax4.tick_params(axis='x', rotation=45)

    # Añadir valores
    for i, v in enumerate(promedio_total_porcentaje):
        ax4.text(i, v + 1, f'{v:.1f}%', ha='center', va='bottom', fontweight='bold', fontsize=10)

    # Líneas de referencia
    promedio_general_porcentaje = promedio_total_porcentaje.mean()
    ax4.axhline(y=promedio_general_porcentaje, color='red', linestyle='--', linewidth=2,
                label=f'Promedio General: {promedio_general_porcentaje:.1f}%')
    ax4.axhline(y=100, color='green', linestyle=':', linewidth=1, alpha=0.5, label='Máximo (100%)')
    ax4.grid(axis='y', alpha=0.2, linestyle='-')
    ax4.legend()
    ax4.set_ylim(0, 105)
    plt.tight_layout()
    st.pyplot(fig4)

    # --- HEATMAP ---
    st.header("Mapa de Calor por Departamento")
    
    heatmap_data = datos[['Ventas B', 'Producción B', 'Ventas C', 'Producción C']]

    fig5, ax5 = plt.subplots(figsize=(12, 8))
    sns.heatmap(heatmap_data, annot=True, fmt='.2f', cmap='RdYlGn',
               center=3.0, vmin=1, vmax=5, ax=ax5,
               cbar_kws={'label': 'Nivel de Satisfacción (1-5)'})
    ax5.set_title('Mapa de Calor - Clima Laboral por Sección y Departamento')
    plt.tight_layout()
    st.pyplot(fig5)

    # --- SEMÁFORO ---
    st.header("Semáforo de Clima Laboral")
    
    umbrales = {
        'Funciones laborales': (3.8, 4.2),
        'Entorno de trabajo': (3.5, 4.0),
        'Relaciones laborales': (4.0, 4.5),
        'Compensación y beneficios': (3.0, 3.5),
        'Desarrollo profesional': (2.5, 3.0),
        'Liderazgo': (3.2, 3.7),
        'Cultura organizacional': (3.8, 4.2)
    }

    colores = []
    for dimension in datos.index:
        valor = datos.loc[dimension, 'Promedio General']
        min_aceptable, min_deseable = umbrales[dimension]
        if valor < min_aceptable:
            colores.append('#FF6B6B')  # Rojo
        elif valor < min_deseable:
            colores.append('#FFD166')  # Amarillo
        else:
            colores.append('#06D6A0')  # Verde

    fig6, ax6 = plt.subplots(figsize=(16, 8))
    bars = ax6.bar(datos.index, datos['Promedio General'],
                  color=colores, edgecolor='black', linewidth=0.8, alpha=0.8)

    for i, (idx, row) in enumerate(datos.iterrows()):
        ax6.text(i, row['Promedio General'] + 0.05, f'{row["Promedio General"]:.2f}',
                ha='center', va='bottom', fontweight='bold', fontsize=11)

    ax6.set_ylabel('Nivel de Satisfacción (1-5)', fontsize=12, fontweight='bold')
    ax6.set_xlabel('Dimensiones de Clima Laboral', fontsize=12, fontweight='bold')
    ax6.set_title('Semáforo de Clima Laboral - Estado por Dimensión', fontsize=16, fontweight='bold')
    ax6.tick_params(axis='x', rotation=45)
    ax6.grid(axis='y', alpha=0.3, linestyle='--')

    # Leyenda
    from matplotlib.patches import Patch
    legend_elements = [
        Patch(facecolor='#06D6A0', label='Óptimo'),
        Patch(facecolor='#FFD166', label='Mejorable'),
        Patch(facecolor='#FF6B6B', label='Crítico')
    ]
    ax6.legend(handles=legend_elements, loc='upper right')
    ax6.set_ylim(0, 5)
    plt.tight_layout()
    st.pyplot(fig6)

    # --- ESTADÍSTICAS ---
    st.header("Estadísticas Resumen")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Promedio General", f"{datos['Promedio General'].mean():.2f}")
    with col2:
        st.metric("Mejor Sección", f"{datos['Promedio General'].idxmax()} ({datos['Promedio General'].max():.2f})")
    with col3:
        st.metric("Peor Sección", f"{datos['Promedio General'].idxmin()} ({datos['Promedio General'].min():.2f})")

    # Botón de actualización
    if st.button("🔄 Actualizar Datos Ahora", type="primary"):
        st.cache_data.clear()
        st.rerun()

else:
    st.error("No se pudieron cargar los datos. Verifica la conexión.")

# Mostrar datos en tabla
with st.expander("📊 Ver Datos Completos"):
    columnas_numericas = [col for col in datos.columns if col != 'ultima_actualizacion']
    st.dataframe(datos.style.format({col: "{:.2f}" for col in columnas_numericas}))

    # Botón de descarga
    csv = datos.to_csv(index=True)
    st.download_button(
        label="📥 Descargar CSV",
        data=csv,
        file_name="clima_laboral.csv",
        mime="text/csv"
    )
