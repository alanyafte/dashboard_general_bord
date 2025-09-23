import gspread
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import streamlit as st
from oauth2client.service_account import ServiceAccountCredentials

def mostrar_dashboard_oee():
    try:
        # ✅ AUTENTICACIÓN (tu código actual)
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
        
        # ✅ CARGAR DATOS
        sheet_id = st.secrets["gsheets"]["oee_sheet_id"]
        worksheet = gc.open_by_key(sheet_id).worksheet("Produccion")
        data = worksheet.get_all_values()
        df_raw = pd.DataFrame(data[1:], columns=data[0])
        
        # ✅ CONVERTIR COLUMNAS NUMÉRICAS
        columnas_numericas = [
            "cantidad_producida", "unidades_defectuosas", "unidades_buenas",
            "tiempo_planificado_min", "tiempo_paro_planeado_min",
            "tiempo_paro_no_planeado_min", "run_time_min", "tiempo_ciclo_ideal_unit_seg"
        ]
        
        for col in columnas_numericas:
            if col in df_raw.columns:
                df_raw[col] = pd.to_numeric(df_raw[col], errors="coerce")
        
        # ✅ CÁLCULOS OEE CORREGIDOS
        # 1. DISPONIBILIDAD (solo paros NO planeados)
        df_raw["tiempo_operacion"] = df_raw["tiempo_planificado_min"] - df_raw["tiempo_paro_no_planeado_min"]
        df_raw["availability"] = df_raw["tiempo_operacion"] / df_raw["tiempo_planificado_min"]
        
        # 2. RENDIMIENTO 
        df_raw["production_teorica"] = (df_raw["tiempo_operacion"] * 60) / df_raw["tiempo_ciclo_ideal_unit_seg"]
        df_raw["performance"] = df_raw["cantidad_producida"] / df_raw["production_teorica"]
        
        # 3. CALIDAD
        df_raw["quality"] = df_raw["unidades_buenas"] / df_raw["cantidad_producida"]
        
        # 4. OEE FINAL
        df_raw["OEE"] = df_raw["availability"] * df_raw["performance"] * df_raw["quality"]
        
        # ✅ OEE POR MÁQUINA
        st.header("🏭 Dashboard OEE por Máquina")
        
        # Verificar que existe columna de máquina
        if 'maquina' not in df_raw.columns:
            st.error("No se encuentra la columna 'maquina' en los datos")
            return
        
        # Resumen por máquina
        oee_por_maquina = df_raw.groupby('maquina').agg({
            'OEE': 'mean',
            'availability': 'mean', 
            'performance': 'mean',
            'quality': 'mean',
            'cantidad_producida': 'sum',
            'unidades_buenas': 'sum'
        }).round(4)
        
        oee_por_maquina['OEE'] = oee_por_por_maquina['OEE'] * 100  # Convertir a porcentaje
        oee_por_maquina['availability'] = oee_por_maquina['availability'] * 100
        oee_por_maquina['performance'] = oee_por_maquina['performance'] * 100
        oee_por_maquina['quality'] = oee_por_maquina['quality'] * 100
        
        # ✅ MOSTRAR KPI's GENERALES
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("OEE Promedio", f"{df_raw['OEE'].mean()*100:.1f}%")
        with col2:
            st.metric("Disponibilidad", f"{df_raw['availability'].mean()*100:.1f}%")
        with col3:
            st.metric("Rendimiento", f"{df_raw['performance'].mean()*100:.1f}%")
        with col4:
            st.metric("Calidad", f"{df_raw['quality'].mean()*100:.1f}%")
        
        # ✅ TABLA DETALLADA POR MÁQUINA
        st.subheader("📊 OEE por Máquina")
        st.dataframe(oee_por_maquina.style.format({
            'OEE': '{:.1f}%',
            'availability': '{:.1f}%', 
            'performance': '{:.1f}%',
            'quality': '{:.1f}%',
            'cantidad_producida': '{:.0f}',
            'unidades_buenas': '{:.0f}'
        }))
        
        # ✅ GRÁFICO DE BARRAS - OEE POR MÁQUINA
        st.subheader("📈 OEE por Máquina")
        fig, ax = plt.subplots(figsize=(10, 6))
        oee_por_maquina['OEE'].plot(kind='bar', color='skyblue', ax=ax)
        ax.set_ylabel('OEE (%)')
        ax.set_xlabel('Máquina')
        ax.set_title('OEE por Máquina')
        ax.set_ylim(0, 100)
        plt.xticks(rotation=45)
        st.pyplot(fig)
        
        # ✅ GRÁFICO DE COMPONENTES OEE (Disponibilidad, Rendimiento, Calidad)
        st.subheader("🔧 Componentes del OEE por Máquina")
        fig2, ax2 = plt.subplots(figsize=(12, 6))
        
        # Preparar datos para el gráfico
        componentes = oee_por_maquina[['availability', 'performance', 'quality']]
        x_pos = np.arange(len(componentes.index))
        
        ax2.bar(x_pos - 0.2, componentes['availability'], 0.2, label='Disponibilidad', color='green')
        ax2.bar(x_pos, componentes['performance'], 0.2, label='Rendimiento', color='blue')
        ax2.bar(x_pos + 0.2, componentes['quality'], 0.2, label='Calidad', color='orange')
        
        ax2.set_xlabel('Máquina')
        ax2.set_ylabel('Porcentaje (%)')
        ax2.set_title('Componentes del OEE por Máquina')
        ax2.set_xticks(x_pos)
        ax2.set_xticklabels(componentes.index)
        ax2.legend()
        ax2.set_ylim(0, 100)
        plt.xticks(rotation=45)
        st.pyplot(fig2)
        
        # ✅ GRÁFICO DE LÍNEAS - EVOLUCIÓN TEMPORAL (si hay fecha)
        if 'fecha' in df_raw.columns:
            st.subheader("📅 Evolución del OEE")
            df_raw['fecha'] = pd.to_datetime(df_raw['fecha'], errors='coerce')
            
            # OEE promedio por fecha
            oee_evolucion = df_raw.groupby('fecha')['OEE'].mean() * 100
            
            fig3, ax3 = plt.subplots(figsize=(12, 5))
            oee_evolucion.plot(kind='line', marker='o', ax=ax3, color='red')
            ax3.set_ylabel('OEE (%)')
            ax3.set_xlabel('Fecha')
            ax3.set_title('Evolución del OEE en el Tiempo')
            ax3.set_ylim(0, 100)
            ax3.grid(True, alpha=0.3)
            plt.xticks(rotation=45)
            st.pyplot(fig3)
        
        st.success("Dashboard OEE cargado correctamente ✅")
        
    except Exception as e:
        st.error(f"Error en OEE: {e}")

# Ejecutar la función
mostrar_dashboard_oee()
