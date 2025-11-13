# modulo_ia_completo.py - CON IA REAL
import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
import numpy as np
from datetime import datetime, timedelta

# =============================================================================
# CONFIGURACIÓN - VERIFICAR DEPENDENCIAS
# =============================================================================

def verificar_dependencias():
    """Verifica si las dependencias de IA están disponibles"""
    try:
        from prophet import Prophet
        st.sidebar.success("✅ Prophet disponible - IA Activada")
        return True
    except ImportError:
        st.sidebar.warning("⚠️ Prophet no disponible - Usando análisis estadístico")
        return False

# =============================================================================
# PARTE 1: ANÁLISIS DE SENTIMIENTO CON HUGGING FACE (IA REAL)
# =============================================================================

class AnalizadorIncidenciasIA:
    def __init__(self):
        self.headers = {"Authorization": f"Bearer {st.secrets.get('HF_TOKEN', '')}"}
    
    def analizar_sentimiento(self, texto_incidencia):
        """IA REAL: Análisis de sentimiento con modelo pre-entrenado"""
        try:
            API_URL = "https://api-inference.huggingface.co/models/cardiffnlp/twitter-roberta-base-sentiment-latest"
            
            response = requests.post(API_URL, headers=self.headers, json={
                "inputs": texto_incidencia,
                "options": {"wait_for_model": True}
            })
            
            if response.status_code == 200:
                resultado = response.json()
                sentimiento_principal = max(resultado[0], key=lambda x: x['score'])
                return {
                    'sentimiento': sentimiento_principal['label'],
                    'confianza': sentimiento_principal['score'],
                    'color': self._asignar_color(sentimiento_principal['label'])
                }
            return {'error': 'API no disponible'}
        except Exception as e:
            return {'error': f'Error en análisis: {str(e)}'}

# =============================================================================
# PARTE 2: PREDICCIÓN CON PROPHET (IA REAL)
# =============================================================================

def predecir_con_ia_real(df_calculado, dias_prediccion=14):
    """IA REAL: Predicción con Prophet (Facebook)"""
    try:
        from prophet import Prophet
        
        # Preparar datos para Prophet
        df_agrupado = df_calculado.groupby('FECHA').agg({
            'TOTAL_PUNTADAS': 'sum'
        }).reset_index()
        
        df_agrupado = df_agrupado.rename(columns={'FECHA': 'ds', 'TOTAL_PUNTADAS': 'y'})
        
        if len(df_agrupado) < 7:
            return None, "Se necesitan al menos 7 días de datos para IA"
        
        # Configurar y entrenar modelo de IA
        model = Prophet(
            yearly_seasonality=False,
            weekly_seasonality=True,  # Aprende patrones semanales
            daily_seasonality=False,
            changepoint_prior_scale=0.05
        )
        
        # ENTRENAR EL MODELO DE IA
        model.fit(df_agrupado)
        
        # GENERAR PREDICCIÓN
        future = model.make_future_dataframe(periods=dias_prediccion)
        forecast = model.predict(future)
        
        return forecast, "🧠 Predicción generada con IA (Prophet)"
        
    except Exception as e:
        return None, f"Error en IA: {str(e)}"

# =============================================================================
# INTERFAZ PRINCIPAL
# =============================================================================

def mostrar_ia_completa(df_produccion, df_calculado):
    """Interfaz unificada de IA"""
    
    st.header("🧠 Inteligencia Artificial para Producción")
    
    # Verificar capacidades de IA
    ia_disponible = verificar_dependencias()
    
    if not ia_disponible:
        st.warning("""
        **⚠️ Capacidades de IA limitadas**
        - Instala Prophet para predicciones inteligentes
        - Por ahora solo análisis de sentimiento disponible
        """)
    
    # Seleccionar módulo
    opcion = st.selectbox(
        "Selecciona análisis IA:",
        ["🤖 Análisis de Incidencias", "🔮 Predicciones de Producción"]
    )
    
    if opcion == "🤖 Análisis de Incidencias":
        mostrar_analisis_incidencias(df_produccion)
    else:
        mostrar_predicciones_inteligentes(df_calculado, ia_disponible)

def mostrar_predicciones_inteligentes(df_calculado, ia_disponible):
    """Predicciones que usan IA cuando está disponible"""
    
    st.header("🔮 Predicciones Inteligentes de Producción")
    
    if ia_disponible:
        st.success("✅ **IA ACTIVA** - Usando Prophet para predicciones inteligentes")
    else:
        st.warning("📊 **MODO ESTADÍSTICO** - Usando análisis avanzado (sin IA)")
    
    dias = st.slider("Días a predecir", 7, 30, 14)
    
    if st.button("🎯 Generar Predicción Inteligente"):
        with st.spinner("🧠 Ejecutando modelo de IA..." if ia_disponible else "📊 Analizando tendencias..."):
            
            if ia_disponible:
                forecast, mensaje = predecir_con_ia_real(df_calculado, dias)
            else:
                forecast, mensaje = predecir_avanzada_sin_ia(df_calculado, dias)
            
            if forecast is not None:
                mostrar_resultados_prediccion(forecast, mensaje)
            else:
                st.error(mensaje)
