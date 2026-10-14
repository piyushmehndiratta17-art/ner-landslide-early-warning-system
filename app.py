"""
NER Landslide Early Warning System - command centre front end.

Same backend contracts as the original app (src.ai_model, src.iot_simulator,
src.ews_dispatcher, src.vision_analyzer, src.data_manager); only the
presentation layer is new.

Design rule: red / orange / yellow / green appear ONLY to mean risk.
"""

import html as _html
import math
import os
import re
import statistics
import time
import zlib
from urllib.parse import quote

import folium
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from PIL import Image
from streamlit_folium import st_folium

from src.data_manager import NER_STATIONS
from src.ai_model import LandslidePredictor
from src.iot_simulator import IoTSimulator, SCENARIOS
from src.ews_dispatcher import EWSDispatcher
from src.vision_analyzer import DroneSlopeAnalyzer

st.set_page_config(
    page_title="NER Landslide Early Warning",
    page_icon="🏔️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --------------------------------------------------------------------------
# Tokens
# --------------------------------------------------------------------------
INK = "#14261F"
MUTED = "#5A6B63"
RULE = "#CCD5CF"
GRID = "#DCE3DE"
FONT = "Public Sans, Noto Sans Bengali, system-ui, sans-serif"

TIER_COLOR = {"GREEN": "#2E9E6B", "YELLOW": "#E2B100", "ORANGE": "#E8741A", "RED": "#D6342C"}
TIER_TEXT = {"GREEN": INK, "YELLOW": INK, "ORANGE": INK, "RED": "#FFFFFF"}
RED_TEXT = "#B72A23"  # red for small text on light backgrounds
TIER_ORDER = ["RED", "ORANGE", "YELLOW", "GREEN"]
LSI_BANDS = (0.35, 0.60, 0.80)

CUSTOM_LABEL = "Custom sensor sandbox"

# The drone analyzer reports its own tier names; map them onto the shared palette.
VISION_TIER = {"LOW": "GREEN", "MODERATE": "YELLOW", "HIGH": "ORANGE", "CRITICAL": "RED"}


def _st_version():
    out = []
    for part in st.__version__.split(".")[:2]:
        digits = "".join(ch for ch in part if ch.isdigit())
        out.append(int(digits or 0))
    return tuple(out)


# Streamlit replaced use_container_width with width="stretch" around 1.50.
FILL = {"width": "stretch"} if _st_version() >= (1, 50) else {"use_container_width": True}


# --------------------------------------------------------------------------
# Small helpers
# --------------------------------------------------------------------------
def esc(value):
    return _html.escape(str(value))


def md(markup):
    """Render HTML. Lines are stripped so Markdown never sees indented code."""
    st.markdown("".join(line.strip() for line in markup.splitlines()), unsafe_allow_html=True)


def fmt(value, digits=1):
    try:
        return f"{float(value):.{digits}f}"
    except (TypeError, ValueError):
        return esc(value)


def rgba(hex_color, alpha):
    h = hex_color.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return f"rgba({r},{g},{b},{alpha})"


def tier_color(tier, fallback="#2E9E6B"):
    return TIER_COLOR.get(tier, fallback)


def carto_key():
    """CARTO basemap key from .streamlit/secrets.toml or the CARTO_API_KEY environment variable."""
    try:
        key = st.secrets.get("CARTO_API_KEY")
    except Exception:
        key = None
    key = key or os.environ.get("CARTO_API_KEY") or ""
    return re.sub(r"[^A-Za-z0-9_\-]", "", str(key))


def plural(n, word):
    return f"{n} {word}{'' if n == 1 else 's'}"


def clean_title(label):
    """Drop leading emoji from scenario titles for display."""
    return re.sub(r"^[^\w]+", "", label)


def section(title, sub=None):
    sub_html = f'<div class="sec-sub">{sub}</div>' if sub else ""
    md(f'<div class="sec">{title}</div>{sub_html}')


def plot(fig):
    st.plotly_chart(fig, theme=None, config={"displayModeBar": False}, **FILL)


def style_fig(fig, height):
    fig.update_layout(
        height=height,
        margin=dict(l=4, r=4, t=30, b=4),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family=FONT, color=INK, size=12),
        hoverlabel=dict(font_family=FONT),
        legend=dict(orientation="h", y=1.1, x=0),
    )
    fig.update_xaxes(gridcolor=GRID, linecolor=RULE, zeroline=False)
    fig.update_yaxes(gridcolor=GRID, linecolor=RULE, zeroline=False)
    return fig


def contour_uri():
    """Topographic rings used as the hero background."""
    cx, cy = 880, 230
    rings = []
    for k in range(1, 11):
        base = 28 * k
        pts = []
        for i in range(121):
            th = 2 * math.pi * i / 120
            wob = 1 + 0.10 * math.sin(3 * th + k * 0.6) + 0.06 * math.sin(5 * th - k * 0.9) + 0.03 * math.sin(2 * th + k)
            r = base * wob
            pts.append(f"{cx + r * math.cos(th) * 1.7:.1f},{cy + r * math.sin(th) * 0.8:.1f}")
        rings.append('<polygon points="' + " ".join(pts) + '"/>')
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 420" preserveAspectRatio="xMaxYMid slice">'
        '<g fill="none" stroke="#8FD0B8" stroke-opacity="0.16" stroke-width="1.2">' + "".join(rings) + "</g></svg>"
    )
    return "data:image/svg+xml;utf8," + quote(svg)


def meter_html(lsi):
    """Susceptibility index on a 0-1 scale with the four alert bands."""
    widths = (35, 25, 20, 20)
    zones = "".join(
        f'<i style="width:{w}%;background:{rgba(TIER_COLOR[t], 0.5)}"></i>'
        for w, t in zip(widths, ("GREEN", "YELLOW", "ORANGE", "RED"))
    )
    pos = min(max(float(lsi), 0), 1) * 100
    labels = "".join(f'<span style="left:{b * 100:.0f}%">{b:.2f}</span>' for b in LSI_BANDS)
    return (
        f'<div class="meter-wrap"><div class="meter">{zones}</div>'
        f'<div class="marker" style="left:{pos:.1f}%"></div></div>'
        f'<div class="meter-lbl">{labels}</div>'
    )


def sensor_html(name, value, unit, threshold, vmax):
    value = float(value)
    over = value >= threshold
    fill = TIER_COLOR["RED"] if over else "#6F8A7E"
    width = min(value / vmax, 1) * 100
    tick = threshold / vmax * 100
    note = f"Above the {threshold:g} {unit} alert level" if over else f"Alert level {threshold:g} {unit}"
    note_cls = "s-note over" if over else "s-note"
    return (
        f'<div class="sensor"><div class="s-head"><span>{name}</span>'
        f'<span class="s-val">{value:.1f} <small>{unit}</small></span></div>'
        f'<div class="track"><div class="fill" style="width:{width:.1f}%;background:{fill}"></div>'
        f'<div class="tick" style="left:{tick:.1f}%"></div></div>'
        f'<div class="{note_cls}">{note}</div></div>'
    )


def chip(name, tier, size="1.25rem"):
    """Tier name on its colour fill, always readable."""
    return (
        f'<span class="chip" style="background:{TIER_COLOR.get(tier, TIER_COLOR["GREEN"])};'
        f'color:{TIER_TEXT.get(tier, INK)};font-size:{size}">{esc(name)}</span>'
    )


def stat_html(label, value):
    return f'<div class="stat"><span>{label}</span><b>{value}</b></div>'


# --------------------------------------------------------------------------
# Styles
# --------------------------------------------------------------------------
CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,500..800&family=Noto+Sans+Bengali:wght@400;600&family=Public+Sans:wght@400;500;600&display=swap');

:root {
  --ink:#14261F; --muted:#5A6B63; --rule:#CCD5CF; --mist:#EDF1EE; --spruce:#0D2A25;
  --green:#2E9E6B; --yellow:#E2B100; --orange:#E8741A; --red:#D6342C;
  --display:'Bricolage Grotesque','Public Sans',system-ui,sans-serif;
}
html, body, .stApp, .stApp *:not([data-testid="stIconMaterial"]):not(.material-icons):not(.material-symbols-rounded) {
  font-family:'Public Sans','Noto Sans Bengali',system-ui,sans-serif; }
/* keep Streamlit's own icon font so arrows and toolbar icons draw as icons, not as their names */
[data-testid="stIconMaterial"], .material-icons, .material-symbols-rounded {
  font-family:'Material Symbols Rounded','Material Icons' !important; }
.stApp { background:var(--mist); color:var(--ink); }
.block-container { max-width:1320px; padding-top:1.4rem; padding-bottom:3rem; }
header[data-testid="stHeader"] { background:transparent; }
#MainMenu, footer { visibility:hidden; }
section[data-testid="stSidebar"] { background:#E1E8E3; border-right:1px solid var(--rule); }
section[data-testid="stSidebar"] .block-container { padding-top:1.2rem; }
@media (min-width:900px) { section[data-testid="stSidebar"][aria-expanded="true"] { width:350px !important; min-width:350px !important; } }

/* sidebar */
.wordmark { display:flex; align-items:center; gap:10px; font-family:var(--display); font-weight:700; font-size:1.15rem; letter-spacing:-0.01em; }
.side-h { font-size:.82rem; font-weight:600; color:var(--muted); margin:22px 0 6px; }
section[data-testid="stSidebar"] button[kind="primary"],
section[data-testid="stSidebar"] [data-testid="stBaseButton-primary"] {
  background:var(--red); border-color:var(--red); color:#fff; font-weight:600; }
section[data-testid="stSidebar"] button[kind="primary"]:hover,
section[data-testid="stSidebar"] [data-testid="stBaseButton-primary"]:hover { background:#B72A23; border-color:#B72A23; color:#fff; }

/* hero */
.hero { position:relative; background:var(--spruce); color:#EAF2EE; border-radius:14px; padding:26px 32px 22px; overflow:hidden; margin-bottom:30px; }
.hero::before { content:""; position:absolute; inset:0; background-image:url("__CONTOURS__"); background-size:cover; background-position:right center; pointer-events:none; }
.hero > * { position:relative; }
.hero-top { display:flex; justify-content:space-between; gap:16px; flex-wrap:wrap; font-size:.88rem; color:#9DB8AE; margin-bottom:34px; }
.hero-top b { color:#fff; font-family:var(--display); font-size:1rem; font-weight:600; }
.hero-grid { display:grid; grid-template-columns:minmax(0,5fr) minmax(0,6fr); gap:44px; align-items:end; }
.hero-title { font-family:var(--display); font-weight:700; font-size:2.3rem; line-height:1.06; letter-spacing:-0.02em; color:#fff; margin:0 0 12px; }
.hero-sub { color:#C3D6CE; font-size:1.02rem; max-width:34rem; }
.hero-scn { color:#8FAEA3; font-size:.88rem; margin-top:6px; max-width:34rem; }
.legend { display:flex; flex-wrap:wrap; gap:8px 22px; margin-top:22px; font-size:.9rem; color:#C3D6CE; }
.legend .sw { display:inline-block; width:10px; height:10px; border-radius:2px; margin-right:7px; }
.legend b { color:#fff; font-weight:600; margin-right:5px; }
.ribbon { position:relative; height:88px; display:flex; align-items:flex-end; gap:4px; border-bottom:1px solid rgba(255,255,255,.28); }
.ribbon .bar { flex:1; min-height:6px; border-radius:3px 3px 0 0; }
.ribbon .gl { position:absolute; left:0; right:0; border-top:1px dashed rgba(255,255,255,.3); }
.ribbon-ids { display:flex; gap:4px; margin-top:6px; font-size:.62rem; letter-spacing:-0.01em; color:#8FAEA3; }
.ribbon-ids span { flex:1; min-width:0; text-align:center; overflow:visible; white-space:nowrap; }
.ribbon-note { font-size:.78rem; color:#8FAEA3; margin-top:8px; }

/* section headings */
.sec { font-family:var(--display); font-weight:600; font-size:1.4rem; letter-spacing:-0.01em; margin:4px 0 2px; }
.sec-sub { color:var(--muted); font-size:.94rem; margin-bottom:14px; max-width:46rem; line-height:1.5; }

/* station table */
.tbl-wrap { max-height:540px; overflow:auto; border-top:1px solid var(--rule); }
.tbl { width:100%; border-collapse:collapse; font-size:.9rem; font-variant-numeric:tabular-nums; }
.tbl th { text-align:right; font-weight:500; font-size:.78rem; color:var(--muted); padding:8px 8px; position:sticky; top:0; background:var(--mist); }
.tbl th:first-child { text-align:left; }
.tbl td { text-align:right; padding:9px 8px; border-bottom:1px solid var(--rule); }
.tbl td.nm { text-align:left; border-left:4px solid var(--tc); padding-left:10px; }
.tbl td.nm b { display:block; font-weight:600; }
.tbl td.nm small { color:var(--muted); font-size:.78rem; }
.tbl tr.sel td { background:rgba(20,38,31,.07); }
.lsi { display:inline-block; min-width:44px; text-align:center; padding:2px 8px; border-radius:10px; font-weight:600; font-size:.82rem; }

/* station status */
.st-name { font-family:var(--display); font-weight:700; font-size:2rem; letter-spacing:-0.02em; margin:0 0 10px; }
.meta { display:grid; grid-template-columns:repeat(auto-fit,minmax(130px,1fr)); gap:12px 26px; margin-bottom:22px; }
.meta .k { font-size:.78rem; color:var(--muted); }
.meta .v { font-weight:600; }
.status { border-left:6px solid var(--tc); background:var(--bg); padding:16px 22px 14px; border-radius:0 10px 10px 0; margin-bottom:26px; }
.status .tier { display:flex; align-items:center; flex-wrap:wrap; gap:12px; }
.chip { display:inline-block; padding:3px 14px; border-radius:7px; font-family:var(--display); font-weight:700; line-height:1.3; }
.status .tier small { font-weight:500; font-size:1rem; color:var(--ink); }
.status .dir { margin-top:4px; max-width:48rem; }
.status .ttf { margin-top:8px; font-weight:600; color:#B72A23; }
.meter-wrap { position:relative; padding:6px 0; margin-top:12px; max-width:520px; }
.meter { display:flex; height:10px; border-radius:5px; overflow:hidden; }
.meter i { display:block; height:100%; }
.marker { position:absolute; top:0; width:4px; height:22px; background:var(--ink); border-radius:2px; transform:translateX(-50%); }
.meter-lbl { position:relative; height:16px; max-width:520px; font-size:.72rem; color:var(--muted); }
.meter-lbl span { position:absolute; transform:translateX(-50%); }

/* sensor bars */
.sensor { margin-bottom:20px; }
.s-head { display:flex; justify-content:space-between; align-items:baseline; font-weight:500; }
.s-val { font-family:var(--display); font-weight:700; font-size:1.35rem; font-variant-numeric:tabular-nums; }
.s-val small { font-family:'Public Sans',sans-serif; font-weight:400; font-size:.8rem; color:var(--muted); }
.track { position:relative; height:8px; background:#D5DDD7; border-radius:4px; margin:6px 0 4px; }
.track .fill { height:100%; border-radius:4px; }
.track .tick { position:absolute; top:-4px; width:2px; height:16px; background:var(--ink); }
.s-note { font-size:.78rem; color:var(--muted); }
.s-note.over { color:#B72A23; font-weight:600; }

/* stat rows */
.stat { display:flex; justify-content:space-between; gap:12px; padding:9px 0; border-bottom:1px solid var(--rule); }
.stat span { color:var(--muted); }
.stat b { font-variant-numeric:tabular-nums; text-align:right; }

/* alerts */
.msg { border-left:3px solid var(--rule); padding:2px 0 2px 14px; margin-bottom:16px; }
.msg .lang { font-size:.8rem; color:var(--muted); font-weight:600; }
.msg p { margin:2px 0 0; line-height:1.5; }

/* about */
.flow { display:grid; grid-template-columns:repeat(4,1fr); border-top:2px solid var(--ink); margin:8px 0 30px; }
.stage { padding:14px 18px 4px 0; }
.stage .n { display:inline-flex; align-items:center; justify-content:center; width:24px; height:24px; border-radius:50%; background:var(--ink); color:#fff; font-size:.78rem; font-weight:600; }
.stage h4 { font-family:var(--display); font-size:1.1rem; margin:8px 0 4px; padding:0; }
.stage p { font-size:.9rem; color:var(--muted); margin:0; line-height:1.5; }
.prose p, .prose li { line-height:1.6; max-width:42rem; }

/* tabs */
.stTabs [data-baseweb="tab-list"] { gap:26px; border-bottom:1px solid var(--rule); }
.stTabs [data-baseweb="tab"] { padding:10px 0; height:auto; background:transparent; color:var(--muted); font-weight:500; }
.stTabs [aria-selected="true"] { color:var(--ink); font-weight:600; }
.stTabs [data-baseweb="tab-highlight"] { background:var(--ink); height:3px; }
.stTabs [data-baseweb="tab-panel"] { padding-top:24px; }

.foot { color:var(--muted); font-size:.82rem; margin-top:40px; padding-top:14px; border-top:1px solid var(--rule); }

@media (max-width:900px) {
  .hero { padding:20px; }
  .hero-grid { grid-template-columns:1fr; gap:26px; }
  .hero-title { font-size:2rem; }
  .flow { grid-template-columns:1fr 1fr; }
}
</style>
""".replace("__CONTOURS__", contour_uri())
st.markdown(CSS, unsafe_allow_html=True)


# --------------------------------------------------------------------------
# Backend
# --------------------------------------------------------------------------
@st.cache_resource
def load_system_core():
    predictor = LandslidePredictor()
    simulator = IoTSimulator(predictor)
    dispatcher = EWSDispatcher()
    vision_analyzer = DroneSlopeAnalyzer()
    # Time the real model so the About tab reports a measured figure.
    probe = {"slope_deg": 40, "rainfall_24h": 120, "rainfall_72h_ari": 250, "rainfall_intensity_max": 20,
             "soil_moisture_pct": 70, "pore_water_pressure_kpa": 30, "displacement_rate_mm_day": 3,
             "lithology_factor": 3, "elevation_m": 1200, "ndvi": 0.5, "seismic_pga_g": 0.05}
    predictor.predict_risk(probe)
    runs = []
    for _ in range(15):
        t0 = time.perf_counter()
        predictor.predict_risk(probe)
        runs.append((time.perf_counter() - t0) * 1000)
    return predictor, simulator, dispatcher, vision_analyzer, statistics.median(runs)


predictor, simulator, dispatcher, vision_analyzer, latency_ms = load_system_core()

# Readings hold steady between interactions; "Refresh readings" draws a new set.
if "tick" not in st.session_state:
    st.session_state["tick"] = 0

# --------------------------------------------------------------------------
# Sidebar
# --------------------------------------------------------------------------
scenario_keys = list(SCENARIOS.keys())
scenario_labels = [SCENARIOS[k]["title"] for k in scenario_keys] + [CUSTOM_LABEL]

with st.sidebar:
    md(
        '<div class="wordmark">'
        '<svg width="30" height="30" viewBox="0 0 30 30" fill="none">'
        '<rect width="30" height="30" rx="7" fill="#0D2A25"/>'
        '<path d="M4 22 L12 10 L16 16 L19 12 L26 22 Z" fill="#8FD0B8"/></svg>'
        "NER Landslide EWS</div>"
    )

    md('<div class="side-h">Scenario</div>')
    selected_scenario_label = st.selectbox(
        "Scenario",
        scenario_labels,
        index=1,
        format_func=clean_title,
        label_visibility="collapsed",
    )
    is_custom = selected_scenario_label == CUSTOM_LABEL
    if is_custom:
        selected_scenario_key = "baseline"
        st.caption("Set the sensor values below. Every tab updates with them.")
    else:
        selected_scenario_key = next(k for k in scenario_keys if SCENARIOS[k]["title"] == selected_scenario_label)
        st.caption(SCENARIOS[selected_scenario_key]["description"])

    if st.button("Refresh readings", **FILL):
        st.session_state["tick"] += 1
    st.caption("Readings hold steady while you work. Refresh draws a new set.")

    md('<div class="side-h">Station</div>')
    station_lookup = {s["id"]: s for s in NER_STATIONS}
    selected_station_id = st.selectbox(
        "Station",
        list(station_lookup),
        index=2,
        format_func=lambda i: f"{station_lookup[i]['name']}, {station_lookup[i]['state']}",
        label_visibility="collapsed",
    )
    selected_station_meta = station_lookup[selected_station_id]

    custom_overrides = None
    if is_custom:
        md('<div class="side-h">Sensor values</div>')
        c_rain = st.slider("24-hour rainfall (mm)", 0.0, 350.0, 220.0, 5.0)
        c_slope = st.slider("Slope angle (°)", 15.0, 65.0, float(selected_station_meta["slope_deg"]), 0.5)
        c_moist = st.slider("Soil moisture (%)", 15.0, 98.0, 88.0, 1.0)
        c_pwp = st.slider("Pore water pressure (kPa)", 0.0, 80.0, 52.0, 1.0)
        c_disp = st.slider("Displacement rate (mm/day)", 0.0, 35.0, 12.5, 0.5)
        c_pga = st.slider("Seismic PGA (g)", 0.01, 0.45, 0.08, 0.01)
        custom_overrides = {
            "stn_id": selected_station_id,
            "rainfall_24h": c_rain,
            "slope_deg": c_slope,
            "soil_moisture_pct": c_moist,
            "pore_water_pressure_kpa": c_pwp,
            "displacement_rate_mm_day": c_disp,
            "seismic_pga_g": c_pga,
        }

    md('<div class="side-h">Emergency</div>')
    siren_triggered = st.button("Sound siren and broadcast alert", type="primary", **FILL)
    if siren_triggered:
        st.success("Demo broadcast sent to SACHET and SDRF.")
        st.markdown(
            '<audio autoplay><source src="https://actions.google.com/sounds/v1/alarms/alarm_clock.ogg" type="audio/ogg"></audio>',
            unsafe_allow_html=True,
        )

np.random.seed(zlib.crc32(f"{selected_scenario_key}-{st.session_state['tick']}".encode()))
all_telemetry = simulator.get_all_stations_telemetry(
    scenario_key=selected_scenario_key,
    custom_overrides=custom_overrides,
)
active = next(t for t in all_telemetry if t["station_id"] == selected_station_id)
scenario_name = clean_title(selected_scenario_label)
sb_suffix = f"{selected_scenario_key}_{'custom' if is_custom else 'preset'}_{selected_station_id}"

# --------------------------------------------------------------------------
# Hero
# --------------------------------------------------------------------------
counts = {t: sum(1 for x in all_telemetry if x["tier"] == t) for t in TIER_ORDER}
peak = max(all_telemetry, key=lambda x: x["lsi"])
mean_rain = float(np.mean([x["rainfall_24h"] for x in all_telemetry]))

if counts["RED"]:
    headline = f"Evacuation advised at {plural(counts['RED'], 'station')}"
elif counts["ORANGE"]:
    headline = f"High alert at {plural(counts['ORANGE'], 'station')}"
elif counts["YELLOW"]:
    headline = f"{plural(counts['YELLOW'], 'station')} on advisory"
else:
    headline = "All stations within normal range"

peak_line = f"{esc(peak['station_name'])}, {esc(peak['state'])} has the highest index at {fmt(peak['lsi'], 2)}."

ranked = sorted(all_telemetry, key=lambda x: x["lsi"], reverse=True)
bars = "".join(
    f'<div class="bar" title="{esc(x["station_name"])}: {fmt(x["lsi"], 2)}" '
    f'style="height:{max(min(float(x["lsi"]), 1) * 100, 4):.1f}%;background:{tier_color(x["tier"], x["color"])}"></div>'
    for x in ranked
)
gridlines = "".join(f'<div class="gl" style="bottom:{b * 100:.0f}%"></div>' for b in LSI_BANDS)
ids = "".join(f"<span>{esc(str(x['station_id']).replace('STN-', ''))}</span>" for x in ranked)
legend = "".join(
    f'<span><i class="sw" style="background:{TIER_COLOR[t]}"></i><b>{counts[t]}</b>{t.capitalize()}</span>'
    for t in TIER_ORDER
)

md(
    f"""
<div class="hero">
  <div class="hero-top">
    <b>NER Landslide Early Warning</b>
    <span>{len(all_telemetry)} stations reporting over LoRaWAN, 865 MHz</span>
  </div>
  <div class="hero-grid">
    <div>
      <div class="hero-title">{headline}</div>
      <div class="hero-sub">{peak_line}</div>
      <div class="hero-scn">{esc(scenario_name)}</div>
      <div class="legend">{legend}<span>Mean 24-hour rainfall <b style="margin-left:5px">{mean_rain:.0f} mm</b></span></div>
    </div>
    <div>
      <div class="ribbon">{gridlines}{bars}</div>
      <div class="ribbon-ids">{ids}</div>
      <div class="ribbon-note">Bar height is each station's susceptibility index, highest first. Dashed lines mark the yellow, orange and red thresholds.</div>
    </div>
  </div>
</div>
"""
)

tab_map, tab_station, tab_sandbox, tab_vision, tab_alerts, tab_about = st.tabs(
    ["Map", "Station", "Sandbox", "Drone imagery", "Alerts", "About"]
)

# --------------------------------------------------------------------------
# Map
# --------------------------------------------------------------------------
with tab_map:
    section(
        "Hazard map",
        "Pins show each station's susceptibility index. Shaded circles mark evacuation and standby zones. "
        "Choose a station in the sidebar to open it in the Station tab.",
    )
    col_map, col_tbl = st.columns([3, 2], gap="large")

    with col_map:
        key = carto_key()
        if key:
            fmap = folium.Map(tiles=None, control_scale=True, zoom_control=True)
            folium.TileLayer(
                tiles=f"https://basemaps.cartocdn.com/rastertiles/voyager/{{z}}/{{x}}/{{y}}.png?key={key}",
                attr="&copy; OpenStreetMap contributors &copy; CARTO",
                max_zoom=19,
            ).add_to(fmap)
        else:
            fmap = folium.Map(tiles="OpenStreetMap", control_scale=True, zoom_control=True)
        lats = [t["lat"] for t in all_telemetry]
        lons = [t["lon"] for t in all_telemetry]
        fmap.fit_bounds([[min(lats), min(lons)], [max(lats), max(lons)]], padding=(40, 40))

        fmap.get_root().html.add_child(
            folium.Element(
                """
<style>
.leaflet-tile-pane { filter:grayscale(1) contrast(.92) brightness(1.04); }
.ner-pin span { display:block; min-width:42px; height:26px; line-height:22px; text-align:center; border-radius:13px;
  border:2px solid #fff; font:700 12px/22px 'Public Sans',system-ui,sans-serif; box-shadow:0 1px 4px rgba(0,0,0,.35); }
.ner-pin.sel span { outline:3px solid #14261F; outline-offset:1px; }
.ner-pin.RED span { animation:pulse 1.8s ease-out infinite; }
@keyframes pulse { 0% { box-shadow:0 0 0 0 rgba(214,52,44,.55);} 100% { box-shadow:0 0 0 16px rgba(214,52,44,0);} }
@media (prefers-reduced-motion: reduce) { .ner-pin.RED span { animation:none; } }
</style>
"""
            )
        )

        for stn in all_telemetry:
            col = tier_color(stn["tier"], stn["color"])
            if stn["tier"] in ("RED", "ORANGE"):
                folium.Circle(
                    location=[stn["lat"], stn["lon"]],
                    radius=12000 if stn["tier"] == "RED" else 6000,
                    color=col, weight=1, fill=True, fill_color=col, fill_opacity=0.18,
                ).add_to(fmap)

            popup = (
                f"<div style=\"font-family:'Public Sans',Arial,sans-serif;width:220px;color:#14261F\">"
                f"<div style='font-weight:700;font-size:15px'>{esc(stn['station_name'])}</div>"
                f"<div style='color:#5A6B63;font-size:12px;margin-bottom:6px'>{esc(stn['district'])}, {esc(stn['state'])}</div>"
                f"<div style='font-weight:700;color:{col}'>{esc(stn['tier'])}, index {fmt(stn['lsi'], 2)}</div>"
                f"<div style='font-size:13px;line-height:1.6'>"
                f"Rainfall (24 h): {fmt(stn['rainfall_24h'])} mm<br>"
                f"Pore pressure: {fmt(stn['pore_water_pressure_kpa'])} kPa<br>"
                f"Displacement: {fmt(stn['displacement_rate_mm_day'])} mm/day<br>"
                f"Slope: {fmt(stn['slope_deg'], 0)}°</div>"
                f"<div style='margin-top:6px;padding:6px 8px;background:#EDF1EE;border-radius:4px;font-size:12px'>{esc(stn['action_code'])}</div>"
                f"</div>"
            )
            sel = " sel" if stn["station_id"] == selected_station_id else ""
            pin = (
                f'<div class="ner-pin {stn["tier"]}{sel}"><span style="background:{col};color:{TIER_TEXT.get(stn["tier"], "#fff")}">'
                f'{fmt(stn["lsi"], 2)}</span></div>'
            )
            folium.Marker(
                location=[stn["lat"], stn["lon"]],
                popup=folium.Popup(popup, max_width=260),
                tooltip=f"{stn['station_name']} ({stn['state']})",
                icon=folium.DivIcon(html=pin, icon_size=(46, 28), icon_anchor=(23, 14), class_name="ner-pin-wrap"),
            ).add_to(fmap)

        st_folium(fmap, width="100%", height=540, returned_objects=[])

    with col_tbl:
        rows = []
        for t in ranked:
            c = tier_color(t["tier"], t["color"])
            sel = " sel" if t["station_id"] == selected_station_id else ""
            rows.append(
                f'<tr class="{sel.strip()}" style="--tc:{c}">'
                f'<td class="nm"><b>{esc(t["station_name"])}</b><small>{esc(t["state"])}</small></td>'
                f'<td><span class="lsi" style="background:{c};color:{TIER_TEXT.get(t["tier"], "#fff")}">{fmt(t["lsi"], 2)}</span></td>'
                f'<td>{fmt(t["rainfall_24h"], 0)}</td>'
                f'<td>{fmt(t["pore_water_pressure_kpa"], 0)}</td>'
                f'<td>{fmt(t["displacement_rate_mm_day"])}</td></tr>'
            )
        md(
            '<div class="tbl-wrap"><table class="tbl"><thead><tr>'
            "<th>Station</th><th>Index</th><th>Rain mm</th><th>Pore kPa</th><th>Disp mm/d</th>"
            "</tr></thead><tbody>" + "".join(rows) + "</tbody></table></div>"
        )

# --------------------------------------------------------------------------
# Station
# --------------------------------------------------------------------------
with tab_station:
    tc = tier_color(active["tier"], active["color"])
    ttf = active.get("ttf_hours")
    ttf_html = (
        f'<div class="ttf">Estimated time to failure: about {esc(ttf)} hours (Saito inverse-velocity method)</div>'
        if ttf else ""
    )

    md(
        f"""
<div class="st-name">{esc(active['station_name'])}</div>
<div class="meta">
  <div><div class="k">State</div><div class="v">{esc(active['state'])}</div></div>
  <div><div class="k">District</div><div class="v">{esc(active['district'])}</div></div>
  <div><div class="k">Elevation</div><div class="v">{fmt(active['elevation_m'], 0)} m</div></div>
  <div><div class="k">Slope</div><div class="v">{fmt(active['slope_deg'], 0)}°</div></div>
  <div><div class="k">Lithology</div><div class="v">{esc(active['lithology'])}</div></div>
</div>
<div class="status" style="--tc:{tc};--bg:{rgba(tc, 0.1)}">
  <div class="tier">{chip(active['tier'].capitalize(), active['tier'])}<small>{esc(active['tier_label'])}</small></div>
  <div class="dir">{esc(active['action_code'])}</div>
  {ttf_html}
  {meter_html(active['lsi'])}
</div>
"""
    )

    section("Sensor readings", "The black tick on each bar is the level where the model starts to flag this sensor.")
    sc1, sc2 = st.columns(2, gap="large")
    with sc1:
        md(sensor_html("24-hour rainfall", active["rainfall_24h"], "mm", 150, 350))
        md(sensor_html("Pore water pressure", active["pore_water_pressure_kpa"], "kPa", 45, 80))
    with sc2:
        md(sensor_html("Soil moisture", active["soil_moisture_pct"], "%", 85, 100))
        md(sensor_html("Displacement rate", active["displacement_rate_mm_day"], "mm/day", 8, 30))

    st.write("")
    c_trend, c_factors = st.columns([3, 2], gap="large")

    with c_trend:
        section("Last 24 hours", "Hourly rain against pore pressure and slope movement.")
        np.random.seed(zlib.crc32(f"{active['station_id']}-{st.session_state['tick']}".encode()))
        df_24h = simulator.generate_24h_history(active)
        fig = go.Figure()
        fig.add_trace(go.Bar(x=df_24h["Time"], y=df_24h["Rainfall_mm"], name="Rain (mm/h)", marker_color="rgba(79,124,172,.55)"))
        fig.add_trace(go.Scatter(x=df_24h["Time"], y=df_24h["Pore_Pressure_kPa"], name="Pore pressure (kPa)",
                                 line=dict(color="#6B4E9B", width=3), yaxis="y2"))
        fig.add_trace(go.Scatter(x=df_24h["Time"], y=df_24h["Displacement_mm_day"], name="Displacement (mm/day)",
                                 line=dict(color=INK, width=2.5, dash="dot"), yaxis="y2"))
        style_fig(fig, 340)
        fig.update_layout(
            yaxis=dict(title="Rain (mm/h)"),
            yaxis2=dict(title="kPa and mm/day", overlaying="y", side="right", showgrid=False),
        )
        plot(fig)

    with c_factors:
        section("Why this score", "The inputs that contribute most to this score. A green bar, when one appears, is holding risk down.")
        factors = pd.DataFrame(active["top_factors"])
        if not factors.empty:
            fig_f = px.bar(
                factors, x="score", y="factor", orientation="h", color="direction",
                color_discrete_map={"Aggravating": TIER_COLOR["RED"], "Mitigating": TIER_COLOR["GREEN"]},
                labels={"score": "Contribution", "factor": ""},
            )
            style_fig(fig_f, 340)
            fig_f.update_layout(showlegend=False, yaxis=dict(autorange="reversed"))
            plot(fig_f)
        else:
            st.info("No factor breakdown is available for this station.")

    section(
        "Rainfall intensity and duration",
        "A storm above the line has historically triggered slides in the Eastern Himalaya "
        "(I = 14.82 × D<sup>-0.39</sup>).",
    )
    durations = np.linspace(1, 72, 80)
    critical = 14.82 * durations ** -0.39
    now_i = float(active["actual_mean_intensity"])
    ymax = max(float(critical.max()), now_i * 1.3)
    fig_id = go.Figure()
    fig_id.add_trace(go.Scatter(x=durations, y=critical, mode="lines", name="Threshold", line=dict(color=INK, width=3)))
    fig_id.add_trace(go.Scatter(x=[1, 72], y=[ymax, ymax], mode="lines", line=dict(width=0), fill="tonexty",
                                fillcolor="rgba(214,52,44,.09)", name="Failure-prone", hoverinfo="skip"))
    fig_id.add_trace(go.Scatter(x=[24], y=[now_i], mode="markers", name="This station, 24 h",
                                marker=dict(color=tc, size=16, symbol="diamond", line=dict(color="white", width=2))))
    style_fig(fig_id, 300)
    fig_id.update_layout(xaxis_title="Storm duration (hours)", yaxis_title="Mean intensity (mm/h)")
    fig_id.update_yaxes(range=[0, ymax])
    plot(fig_id)

# --------------------------------------------------------------------------
# Sandbox
# --------------------------------------------------------------------------
with tab_sandbox:
    section(
        "Sensor sandbox",
        f"Change any value for {esc(active['station_name'])} and the model re-scores it immediately.",
    )
    sb_left, sb_right = st.columns(2, gap="large")

    with sb_left:
        sb_rain = st.slider("24-hour rainfall (mm)", 0.0, 350.0, float(active["rainfall_24h"]), 5.0, key=f"sb_rain_{sb_suffix}")
        sb_slope = st.slider("Slope angle (°)", 15.0, 65.0, float(active["slope_deg"]), 1.0, key=f"sb_slope_{sb_suffix}")
        sb_pwp = st.slider("Pore water pressure (kPa)", 0.0, 85.0, float(active["pore_water_pressure_kpa"]), 1.0, key=f"sb_pwp_{sb_suffix}")
        sb_disp = st.slider("Displacement rate (mm/day)", 0.0, 35.0, float(active["displacement_rate_mm_day"]), 0.5, key=f"sb_disp_{sb_suffix}")
        sb_moist = st.slider("Soil moisture (%)", 15.0, 99.0, float(active["soil_moisture_pct"]), 1.0, key=f"sb_moist_{sb_suffix}")
        sb_pga = st.slider("Peak ground acceleration (g)", 0.01, 0.45, float(active["seismic_pga_g"]), 0.01, key=f"sb_pga_{sb_suffix}")

    with sb_right:
        result = predictor.predict_risk({
            "slope_deg": sb_slope,
            "rainfall_24h": sb_rain,
            "rainfall_72h_ari": sb_rain * 2.1,
            "rainfall_intensity_max": sb_rain * 0.18,
            "soil_moisture_pct": sb_moist,
            "pore_water_pressure_kpa": sb_pwp,
            "displacement_rate_mm_day": sb_disp,
            "lithology_factor": active["lithology_factor"],
            "elevation_m": active["elevation_m"],
            "ndvi": active["ndvi"],
            "seismic_pga_g": sb_pga,
        })
        rc = tier_color(result["tier"], result["color"])
        md(
            f"""
<div class="status" style="--tc:{rc};--bg:{rgba(rc, 0.1)}">
  <div class="tier">{chip(result['tier'].capitalize(), result['tier'])}<small>{esc(result['tier_label'])}</small></div>
  <div style="font-family:var(--display);font-weight:700;font-size:3rem;line-height:1.1;margin-top:6px">{fmt(result['lsi'], 2)}<span style="font-size:1.1rem;font-weight:500;color:var(--muted)"> / 1.00</span></div>
  {meter_html(result['lsi'])}
  <div class="dir" style="margin-top:10px">{esc(result['action_code'])}</div>
</div>
"""
        )
        breached = "Exceeded" if result["id_threshold_breached"] else "Within limit"
        ttf_val = f"about {result['ttf_hours']} hours" if result["ttf_hours"] else "Not applicable, slope is stable"
        md(stat_html("Rainfall intensity threshold", breached) + stat_html("Estimated time to failure", ttf_val))

# --------------------------------------------------------------------------
# Drone imagery
# --------------------------------------------------------------------------
with tab_vision:
    section(
        "Drone imagery",
        "Checks aerial photos for surface cracks, bare ground and vegetation loss, "
        "then combines the result with the station's sensor index.",
    )
    v_left, v_right = st.columns(2, gap="large")

    PRESETS = {
        "Intact forested slope, Sikkim valley (stable)": "sample_stable_slope.jpg",
        "Developing tension cracks, NH-10 rock cutting": "sample_tension_crack_slope.jpg",
        "Severe scarp fracture, Tupul valley": "sample_severe_collapse_scarp.jpg",
    }
    image = None
    with v_left:
        source = st.radio("Image source", ["Sample surveys", "Upload an image"], horizontal=True)
        if source == "Sample surveys":
            choice = st.selectbox("Survey", list(PRESETS.keys()))
            path = os.path.join(os.path.dirname(__file__), "data", "sample_drone_images", PRESETS[choice])
            if os.path.exists(path):
                image = Image.open(path)
            else:
                st.info(f"Sample image not found. Add {PRESETS[choice]} to data/sample_drone_images.")
        else:
            up = st.file_uploader("Aerial photo (JPG or PNG)", type=["jpg", "jpeg", "png"])
            if up:
                image = Image.open(up)
        if image:
            st.image(image, caption="Original photo", **FILL)

    with v_right:
        if image:
            v = vision_analyzer.analyze_image(image)
            vtier = VISION_TIER.get(v["tier"], "GREEN")
            vc = tier_color(vtier, v["color"])
            st.image(v["annotated_image"], caption="Detected cracks highlighted in red", **FILL)
            md(
                f"""
<div class="status" style="--tc:{vc};--bg:{rgba(vc, 0.1)};margin-top:14px">
  <div class="tier">{chip(v['tier'].capitalize(), vtier)}<small>Visual index {fmt(v['vii_score'], 2)}</small></div>
  <div class="dir">{esc(v['diagnosis'])}</div>
</div>
"""
            )
            md(
                stat_html("Crack density", f"{v['crack_density_pct']}%")
                + stat_html("Bare earth and debris", f"{v['bare_soil_pct']}%")
                + stat_html("Vegetation cover", f"{v['vegetation_pct']}%")
            )
            fused = round(0.65 * active["lsi"] + 0.35 * v["vii_score"], 3)
            ftier = "RED" if fused >= 0.60 else "GREEN"
            verdict = "Hazardous" if fused >= 0.60 else "Stable"
            st.write("")
            section(
                f"Combined risk at {esc(active['station_name'])}",
                "Weights the sensor index at 65% and the visual index at 35%.",
            )
            md(
                f'<div style="font-family:var(--display);font-weight:700;font-size:2.6rem;line-height:1.1">{fmt(fused, 2)}'
                f'<span style="font-size:1.1rem;font-weight:500;color:var(--muted)"> / 1.00</span>'
                f'<span style="margin-left:14px">{chip(verdict, ftier, "1rem")}</span></div>'
                + meter_html(fused)
            )
        else:
            st.info("Choose a sample survey or upload a photo to start the inspection.")

# --------------------------------------------------------------------------
# Alerts
# --------------------------------------------------------------------------
with tab_alerts:
    section(
        "Alerts and dispatch",
        f"Community messages and the CAP v1.2 payload for {esc(active['station_name'])}.",
    )
    a_left, a_right = st.columns(2, gap="large")

    with a_left:
        md('<div class="sec" style="font-size:1.1rem">Community messages</div>')
        messages = dispatcher.get_multilingual_messages(active)
        md("".join(f'<div class="msg"><div class="lang">{esc(lang)}</div><p>{esc(msg)}</p></div>' for lang, msg in messages.items()))

        md('<div class="sec" style="font-size:1.1rem;margin-top:18px">Response checklist</div>')
        tier = active["tier"]
        key = f"{sb_suffix}_{tier}"
        st.checkbox("Sirens sounded along vulnerable corridors", value=(tier == "RED"), key=f"c1_{key}")
        st.checkbox("Highway police halted traffic on NH-10, NH-6 and NH-29", value=(tier in ("RED", "ORANGE")), key=f"c2_{key}")
        st.checkbox("SDRF and NDRF teams deployed", value=(tier in ("RED", "ORANGE")), key=f"c3_{key}")
        st.checkbox("Village committees notified on WhatsApp", value=True, key=f"c4_{key}")

    with a_right:
        md('<div class="sec" style="font-size:1.1rem">NDMA SACHET payload (CAP v1.2)</div>')
        st.json(dispatcher.generate_cap_alert(active), expanded=1)

        md('<div class="sec" style="font-size:1.1rem;margin-top:18px">Situation report</div>')
        st.caption("All stations for the current scenario, ready for district disaster authorities.")
        st.download_button(
            "Download situation report (.md)",
            data=dispatcher.generate_sitrep_markdown(all_telemetry, selected_scenario_label),
            file_name=f"NER_Landslide_SITREP_{selected_station_id}.md",
            mime="text/markdown",
            **FILL,
        )

# --------------------------------------------------------------------------
# About
# --------------------------------------------------------------------------
with tab_about:
    section("How the system works")
    md(
        """
<div class="flow">
  <div class="stage"><span class="n">1</span><h4>Sense</h4><p>Rain gauges, soil moisture probes, piezometers, inclinometers and geophones on the slope.</p></div>
  <div class="stage"><span class="n">2</span><h4>Relay</h4><p>Solar ESP32 nodes send readings over LoRaWAN, with 4G as backup when the mesh is down.</p></div>
  <div class="stage"><span class="n">3</span><h4>Assess</h4><p>A random forest scores each slope, checked against rainfall thresholds and a time-to-failure estimate.</p></div>
  <div class="stage"><span class="n">4</span><h4>Alert</h4><p>CAP v1.2 alerts, multilingual SMS and WhatsApp messages, sirens and a situation report.</p></div>
</div>
"""
    )

    ab_left, ab_right = st.columns(2, gap="large")
    with ab_left:
        section("Why the North East")
        md(
            """
<div class="prose"><ul>
<li>Cherrapunji and Mawsynram receive more than 11,000 mm of rain a year, which saturates slopes quickly.</li>
<li>The region lies in seismic zones IV and V, so tremors weaken steep road and rail cuttings.</li>
<li>One blocked highway can cut off a state. Sikkim depends on NH-10, and the Kohima corridor on NH-29.</li>
</ul></div>
"""
        )
        section("What the model uses")
        md(
            """
<div class="prose"><ul>
<li><b>Random forest.</b> Rainfall history, slope, soil moisture, pore pressure, tilt velocity, lithology, elevation, vegetation and ground shaking go in. A 0 to 1 susceptibility index comes out.</li>
<li><b>Rainfall threshold.</b> An empirical intensity and duration curve for the Eastern Himalaya.</li>
<li><b>Saito inverse velocity.</b> When a slope accelerates, the trend is extended to estimate hours to failure.</li>
</ul></div>
"""
        )
    with ab_right:
        section("Model", "Read from the trained model file. The training and test data are synthetic.")
        m = predictor.metrics or {}
        rows = []
        if "roc_auc" in m:
            rows.append(("ROC-AUC on held-out synthetic data", f"{m['roc_auc']}"))
        if "accuracy" in m:
            rows.append(("Accuracy on held-out synthetic data", f"{float(m['accuracy']) * 100:.1f}%"))
        if "samples" in m:
            rows.append(("Synthetic samples generated", f"{m['samples']:,}"))
        rows.append(("Median inference time (measured now)", f"{latency_ms:.0f} ms"))
        md("".join(stat_html(k, v) for k, v in rows))
        st.write("")
        section("Alert levels")
        md(
            "".join(
                f'<div class="stat"><span><i class="sw" style="display:inline-block;width:10px;height:10px;border-radius:2px;margin-right:8px;background:{TIER_COLOR[t]}"></i>{t.capitalize()}</span><b>{label}</b></div>'
                for t, label in (
                    ("GREEN", "Index below 0.35"),
                    ("YELLOW", "0.35 to 0.60"),
                    ("ORANGE", "0.60 to 0.80"),
                    ("RED", "0.80 and above"),
                )
            )
        )

md('<div class="foot">AI-Based Landslide Early Warning and Risk Monitoring System for the North Eastern Region of India. Tech Expo edition.</div>')
