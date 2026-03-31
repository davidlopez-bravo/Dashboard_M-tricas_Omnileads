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
    /* 1. KPIs Y CONTENEDOR (Lo que ya te gusta) */
    .block-container {padding-top: 1rem; padding-bottom: 0rem; background:#A597D1; color:#3C2D61}
    #MainMenu, footer {visibility: hidden;}

    [data-testid="stMetric"] {
        background-color: #ffffff;
        border: 1px solid #e6e9ef;
        border-radius: 10px;
        padding: 10px !important;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    [data-testid="stMetricLabel"] { font-size: 0.8rem !important; color: #555 !important; }
    [data-testid="stMetricValue"] { font-size: 1.4rem !important; color: #000 !important; }

    /* 2. SELECTORES Y CAJAS (INPUTS) */
    .stSelectbox div[data-baseweb="select"], 
    .stDateInput div[data-baseweb="input"] {
        font-size: 0.8rem !important;
        min-height: 28px !important;
    }

    /* 3. EL "TRUCO" PARA EL CALENDARIO Y DESPLEGABLES */
    div[data-baseweb="popover"] {
        transform: scale(0.85) !important;
        transform-origin: top left !important;
        z-index: 10000 !important;
    }

    /* Ajuste para que el calendario no se pegue al borde izquierdo */
    div[data-baseweb="calendar"] {
        margin-left: 5px !important;
    }

    /* 4. TEXTO DE LAS LISTAS */
    div[data-baseweb="popover"] li, 
    div[data-baseweb="popover"] div {
        font-size: 0.75rem !important;
        padding: 1px 4px !important;
    }

    /* 5. SIDEBAR COMPACTA */
    [data-testid="stSidebar"] [data-testid="stVerticalBlock"] {
        gap: 0.5rem !important;
        padding-top: 2rem !important;
    }
    [data-testid="stWidgetLabel"] p {
        font-size: 0.8rem !important;
        margin-bottom: 0px !important;       
    }
            /* 6. COLOR DEL FONDO PRINCIPAL */
    [data-testid="stAppViewContainer"] {
        background-color: #f0f2f5; /* Cambia este color por el que quieras */
    }

    /* 7. COLOR DE LA BARRA LATERAL (SIDEBAR) */
    [data-testid="stSidebar"] {
        background-color: #5d3f92; /* Un morado como el de tu logo */
    }

    /* 8. COLOR DEL TEXTO EN LA SIDEBAR (Opcional, por si pones fondo oscuro) */
    [data-testid="stSidebar"] .stMarkdown, 
    [data-testid="stSidebar"] label, 
    [data-testid="stSidebar"] h2 {
        color: white !important;
    }
</style>
""", unsafe_allow_html=True)

logo_url = "https://media.licdn.com/dms/image/v2/D4E0BAQGNl0-8M52OUw/company-logo_200_200/B4EZgTsXs1GcAI-/0/1752677055732/bravo_colombia_logo?e=2147483647&v=beta&t=irvJ5n8nwvm2gL4X05j-l58FmMXoUL4ztRwhiwvfqJs"

# Usamos Markdown con HTML
st.markdown(
    f"""
    <br>
<div style='display: flex; align-items: center;'>
        <img src='{logo_url}' 
             style='width: 60px; 
                    height: 60px; 
                    border-radius: 15px; 
                    object-fit: cover; 
                    margin-right: 15px;
                    border: 2px solid #5d3f92;'>
        <h1 style='margin: 0;'>Monitor - Bravo Colombia</h1>
    </div>
    """, 
    unsafe_allow_html=True
)

query_hc = """SELECT 
    email,
    employee_id,
    name,
    job_title,
    leader,
    status,
    joined_resuelve_on,
    became_inactive_on,
    cedula
FROM
    coyote_employees
WHERE 
    office = 'Colombia'
    AND area = 'Negociación'
    AND status = 'Activo'
"""
df_hc = extraccion_metabase_final(16, query_hc)[['email', 'leader']]
CORREOS = df_hc['email'].to_list()
LIDERES = df_hc['leader'].unique().tolist()
LIDERES = [x for x in LIDERES if x not in['Natalia Valentina Castro Jimenez', 'Diego Pailles Badía', 'Felipe Castillo Szpoganicz', 'Roberto Carlos Chapman Diaz', 'Julio Enrique Delgado Diaz']]

# Tu lista actualizada
correos_sql = "'" + "','".join(CORREOS) + "'"
COLORES = {'llamada': '#2ca02c', 'descanso': '#d62728', 'actualizacion': '#1f77b4'}

# --- 1. FILTROS ---
st.sidebar.header("Filtros de Búsqueda")

# 1.1 Rango de fechas
rango = st.sidebar.date_input(
    "1. Rango de fechas",
    value=(datetime.date.today(), datetime.date.today())
)

if isinstance(rango, tuple) and len(rango) == 2:
    f_inicio, f_fin = rango
else:
    f_inicio = f_fin = rango if not isinstance(rango, tuple) else rango[0]

# 1.2 Filtro por Líder
lider_seleccionado = st.sidebar.selectbox("2. Filtrar por Líder:", ["Todos"] + LIDERES)

# Lógica para filtrar los correos según el líder
if lider_seleccionado != "Todos":
    correos_filtrados_lider = df_hc[df_hc['leader'] == lider_seleccionado]['email'].tolist()
else:
    correos_filtrados_lider = CORREOS

# 1.3 Filtro por Asesor Individual (depende del líder seleccionado)
asesor_seleccionado = st.sidebar.selectbox("3. Ver Perfil Detallado de:", ["Equipo Completo"] + correos_filtrados_lider)

# Actualizamos correos_sql para la consulta SQL basado en el filtro de líder
correos_sql_param = "'" + "','".join(correos_filtrados_lider) + "'"

# --- 2. CARGA DE DATOS ---
@st.cache_data(show_spinner="Consultando Metabase...")
def cargar_datos(inicio, fin, correos_sql_param):
    
    query_act = f"""
    SELECT debts.id as debt_id, cr.bank_reference, act.end AS email, (act.executed_at AT TIME ZONE 'UTC' AT TIME ZONE 'America/Bogota') AS executed_at
    FROM credit_repair_debts AS debts
    JOIN credit_repair_debt_activities AS act ON debts.id = act.debt_id
    JOIN credit_repairs as cr ON cr.id = debts.credit_repair_id
    WHERE (act.executed_at AT TIME ZONE 'UTC' AT TIME ZONE 'America/Bogota')::DATE >= '{inicio}'
      AND (act.executed_at AT TIME ZONE 'UTC' AT TIME ZONE 'America/Bogota')::DATE <= '{fin}'
      AND act.payment_to_bank IS NOT NULL AND act.end IN ({correos_sql_param})
    """
    df_a = extraccion_metabase_final(12, query_act)
    if not df_a.empty:
        df_a['executed_at'] = pd.to_datetime(df_a['executed_at'], format='ISO8601')
        df_a = df_a[(df_a['executed_at'].dt.hour >= 7) & (df_a['executed_at'].dt.hour <= 19)]

    query_log = rf"""
    SELECT log.callid, DATETIME(log.time, 'America/Bogota') AS time, log.event, u.email, log.numero_marcado
    FROM omnileads_co_public.reportes_app_llamadalog AS log
    JOIN omnileads_co_public.ominicontacto_app_agenteprofile AS agent ON log.agente_id = agent.id
    JOIN omnileads_co_public.ominicontacto_app_user AS u ON agent.user_id = u.id
    WHERE DATETIME(log.time, 'America/Bogota') >= '{inicio} 00:00:00'
      AND DATETIME(log.time, 'America/Bogota') <= '{fin} 23:59:59'
      AND u.email in ({correos_sql_param})
    """
    df_l = extraccion_metabase_final(50, query_log)
    
    if df_l.empty: return df_a, pd.DataFrame()

    df_l['time'] = pd.to_datetime(df_l['time'], format='ISO8601')
    
    # 1. Extraemos el mapeo de CallID -> Numero (limpiando nulos)
    df_nums = df_l[df_l['numero_marcado'].notnull()][['callid', 'numero_marcado']].drop_duplicates('callid')

    # 2. Pivotamos normal (sin meter el número en el index para no romper los tiempos)
    pivot = df_l.pivot_table(values='time', index=['callid', 'email'], columns='event', aggfunc='min')
    
    if 'DIAL' not in pivot.columns: return df_a, pd.DataFrame()

    llamadas = pivot[pivot['DIAL'].notnull()].copy()
    llamadas['inicio'] = llamadas.min(axis=1)
    llamadas['fin'] = llamadas.max(axis=1)
    llamadas['actividad'] = 'llamada'
    llamadas = llamadas.reset_index()

    # 3. Le pegamos el número marcado de vuelta usando el callid
    llamadas = llamadas.merge(df_nums, on='callid', how='left')
    llamadas['numero_marcado'] = llamadas['numero_marcado'].fillna("Desconocido")
    
    llamadas = llamadas.sort_values(by=['email', 'inicio'])

    # Descansos
    descansos = llamadas.copy()
    descansos['inicio_d'] = descansos.groupby('email')['fin'].shift(1)
    descansos = descansos.dropna(subset=['inicio_d'])
    descansos = descansos[descansos['inicio'] > descansos['inicio_d']]
    
    df_desc = pd.DataFrame({
        'email': descansos['email'], 'callid': 'PAUSA',
        'inicio': descansos['inicio_d'], 'fin': descansos['inicio'], 'actividad': 'descanso',
        'numero_marcado': 'N/A'
    })

    timeline = pd.concat([llamadas[['email','callid','inicio','fin','actividad','numero_marcado']], df_desc])
    timeline['duracion_min'] = ((timeline['fin'] - timeline['inicio']).dt.total_seconds() / 60).round(1)
    
    return df_a, timeline

df_act_raw, df_tl_raw = cargar_datos(f_inicio, f_fin, correos_sql_param)

# --- NUEVA LÓGICA DE FILTRADO PARA LA GRÁFICA ---
if asesor_seleccionado != "Equipo Completo":
    # Si seleccionó a alguien, filtramos solo a esa persona
    emails_a_mostrar = [asesor_seleccionado]
else:
    # Si es "Equipo Completo", mostramos a todos los que pertenecen a ese líder
    emails_a_mostrar = correos_filtrados_lider

df_tl_raw = df_tl_raw[df_tl_raw['email'].isin(emails_a_mostrar)]
df_act_raw = df_act_raw[df_act_raw['email'].isin(emails_a_mostrar)]

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
                # customdata: [0]=duracion, [1]=callid, [2]=fin, [3]=numero_marcado
                customdata=d[['duracion_min', 'callid', 'fin', 'numero_marcado']],
                hovertemplate="<b>%{name}</b><br>Asesor: %{y}<br>Número: <b>%{customdata[3]}</b><br>Inicio: %{base|%H:%M:%S}<br>Fin: %{customdata[2]|%H:%M:%S}<br>Duración: %{customdata[0]} min<extra></extra>"
            ))

# --- CAMBIO AQUÍ: Actualizaciones como go.Bar para igualar el alto ---
if not df_act_raw.empty:
    # Definimos un ancho visual muy pequeño (10 segundos) en milisegundos para la barra
    ancho_visual_ms = 100 * 1000 
    
    fig.add_trace(go.Bar(
        base=df_act_raw['executed_at'], # El punto de inicio es la hora de ejecución
        x=[ancho_visual_ms] * len(df_act_raw), # Duración fija y pequeña
        y=df_act_raw['email'], 
        orientation='h', 
        name='Actualización',
        marker_color=COLORES['actualizacion'],
        opacity=0.8, # Un poco más opaca para que se note al ser delgada
        customdata=df_act_raw[['debt_id', 'bank_reference']], 
        hovertemplate=(
            "<b>Actualización</b><br>" +
            "Asesor: %{y}<br>" +
            "Hora: %{base|%H:%M:%S}<br>" + # Usamos base para mostrar la hora exacta
            "ID Deuda: %{customdata[0]}<br>" +
            "Ref. Banco: %{customdata[1]}" +
            "<extra></extra>"
        )
    ))


fig.update_layout(
    xaxis=dict(type="date", tickformat="%H:%M", title="Hora"),
    yaxis=dict(title="", categoryorder='category ascending', tickfont=dict(size=12, color='#3C2D61', weight='bold')), 

    paper_bgcolor='rgba(0,0,0,0)', # Fondo exterior transparente
    plot_bgcolor='rgba(0,0,0,0)',  # Fondo interior transparente


    barmode='overlay', 
    height=len(emails_a_mostrar) * 40 + 100, 
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    hovermode="closest",
    margin=dict(l=0, r=0, t=30, b=0),
    autosize=True
)
# Capturamos la selección del gráfico
seleccion = st.plotly_chart(
    fig, 
    use_container_width=True, 
    on_select="rerun",
    config={
        'scrollZoom': True,        # Activa zoom con la rueda del mouse
        'displaylogo': False,      # Quita el logo de Plotly
        'modeBarButtonsToAdd': ['drawline', 'drawopenpath', 'eraseshape'], # Herramientas extra si quieres anotar
        'modeBarButtonsToRemove': ['lasso2d', 'select2d'], # Limpiamos para que no estorben
        'displayModeBar': False     # Asegura que la barra de herramientas sea visible
    }
)

# --- 3.5. EXTRACTOR DE DATOS COPIABLES (Al hacer clic en el gráfico) ---
if seleccion and "selection" in seleccion and seleccion["selection"]["points"]:
    punto = seleccion["selection"]["points"][0]
    # Detectamos si lo que clickeó fue una actualización (tienen customdata de 2 elementos: debt_id y bank_reference)
    if "customdata" in punto and len(punto["customdata"]) == 2 and isinstance(punto["customdata"][0], (int, str)):
        st.success(f"📈 **Datos de la actualización seleccionada:** \n"
                   f"**ID Deuda:** `{punto['customdata'][0]}` | **Ref. Banco:** `{punto['customdata'][1]}` | **Asesor:** `{punto['y']}`")

st.divider()


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
with c4:
    st.metric("📝 Actualizaciones", len(df_act_view) if not df_act_view.empty else 0)

# --- 6. TABLA UNIFICADA (Llamadas, Descansos y Actualizaciones) ---
st.write("### 📋 Historial Completo de Actividades")

frames_tabla = []

if not df_tl_view.empty:
    # Preparamos las llamadas y descansos
    t1 = df_tl_view[['email', 'actividad', 'inicio', 'fin', 'duracion_min', 'numero_marcado']].rename(columns={'inicio': 'fecha_hora'})
    t1['detalle'] = t1.apply(lambda x: f"📞 {x['numero_marcado']} | {x['duracion_min']} min" if x['actividad'] == 'llamada' else f"☕ Descanso de {x['duracion_min']} min", axis=1)
    frames_tabla.append(t1[['email', 'actividad', 'fecha_hora', 'fin', 'detalle']])

if not df_act_view.empty:
    # Preparamos las actualizaciones para que encajen en la misma tabla
    t2 = df_act_view[['email', 'executed_at', 'debt_id', 'bank_reference']].copy()
    t2['actividad'] = 'actualizacion'
    t2 = t2.rename(columns={'executed_at': 'fecha_hora'})
    t2['fin'] = pd.NaT # Las actualizaciones son un punto en el tiempo, no tienen fin
    t2['detalle'] = "📝 ID: " + t2['debt_id'].astype(str) + " | Ref: " + t2['bank_reference'].astype(str)
    frames_tabla.append(t2[['email', 'actividad', 'fecha_hora', 'fin', 'detalle']])

if frames_tabla:
    # Unimos todo y lo ordenamos por hora
    tabla_completa = pd.concat(frames_tabla).sort_values(by='fecha_hora', ascending=False)
    
    st.dataframe(
        tabla_completa[['fecha_hora', 'actividad', 'detalle', 'email']], 
        use_container_width=True, 
        hide_index=True,
        column_config={
            "fecha_hora": st.column_config.DatetimeColumn("Hora", format="HH:mm:ss"),
            "actividad": st.column_config.TextColumn("Tipo"),
            "detalle": st.column_config.TextColumn("Información"),
            "email": st.column_config.TextColumn("Asesor")
        }
    )
else:
    st.info("No hay datos de actividad.")

if __name__ == "__main__":
    pass