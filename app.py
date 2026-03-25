import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import datetime
# Asegúrate de que esta importación coincida con tu archivo real
from tools import extraccion_metabase_final

# --- 0. CONFIGURACIÓN Y CSS (ESTILO PERSONALIZADO) ---
st.set_page_config(page_title="Monitor Integral - Equipo", layout="wide", page_icon="📊")

# Inyección de CSS para que no se vea tan genérico
st.markdown("""
<style>
    /* Estilo para las tarjetas de las métricas (KPIs) */
[data-testid="stMetric"] {
        background-color: #ffffff; /* Fondo blanco puro para resaltar */
        border: 1px solid #e6e9ef;
        border-radius: 12px;
        padding: 20px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
    }
            /* Color de la etiqueta (el nombre del KPI) */
    [data-testid="stMetricLabel"] {
        color: #1f1f1f !important; /* Negro/Gris muy oscuro */
        font-weight: 600 !important;
        font-size: 1.1rem !important;
    }
            /* Color del valor (el número) */
    [data-testid="stMetricValue"] {
        color: #000000 !important;
        font-weight: 300 !important;
    }
    /* Ocultar menú de hamburguesa y pie de página de Streamlit */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    /* Reducir el espacio en blanco de arriba */
    .block-container {padding-top: 2rem;}
</style>
""", unsafe_allow_html=True)

st.title("📊 Monitor Integral: Equipo Bravo")

# Tu lista actualizada
CORREOS = [
    'william.abril@gobravo.com.co', 
    'katherine.marulanda@gobravo.com.co', 'isabel.velasquez@gobravo.com.co',
    'jhonnatan.garcia@gobravo.com.co', 'david.tinjaca@gobravo.com.co', 
    'ivonne.valbuena@gobravo.com.co', 'milena.perez@gobravo.com.co',
    'sonia.restrepo@gobravo.com.co',  'juan.portillo@gobravo.com.co'
]
correos_sql = "'" + "','".join(CORREOS) + "'"
COLORES = {'llamada': '#2ca02c', 'descanso': '#d62728', 'actualizacion': '#1f77b4'}

# --- 1. FILTROS ---
st.sidebar.header("Filtros de Búsqueda")
rango = st.sidebar.date_input(
    "Selecciona el rango de fechas",
    value=(datetime.date.today(), datetime.date.today())
)

if isinstance(rango, tuple) and len(rango) == 2:
    f_inicio, f_fin = rango
else:
    f_inicio = f_fin = rango if not isinstance(rango, tuple) else rango[0]

# --- 2. CARGA DE DATOS ---
@st.cache_data(show_spinner="Consultando Metabase...")
def cargar_datos(inicio, fin):
    
    query_act = f"""
    SELECT debts.id as debt_id, cr.bank_reference, act.end AS email, (act.executed_at AT TIME ZONE 'UTC' AT TIME ZONE 'America/Bogota') AS executed_at
    FROM credit_repair_debts AS debts
    JOIN credit_repair_debt_activities AS act ON debts.id = act.debt_id
    JOIN credit_repairs as cr ON cr.id = debts.credit_repair_id
    WHERE (act.executed_at AT TIME ZONE 'UTC' AT TIME ZONE 'America/Bogota')::DATE >= '{inicio}'
      AND (act.executed_at AT TIME ZONE 'UTC' AT TIME ZONE 'America/Bogota')::DATE <= '{fin}'
      AND act.payment_to_bank IS NOT NULL AND act.end IN ({correos_sql})
    """
    df_a = extraccion_metabase_final(12, query_act)
    if not df_a.empty:
        df_a['executed_at'] = pd.to_datetime(df_a['executed_at'], format='ISO8601')

    query_log = rf"""
    SELECT log.callid, DATETIME(log.time, 'America/Bogota') AS time, log.event, u.email
    FROM omnileads_co_public.reportes_app_llamadalog AS log
    JOIN omnileads_co_public.ominicontacto_app_agenteprofile AS agent ON log.agente_id = agent.id
    JOIN omnileads_co_public.ominicontacto_app_user AS u ON agent.user_id = u.id
    WHERE DATETIME(log.time, 'America/Bogota') >= '{inicio} 00:00:00'
      AND DATETIME(log.time, 'America/Bogota') <= '{fin} 23:59:59'
      AND u.email in ({correos_sql})
    """
    df_l = extraccion_metabase_final(50, query_log)
    
    if df_l.empty: return df_a, pd.DataFrame()

    df_l['time'] = pd.to_datetime(df_l['time'], format='ISO8601')
    pivot = df_l.pivot_table(values='time', index=('callid', 'email'), columns='event', aggfunc='min')
    
    if 'DIAL' not in pivot.columns: return df_a, pd.DataFrame()

    llamadas = pivot[pivot['DIAL'].notnull()].copy()
    llamadas['inicio'] = llamadas.min(axis=1)
    llamadas['fin'] = llamadas.max(axis=1)
    llamadas['actividad'] = 'llamada'
    llamadas = llamadas.reset_index().sort_values(by=['email', 'inicio'])

    descansos = llamadas.copy()
    descansos['inicio_d'] = descansos.groupby('email')['fin'].shift(1)
    descansos = descansos.dropna(subset=['inicio_d'])
    descansos = descansos[descansos['inicio'] > descansos['inicio_d']]
    
    df_desc = pd.DataFrame({
        'email': descansos['email'], 'callid': 'PAUSA',
        'inicio': descansos['inicio_d'], 'fin': descansos['inicio'], 'actividad': 'descanso'
    })

    timeline = pd.concat([llamadas[['email','callid','inicio','fin','actividad']], df_desc])
    timeline['duracion_min'] = ((timeline['fin'] - timeline['inicio']).dt.total_seconds() / 60).round(1)
    
    return df_a, timeline

df_act_raw, df_tl_raw = cargar_datos(f_inicio, f_fin)

# --- 3. GRÁFICO PRINCIPAL ---
st.subheader(f"Vista General: {f_inicio} al {f_fin}")

fig = go.Figure()

if not df_tl_raw.empty:
    for act, color in [('descanso', COLORES['descanso']), ('llamada', COLORES['llamada'])]:
        d = df_tl_raw[df_tl_raw['actividad'] == act]
        if not d.empty:
            fig.add_trace(go.Bar(
                base=d['inicio'], 
                x=(d['fin'] - d['inicio']).dt.total_seconds()*1000,
                y=d['email'], 
                orientation='h', 
                name=act.capitalize(),
                marker_color=color, 
                opacity=0.7,
                text="", 
                customdata=d[['duracion_min', 'callid', 'fin']],
                hovertemplate="<b>%{name}</b><br>Asesor: %{y}<br>Inicio: %{base|%H:%M:%S}<br>Fin: %{customdata[2]|%H:%M:%S}<br>Duración: %{customdata[0]} min<extra></extra>"
            ))

if not df_act_raw.empty:
    fig.add_trace(go.Scatter(
        x=df_act_raw['executed_at'], 
        y=df_act_raw['email'], 
        mode='markers', 
        name='Actualización',
        customdata=df_act_raw[['debt_id', 'bank_reference']], 
        marker=dict(color=COLORES['actualizacion'], symbol='line-ns-open', size=35, line=dict(width=3)),
        hovertemplate=(
            "<b>Actualización</b><br>" +
            "Asesor: %{y}<br>" +
            "Hora: %{x|%H:%M:%S}<br>" +
            "ID Deuda: %{customdata[0]}<br>" +
            "Ref. Banco: %{customdata[1]}" +
            "<extra></extra>"
        )
    ))

fig.update_layout(
    xaxis=dict(type="date", tickformat="%H:%M", title="Hora"),
    yaxis=dict(title="", categoryorder='category ascending'),
    barmode='overlay', 
    height=len(CORREOS) * 60 + 100,
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    hovermode="closest",
    margin=dict(l=0, r=0, t=30, b=0) # Ajuste de márgenes para que se vea más limpio
)

# Capturamos la selección del gráfico
seleccion = st.plotly_chart(fig, use_container_width=True, on_select="rerun")

# --- 3.5. EXTRACTOR DE DATOS COPIABLES (Al hacer clic en el gráfico) ---
if seleccion and "selection" in seleccion and seleccion["selection"]["points"]:
    punto = seleccion["selection"]["points"][0]
    # Detectamos si lo que clickeó fue una actualización (tienen customdata de 2 elementos: debt_id y bank_reference)
    if "customdata" in punto and len(punto["customdata"]) == 2 and isinstance(punto["customdata"][0], (int, str)):
        st.success(f"📈 **Datos de la actualización seleccionada:** \n"
                   f"**ID Deuda:** `{punto['customdata'][0]}` | **Ref. Banco:** `{punto['customdata'][1]}` | **Asesor:** `{punto['y']}`")

st.divider()

# --- 4. PERFIL DEL ASESOR ---
# Añadimos un selector para poder enfocar a un asesor manualmente
asesor_seleccionado = st.sidebar.selectbox("🔎 Ver Perfil Detallado de:", ["Equipo Completo"] + CORREOS)

# Si hacen clic en la gráfica, ese clic manda. Si no, manda el desplegable.
asesor_foco = None
if seleccion and "selection" in seleccion and seleccion["selection"]["points"]:
    asesor_foco = seleccion["selection"]["points"][0]["y"]
elif asesor_seleccionado != "Equipo Completo":
    asesor_foco = asesor_seleccionado

if asesor_foco:
    st.subheader(f"👤 Perfil Detallado: {asesor_foco}")
    df_tl_view = df_tl_raw[df_tl_raw['email'] == asesor_foco]
    df_act_view = df_act_raw[df_act_raw['email'] == asesor_foco]
else:
    st.subheader("👥 Resumen del Equipo Completo")
    df_tl_view = df_tl_raw
    df_act_view = df_act_raw

# --- 5. KPIs ---
c1, c2, c3, c4 = st.columns(4)
with c1:
    aire = df_tl_view[df_tl_view['actividad'] == 'llamada']['duracion_min'].sum() if not df_tl_view.empty else 0
    st.metric("📞 Tiempo Aire Total", f"{aire:,.1f} min")
with c2:
    break_time = df_tl_view[df_tl_view['actividad'] == 'descanso']['duracion_min'].sum() if not df_tl_view.empty else 0
    st.metric("☕ Tiempo Descanso", f"{break_time:,.1f} min")
with c3:
    n_llamadas = len(df_tl_view[df_tl_view['actividad'] == 'llamada']) if not df_tl_view.empty else 0
    st.metric("🎧 Cant. Llamadas", n_llamadas)
# with c4: ##RECORDAR PONER DESPUÉS
#     st.metric("📝 Actualizaciones", len(df_act_view) if not df_act_view.empty else 0)

# --- 6. TABLA UNIFICADA (Llamadas, Descansos y Actualizaciones) ---
st.write("### 📋 Historial Completo de Actividades")

frames_tabla = []

if not df_tl_view.empty:
    # Preparamos las llamadas y descansos
    t1 = df_tl_view[['email', 'actividad', 'inicio', 'fin', 'duracion_min']].rename(columns={'inicio': 'fecha_hora'})
    t1['detalle'] = "Duración: " + t1['duracion_min'].astype(str) + " min"
    frames_tabla.append(t1)

if not df_act_view.empty:
    # Preparamos las actualizaciones para que encajen en la misma tabla
    t2 = df_act_view[['email', 'executed_at', 'debt_id', 'bank_reference']].copy()
    t2['actividad'] = 'actualizacion'
    t2 = t2.rename(columns={'executed_at': 'fecha_hora'})
    t2['fin'] = pd.NaT # Las actualizaciones son un punto en el tiempo, no tienen fin
    t2['duracion_min'] = 0.0
    t2['detalle'] = "ID Deuda: " + t2['debt_id'].astype(str) + " | Ref: " + t2['bank_reference'].astype(str)
    frames_tabla.append(t2[['email', 'actividad', 'fecha_hora', 'fin', 'duracion_min', 'detalle']])

if frames_tabla:
    # Unimos todo y lo ordenamos por hora
    tabla_completa = pd.concat(frames_tabla).sort_values(by='fecha_hora', ascending=False)
    
    # Reordenamos las columnas para que se lea mejor
    tabla_completa = tabla_completa[['fecha_hora', 'actividad', 'detalle', 'fin', 'email']]
    
    st.dataframe(
        tabla_completa, 
        use_container_width=True, 
        hide_index=True,
        column_config={
            "fecha_hora": st.column_config.DatetimeColumn("Inicio / Ejecución", format="HH:mm:ss"),
            "fin": st.column_config.DatetimeColumn("Fin", format="HH:mm:ss"),
            "actividad": st.column_config.TextColumn("Tipo de Actividad"),
            "detalle": st.column_config.TextColumn("Información Adicional"),
            "email": st.column_config.TextColumn("Asesor")
        }
    )
else:
    st.info("No hay datos de actividad para mostrar con los filtros actuales.")