import streamlit as st
import gspread
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns
from datetime import datetime
from oauth2client.service_account import ServiceAccountCredentials

def mostrar_dashboard_satisfaccion():
    # --- CONFIGURACIÓN STREAMLIT ---
    st.header("😊 Dashboard de Satisfacción al Cliente")
    st.caption("Datos actualizados desde Google Sheets - Costumatic & Bordamatic")
    
    try:
        # ✅ AUTENTICACIÓN
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
    
        # Aquí necesitarás el Sheet ID de tus formularios de satisfacción
        sheet_id = st.secrets["gsheets"]["satisfaccion_cliente_sheet_id"]
        sh = gc.open_by_key(sheet_id)
        
        # Leer las dos pestañas de formularios
        costumatic_df = pd.DataFrame(sh.worksheet("respuesta_cliente_costumatic").get_all_records())
        bordamatic_df = pd.DataFrame(sh.worksheet("respuesta_cliente_bordamatic").get_all_records())
        
        st.success(f"✅ Datos cargados correctamente. Costumatic: {len(costumatic_df)} registros | Bordamatic: {len(bordamatic_df)} registros")
        
        # --- PROCESAMIENTO DE DATOS ---
        # Agregar identificador de marca
        costumatic_df['Marca'] = 'Costumatic'
        bordamatic_df['Marca'] = 'Bordamatic'
        
        # 🔴 RENOMBRADO DIFERENCIADO POR MARCA
        costumatic_df = costumatic_df.rename(columns={
            '¿Cómo calificarías nuestra atención al cliente?': 'Atencion_Cliente',
            '¿Qué tan satisfecho está con los productos y servicios que ofrece Costumatic?': 'Satisfaccion_General',
            '¿Nos recomendarías?': 'Recomendacion',
            '¿Tienes algún comentario o sugerencia?': 'Comentarios'
        })
        
        bordamatic_df = bordamatic_df.rename(columns={
            '¿Cómo calificarías nuestra atención al cliente?': 'Atencion_Cliente',
            '¿Cómo calificarías el tiempo de entrega?': 'Tiempo_Entrega',
            '¿La calidad del trabajo fue la esperada?': 'Calidad_Trabajo',
            '¿Nos recomendarías?': 'Recomendacion',
            '¿Tienes algún comentario o sugerencia?': 'Comentarios'
        })
        
        # Unificar dataframes
        df_unificado = pd.concat([costumatic_df, bordamatic_df], ignore_index=True)
        
        # --- LIMPIEZA Y CONVERSIÓN DE DATOS ---
        # Convertir marca temporal a datetime
        df_unificado['Marca temporal'] = pd.to_datetime(df_unificado['Marca temporal'])
        df_unificado['Mes'] = df_unificado['Marca temporal'].dt.to_period('M')
        
        # 🔴 LIMPIEZA DE COLUMNAS NUMÉRICAS
        columnas_numericas = ['Atencion_Cliente', 'Tiempo_Entrega', 'Satisfaccion_General']
        for col in columnas_numericas:
            if col in df_unificado.columns:
                df_unificado[col] = pd.to_numeric(
                    df_unificado[col].astype(str).str.strip(), 
                    errors='coerce'
                )
        
        # 🔴 FUNCIÓN PARA LIMPIAR VALORES SÍ/NO
        def limpiar_si_no(valor):
            if pd.isna(valor):
                return valor
            valor_str = str(valor).strip().lower()
            if valor_str in ['Sí', 'si', 's', 'yes', 'y']:
                return 'sí'
            elif valor_str in ['No', 'n']:
                return 'no'
            return valor_str
        
        # Aplicar limpieza a columnas Sí/No
        if 'Calidad_Trabajo' in df_unificado.columns:
            df_unificado['Calidad_Trabajo'] = df_unificado['Calidad_Trabajo'].apply(limpiar_si_no)
        
        df_unificado['Recomendacion'] = df_unificado['Recomendacion'].apply(limpiar_si_no)
        
        # Limpiar comentarios
        df_unificado['Comentarios'] = df_unificado['Comentarios'].astype(str).str.strip()
        df_unificado['Comentarios'] = df_unificado['Comentarios'].replace({
            'nan': '', 'None': '', '': ''
        })
        
        # --- SECCIÓN DE KPIs PRINCIPALES ---
        st.subheader("📊 KPIs Principales")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            csat_general = df_unificado['Atencion_Cliente'].mean()
            st.metric("CSAT General", f"{csat_general:.1f}/5", delta="0.2" if not pd.isna(csat_general) else "N/A")
        
        with col2:
            tasa_recomendacion = (df_unificado['Recomendacion'] == 'sí').mean() * 100
            st.metric("Tasa Recomendación", f"{tasa_recomendacion:.1f}%", delta="3%")
        
        with col3:
            total_respuestas = len(df_unificado)
            st.metric("Total Respuestas", total_respuestas)
        
        with col4:
            tasa_respuesta_comentarios = (df_unificado['Comentarios'].notna() & 
                                        (df_unificado['Comentarios'] != '')).mean() * 100
            st.metric("Feedback con Comentarios", f"{tasa_respuesta_comentarios:.1f}%")
        
        # --- FILTROS ---
        st.subheader("🔍 Filtros")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            marcas_seleccionadas = st.multiselect(
                "Marca:",
                options=df_unificado['Marca'].unique(),
                default=df_unificado['Marca'].unique()
            )
        
        with col2:
            fecha_min = df_unificado['Marca temporal'].min().date()
            fecha_max = df_unificado['Marca temporal'].max().date()
            rango_fechas = st.date_input(
                "Rango de fechas:",
                value=(fecha_min, fecha_max),
                min_value=fecha_min,
                max_value=fecha_max
            )
        
        with col3:
            if len(rango_fechas) == 2:
                fecha_inicio, fecha_fin = rango_fechas
                df_filtrado = df_unificado[
                    (df_unificado['Marca'].isin(marcas_seleccionadas)) &
                    (df_unificado['Marca temporal'].dt.date >= fecha_inicio) &
                    (df_unificado['Marca temporal'].dt.date <= fecha_fin)
                ]
            else:
                df_filtrado = df_unificado[df_unificado['Marca'].isin(marcas_seleccionadas)]
        
        # --- VISUALIZACIONES ---
        st.subheader("📈 Análisis de Satisfacción")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # CSAT por Marca
            fig, ax = plt.subplots(figsize=(10, 6))
            csat_por_marca = df_filtrado.groupby('Marca')['Atencion_Cliente'].mean()
            colors = ['#FF6B6B', '#4ECDC4']
            
            if not csat_por_marca.empty:
                bars = ax.bar(csat_por_marca.index, csat_por_marca.values, color=colors, alpha=0.8)
                
                # Añadir valores en las barras
                for bar in bars:
                    height = bar.get_height()
                    ax.text(bar.get_x() + bar.get_width()/2., height + 0.05,
                           f'{height:.1f}', ha='center', va='bottom')
                
                ax.set_ylabel('CSAT (1-5)')
                ax.set_title('CSAT por Marca')
                ax.set_ylim(0, 5.5)
                st.pyplot(fig)
            else:
                st.info("No hay datos suficientes para mostrar CSAT por marca")
        
        with col2:
            # Tasa de Recomendación por Marca
            fig, ax = plt.subplots(figsize=(10, 6))
            recomendacion_por_marca = df_filtrado.groupby('Marca')['Recomendacion'].apply(
                lambda x: (x == 'sí').mean() * 100
            )
            
            if not recomendacion_por_marca.empty:
                bars = ax.bar(recomendacion_por_marca.index, recomendacion_por_marca.values, 
                             color=colors, alpha=0.8)
                
                for bar in bars:
                    height = bar.get_height()
                    ax.text(bar.get_x() + bar.get_width()/2., height + 1,
                           f'{height:.1f}%', ha='center', va='bottom')
                
                ax.set_ylabel('Tasa de Recomendación (%)')
                ax.set_title('Recomendación por Marca')
                ax.set_ylim(0, 100)
                st.pyplot(fig)
            else:
                st.info("No hay datos suficientes para mostrar recomendación por marca")
        
        # --- ANÁLISIS DETALLADO POR MARCA ---
        st.subheader("🔬 Análisis Detallado por Marca")
        
        marca_seleccionada = st.selectbox("Selecciona una marca para análisis detallado:", 
                                         df_filtrado['Marca'].unique())
        
        df_marca = df_filtrado[df_filtrado['Marca'] == marca_seleccionada]
        
        # 🔴 ANÁLISIS DIFERENCIADO POR MARCA
        if marca_seleccionada == 'Costumatic':
            # MÉTRICAS ESPECÍFICAS DE COSTUMATIC
            col1, col2 = st.columns(2)
            
            with col1:
                satisfaccion_productos = df_marca['Satisfaccion_General'].mean()
                st.metric("Satisfacción con Productos", f"{satisfaccion_productos:.1f}/5" if not pd.isna(satisfaccion_productos) else "N/A")
            
            with col2:
                if 'Satisfaccion_General' in df_marca.columns:
                    distribucion_satisfaccion = df_marca['Satisfaccion_General'].value_counts().sort_index()
                    fig, ax = plt.subplots(figsize=(8, 6))
                    ax.pie(distribucion_satisfaccion.values, labels=distribucion_satisfaccion.index, 
                          autopct='%1.1f%%', startangle=90)
                    ax.set_title('Distribución Satisfacción Productos - Costumatic')
                    st.pyplot(fig)

        else:  # Bordamatic
            # MÉTRICAS ESPECÍFICAS DE BORDAMATIC
            col1, col2, col3 = st.columns(3)
            
            with col1:
                tiempo_entrega = df_marca['Tiempo_Entrega'].mean()
                st.metric("Tiempo de Entrega", f"{tiempo_entrega:.1f}/5" if not pd.isna(tiempo_entrega) else "N/A")
            
            with col2:
                calidad_trabajo = (df_marca['Calidad_Trabajo'] == 'sí').mean() * 100
                st.metric("Calidad Satisfactoria", f"{calidad_trabajo:.1f}%")
            
            with col3:
                # Triple métrica para Bordamatic
                fig, ax = plt.subplots(figsize=(10, 6))
                metricas = ['Atencion_Cliente', 'Tiempo_Entrega']
                promedios = [df_marca[metrica].mean() for metrica in metricas]
                
                # Agregar calidad como porcentaje (escalado a 5)
                calidad_escalada = (df_marca['Calidad_Trabajo'] == 'sí').mean() * 5
                promedios.append(calidad_escalada)
                
                bars = ax.bar(['Atención', 'Tiempo Entrega', 'Calidad'], promedios, 
                             color=['#FF6B6B', '#4ECDC4', '#45B7D1'], alpha=0.8)
                
                for bar in bars:
                    height = bar.get_height()
                    ax.text(bar.get_x() + bar.get_width()/2., height + 0.05,
                           f'{height:.1f}', ha='center', va='bottom')
                
                ax.set_ylabel('Calificación (1-5)')
                ax.set_title('Métricas de Servicio - Bordamatic')
                ax.set_ylim(0, 5.5)
                st.pyplot(fig)
        
        # --- COMENTARIOS Y SUGERENCIAS ---
        st.subheader("💬 Comentarios y Sugerencias")
        
        comentarios_df = df_filtrado[
            (df_filtrado['Comentarios'].notna()) & 
            (df_filtrado['Comentarios'] != '') &
            (df_filtrado['Comentarios'] != 'nan')
        ]
        
        if not comentarios_df.empty:
            for idx, row in comentarios_df.iterrows():
                with st.expander(f"Comentario de {row['Marca']} - {row['Marca temporal'].strftime('%d/%m/%Y')}"):
                    st.write(f"**Atención:** {row['Atencion_Cliente']}/5")
                    
                    # 🔴 MOSTRAR MÉTRICAS ESPECÍFICAS SEGÚN MARCA
                    if row['Marca'] == 'Costumatic' and 'Satisfaccion_General' in row:
                        st.write(f"**Satisfacción Productos:** {row['Satisfaccion_General']}/5")
                    elif row['Marca'] == 'Bordamatic':
                        st.write(f"**Tiempo Entrega:** {row.get('Tiempo_Entrega', 'N/A')}/5")
                        st.write(f"**Calidad Satisfactoria:** {row.get('Calidad_Trabajo', 'N/A')}")
                    
                    st.write(f"**Recomendaría:** {row['Recomendacion']}")
                    st.write(f"**Comentario:** {row['Comentarios']}")
        else:
            st.info("No hay comentarios disponibles para el período seleccionado.")
        
        # --- TENDENCIAS TEMPORALES ---
        st.subheader("📅 Evolución Temporal")
        
        if len(df_filtrado) > 1:
            tendencias = df_filtrado.groupby(['Mes', 'Marca'])['Atencion_Cliente'].mean().unstack()
            
            if not tendencias.empty:
                fig, ax = plt.subplots(figsize=(12, 6))
                for marca in tendencias.columns:
                    ax.plot(tendencias.index.astype(str), tendencias[marca], 
                           marker='o', label=marca, linewidth=2)
                
                ax.set_xlabel('Mes')
                ax.set_ylabel('CSAT Promedio')
                ax.set_title('Evolución del CSAT por Mes')
                ax.legend()
                ax.grid(True, alpha=0.3)
                plt.xticks(rotation=45)
                st.pyplot(fig)
            else:
                st.info("No hay datos suficientes para mostrar tendencias temporales")
        
    except Exception as e:
        st.error(f"❌ Error al cargar los datos: {str(e)}")
        st.info("""
        Para configurar este dashboard necesitas:
        1. Agregar el Sheet ID de tus formularios a streamlit secrets
        2. Asegurarte que las hojas se llamen exactamente: 
           - 'respuesta_cliente_costumatic'
           - 'respuesta_cliente_bordamatic'
        3. Verificar que el servicio account tenga acceso al Sheet
        """)
