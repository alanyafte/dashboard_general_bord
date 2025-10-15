import gspread
import pandas as pd
import matplotlib.pyplot as plt
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
import streamlit as st
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, timedelta, date
import pytz
import io

# ==================== CONFIGURACIÓN ====================

# Configuración de la página
st.set_page_config(
    page_title="Dashboard Producción Mejorado",
    page_icon="🏭",
    layout="wide"
)

# ==================== FUNCIONES DE LIMPIEZA ====================

def limpiar_dataframe(df_raw):
    """Limpiar y procesar el dataframe desde Google Forms"""
    df = df_raw.copy()
    
    # Eliminar columna de correo electrónico
    if "Dirección de correo electrónico" in df.columns:
        df = df.drop("Dirección de correo electrónico", axis=1)
    
    # Limpiar espacios en nombres de columnas y valores
    df.columns = df.columns.str.strip()
    for col in df.columns:
        if df[col].dtype == 'object':
            df[col] = df[col].str.strip()
    
    # Convertir Marca temporal a datetime
    if "Marca temporal" in df.columns:
        df["Marca temporal"] = pd.to_datetime(df["Marca temporal"], errors='coerce')
    
    # Convertir columnas numéricas
    numeric_columns = ["CANTIDAD", "PUNTADAS", "MULTIPLOS", "CABEZAS"]
    for col in numeric_columns:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
            df[col] = df[col].fillna(0)
    
    # Validar CABEZAS (valor por defecto 6 si está vacío o 0)
    if "CABEZAS" in df.columns:
        df["CABEZAS"] = df["CABEZAS"].replace(0, 6)
        df["CABEZAS"] = df["CABEZAS"].fillna(6)
    
    return df

# ==================== FUNCIONES DE CÁLCULO ====================

def calcular_puntadas_automaticamente(df):
    """Calcular automáticamente las puntadas usando CABEZAS del reporte"""
    
    if df.empty or "OPERADOR" not in df.columns:
        return pd.DataFrame()
    
    # Validar columnas necesarias
    required_cols = ['OPERADOR', 'CANTIDAD', 'PUNTADAS', 'CABEZAS']
    missing = [col for col in required_cols if col not in df.columns]
    if missing:
        st.error(f"❌ Columnas faltantes: {missing}")
        return pd.DataFrame()
    
    resultados = []
    
    # Agrupar por operador y fecha
    df_con_fecha = df.copy()
    df_con_fecha['Fecha'] = df_con_fecha['Marca temporal'].dt.date
    
    grupos = df_con_fecha.groupby(['OPERADOR', 'Fecha'])
    
    for (operador, fecha), grupo in grupos:
        # Ordenar por hora para calcular correctamente los cambios
        grupo_ordenado = grupo.sort_values('Marca temporal')
        
        for idx, (indice_fila, fila) in enumerate(grupo_ordenado.iterrows()):
            # Usar CABEZAS del reporte (no configuración fija)
            cabezas = fila.get("CABEZAS", 6)
            
            # Validar datos necesarios
            if pd.isna(fila.get("CANTIDAD")) or pd.isna(fila.get("PUNTADAS")) or cabezas == 0:
                continue
                
            piezas = fila["CANTIDAD"]
            puntadas_base = fila["PUNTADAS"]
            
            # Calcular múltiplos usando CABEZAS del reporte
            pasadas = np.ceil(piezas / cabezas)
            multiplo = pasadas * cabezas
            puntadas_ajustadas = max(puntadas_base, 4000)
            puntadas_multiplos = multiplo * puntadas_ajustadas
            
            # Calcular cambios de color
            if idx == 0:  # Primera orden del día
                puntadas_cambios = 36000 + 18000  # Inicio turno + primera orden
            else:  # Órdenes adicionales
                puntadas_cambios = 18000  # Solo cambio de color
            
            total_puntadas = puntadas_multiplos + puntadas_cambios
            
            resultados.append({
                'OPERADOR': operador,
                'FECHA': fecha,
                'PEDIDO': fila.get('#DE PEDIDO', 'N/A'),
                'TIPO_PRENDA': fila.get('TIPO DE PRENDA', 'N/A'),
                'DISEÑO': fila.get('DISEÑO', 'N/A'),
                'COLORES': fila.get('COLORES', 'N/A'),
                'CLAVE': fila.get('CLAVE', 'N/A'),
                'CANTIDAD': piezas,
                'PUNTADAS_BASE': puntadas_base,
                'CABEZAS_REPORTADAS': cabezas,
                'PASADAS': pasadas,
                'MULTIPLO': multiplo,
                'PUNTADAS_MULTIPLOS': puntadas_multiplos,
                'PUNTADAS_CAMBIOS': puntadas_cambios,
                'TOTAL_PUNTADAS': total_puntadas,
                'FECHA_CALCULO': datetime.now().date(),
                'HORA_CALCULO': datetime.now().strftime("%H:%M:%S"),
                'ORDEN_DEL_DIA': idx + 1
            })
    
    return pd.DataFrame(resultados)

# ==================== FUNCIONES DE GUARDADO ====================

def guardar_calculos_en_sheets(df_calculado):
    """Guardar cálculos en Google Sheets sin duplicados"""
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        
        service_account_info = {
            "type": st.secrets["gservice_account"]["type"],
            "project_id": st.secrets["gservice_account"]["project_id"],
            "private_key_id": st.secrets["gservice_account"]["private_key_id"],
            "private_key": st.secrets["gservice_account"]["private_key"],
            "client_email": st.secrets["gservice_account"]["client_email"],
            "client_id": st.secrets["gservice_account"]["client_id"],
            "auth_uri": st.secrets["gservice_account"]["auth_uri"],
            "token_uri": st.secrets["gservice_account"]["token_uri"]
        }
        
        creds = ServiceAccountCredentials.from_json_keyfile_dict(service_account_info, scope)
        gc = gspread.authorize(creds)
        
        sheet_id = st.secrets["gsheets"]["produccion_sheet_id"]
        spreadsheet = gc.open_by_key(sheet_id)
        
        try:
            worksheet = spreadsheet.worksheet("puntadas_calculadas")
        except:
            worksheet = spreadsheet.add_worksheet(title="puntadas_calculadas", rows="10000", cols="25")
        
        # Obtener datos existentes
        datos_existentes = worksheet.get_all_values()
        
        # Convertir fechas a string
        df_guardar = df_calculado.copy()
        df_guardar['FECHA'] = df_guardar['FECHA'].astype(str)
        df_guardar['FECHA_CALCULO'] = df_guardar['FECHA_CALCULO'].astype(str)
        
        # Verificar duplicados por operador, fecha, pedido
        if len(datos_existentes) > 1:
            df_existente = pd.DataFrame(datos_existentes[1:], columns=datos_existentes[0])
            
            # Filtrar duplicados
            df_nuevo = df_guardar.copy()
            for _, fila in df_guardar.iterrows():
                mask = (
                    (df_existente['OPERADOR'] == fila['OPERADOR']) &
                    (df_existente['FECHA'] == str(fila['FECHA'])) &
                    (df_existente['PEDIDO'] == fila['PEDIDO'])
                )
                if not df_existente[mask].empty:
                    df_nuevo = df_nuevo.drop(df_nuevo[df_nuevo.index == fila.name].index)
            
            if df_nuevo.empty:
                return True  # No hay datos nuevos que guardar
        else:
            df_nuevo = df_guardar
        
        # Escribir nuevos datos
        if not df_nuevo.empty:
            if len(datos_existentes) == 0:  # Hoja vacía
                worksheet.update('A1', [df_nuevo.columns.tolist()])
                proxima_fila = 2
            else:
                proxima_fila = len(datos_existentes) + 1
            
            nuevas_filas = df_nuevo.values.tolist()
            worksheet.update(f'A{proxima_fila}', nuevas_filas)
        
        return True
    except Exception as e:
        st.error(f"❌ Error al guardar cálculos: {str(e)}")
        return False

# ==================== FUNCIONES DE FILTROS ====================

def aplicar_filtros_avanzados(df):
    """Aplicar filtros interactivos avanzados"""
    df_filtrado = df.copy()
    
    st.sidebar.header("🔍 Filtros Avanzados")
    
    # Filtro por OPERADOR
    if "OPERADOR" in df.columns:
        operadores = sorted(df["OPERADOR"].unique())
        operadores_seleccionados = st.sidebar.multiselect(
            "Operadores:",
            options=operadores,
            default=operadores
        )
        if operadores_seleccionados:
            df_filtrado = df_filtrado[df_filtrado["OPERADOR"].isin(operadores_seleccionados)]
    
    # Filtro por fecha
    if "Marca temporal" in df.columns and not df_filtrado["Marca temporal"].isna().all():
        fechas_disponibles = df_filtrado["Marca temporal"].dropna()
        if not fechas_disponibles.empty:
            fecha_min = fechas_disponibles.min().to_pydatetime().date()
            fecha_max = fechas_disponibles.max().to_pydatetime().date()
            
            rango_fechas = st.sidebar.date_input(
                "Rango de Fechas:",
                value=(fecha_min, fecha_max),
                min_value=fecha_min,
                max_value=fecha_max
            )
            
            if len(rango_fechas) == 2:
                fecha_inicio, fecha_fin = rango_fechas
                fecha_inicio_dt = pd.to_datetime(fecha_inicio)
                fecha_fin_dt = pd.to_datetime(fecha_fin) + timedelta(days=1)
                
                mask = (df_filtrado["Marca temporal"] >= fecha_inicio_dt) & \
                       (df_filtrado["Marca temporal"] < fecha_fin_dt)
                df_filtrado = df_filtrado[mask]
    
    # Filtro por TIPO DE PRENDA
    if "TIPO DE PRENDA" in df.columns:
        tipos_prenda = sorted(df_filtrado["TIPO DE PRENDA"].unique())
        tipos_seleccionados = st.sidebar.multiselect(
            "Tipo de Prenda:",
            options=tipos_prenda,
            default=tipos_prenda
        )
        if tipos_seleccionados:
            df_filtrado = df_filtrado[df_filtrado["TIPO DE PRENDA"].isin(tipos_seleccionados)]
    
    # Filtro por DISEÑO
    if "DISEÑO" in df.columns:
        diseños = sorted(df_filtrado["DISEÑO"].unique())
        diseños_seleccionados = st.sidebar.multiselect(
            "Diseños:",
            options=diseños,
            default=diseños
        )
        if diseños_seleccionados:
            df_filtrado = df_filtrado[df_filtrado["DISEÑO"].isin(diseños_seleccionados)]
    
    # Filtro por COLORES
    if "COLORES" in df.columns:
        colores = sorted(df_filtrado["COLORES"].unique())
        colores_seleccionados = st.sidebar.multiselect(
            "Colores:",
            options=colores,
            default=colores
        )
        if colores_seleccionados:
            df_filtrado = df_filtrado[df_filtrado["COLORES"].isin(colores_seleccionados)]
    
    # Filtro por CLAVE
    if "CLAVE" in df.columns:
        claves = sorted(df_filtrado["CLAVE"].unique())
        claves_seleccionadas = st.sidebar.multiselect(
            "Claves:",
            options=claves,
            default=claves
        )
        if claves_seleccionadas:
            df_filtrado = df_filtrado[df_filtrado["CLAVE"].isin(claves_seleccionadas)]
    
    # Filtro por CABEZAS
    if "CABEZAS" in df.columns:
        cabezas_disponibles = sorted(df["CABEZAS"].unique())
        cabezas_seleccionadas = st.sidebar.multiselect(
            "Número de Cabezas:",
            options=cabezas_disponibles,
            default=cabezas_disponibles
        )
        if cabezas_seleccionadas:
            df_filtrado = df_filtrado[df_filtrado["CABEZAS"].isin(cabezas_seleccionadas)]
    
    st.sidebar.info(f"📊 Registros filtrados: {len(df_filtrado)}")
    
    return df_filtrado

# ==================== FUNCIONES DE GRÁFICOS ====================

def mostrar_graficos_interactivos(df, df_calculado):
    """Mostrar gráficos interactivos con Plotly"""
    
    if df.empty:
        st.warning("No hay datos para mostrar gráficos")
        return
    
    st.subheader("📊 Gráficos Interactivos")
    
    # Gráfico 1: Puntadas por operador
    if df_calculado is not None and not df_calculado.empty and "TOTAL_PUNTADAS" in df_calculado.columns:
        st.write("**🏆 Puntadas Calculadas por Operador**")
        puntadas_por_operador = df_calculado.groupby("OPERADOR")["TOTAL_PUNTADAS"].sum().sort_values(ascending=False).reset_index()
        
        fig1 = px.bar(
            puntadas_por_operador,
            x="OPERADOR",
            y="TOTAL_PUNTADAS",
            title="Total de Puntadas Calculadas por Operador",
            color="TOTAL_PUNTADAS",
            text="TOTAL_PUNTADAS"
        )
        fig1.update_traces(texttemplate='%{text:,.0f}', textposition='outside')
        fig1.update_layout(xaxis_tickangle=-45)
        st.plotly_chart(fig1, use_container_width=True)
    
    # Gráfico 2: Evolución temporal
    if "Marca temporal" in df.columns:
        st.write("**📈 Evolución Temporal de Pedidos**")
        df_temporal = df.copy()
        df_temporal['Fecha'] = df_temporal['Marca temporal'].dt.date
        
        tendencias = df_temporal.groupby('Fecha').agg({
            '#DE PEDIDO': 'count',
            'CANTIDAD': 'sum' if 'CANTIDAD' in df.columns else None,
            'PUNTADAS': 'sum' if 'PUNTADAS' in df.columns else None
        }).reset_index()
        
        if len(tendencias) > 1:
            fig2 = px.line(
                tendencias,
                x="Fecha",
                y="#DE PEDIDO",
                title="Evolución de Pedidos por Día",
                markers=True
            )
            st.plotly_chart(fig2, use_container_width=True)
    
    # Gráfico 3: Distribución por tipo de prenda
    if "TIPO DE PRENDA" in df.columns:
        st.write("**👕 Distribución por Tipo de Prenda**")
        tipos_prenda = df["TIPO DE PRENDA"].value_counts().reset_index()
        tipos_prenda.columns = ['Tipo de Prenda', 'Cantidad']
        
        fig3 = px.pie(
            tipos_prenda,
            values='Cantidad',
            names='Tipo de Prenda',
            title="Distribución por Tipo de Prenda"
        )
        st.plotly_chart(fig3, use_container_width=True)
    
    # Gráfico 4: Análisis de cabezas
    if "CABEZAS" in df.columns:
        st.write("**🔧 Análisis de Cabezas por Operador**")
        cabezas_por_operador = df.groupby("OPERADOR")["CABEZAS"].agg(['mean', 'min', 'max']).reset_index()
        cabezas_por_operador.columns = ['Operador', 'Promedio', 'Mínimo', 'Máximo']
        
        fig4 = px.bar(
            cabezas_por_operador,
            x="Operador",
            y="Promedio",
            title="Promedio de Cabezas por Operador",
            color="Promedio",
            text="Promedio"
        )
        fig4.update_traces(texttemplate='%{text:.1f}', textposition='outside')
        fig4.update_layout(xaxis_tickangle=-45)
        st.plotly_chart(fig4, use_container_width=True)
    
    # Gráfico 5: Top diseños
    if "DISEÑO" in df.columns:
        st.write("**🎨 Top 10 Diseños Más Producidos**")
        top_diseños = df["DISEÑO"].value_counts().head(10).reset_index()
        top_diseños.columns = ['Diseño', 'Cantidad']
        
        fig5 = px.bar(
            top_diseños,
            x="Cantidad",
            y="Diseño",
            orientation='h',
            title="Top 10 Diseños Más Producidos",
            color="Cantidad",
            text="Cantidad"
        )
        fig5.update_traces(texttemplate='%{text}', textposition='outside')
        st.plotly_chart(fig5, use_container_width=True)

# ==================== FUNCIONES DE EXPORTACIÓN ====================

def exportar_datos(df, df_calculado, formato='csv'):
    """Exportar datos a CSV o Excel"""
    
    if formato == 'csv':
        # Exportar datos originales
        csv_original = df.to_csv(index=False)
        st.download_button(
            label="📥 Descargar Datos Originales (CSV)",
            data=csv_original,
            file_name=f"datos_originales_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv"
        )
        
        # Exportar cálculos
        if df_calculado is not None and not df_calculado.empty:
            csv_calculado = df_calculado.to_csv(index=False)
            st.download_button(
                label="📥 Descargar Cálculos (CSV)",
                data=csv_calculado,
                file_name=f"calculos_puntadas_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )
    
    elif formato == 'excel':
        # Crear archivo Excel con múltiples hojas
        output = io.BytesIO()
        
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Datos_Originales', index=False)
            if df_calculado is not None and not df_calculado.empty:
                df_calculado.to_excel(writer, sheet_name='Calculos_Puntadas', index=False)
        
        output.seek(0)
        
        st.download_button(
            label="📥 Descargar Excel Completo",
            data=output.getvalue(),
            file_name=f"dashboard_produccion_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

# ==================== FUNCIONES DE ANÁLISIS ====================

def mostrar_metricas_principales(df, df_calculado):
    """Mostrar métricas principales"""
    
    if df.empty:
        st.warning("No hay datos para mostrar métricas")
        return
    
    st.subheader("📈 Métricas Principales")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_pedidos = len(df)
        st.metric("Total de Pedidos", f"{total_pedidos:,}")
    
    with col2:
        if "CANTIDAD" in df.columns:
            total_unidades = df["CANTIDAD"].sum()
            st.metric("Total Unidades", f"{total_unidades:,}")
        else:
            st.metric("Operadores Activos", df["OPERADOR"].nunique())
    
    with col3:
        if "OPERADOR" in df.columns:
            operadores_activos = df["OPERADOR"].nunique()
            st.metric("Operadores Activos", operadores_activos)
        else:
            st.metric("Diseños Únicos", df["DISEÑO"].nunique())
    
    with col4:
        if df_calculado is not None and not df_calculado.empty and "TOTAL_PUNTADAS" in df_calculado.columns:
            total_puntadas = df_calculado["TOTAL_PUNTADAS"].sum()
            st.metric("Total Puntadas Calculadas", f"{total_puntadas:,.0f}")
        elif "PUNTADAS" in df.columns:
            total_puntadas = df["PUNTADAS"].sum()
            st.metric("Total Puntadas Base", f"{total_puntadas:,.0f}")
        else:
            st.metric("Pedidos Únicos", df["#DE PEDIDO"].nunique())

def mostrar_analisis_detallado(df, df_calculado):
    """Mostrar análisis detallado"""
    
    if df.empty:
        return
    
    st.subheader("📊 Análisis Detallado")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Análisis por operador
        if "OPERADOR" in df.columns:
            st.write("**👤 Desempeño por Operador**")
            metricas_operador = df.groupby("OPERADOR").agg({
                '#DE PEDIDO': 'count',
                'CANTIDAD': 'sum' if 'CANTIDAD' in df.columns else None,
                'PUNTADAS': 'sum' if 'PUNTADAS' in df.columns else None
            }).reset_index()
            
            if 'CANTIDAD' in df.columns and 'PUNTADAS' in df.columns:
                metricas_operador.columns = ['Operador', 'Total Pedidos', 'Total Unidades', 'Total Puntadas']
            elif 'CANTIDAD' in df.columns:
                metricas_operador.columns = ['Operador', 'Total Pedidos', 'Total Unidades']
            elif 'PUNTADAS' in df.columns:
                metricas_operador.columns = ['Operador', 'Total Pedidos', 'Total Puntadas']
            else:
                metricas_operador.columns = ['Operador', 'Total Pedidos']
            
            st.dataframe(metricas_operador, use_container_width=True)
    
    with col2:
        # Análisis de cabezas
        if "CABEZAS" in df.columns:
            st.write("**🔧 Análisis de Cabezas**")
            cabezas_por_operador = df.groupby("OPERADOR")["CABEZAS"].agg(['mean', 'min', 'max', 'count']).reset_index()
            cabezas_por_operador.columns = ['Operador', 'Promedio', 'Mínimo', 'Máximo', 'Registros']
            st.dataframe(cabezas_por_operador, use_container_width=True)

# ==================== FUNCIONES DE CARGA ====================

@st.cache_data(ttl=300)  # Cache de 5 minutos
def cargar_datos_desde_sheets():
    """Cargar datos desde Google Sheets con cache"""
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        
        service_account_info = {
            "type": st.secrets["gservice_account"]["type"],
            "project_id": st.secrets["gservice_account"]["project_id"],
            "private_key_id": st.secrets["gservice_account"]["private_key_id"],
            "private_key": st.secrets["gservice_account"]["private_key"],
            "client_email": st.secrets["gservice_account"]["client_email"],
            "client_id": st.secrets["gservice_account"]["client_id"],
            "auth_uri": st.secrets["gservice_account"]["auth_uri"],
            "token_uri": st.secrets["gservice_account"]["token_uri"]
        }
        
        creds = ServiceAccountCredentials.from_json_keyfile_dict(service_account_info, scope)
        gc = gspread.authorize(creds)
        
        sheet_id = st.secrets["gsheets"]["produccion_sheet_id"]
        worksheet = gc.open_by_key(sheet_id).worksheet("reporte_de_trabajo")
        data = worksheet.get_all_values()
        
        df_raw = pd.DataFrame(data[1:], columns=data[0])
        df = limpiar_dataframe(df_raw)
        
        # Calcular puntadas automáticamente
        df_calculado = calcular_puntadas_automaticamente(df)
        
        # Guardar cálculos si hay datos nuevos
        if not df_calculado.empty:
            guardar_calculos_en_sheets(df_calculado)
        
        return df, df_calculado
        
    except Exception as e:
        st.error(f"❌ Error cargando datos: {str(e)}")
        return pd.DataFrame(), pd.DataFrame()

# ==================== FUNCIÓN PRINCIPAL ====================

def mostrar_dashboard_produccion():
    """Función principal del dashboard mejorado"""
    
    st.title("🏭 Dashboard de Producción Mejorado")
    st.markdown("---")
    
    # Botón de actualización
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("🔄 Actualizar Datos", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
    
    # Cargar datos
    df, df_calculado = cargar_datos_desde_sheets()
    
    if df.empty:
        st.error("❌ No se pudieron cargar los datos")
        return
    
    # Mostrar resumen de datos
    st.success(f"✅ Datos cargados: {len(df)} registros")
    if df_calculado is not None and not df_calculado.empty:
        st.success(f"✅ Cálculos generados: {len(df_calculado)} registros")
    
    # Aplicar filtros
    df_filtrado = aplicar_filtros_avanzados(df)
    
    # Tabs principales
    tab1, tab2, tab3, tab4 = st.tabs([
        "📊 Dashboard Principal", 
        "📈 Gráficos Interactivos", 
        "📋 Datos Detallados",
        "📥 Exportar Datos"
    ])
    
    with tab1:
        mostrar_metricas_principales(df_filtrado, df_calculado)
        mostrar_analisis_detallado(df_filtrado, df_calculado)
    
    with tab2:
        mostrar_graficos_interactivos(df_filtrado, df_calculado)
    
    with tab3:
        st.subheader("📋 Datos Filtrados")
        st.dataframe(df_filtrado, use_container_width=True, height=400)
        
        if df_calculado is not None and not df_calculado.empty:
            st.subheader("🧵 Cálculos de Puntadas")
            st.dataframe(df_calculado, use_container_width=True, height=400)
    
    with tab4:
        st.subheader("📥 Exportar Datos")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**Exportar como CSV:**")
            exportar_datos(df_filtrado, df_calculado, formato='csv')
        
        with col2:
            st.write("**Exportar como Excel:**")
            exportar_datos(df_filtrado, df_calculado, formato='excel')
    
    # Footer
    st.sidebar.markdown("---")
    st.sidebar.write(f"🕐 Última actualización: {datetime.now().strftime('%H:%M:%S')}")
    st.sidebar.write(f"📊 Total registros: {len(df)}")
    if df_calculado is not None and not df_calculado.empty:
        st.sidebar.write(f"🧵 Total cálculos: {len(df_calculado)}")

def main():
    """Función principal"""
    mostrar_dashboard_produccion()

if __name__ == "__main__":
    main()