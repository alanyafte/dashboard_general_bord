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
        
        # ✅ OEE POR MÁQUINA
        oee_por_maquina = df_raw.groupby("maquina")[["availability","performance","quality","OEE"]].mean()
        
        # ✅ OEE POR PEDIDO
        oee_por_pedido = df_raw.groupby("codigo_pedido")[["availability","performance","quality","OEE"]].mean()
        
       # ✅ MOSTRAR RESULTADOS PRINCIPALES
        st.header("🏭 Dashboard OEE")
        
      # ✅ RESUMEN ESTADÍSTICO AL INICIO
        st.subheader("📈 Resumen Estadístico")
        
        # Crear columnas para el resumen
        col_res1, col_res2, col_res3 = st.columns(3)
        
        with col_res1:
            # Mejor OEE
            st.metric("Mejor OEE", 
                     f"{oee_por_maquina['OEE'].idxmax()}: {oee_por_maquina['OEE'].max():.2%}")
        
        with col_res2:
            # Peor OEE
            st.metric("Peor OEE", 
                     f"{oee_por_maquina['OEE'].idxmin()}: {oee_por_maquina['OEE'].min():.2%}")
        
        with col_res3:
            # Total de registros
            st.metric("Total Registros", len(df_raw))
        
        # Información adicional de máquinas disponibles
        st.info(f"🔧 **Máquinas en sistema:** {', '.join(oee_por_maquina.index.tolist())}")
        
        # ✅ TABLA OEE POR MÁQUINA
        st.subheader("📊 OEE por Máquina")
        st.dataframe(oee_por_maquina.style.format("{:.2%}"))
        
        # ✅ TABLA OEE POR PEDIDO
        st.subheader("📋 OEE por Pedido")
        st.dataframe(oee_por_pedido.style.format("{:.2%}"))
        
        # ✅ GRÁFICO OEE POR MÁQUINA
        st.subheader("📈 OEE por Máquina")
        fig1, ax1 = plt.subplots(figsize=(10, 6))
        oee_por_maquina["OEE"].plot(kind="bar", ax=ax1, color='skyblue')
        ax1.set_title("OEE por Máquina")
        ax1.set_ylabel("OEE")
        ax1.set_xlabel("Máquina")
        ax1.tick_params(axis='x', rotation=45)
        plt.tight_layout()
        st.pyplot(fig1)
        
        # ✅ GRÁFICO OEE POR PEDIDO
        st.subheader("📦 OEE por Pedido")
        fig2, ax2 = plt.subplots(figsize=(12, 6))
        oee_por_pedido["OEE"].plot(kind="bar", ax=ax2, color='lightgreen')
        ax2.set_title("OEE por Pedido")
        ax2.set_ylabel("OEE")
        ax2.set_xlabel("Pedido")
        ax2.tick_params(axis='x', rotation=45)
        plt.tight_layout()
        st.pyplot(fig2)
        
        # ✅ EVOLUCIÓN TEMPORAL DEL OEE
        st.subheader("📅 Evolución del OEE en el Tiempo")
        
        # Verificar y convertir fecha
        if 'fecha_inic' in df_raw.columns:
            df_raw["fecha_inic"] = pd.to_datetime(df_raw["fecha_inic"], errors="coerce", dayfirst=True)
            oee_tiempo = df_raw.groupby("fecha_inic")["OEE"].mean().sort_index()
            
            fig3, ax3 = plt.subplots(figsize=(12, 6))
            oee_tiempo.plot(marker="o", ax=ax3, color='red', linewidth=2, markersize=6)
            ax3.set_title("Evolución del OEE en el tiempo")
            ax3.set_ylabel("OEE")
            ax3.set_xlabel("Fecha")
            ax3.grid(True, alpha=0.3)
            plt.tight_layout()
            st.pyplot(fig3)
        else:
            st.warning("No se encontró la columna 'fecha_inic' para la evolución temporal")
        
        # ✅ RADAR CHART - COMPONENTES POR MÁQUINA
        st.subheader("🎯 Radar Chart - Componentes OEE por Máquina")
        
        if len(oee_por_maquina) > 0:
            # Preparar datos para radar chart
            oee_componentes = df_raw.groupby("maquina")[["availability","performance","quality"]].mean()
            oee_componentes = oee_componentes * 100  # Convertir a porcentaje
            
            categorias = list(oee_componentes.columns)
            N = len(categorias)
            
            # Ángulos del radar
            angulos = np.linspace(0, 2 * np.pi, N, endpoint=False).tolist()
            angulos += angulos[:1]  # cerrar el círculo
            
            # Crear gráfico
            fig4, ax4 = plt.subplots(figsize=(10, 10), subplot_kw=dict(projection='polar'))
            
            for maquina, fila in oee_componentes.iterrows():
                valores = fila.tolist()
                valores += valores[:1]  # cerrar el gráfico
                ax4.plot(angulos, valores, marker="o", label=maquina, linewidth=2)
                ax4.fill(angulos, valores, alpha=0.1)
            
            # Configuración del gráfico
            ax4.set_xticks(angulos[:-1])
            ax4.set_xticklabels(categorias)
            ax4.set_yticks([20, 40, 60, 80, 100])
            ax4.set_yticklabels(["20%", "40%", "60%", "80%", "100%"])
            ax4.set_ylim(0, 100)
            ax4.set_title("Componentes OEE por Máquina", size=14, pad=20)
            ax4.legend(loc="upper right", bbox_to_anchor=(1.3, 1.1))
            
            plt.tight_layout()
            st.pyplot(fig4)
        
        # ✅ GRÁFICO DE COMPONENTES OEE (Barras agrupadas)
        st.subheader("🔧 Componentes OEE por Máquina")
        
        fig5, ax5 = plt.subplots(figsize=(12, 6))
        
        # Preparar datos
        maquinas = oee_componentes.index
        x = np.arange(len(maquinas))
        width = 0.25
        
        # Crear barras para cada componente
        ax5.bar(x - width, oee_componentes['availability'], width, label='Disponibilidad', color='blue', alpha=0.7)
        ax5.bar(x, oee_componentes['performance'], width, label='Rendimiento', color='green', alpha=0.7)
        ax5.bar(x + width, oee_componentes['quality'], width, label='Calidad', color='orange', alpha=0.7)
        
        ax5.set_xlabel('Máquina')
        ax5.set_ylabel('Porcentaje (%)')
        ax5.set_title('Componentes OEE por Máquina')
        ax5.set_xticks(x)
        ax5.set_xticklabels(maquinas)
        ax5.legend()
        ax5.set_ylim(0, 100)
        ax5.grid(axis='y', alpha=0.3)
        
        plt.xticks(rotation=45)
        plt.tight_layout()
        st.pyplot(fig5)
        
        
        # ✅ DATOS CRUDOS (opcional)
        with st.expander("📋 Ver Datos Crudos"):
            st.dataframe(df_raw)
            
            # Botón de descarga
            csv = df_raw.to_csv(index=False)
            st.download_button(
                label="📥 Descargar Datos CSV",
                data=csv,
                file_name="datos_oee.csv",
                mime="text/csv"
            )
        
        st.success("Dashboard OEE cargado correctamente ✅")
        
    except Exception as e:
        st.error(f"Error en OEE: {e}")
        st.info("Verifica que las columnas en tu Google Sheets coincidan con los nombres esperados")

# Ejecutar la función
mostrar_dashboard_oee()
