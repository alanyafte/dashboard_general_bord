import gspread
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import streamlit as st
from oauth2client.service_account import ServiceAccountCredentials

def mostrar_dashboard_oee():
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
        
        # ✅ CÁLCULOS OEE
        df_raw["tiempo_operativo_min"] = (
            df_raw["tiempo_planificado_min"]
            - df_raw["tiempo_paro_planeado_min"]
            - df_raw["tiempo_paro_no_planeado_min"]
        )
        
        df_raw["availability"] = df_raw["tiempo_operativo_min"] / df_raw["tiempo_planificado_min"]
        
        df_raw["performance"] = (
            (df_raw["cantidad_producida"] * df_raw["tiempo_ciclo_ideal_unit_seg"])
            / (df_raw["tiempo_operativo_min"] * 60)
        )
        
        df_raw["quality"] = df_raw["unidades_buenas"] / df_raw["cantidad_producida"]
        df_raw["OEE"] = df_raw["availability"] * df_raw["performance"] * df_raw["quality"]
        
        # ✅ MOSTRAR RESULTADOS
        st.header("🏭 Dashboard OEE")
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("OEE Promedio", f"{df_raw['OEE'].mean():.2%}")
        with col2:
            st.metric("Disponibilidad", f"{df_raw['availability'].mean():.2%}")
        with col3:
            st.metric("Rendimiento", f"{df_raw['performance'].mean():.2%}")
        with col4:
            st.metric("Calidad", f"{df_raw['quality'].mean():.2%}")
            
        st.success("Dashboard OEE cargado correctamente ✅")
        
    except Exception as e:
        st.error(f"Error en OEE: {e}")
