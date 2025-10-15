import gspread
import pandas as pd
import matplotlib.pyplot as plt
import plotly.express as px
import numpy as np
import streamlit as st
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, timedelta, date
import pytz

# ==================== MÓDULO: NORMALIZACIÓN DE FECHAS ====================

def parsear_timestamp(timestamp_str):
    """
    Convierte timestamp de Google Forms al formato consistente.
    Entrada: "26/9/2025 11:29:23"
    Retorna: (datetime_obj, fecha_date, hora_int, turno_str)
    """
    try:
        dt = pd.to_datetime(timestamp_str, format='%d/%m/%Y %H:%M:%S')
        fecha = dt.date()
        hora = dt.hour
        
        # Determinar turno
        if 6 <= hora < 14:
            turno = "TURNO_1_6AM_2PM"
        elif 14 <= hora < 22:
            turno = "TURNO_2_2PM_10PM"
        else:
            turno = "TURNO_INVALIDO"
        
        return dt, fecha, hora, turno
    except Exception as e:
        st.warning(f"Error al parsear timestamp '{timestamp_str}': {e}")
        return None, None, None, None

# ==================== MÓDULO: PERÍODOS DE CORTE ====================

def calcular_fecha_corte(dia_corte, mes, año, forzar_dia_siguiente_si_domingo=True):
    """
    Calcula fecha de corte, manejo de domingos.
    Si forzar_dia_siguiente_si_domingo=True, si cae domingo → lunes
    """
    try:
        fecha_corte = date(año, mes, dia_corte)
        
        # Si es domingo (weekday=6), pasar al lunes
        if forzar_dia_siguiente_si_domingo and fecha_corte.weekday() == 6:
            fecha_corte += timedelta(days=1)
        
        return fecha_corte
    except:
        return None

def obtener_periodo_actual():
    """
    Retorna (fecha_inicio, fecha_fin, periodo_str, numero_periodo)
    Períodos: 10-25, 25-10 (del siguiente mes)
    Maneja excepciones de domingo.
    """
    hoy = date.today()
    dia = hoy.day
    mes = hoy.month
    año = hoy.year
    
    # Corte 25 del mes actual
    fecha_corte_25 = calcular_fecha_corte(25, mes, año)
    
    # Corte 10 del siguiente mes
    mes_siguiente = mes + 1 if mes < 12 else 1
    año_siguiente = año + 1 if mes == 12 else año
    fecha_corte_10_sig = calcular_fecha_corte(10, mes_siguiente, año_siguiente)
    
    # Determinar en qué período estamos
    if hoy <= fecha_corte_25:
        # Estamos en período 10-25
        fecha_inicio = calcular_fecha_corte(10, mes, año)
        fecha_fin = fecha_corte_25
        periodo_str = f"10-{fecha_corte_25.day} {fecha_corte_25.strftime('%b')}"
        numero_periodo = 1
    else:
        # Estamos en período 25-10
        fecha_inicio = fecha_corte_25
        fecha_fin = fecha_corte_10_sig
        periodo_str = f"{fecha_corte_25.day} {fecha_corte_25.strftime('%b')}-{fecha_corte_10_sig.day} {fecha_corte_10_sig.strftime('%b')}"
        numero_periodo = 2
    
    return fecha_inicio, fecha_fin, periodo_str, numero_periodo

def obtener_periodos_historicos(num_periodos=6):
    """
    Retorna lista de últimos N períodos para consulta histórica.
    Cada período es: (fecha_inicio, fecha_fin, periodo_str, numero_periodo)
    """
    hoy = date.today()
    periodos = []
    
    fecha_actual = hoy
    for i in range(num_periodos):
        # Calcular período que contenga fecha_actual
        dia = fecha_actual.day
        mes = fecha_actual.month
        año = fecha_actual.year
        
        fecha_corte_25 = calcular_fecha_corte(25, mes, año)
        
        if fecha_actual <= fecha_corte_25:
            fecha_inicio = calcular_fecha_corte(10, mes, año)
            fecha_fin = fecha_corte_25
            periodo_str = f"10-{fecha_corte_25.day} {fecha_corte_25.strftime('%b %Y')}"
        else:
            fecha_inicio = fecha_corte_25
            mes_siguiente = mes + 1 if mes < 12 else 1
            año_siguiente = año + 1 if mes == 12 else año
            fecha_fin = calcular_fecha_corte(10, mes_siguiente, año_siguiente)
            periodo_str = f"{fecha_corte_25.day} {fecha_corte_25.strftime('%b')}-{fecha_fin.day} {fecha_fin.strftime('%b %Y')}"
        
        periodos.append((fecha_inicio, fecha_fin, periodo_str))
        
        # Retroceder al período anterior
        fecha_actual = fecha_inicio - timedelta(days=1)
    
    return periodos

# ==================== MÓDULO: LIMPIEZA Y PROCESAMIENTO ====================

def limpiar_dataframe(df_raw):
    """Limpia y normaliza el dataframe desde Google Forms"""
    df = df_raw.copy()
    
    # Eliminar email si existe
    if "Dirección de correo electrónico" in df.columns:
        df = df.drop("Dirección de correo electrónico", axis=1)
    
    # Limpiar espacios en columnas y valores
    df.columns = df.columns.str.strip()
    for col in df.columns:
        if df[col].dtype == 'object':
            df[col] = df[col].str.strip()
    
    # ✅ NUEVA LÓGICA: Normalizar timestamps
    if "Marca temporal" in df.columns:
        df['fecha_dt'] = pd.NaT
        df['fecha'] = pd.NaT
        df['hora'] = 0
        df['turno'] = ""
        
        for idx, ts in enumerate(df["Marca temporal"]):
            dt, fecha, hora, turno = parsear_timestamp(ts)
            if dt is not None:
                df.loc[idx, 'fecha_dt'] = dt
                df.loc[idx, 'fecha'] = fecha
                df.loc[idx, 'hora'] = hora
                df.loc[idx, 'turno'] = turno
    
    # Convertir CANTIDAD, PUNTADAS, MULTIPLOS, CABEZAS a numérico
    for col in ["CANTIDAD", "PUNTADAS", "MULTIPLOS", "CABEZAS"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
            df[col] = df[col].fillna(0)
    
    return df

# ==================== MÓDULO: CÁLCULO DE PUNTADAS ====================

def calcular_puntadas_automaticamente(df):
    """
    Calcula puntadas totales incluyendo cambios de color e inicio de turno.
    ✅ CORREGIDO: Identifica inicio de turno por (operador, fecha, turno)
    """
    if df.empty or "OPERADOR" not in df.columns:
        return pd.DataFrame()
    
    # Validar que tenemos columnas necesarias
    required_cols = ['OPERADOR', 'fecha', 'turno', 'CANTIDAD', 'PUNTADAS', 'CABEZAS']
    missing = [col for col in required_cols if col not in df.columns]
    if missing:
        st.error(f"Columnas faltantes: {missing}")
        return pd.DataFrame()
    
    resultados = []
    
    # Agrupar por operador, fecha, turno
    for (operador, fecha, turno), grupo in df.groupby(['OPERADOR', 'fecha', 'turno']):
        # Ordenar por hora dentro del turno
        grupo_ordenado = grupo.sort_values('hora').reset_index(drop=True)
        
        for idx, (_, fila) in enumerate(grupo_ordenado.iterrows()):
            try:
                piezas = fila["CANTIDAD"]
                puntadas_base = fila["PUNTADAS"]
                cabezas = fila["CABEZAS"]
                
                # Validar datos
                if pd.isna(piezas) or pd.isna(puntadas_base) or cabezas == 0:
                    continue
                
                # Cálculos
                pasadas = np.ceil(piezas / cabezas)
                multiplo = pasadas * cabezas
                puntadas_ajustadas = max(puntadas_base, 4000)
                puntadas_multiplos = multiplo * puntadas_ajustadas
                
                # ✅ CORRECCIÓN: Inicio de turno solo en idx==0
                puntadas_cambios = 36000 if idx == 0 else 18000
                
                total_puntadas = puntadas_multiplos + puntadas_cambios
                
                resultados.append({
                    'OPERADOR': operador,
                    'FECHA': fecha,
                    'TURNO': turno,
                    'PEDIDO': fila.get('#DE PEDIDO', 'N/A'),
                    'TIPO_PRENDA': fila.get('TIPO DE PRENDA', 'N/A'),
                    'DISEÑO': fila.get('DISEÑO', 'N/A'),
                    'CANTIDAD': int(piezas),
                    'PUNTADAS_BASE': int(puntadas_base),
                    'CABEZAS': int(cabezas),
                    'PASADAS': int(pasadas),
                    'MULTIPLO': int(multiplo),
                    'PUNTADAS_MULTIPLOS': int(puntadas_multiplos),
                    'PUNTADAS_CAMBIOS': int(puntadas_cambios),
                    'TOTAL_PUNTADAS': int(total_puntadas),
                    'ES_INICIO_TURNO': idx == 0,
                    'ORDEN_EN_TURNO': idx + 1,
                    'FECHA_CALCULO': datetime.now().date(),
                    'HORA_CALCULO': datetime.now().strftime("%H:%M:%S")
                })
            except Exception as e:
                st.warning(f"Error procesando fila: {e}")
                continue
    
    return pd.DataFrame(resultados)

# ==================== MÓDULO: GUARDADO EN SHEETS ====================

def guardar_calculos_en_sheets(df_calculado):
    """Guarda cálculos en hoja 'puntadas_calculadas'"""
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
            worksheet = spreadsheet.add_worksheet(title="puntadas_calculadas", rows="10000", cols="20")
        
        # Convertir fechas a string
        df_guardar = df_calculado.copy()
        df_guardar['FECHA'] = df_guardar['FECHA'].astype(str)
        df_guardar['FECHA_CALCULO'] = df_guardar['FECHA_CALCULO'].astype(str)
        df_guardar['ES_INICIO_TURNO'] = df_guardar['ES_INICIO_TURNO'].astype(str)
        
        # Append en lugar de overwrite (preserva histórico)
        datos_existentes = worksheet.get_all_values()
        proxima_fila = len(datos_existentes) + 1
        
        if proxima_fila == 1:  # Tabla vacía, escribir encabezados
            worksheet.update('A1', [df_guardar.columns.tolist()])
            proxima_fila = 2
        
        # Escribir nuevas filas
        nuevas_filas = df_guardar.values.tolist()
        worksheet.update(f'A{proxima_fila}', nuevas_filas)
        
        return True
    except Exception as e:
        st.error(f"Error al guardar cálculos: {str(e)}")
        return False

def guardar_resumen_ejecutivo(df_calculado):
    """Agrupa puntadas por operador-periodo y guarda en 'resumen_ejecutivo'"""
    try:
        if df_calculado.empty:
            return False
        
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
            worksheet = spreadsheet.worksheet("resumen_ejecutivo")
        except:
            worksheet = spreadsheet.add_worksheet(title="resumen_ejecutivo", rows="5000", cols="10")
            encabezados = ["FECHA_INICIO_PERIODO", "FECHA_FIN_PERIODO", "PERIODO", "OPERADOR", 
                          "TOTAL_PUNTADAS", "COMISION", "BONIFICACION", "COMISION_TOTAL", 
                          "FECHA_ACTUALIZACION", "ACTUALIZADO_POR"]
            worksheet.update('A1', [encabezados])
        
        # Determinar período actual
        fecha_inicio_periodo, fecha_fin_periodo, periodo_str, _ = obtener_periodo_actual()
        
        # Agrupar cálculos por operador en este período
        df_filtrado = df_calculado[
            (df_calculado['FECHA'] >= fecha_inicio_periodo) & 
            (df_calculado['FECHA'] <= fecha_fin_periodo)
        ]
        
        resumen = df_filtrado.groupby('OPERADOR')['TOTAL_PUNTADAS'].sum().reset_index()
        
        # Obtener datos existentes
        datos_existentes = worksheet.get_all_values()
        df_existente = pd.DataFrame(datos_existentes[1:], columns=datos_existentes[0]) if len(datos_existentes) > 1 else pd.DataFrame()
        
        # Nuevos registros
        nuevos_registros = []
        for _, fila in resumen.iterrows():
            operador = fila['OPERADOR']
            total_puntadas = int(fila['TOTAL_PUNTADAS'])
            
            # Verificar si ya existe
            existe = False
            if not df_existente.empty:
                mask = (df_existente['OPERADOR'] == operador) & (df_existente['PERIODO'] == periodo_str)
                existe = not df_existente[mask].empty
            
            if not existe:
                nuevos_registros.append([
                    str(fecha_inicio_periodo),
                    str(fecha_fin_periodo),
                    periodo_str,
                    operador,
                    total_puntadas,
                    "",  # COMISION (vacío para encargado)
                    "",  # BONIFICACION
                    "",  # COMISION_TOTAL
                    "",  # FECHA_ACTUALIZACION
                    ""   # ACTUALIZADO_POR
                ])
        
        if nuevos_registros:
            proxima_fila = len(datos_existentes) + 1
            worksheet.update(f'A{proxima_fila}', nuevos_registros)
        
        return True
    except Exception as e:
        st.error(f"Error al guardar resumen: {str(e)}")
        return False

# ==================== MÓDULO: CARGA DE DATOS ====================

def cargar_datos_de_sheets():
    """Carga datos desde Google Sheets y aplica cálculos"""
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
        
        # Calcular puntadas
        df_calculado = calcular_puntadas_automaticamente(df)
        
        # Guardar cálculos
        if not df_calculado.empty:
            guardar_calculos_en_sheets(df_calculado)
            guardar_resumen_ejecutivo(df_calculado)
        
        return df, df_calculado
        
    except Exception as e:
        st.error(f"Error cargando datos: {str(e)}")
        return pd.DataFrame(), pd.DataFrame()

# ==================== MÓDULO: INTERFAZ DE OPERADOR ====================

def mostrar_resumen_periodo_actual(df_calculado, operador):
    """Muestra resumen para período actual"""
    fecha_inicio, fecha_fin, periodo_str, _ = obtener_periodo_actual()
    
    df_operador = df_calculado[
        (df_calculado['OPERADOR'] == operador) &
        (df_calculado['FECHA'] >= fecha_inicio) &
        (df_calculado['FECHA'] <= fecha_fin)
    ]
    
    if df_operador.empty:
        st.info("No hay registros en el período actual.")
        return
    
    st.subheader(f"Período: {periodo_str}")
    
    # Métricas
    col1, col2, col3, col4 = st.columns(4)
    
    total_puntadas = df_operador['TOTAL_PUNTADAS'].sum()
    total_pedidos = len(df_operador)
    total_piezas = df_operador['CANTIDAD'].sum()
    promedio_por_pedido = total_puntadas / total_pedidos if total_pedidos > 0 else 0
    
    with col1:
        st.metric("Pedidos", total_pedidos)
    with col2:
        st.metric("Piezas", f"{int(total_piezas):,}")
    with col3:
        st.metric("Total Puntadas", f"{int(total_puntadas):,}")
    with col4:
        st.metric("Promedio/Pedido", f"{int(promedio_por_pedido):,}")
    
    # Detalle por día
    st.write("**Detalle por Día:**")
    resumen_diario = df_operador.groupby('FECHA').agg({
        'PEDIDO': 'count',
        'CANTIDAD': 'sum',
        'TOTAL_PUNTADAS': 'sum'
    }).reset_index()
    resumen_diario.columns = ['Fecha', 'Pedidos', 'Piezas', 'Puntadas']
    resumen_diario['Fecha'] = resumen_diario['Fecha'].astype(str)
    resumen_diario['Piezas'] = resumen_diario['Piezas'].astype(int)
    resumen_diario['Puntadas'] = resumen_diario['Puntadas'].astype(int)
    
    st.dataframe(resumen_diario, use_container_width=True, height=300)
    
    # Detalle de pedidos
    st.write("**Detalle de Pedidos:**")
    columnas = ['FECHA', 'TURNO', 'PEDIDO', 'DISEÑO', 'CANTIDAD', 'PUNTADAS_MULTIPLOS', 'PUNTADAS_CAMBIOS', 'TOTAL_PUNTADAS']
    df_mostrar = df_operador[columnas].copy()
    df_mostrar['FECHA'] = df_mostrar['FECHA'].astype(str)
    for col in ['CANTIDAD', 'PUNTADAS_MULTIPLOS', 'PUNTADAS_CAMBIOS', 'TOTAL_PUNTADAS']:
        df_mostrar[col] = df_mostrar[col].astype(int)
    
    st.dataframe(df_mostrar, use_container_width=True, height=300)

def mostrar_historico_periodos(df_calculado, operador):
    """Muestra histórico de períodos anteriores"""
    periodos = obtener_periodos_historicos(6)
    
    # Selectbox para elegir período
    opciones_periodo = [p[2] for p in periodos]  # periodo_str
    periodo_seleccionado_str = st.selectbox("Selecciona período:", opciones_periodo)
    
    # Encontrar período seleccionado
    periodo_seleccionado = next(p for p in periodos if p[2] == periodo_seleccionado_str)
    fecha_inicio, fecha_fin, periodo_str = periodo_seleccionado
    
    df_operador = df_calculado[
        (df_calculado['OPERADOR'] == operador) &
        (df_calculado['FECHA'] >= fecha_inicio) &
        (df_calculado['FECHA'] <= fecha_fin)
    ]
    
    if df_operador.empty:
        st.info(f"No hay registros en {periodo_str}")
        return
    
    st.subheader(f"Período: {periodo_str}")
    
    # Métricas
    col1, col2, col3 = st.columns(3)
    
    total_puntadas = df_operador['TOTAL_PUNTADAS'].sum()
    total_pedidos = len(df_operador)
    total_piezas = df_operador['CANTIDAD'].sum()
    
    with col1:
        st.metric("Pedidos", total_pedidos)
    with col2:
        st.metric("Piezas", f"{int(total_piezas):,}")
    with col3:
        st.metric("Total Puntadas", f"{int(total_puntadas):,}")
    
    # Tabla de detalle
    st.write("**Detalle de Pedidos:**")
    columnas = ['FECHA', 'PEDIDO', 'DISEÑO', 'CANTIDAD', 'TOTAL_PUNTADAS']
    df_mostrar = df_operador[columnas].copy()
    df_mostrar['FECHA'] = df_mostrar['FECHA'].astype(str)
    df_mostrar['CANTIDAD'] = df_mostrar['CANTIDAD'].astype(int)
    df_mostrar['TOTAL_PUNTADAS'] = df_mostrar['TOTAL_PUNTADAS'].astype(int)
    
    st.dataframe(df_mostrar, use_container_width=True, height=300)

def mostrar_comisiones_operador(operador):
    """Muestra comisiones que el encargado ingresó en Sheets"""
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
        worksheet = gc.open_by_key(sheet_id).worksheet("resumen_ejecutivo")
        datos = worksheet.get_all_values()
        
        if len(datos) > 1:
            df_resumen = pd.DataFrame(datos[1:], columns=datos[0])
            df_operador = df_resumen[df_resumen['OPERADOR'] == operador]
            
            if not df_operador.empty:
                st.subheader("💰 Mis Comisiones")
                
                # Convertir a números
                df_operador['TOTAL_PUNTADAS'] = pd.to_numeric(df_operador['TOTAL_PUNTADAS'], errors='coerce')
                df_operador['COMISION'] = pd.to_numeric(df_operador['COMISION'], errors='coerce')
                df_operador['BONIFICACION'] = pd.to_numeric(df_operador['BONIFICACION'], errors='coerce')
                df_operador['COMISION_TOTAL'] = pd.to_numeric(df_operador['COMISION_TOTAL'], errors='coerce')
                
                # Mostrar tabla
                columnas = ['PERIODO', 'TOTAL_PUNTADAS', 'COMISION', 'BONIFICACION', 'COMISION_TOTAL']
                df_mostrar = df_operador[columnas].copy()
                df_mostrar['TOTAL_PUNTADAS'] = df_mostrar['TOTAL_PUNTADAS'].apply(lambda x: f"{int(x):,}" if pd.notna(x) else "N/A")
                df_mostrar['COMISION'] = df_mostrar['COMISION'].apply(lambda x: f"${x:.2f}" if pd.notna(x) and x > 0 else "Pendiente")
                df_mostrar['COMISION_TOTAL'] = df_mostrar['COMISION_TOTAL'].apply(lambda x: f"${x:.2f}" if pd.notna(x) and x > 0 else "Pendiente")
                
                st.dataframe(df_mostrar, use_container_width=True)
            else:
                st.info("No hay comisiones registradas aún.")
    except Exception as e:
        st.warning(f"No se pudieron cargar comisiones: {e}")

def vista_admin_encargado():
    """Vista solo para el encargado de operación"""
    
    # Protección: solo si el usuario tiene permiso (por ahora, usar contraseña simple)
    st.subheader("🔐 Área Restringida - Encargado de Operación")
    
    password = st.text_input("Contraseña:", type="password")
    if password != st.secrets.get("admin_password", "admin123"):
        st.error("Contraseña incorrecta")
        return
    
    # Cargar resumen ejecutivo
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
    worksheet = gc.open_by_key(sheet_id).worksheet("resumen_ejecutivo")
    datos = worksheet.get_all_values()
    
    df_resumen = pd.DataFrame(datos[1:], columns=datos[0])
    
    st.write("**Resumen de Puntadas por Operador y Período:**")
    st.dataframe(df_resumen, use_container_width=True, height=400)
    
    st.info("📝 Para editar comisiones, dirígete a la hoja 'resumen_ejecutivo' en Google Sheets")
    st.link_button("Abrir Google Sheets", f"https://docs.google.com/spreadsheets/d/{st.secrets['gsheets']['produccion_sheet_id']}")

# ==================== DASHBOARD PRINCIPAL ====================

def mostrar_dashboard_produccion():
    """
    Función principal del dashboard de producción.
    Punto de entrada para app_principal.py
    """
    st.set_page_config(page_title="Dashboard Producción", layout="wide")
    st.title("🏭 Dashboard de Producción - Puntadas y Comisiones")
    
    # Cargar datos
    df, df_calculado = cargar_datos_de_sheets()
    
    if df.empty:
        st.error("No se pudieron cargar los datos.")
        return
    
    # Sidebar
    st.sidebar.title("👤 Mi Consulta")
    operadores = sorted(df['OPERADOR'].unique())
    es_admin = st.sidebar.checkbox("Soy encargado de operación")

    if es_admin:
        vista_admin_encargado()
    else:
        # Interfaz de operador normal
        operador_seleccionado = st.sidebar.selectbox(
            "Selecciona tu nombre:",
            ["-- Selecciona --"] + operadores,
            key="operador_select"
        )
        
        if operador_seleccionado == "-- Selecciona --":
            st.info("👆 Por favor selecciona tu nombre para ver tus datos.")
        else:
            # Tabs
            tab1, tab2, tab3 = st.tabs(["📊 Período Actual", "📅 Histórico", "💰 Comisiones"])

            with tab1:
                mostrar_resumen_periodo_actual(df_calculado, operador_seleccionado)

            with tab2:
                mostrar_historico_periodos(df_calculado, operador_seleccionado)

            with tab3:
                mostrar_comisiones_operador(operador_seleccionado)
    
    # Footer
    st.sidebar.markdown("---")
    st.sidebar.write(f"Última actualización: {datetime.now().strftime('%H:%M:%S')}")
    st.sidebar.write(f"Total registros: {len(df)}")
    st.sidebar.write(f"Total cálculos: {len(df_calculado)}")

# ==================== MAIN ====================

def main():
    st.set_page_config(page_title="Dashboard Producción", layout="wide")
    st.title("🏭 Dashboard de Producción - Puntadas y Comisiones")
    
    # Cargar datos
    df, df_calculado = cargar_datos_de_sheets()
    
    if df.empty:
        st.error("No se pudieron cargar los datos.")
        return
    
    # Sidebar
    st.sidebar.title("👤 Mi Consulta")
    operadores = sorted(df['OPERADOR'].unique())
    es_admin = st.sidebar.checkbox("Soy encargado de operación")

    if es_admin:
        vista_admin_encargado()
    else:
        # Interfaz de operador normal
        operador_seleccionado = st.sidebar.selectbox(
            "Selecciona tu nombre:",
            ["-- Selecciona --"] + operadores,
            key="operador_select"
        )
        
        if operador_seleccionado == "-- Selecciona --":
            st.info("👆 Por favor selecciona tu nombre para ver tus datos.")
        else:
            # Tabs
            tab1, tab2, tab3 = st.tabs(["📊 Período Actual", "📅 Histórico", "💰 Comisiones"])

            with tab1:
                mostrar_resumen_periodo_actual(df_calculado, operador_seleccionado)

            with tab2:
                mostrar_historico_periodos(df_calculado, operador_seleccionado)

            with tab3:
                mostrar_comisiones_operador(operador_seleccionado)
    
    # Footer
    st.sidebar.markdown("---")
    st.sidebar.write(f"Última actualización: {datetime.now().strftime('%H:%M:%S')}")
    st.sidebar.write(f"Total registros: {len(df)}")
    st.sidebar.write(f"Total cálculos: {len(df_calculado)}")

if __name__ == "__main__":
    main()
