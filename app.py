"""
SR3 SOFR FUTURES TERMINAL
Bloomberg-style professional trading dashboard for CME Three-Month SOFR Futures
"""

import streamlit as st
import pandas as pd
import numpy as np
from datetime import date, datetime, timedelta
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import calendar
import json
import io
import requests
import time

from sr3_engine import (
    get_active_sr3_contracts, price_all_contracts, price_sr3_contract,
    build_impact_matrix, calculate_fomc_weightage, DEFAULT_FOMC_DATES_2026_2027,
    build_default_scenarios, calculate_pnl, calculate_spread, calculate_butterfly,
    estimate_convexity_adj, implied_term_sofr, build_daily_sofr_path,
    get_third_wednesday, CONTRACT_MONTH_NAMES, CONTRACT_MONTH_CODES,
    calculate_carry, is_business_day, get_sr3_reference_period
)

# ─────────────────────────────────────────────
# PAGE CONFIGURATION
# ─────────────────────────────────────────────

st.set_page_config(
    page_title="SR3 SOFR Terminal",
    page_icon="🟧",
    layout="wide",
    initial_sidebar_state="collapsed",
    menu_items={"Get help": None, "Report a bug": None, "About": None}
)

# ─────────────────────────────────────────────
# BLOOMBERG TERMINAL CSS
# ─────────────────────────────────────────────

BLOOMBERG_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@300;400;500;600;700&family=Bebas+Neue&display=swap');

:root {
    --bb-bg:       #0a0a0a;
    --bb-panel:    #101010;
    --bb-card:     #141414;
    --bb-border:   #1f1f1f;
    --bb-border2:  #2a2a2a;
    --bb-orange:   #ff6d00;
    --bb-orange2:  #ff9100;
    --bb-blue:     #00b4d8;
    --bb-blue2:    #90e0ef;
    --bb-green:    #00e676;
    --bb-green2:   #69f0ae;
    --bb-red:      #ff1744;
    --bb-red2:     #ff5252;
    --bb-yellow:   #ffd600;
    --bb-magenta:  #e040fb;
    --bb-text:     #d4d4d4;
    --bb-text2:    #888888;
    --bb-text3:    #555555;
    --bb-white:    #f0f0f0;
}

* { box-sizing: border-box; }

html, body { 
    background-color: var(--bb-bg) !important;
    font-family: 'JetBrains Mono', 'Courier New', monospace !important;
}

/* Streamlit root overrides */
.stApp {
    background-color: var(--bb-bg) !important;
}

section[data-testid="stSidebar"] {
    background-color: #080808 !important;
    border-right: 1px solid var(--bb-border2);
}

/* Remove default Streamlit header padding */
.block-container {
    padding-top: 0.5rem !important;
    padding-bottom: 1rem !important;
    max-width: 100% !important;
}

/* Tab styling */
.stTabs [data-baseweb="tab-list"] {
    background-color: var(--bb-panel) !important;
    border-bottom: 2px solid var(--bb-orange) !important;
    gap: 0 !important;
}

.stTabs [data-baseweb="tab"] {
    background-color: transparent !important;
    color: var(--bb-text2) !important;
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 0.72rem !important;
    font-weight: 600 !important;
    letter-spacing: 0.1em !important;
    text-transform: uppercase !important;
    padding: 0.5rem 1.2rem !important;
    border: none !important;
    border-right: 1px solid var(--bb-border2) !important;
}

.stTabs [aria-selected="true"] {
    background-color: var(--bb-orange) !important;
    color: #000000 !important;
    font-weight: 700 !important;
}

.stTabs [data-baseweb="tab-panel"] {
    background-color: var(--bb-bg) !important;
    padding: 0 !important;
}

/* DataFrames */
.stDataFrame {
    background-color: var(--bb-panel) !important;
}

.stDataFrame [data-testid="stTable"] {
    background-color: var(--bb-panel) !important;
}

/* Input widgets */
.stNumberInput input, .stTextInput input, .stSelectbox select {
    background-color: var(--bb-card) !important;
    color: var(--bb-orange) !important;
    border: 1px solid var(--bb-border2) !important;
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 0.85rem !important;
}

.stSlider [data-baseweb="slider"] {
    margin-top: 0.2rem !important;
}

/* Selectbox */
.stSelectbox [data-baseweb="select"] {
    background-color: var(--bb-card) !important;
    border-color: var(--bb-border2) !important;
}

/* Buttons */
.stButton > button {
    background-color: var(--bb-orange) !important;
    color: #000000 !important;
    font-family: 'JetBrains Mono', monospace !important;
    font-weight: 700 !important;
    font-size: 0.75rem !important;
    letter-spacing: 0.08em !important;
    text-transform: uppercase !important;
    border: none !important;
    border-radius: 0 !important;
    padding: 0.4rem 1rem !important;
    transition: background-color 0.1s;
}

.stButton > button:hover {
    background-color: var(--bb-orange2) !important;
}

/* Labels */
label, .stLabel, p {
    font-family: 'JetBrains Mono', monospace !important;
    color: var(--bb-text2) !important;
    font-size: 0.75rem !important;
}

h1, h2, h3, h4, h5, h6 {
    font-family: 'Bebas Neue', 'JetBrains Mono', monospace !important;
    color: var(--bb-orange) !important;
}

/* Metric */
[data-testid="metric-container"] {
    background-color: var(--bb-card) !important;
    border: 1px solid var(--bb-border2) !important;
    padding: 0.5rem !important;
}

[data-testid="stMetricValue"] {
    color: var(--bb-white) !important;
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 1.2rem !important;
    font-weight: 700 !important;
}

[data-testid="stMetricLabel"] {
    color: var(--bb-text2) !important;
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 0.65rem !important;
    text-transform: uppercase !important;
    letter-spacing: 0.1em !important;
}

[data-testid="stMetricDelta"] {
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 0.75rem !important;
}

/* Custom scrollbar */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: var(--bb-bg); }
::-webkit-scrollbar-thumb { background: var(--bb-border2); }
::-webkit-scrollbar-thumb:hover { background: var(--bb-text3); }

/* Divider */
hr { border-color: var(--bb-border2) !important; margin: 0.5rem 0 !important; }

/* Checkbox */
.stCheckbox { color: var(--bb-text2) !important; }
.stCheckbox label { font-size: 0.75rem !important; }

/* Column gaps */
.element-container { margin-bottom: 0.3rem !important; }

/* Warning/info/success */
.stAlert { 
    background-color: var(--bb-card) !important; 
    border-left: 3px solid var(--bb-orange) !important;
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 0.75rem !important;
}
</style>
"""

st.markdown(BLOOMBERG_CSS, unsafe_allow_html=True)

# ─────────────────────────────────────────────
# HTML COMPONENT BUILDERS
# ─────────────────────────────────────────────

def bb_header():
    now = datetime.now()
    dt_str = now.strftime("%a %d %b %Y  %H:%M:%S")
    session = "PRE-MKT" if now.hour < 9 else ("MARKET" if now.hour < 17 else "POST-MKT")
    session_color = "#ffd600" if session != "MARKET" else "#00e676"

    return f"""
    <div style="background:#050505;border-bottom:2px solid #ff6d00;padding:6px 12px;
                display:flex;align-items:center;justify-content:space-between;
                font-family:'JetBrains Mono',monospace;margin-bottom:8px;
                position:sticky;top:0;z-index:100;">
        <div style="display:flex;align-items:center;gap:20px;">
            <span style="color:#ff6d00;font-family:'Bebas Neue',monospace;font-size:1.4rem;
                         letter-spacing:0.15em;font-weight:700;">◈ SR3 SOFR TERMINAL</span>
            <span style="color:#555;font-size:0.65rem;">CME THREE-MONTH SOFR FUTURES · ADVANCED ANALYTICS</span>
        </div>
        <div style="display:flex;align-items:center;gap:24px;">
            <span style="color:{session_color};font-size:0.7rem;font-weight:700;
                         border:1px solid {session_color};padding:2px 6px;">● {session}</span>
            <span style="color:#888;font-size:0.7rem;">{dt_str} ET</span>
            <span style="color:#ff6d00;font-size:0.75rem;font-weight:700;">DV01=$25/bp</span>
        </div>
    </div>
    """

def bb_card(title: str, content: str, color: str = "#ff6d00", width: str = "100%") -> str:
    return f"""
    <div style="background:#101010;border:1px solid #1f1f1f;border-top:2px solid {color};
                padding:10px 12px;font-family:'JetBrains Mono',monospace;width:{width};
                margin-bottom:6px;">
        <div style="color:{color};font-size:0.62rem;font-weight:700;letter-spacing:0.15em;
                    text-transform:uppercase;margin-bottom:6px;">{title}</div>
        {content}
    </div>
    """

def bb_price_tag(ticker: str, price: float, rate: float, chg: float = 0.0) -> str:
    chg_color = "#00e676" if chg > 0 else ("#ff1744" if chg < 0 else "#888")
    chg_sign = "+" if chg > 0 else ""
    return f"""
    <div style="background:#0d0d0d;border:1px solid #1f1f1f;border-left:3px solid #ff6d00;
                padding:8px 10px;display:inline-block;min-width:130px;">
        <div style="color:#888;font-size:0.6rem;letter-spacing:0.1em;">{ticker}</div>
        <div style="color:#f0f0f0;font-size:1.1rem;font-weight:700;
                    font-family:'JetBrains Mono',monospace;">{price:.3f}</div>
        <div style="color:#888;font-size:0.65rem;">{rate:.3f}%
            <span style="color:{chg_color};margin-left:6px;">{chg_sign}{chg:.1f}bp</span>
        </div>
    </div>
    """

def bb_table(df: pd.DataFrame, highlight_col: str = None,
             green_cols=None, red_cols=None) -> str:
    """Render a DataFrame as Bloomberg-styled HTML table."""
    green_cols = green_cols or []
    red_cols = red_cols or []

    html = """<div style="overflow-x:auto;">
    <table style="width:100%;border-collapse:collapse;font-family:'JetBrains Mono',monospace;
                  font-size:0.72rem;">
    <thead><tr>"""

    for col in df.columns:
        if col.startswith('_'):
            continue
        html += f'<th style="background:#1a1a1a;color:#ff6d00;padding:5px 8px;text-align:left;'
        html += f'border-bottom:1px solid #ff6d00;border-right:1px solid #1f1f1f;'
        html += f'letter-spacing:0.08em;font-size:0.63rem;white-space:nowrap;">{col}</th>'
    html += "</tr></thead><tbody>"

    for i, row in df.iterrows():
        bg = "#0a0a0a" if i % 2 == 0 else "#101010"
        html += f'<tr style="background:{bg};">'
        for col in df.columns:
            if col.startswith('_'):
                continue
            val = row[col]
            color = "#d4d4d4"

            if col in green_cols and isinstance(val, (int, float)):
                color = "#00e676" if val > 0 else ("#ff1744" if val < 0 else "#888")
            elif col in red_cols and isinstance(val, (int, float)):
                color = "#ff1744" if val > 0 else ("#00e676" if val < 0 else "#888")
            elif col == highlight_col:
                color = "#ff9100"
            elif col in ["Ticker", "Contract"]:
                color = "#ff6d00"

            # Format numbers
            if isinstance(val, float):
                if abs(val) > 100:
                    val_str = f"{val:,.2f}"
                elif abs(val) > 1:
                    val_str = f"{val:.4f}"
                else:
                    val_str = f"{val:.6f}"
            else:
                val_str = str(val)

            html += f'<td style="color:{color};padding:4px 8px;border-right:1px solid #1a1a1a;'
            html += f'border-bottom:1px solid #141414;white-space:nowrap;">{val_str}</td>'
        html += "</tr>"
    html += "</tbody></table></div>"
    return html

def make_plotly_dark():
    """Return base dark layout for Plotly charts."""
    return go.Layout(
        paper_bgcolor='#0a0a0a',
        plot_bgcolor='#0d0d0d',
        font=dict(family='JetBrains Mono', color='#d4d4d4', size=11),
        xaxis=dict(gridcolor='#1f1f1f', linecolor='#2a2a2a', zerolinecolor='#2a2a2a'),
        yaxis=dict(gridcolor='#1f1f1f', linecolor='#2a2a2a', zerolinecolor='#2a2a2a'),
        margin=dict(l=50, r=20, t=40, b=50),
        legend=dict(bgcolor='#101010', bordercolor='#2a2a2a', borderwidth=1),
    )

# ─────────────────────────────────────────────
# SESSION STATE INITIALIZATION
# ─────────────────────────────────────────────

def init_state():
    if 'base_sofr' not in st.session_state:
        st.session_state.base_sofr = 4.33
    if 'sofr_configured' not in st.session_state:
        st.session_state.sofr_configured = False
    if 'fomc_meetings' not in st.session_state:
        st.session_state.fomc_meetings = DEFAULT_FOMC_DATES_2026_2027[:10]
    if 'fomc_changes' not in st.session_state:
        st.session_state.fomc_changes = {d: 0 for d in DEFAULT_FOMC_DATES_2026_2027[:10]}
    if 'me_basis' not in st.session_state:
        st.session_state.me_basis = 1.0
    if 'qe_basis' not in st.session_state:
        st.session_state.qe_basis = 2.0
    if 'ye_basis' not in st.session_state:
        st.session_state.ye_basis = 4.0
    if 'apply_me' not in st.session_state:
        st.session_state.apply_me = True
    if 'apply_qe' not in st.session_state:
        st.session_state.apply_qe = True
    if 'apply_ye' not in st.session_state:
        st.session_state.apply_ye = True
    if 'scenarios' not in st.session_state:
        st.session_state.scenarios = build_default_scenarios()
    if 'positions' not in st.session_state:
        st.session_state.positions = []
    if 'contracts' not in st.session_state:
        st.session_state.contracts = get_active_sr3_contracts(16)
    if 'num_contracts_display' not in st.session_state:
        st.session_state.num_contracts_display = 12
    if 'live_sofr_data' not in st.session_state:
        st.session_state.live_sofr_data = None
    if 'live_data_fetch_date' not in st.session_state:
        st.session_state.live_data_fetch_date = None
    if 'live_data_error' not in st.session_state:
        st.session_state.live_data_error = None

init_state()

# ─────────────────────────────────────────────
# EXPORT UTILITIES
# ─────────────────────────────────────────────

def df_to_csv_bytes(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False).encode('utf-8')

def df_to_excel_bytes(sheets: dict) -> bytes:
    """sheets = {'Sheet Name': dataframe, ...}"""
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine='openpyxl') as writer:
        for sheet_name, df in sheets.items():
            df.to_excel(writer, sheet_name=sheet_name[:31], index=False)
    return buf.getvalue()

def export_btn_csv(df: pd.DataFrame, filename: str, label: str = "⬇ CSV"):
    """Render a CSV download button."""
    st.download_button(
        label=label,
        data=df_to_csv_bytes(df),
        file_name=filename,
        mime='text/csv',
        key=f"dl_{filename.replace('.','_')}_{id(df)}",
    )

def export_btn_excel(sheets: dict, filename: str, label: str = "⬇ EXCEL"):
    """Render an Excel download button."""
    try:
        data = df_to_excel_bytes(sheets)
        st.download_button(
            label=label,
            data=data,
            file_name=filename,
            mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            key=f"dl_{filename.replace('.','_')}_{abs(hash(str(sheets.keys())))}",
        )
    except Exception:
        st.warning("Install openpyxl for Excel export: pip install openpyxl")

# ─────────────────────────────────────────────
# LIVE DATA — NYFRB SOFR FETCHER
# ─────────────────────────────────────────────

NYFRB_SOFR_URL = "https://markets.newyorkfed.org/api/rates/sofr/last/30.json"
NYFRB_EFFR_URL = "https://markets.newyorkfed.org/api/rates/effr/last/30.json"

def fetch_nyfrb_rates(series: str = "sofr", n: int = 30) -> dict:
    """
    Fetch SOFR or EFFR data from NYFRB public API.
    Returns: {'rates': [{'effectiveDate': 'YYYY-MM-DD', 'rate': 4.33, ...}], 'error': None}
    """
    url = f"https://markets.newyorkfed.org/api/rates/{series}/last/{n}.json"
    try:
        resp = requests.get(url, timeout=10,
                            headers={"Accept": "application/json",
                                     "User-Agent": "SR3-Terminal/1.0"})
        resp.raise_for_status()
        data = resp.json()
        rates = data.get("refRates", [])
        return {"rates": rates, "error": None, "fetched_at": datetime.now().isoformat()}
    except requests.exceptions.ConnectionError:
        return {"rates": [], "error": "Network unavailable — check internet connection.", "fetched_at": None}
    except requests.exceptions.Timeout:
        return {"rates": [], "error": "NYFRB API timeout. Try again.", "fetched_at": None}
    except Exception as e:
        return {"rates": [], "error": str(e), "fetched_at": None}

def should_auto_refresh() -> bool:
    """
    Returns True if we should auto-fetch: either never fetched, or
    today is a new calendar day vs last fetch (morning auto-refresh logic).
    """
    if st.session_state.live_data_fetch_date is None:
        return True
    last = st.session_state.live_data_fetch_date
    today = date.today()
    # Refresh if: new calendar day AND current time is after 8:00 AM ET
    if last < today and datetime.now().hour >= 8:
        return True
    return False

# ─────────────────────────────────────────────
# FIRST-LOAD: SOFR CONFIGURATION MODAL
# ─────────────────────────────────────────────

if not st.session_state.sofr_configured:
    st.markdown("""
    <div style="background:#050505;border:2px solid #ff6d00;max-width:560px;margin:80px auto 0;
                padding:36px 40px;font-family:'JetBrains Mono',monospace;">
        <div style="color:#ff6d00;font-family:'Bebas Neue',monospace;font-size:2.4rem;
                    letter-spacing:0.15em;margin-bottom:2px;">◈ SR3 SOFR TERMINAL</div>
        <div style="color:#333;font-size:0.62rem;letter-spacing:0.12em;
                    border-bottom:1px solid #1f1f1f;padding-bottom:16px;margin-bottom:20px;">
            CME THREE-MONTH SOFR FUTURES · PROFESSIONAL ANALYTICS PLATFORM
        </div>
        <div style="color:#ff9100;font-size:0.7rem;font-weight:700;
                    letter-spacing:0.12em;margin-bottom:8px;">CONFIGURE BASE SOFR RATE</div>
        <div style="color:#555;font-size:0.62rem;line-height:1.6;margin-bottom:20px;">
            Enter the current overnight SOFR fixing to seed all contract pricing,
            scenario analysis, and impact calculations. You can update this at any
            time from the Overview tab or via the Live Data feed.
        </div>
        <div style="display:flex;gap:16px;margin-bottom:12px;flex-wrap:wrap;">
            <span style="color:#888;font-size:0.6rem;">Common rates:</span>
            <span style="color:#ff6d00;font-size:0.6rem;">4.3300 (current)</span>
            <span style="color:#555;font-size:0.6rem;">4.5800 (Nov 24 peak)</span>
            <span style="color:#555;font-size:0.6rem;">5.3300 (Jul 24 peak)</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    _pad1, _form, _pad2 = st.columns([1.5, 1, 1.5])
    with _form:
        startup_sofr = st.number_input(
            "Current SOFR (%)",
            min_value=0.0, max_value=15.0,
            value=4.33, step=0.01, format="%.4f",
            help="Overnight SOFR fixing — e.g. 4.3300"
        )
        st.markdown("""<div style="height:8px"></div>""", unsafe_allow_html=True)
        if st.button("▶  LAUNCH TERMINAL", key="launch_btn"):
            st.session_state.base_sofr = startup_sofr
            st.session_state.sofr_configured = True
            for sc in st.session_state.scenarios:
                sc['base_sofr'] = round(startup_sofr, 4)
            st.rerun()
    st.stop()


# ─────────────────────────────────────────────
# HELPER: BUILD FOMC CHANGES DICT
# ─────────────────────────────────────────────

def get_fomc_changes_decimal():
    """Return fomc_changes with rates in decimal (not bps)."""
    return {d: v for d, v in st.session_state.fomc_changes.items()}

def get_basis_params():
    return {
        'me_basis': st.session_state.me_basis / 10000,
        'qe_basis': st.session_state.qe_basis / 10000,
        'ye_basis': st.session_state.ye_basis / 10000,
        'apply_me': st.session_state.apply_me,
        'apply_qe': st.session_state.apply_qe,
        'apply_ye': st.session_state.apply_ye,
    }

def compute_prices():
    """Compute current prices for all contracts."""
    bp = get_basis_params()
    return price_all_contracts(
        st.session_state.contracts,
        st.session_state.base_sofr / 100,
        get_fomc_changes_decimal(),
        **bp
    )

# ─────────────────────────────────────────────
# RENDER HEADER
# ─────────────────────────────────────────────

st.markdown(bb_header(), unsafe_allow_html=True)

# ─────────────────────────────────────────────
# MAIN TABS
# ─────────────────────────────────────────────

tabs = st.tabs([
    "📊  OVERVIEW",
    "⚙️  PRICING ENGINE",
    "🔄  SCENARIO BUILDER",
    "📋  FOMC IMPACT MATRIX",
    "💰  P&L CALCULATOR",
    "📈  CURVE & ANALYTICS",
    "📐  SPREADS & FLIES",
    "📌  RISK MONITOR",
    "🌐  LIVE DATA",
])

# ═══════════════════════════════════════════════════════════════
# TAB 0 — OVERVIEW
# ═══════════════════════════════════════════════════════════════

with tabs[0]:
    # Quick settings bar
    ov_col1, ov_col2, ov_col3, ov_col4, ov_col5 = st.columns([1.5, 1, 1, 1, 2])
    with ov_col1:
        st.session_state.base_sofr = st.number_input(
            "Base SOFR (%)", min_value=0.0, max_value=10.0,
            value=st.session_state.base_sofr, step=0.01, format="%.4f",
            key="ov_sofr", help="Current overnight SOFR rate in %"
        )
    with ov_col2:
        st.session_state.me_basis = st.number_input(
            "ME Basis (bp)", min_value=0.0, max_value=20.0,
            value=st.session_state.me_basis, step=0.5,
            key="ov_me", help="Month-end basis premium in bps"
        )
    with ov_col3:
        st.session_state.qe_basis = st.number_input(
            "QE Basis (bp)", min_value=0.0, max_value=20.0,
            value=st.session_state.qe_basis, step=0.5,
            key="ov_qe", help="Quarter-end additional basis in bps"
        )
    with ov_col4:
        st.session_state.ye_basis = st.number_input(
            "YE Basis (bp)", min_value=0.0, max_value=30.0,
            value=st.session_state.ye_basis, step=0.5,
            key="ov_ye", help="Year-end additional basis in bps"
        )
    with ov_col5:
        toggle_cols = st.columns(3)
        with toggle_cols[0]:
            st.session_state.apply_me = st.checkbox("ME", value=st.session_state.apply_me, key="ck_me")
        with toggle_cols[1]:
            st.session_state.apply_qe = st.checkbox("QE", value=st.session_state.apply_qe, key="ck_qe")
        with toggle_cols[2]:
            st.session_state.apply_ye = st.checkbox("YE", value=st.session_state.apply_ye, key="ck_ye")

    st.markdown("<hr>", unsafe_allow_html=True)

    # Compute prices
    prices_df = compute_prices()
    display_cols = [c for c in prices_df.columns if not c.startswith('_')]
    show_df = prices_df[display_cols].copy()
    show_df['Price'] = show_df['Price'].map(lambda x: f"{x:.5f}")
    show_df['Rate (%)'] = show_df['Rate (%)'].map(lambda x: f"{x:.4f}%")
    show_df['DV01 ($)'] = show_df['DV01 ($)'].map(lambda x: f"${x:.2f}")
    show_df['Compound'] = show_df['Compound'].map(lambda x: f"{x:.8f}")

    # Quick metrics top row
    m_cols = st.columns(6)
    with m_cols[0]:
        st.metric("BASE SOFR", f"{st.session_state.base_sofr:.4f}%")
    with m_cols[1]:
        if len(prices_df) > 0:
            front_price = prices_df.iloc[0]['Price']
            front_rate = prices_df.iloc[0]['Rate (%)']
            st.metric(f"FRONT ({prices_df.iloc[0]['Ticker']})", f"{front_price:.3f}", f"{front_rate:.3f}%")
    with m_cols[2]:
        if len(prices_df) > 1:
            p2 = prices_df.iloc[1]['Price']
            r2 = prices_df.iloc[1]['Rate (%)']
            st.metric(f"2ND ({prices_df.iloc[1]['Ticker']})", f"{p2:.3f}", f"{r2:.3f}%")
    with m_cols[3]:
        if len(prices_df) > 3:
            p4 = prices_df.iloc[3]['Price']
            r4 = prices_df.iloc[3]['Rate (%)']
            st.metric(f"4TH ({prices_df.iloc[3]['Ticker']})", f"{p4:.3f}", f"{r4:.3f}%")
    with m_cols[4]:
        if len(prices_df) >= 4:
            spread = (prices_df.iloc[3]['Price'] - prices_df.iloc[0]['Price']) * 100
            st.metric("1Y SPREAD", f"{spread:+.1f}bp", delta_color="off")
    with m_cols[5]:
        total_cuts = sum(v for v in st.session_state.fomc_changes.values() if v < 0)
        total_hikes = sum(v for v in st.session_state.fomc_changes.values() if v > 0)
        if total_cuts:
            st.metric("CUTS PRICED", f"{abs(total_cuts)}bp", f"({abs(total_cuts)//25} cuts)")
        elif total_hikes:
            st.metric("HIKES PRICED", f"{total_hikes}bp", f"({total_hikes//25} hikes)", delta_color="inverse")
        else:
            st.metric("CUTS PRICED", "0bp", "FLAT")

    st.markdown("<hr>", unsafe_allow_html=True)

    # Left: price table | Right: curve chart
    ov_left, ov_right = st.columns([1, 1.4])

    with ov_left:
        st.markdown(bb_card("◈ SR3 CONTRACT PRICER",
            bb_table(show_df, highlight_col='Price'),
            color="#ff6d00"), unsafe_allow_html=True)
        # Export row
        _ov_e1, _ov_e2 = st.columns(2)
        with _ov_e1:
            export_btn_csv(prices_df[[c for c in prices_df.columns if not c.startswith("_")]],
                           "sr3_prices_snapshot.csv", "⬇ CSV")
        with _ov_e2:
            export_btn_excel(
                {"SR3 Prices": prices_df[[c for c in prices_df.columns if not c.startswith("_")]]},
                "sr3_prices_snapshot.xlsx", "⬇ EXCEL"
            )

    with ov_right:
        # Forward curve chart
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=prices_df['Contract'],
            y=prices_df['Rate (%)'],
            mode='lines+markers',
            name='Implied Rate',
            line=dict(color='#ff6d00', width=2.5),
            marker=dict(color='#ff9100', size=8, symbol='diamond'),
            hovertemplate='<b>%{x}</b><br>Rate: %{y:.4f}%<extra></extra>'
        ))

        layout = make_plotly_dark()
        layout.update(
            title=dict(text='◈ SR3 FORWARD RATE CURVE', font=dict(color='#ff6d00', size=13), x=0.02),
            yaxis=dict(title='Implied Rate (%)', tickformat='.3f', gridcolor='#1a1a1a'),
            xaxis=dict(title='Contract', gridcolor='#1a1a1a'),
            height=320,
        )
        fig.update_layout(layout)
        fig.add_hline(y=st.session_state.base_sofr, line_dash="dot",
                      line_color="#555", annotation_text=f"Base SOFR {st.session_state.base_sofr:.2f}%",
                      annotation_font_color="#555", annotation_font_size=10)
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

        # FOMC countdown
        today = date.today()
        upcoming = [d for d in DEFAULT_FOMC_DATES_2026_2027 if d >= today]
        if upcoming:
            next_mtg = min(upcoming)
            days_to = (next_mtg - today).days
            cumulative_cuts = 0
            fomc_html = ""
            for i, mtg in enumerate(DEFAULT_FOMC_DATES_2026_2027[:8]):
                chg = st.session_state.fomc_changes.get(mtg, 0)
                cumulative_cuts += chg
                color = "#00e676" if chg < 0 else ("#ff1744" if chg > 0 else "#555")
                chg_str = f"{chg:+d}bp" if chg != 0 else "HOLD"
                past = "dim" if mtg < today else ""
                fomc_html += f"""<div style="display:flex;justify-content:space-between;
                    padding:3px 0;border-bottom:1px solid #141414;
                    opacity:{'0.35' if mtg < today else '1'};">
                    <span style="color:#888;font-size:0.65rem;">{mtg.strftime('%d %b %y')}</span>
                    <span style="color:{color};font-size:0.65rem;font-weight:700;">{chg_str}</span>
                    <span style="color:#555;font-size:0.65rem;">{cumulative_cuts:+d}bp cumul</span>
                </div>"""

            countdown_html = f"""
            <div style="background:#050505;border:1px solid #1f1f1f;border-top:2px solid #00b4d8;
                        padding:10px 12px;font-family:'JetBrains Mono',monospace;">
                <div style="color:#00b4d8;font-size:0.62rem;letter-spacing:0.15em;
                            margin-bottom:8px;">◈ FOMC CALENDAR / RATE PATH</div>
                <div style="color:#fff;font-size:0.9rem;font-weight:700;margin-bottom:8px;">
                    NEXT MTG: {next_mtg.strftime('%d %b %Y')} &nbsp;
                    <span style="color:#ffd600;font-size:0.75rem;">T-{days_to}d</span>
                </div>
                {fomc_html}
            </div>"""
            st.markdown(countdown_html, unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════
# TAB 1 — PRICING ENGINE
# ═══════════════════════════════════════════════════════════════

with tabs[1]:
    st.markdown("""<div style="font-family:'JetBrains Mono',monospace;color:#ff6d00;
        font-size:0.65rem;letter-spacing:0.15em;padding:8px 0;">
        ◈ CONFIGURE FOMC PATH → PRICES UPDATE IN REAL-TIME</div>""", unsafe_allow_html=True)

    pe_left, pe_right = st.columns([1, 2])

    with pe_left:
        st.markdown("""<div style="color:#ff6d00;font-size:0.65rem;letter-spacing:0.1em;
            font-family:'JetBrains Mono',monospace;margin-bottom:6px;">◈ FOMC MEETING INPUTS</div>""",
            unsafe_allow_html=True)

        meetings = st.session_state.fomc_meetings
        for i, mtg in enumerate(meetings[:10]):
            cols = st.columns([1.2, 1.2, 0.8])
            with cols[0]:
                new_date = st.date_input(
                    f"Mtg {i+1}", value=mtg,
                    key=f"mtg_date_{i}", label_visibility="collapsed"
                )
            with cols[1]:
                chg_options = [-75, -50, -25, 0, 25, 50]
                current_chg = st.session_state.fomc_changes.get(mtg, 0)
                chg = st.selectbox(
                    f"Chg {i+1}",
                    options=chg_options,
                    index=chg_options.index(current_chg) if current_chg in chg_options else 3,
                    key=f"fomc_chg_{i}",
                    label_visibility="collapsed",
                    format_func=lambda x: f"{x:+d}bp" if x != 0 else "HOLD"
                )
            with cols[2]:
                cum = sum(st.session_state.fomc_changes.get(m, 0) for m in meetings[:i+1])
                cum_color = "#00e676" if cum < 0 else ("#ff1744" if cum > 0 else "#555")
                st.markdown(
                    f'<div style="color:{cum_color};font-size:0.65rem;font-family:JetBrains Mono,mono;'
                    f'padding-top:8px;">{cum:+d}</div>',
                    unsafe_allow_html=True
                )

            # Update state
            if new_date != mtg:
                meetings[i] = new_date
            st.session_state.fomc_changes[new_date] = chg

        # Rate path visualization (mini)
        cum_rates = []
        rate = st.session_state.base_sofr
        for mtg in meetings[:10]:
            rate += st.session_state.fomc_changes.get(mtg, 0) / 100
            cum_rates.append({'date': mtg.strftime('%b %y'), 'rate': round(rate, 4)})

        rate_fig = go.Figure(go.Bar(
            x=[r['date'] for r in cum_rates],
            y=[r['rate'] for r in cum_rates],
            marker_color=['#00e676' if r['rate'] < cum_rates[0]['rate'] else
                          '#ff1744' if r['rate'] > cum_rates[0]['rate'] else
                          '#ff6d00' for r in cum_rates],
            text=[f"{r['rate']:.2f}%" for r in cum_rates],
            textposition='outside',
            textfont=dict(size=9, color='#888')
        ))
        layout2 = make_plotly_dark()
        layout2.update(
            title=dict(text='Implied SOFR After Each Meeting', font=dict(color='#ff9100', size=11), x=0.02),
            height=200, showlegend=False,
            yaxis=dict(tickformat='.2f', ticksuffix='%'),
            margin=dict(l=40, r=10, t=35, b=40)
        )
        rate_fig.update_layout(layout2)
        st.plotly_chart(rate_fig, use_container_width=True, config={'displayModeBar': False})

    with pe_right:
        # Detailed pricing table with rate breakdown
        bp = get_basis_params()
        full_prices = price_all_contracts(
            st.session_state.contracts,
            st.session_state.base_sofr / 100,
            get_fomc_changes_decimal(),
            **bp
        )

        # Add derived columns
        full_prices['Rate (%)'] = full_prices['Rate (%)'].map(lambda x: f"{x:.5f}%")
        full_prices['Price'] = full_prices['Price'].map(lambda x: f"{x:.5f}")
        full_prices['Convexity (bp)'] = [
            estimate_convexity_adj(i * 0.25) for i in range(len(full_prices))
        ]

        display_df = full_prices[['Ticker', 'Contract', 'Start', 'End', 'Days',
                                    'Price', 'Rate (%)', 'DV01 ($)', 'Convexity (bp)']].copy()

        st.markdown(bb_card("◈ FULL CONTRACT PRICING TABLE", bb_table(display_df)),
                    unsafe_allow_html=True)
        _pe_e1, _pe_e2 = st.columns(2)
        with _pe_e1:
            export_btn_csv(display_df, "sr3_pricing_engine.csv", "⬇ CSV")
        with _pe_e2:
            export_btn_excel({"SR3 Full Pricing": display_df}, "sr3_pricing_engine.xlsx", "⬇ EXCEL")

        # Daily SOFR path chart for a selected contract
        st.markdown("""<div style="color:#00b4d8;font-size:0.65rem;letter-spacing:0.1em;
            font-family:'JetBrains Mono',monospace;margin:8px 0 4px 0;">
            ◈ DAILY SOFR PATH — SELECT CONTRACT</div>""", unsafe_allow_html=True)

        contract_names = [c['name'] for c in st.session_state.contracts[:12]]
        sel = st.selectbox("", contract_names, key="pe_sel_contract", label_visibility="collapsed")
        sel_idx = contract_names.index(sel)
        sel_contract = st.session_state.contracts[sel_idx]

        daily_path = build_daily_sofr_path(
            sel_contract['start'], sel_contract['end'],
            st.session_state.base_sofr / 100,
            get_fomc_changes_decimal(),
            **bp
        )

        fig3 = go.Figure()
        fig3.add_trace(go.Scatter(
            x=daily_path['date'],
            y=daily_path['rate'] * 100,
            mode='lines',
            name='SOFR Rate',
            line=dict(color='#ff6d00', width=1.5),
            fill='tozeroy',
            fillcolor='rgba(255,109,0,0.07)',
            hovertemplate='%{x}<br>SOFR: %{y:.4f}%<extra></extra>'
        ))
        # Mark FOMC meetings in this period
        for mtg, chg in get_fomc_changes_decimal().items():
            if sel_contract['start'] <= mtg <= sel_contract['end'] and chg != 0:
                fig3.add_vline(x=mtg, line_color='#00e676' if chg < 0 else '#ff1744',
                               line_dash='dash', line_width=1,
                               annotation_text=f"{chg:+d}bp",
                               annotation_font_color='#888', annotation_font_size=9)

        layout3 = make_plotly_dark()
        layout3.update(
            title=dict(text=f'Daily SOFR Path — {sel}', font=dict(color='#ff6d00', size=12), x=0.02),
            yaxis=dict(tickformat='.3f', ticksuffix='%'),
            height=250,
            margin=dict(l=50, r=10, t=35, b=40)
        )
        fig3.update_layout(layout3)
        st.plotly_chart(fig3, use_container_width=True, config={'displayModeBar': False})

# ═══════════════════════════════════════════════════════════════
# TAB 2 — SCENARIO BUILDER
# ═══════════════════════════════════════════════════════════════

with tabs[2]:
    st.markdown("""<div style="font-family:'JetBrains Mono',monospace;color:#ff6d00;
        font-size:0.65rem;letter-spacing:0.15em;padding:8px 0;">
        ◈ BUILD UP TO 30 SCENARIOS — TWEAK SOFR PATHS — COMPARE PRICES INSTANTLY</div>""",
        unsafe_allow_html=True)

    sc_left, sc_right = st.columns([1.3, 2.2])

    meetings = DEFAULT_FOMC_DATES_2026_2027[:8]
    mtg_labels = [m.strftime('%d %b %y') for m in meetings]

    with sc_left:
        # Add / remove scenarios
        ctrl_cols = st.columns([2, 1, 1])
        with ctrl_cols[0]:
            new_name = st.text_input("Scenario Name", value="Custom Scenario",
                                      key="sc_new_name", label_visibility="visible")
        with ctrl_cols[1]:
            new_sofr = st.number_input("Base SOFR %", value=st.session_state.base_sofr,
                                        step=0.01, format="%.2f", key="sc_new_sofr")
        with ctrl_cols[2]:
            st.markdown("<div style='height:24px'></div>", unsafe_allow_html=True)
            add_btn = st.button("+ ADD", key="sc_add")

        if add_btn and len(st.session_state.scenarios) < 30:
            st.session_state.scenarios.append({
                'name': new_name,
                'base_sofr': new_sofr,
                'changes': {m: 0 for m in meetings},
                'color': f"#{np.random.randint(0, 255):02x}{np.random.randint(0, 255):02x}{np.random.randint(128, 255):02x}",
                'description': 'User-defined scenario'
            })
            st.rerun()

        st.markdown(f"""<div style="color:#555;font-size:0.65rem;font-family:'JetBrains Mono',mono;
            margin:4px 0;">{len(st.session_state.scenarios)}/30 scenarios</div>""",
            unsafe_allow_html=True)

        # Scenario editor
        sc_names = [s['name'] for s in st.session_state.scenarios]
        sel_sc_idx = st.selectbox("Edit Scenario", range(len(sc_names)),
                                   format_func=lambda i: sc_names[i],
                                   key="sc_sel")

        if sel_sc_idx is not None and sel_sc_idx < len(st.session_state.scenarios):
            sc = st.session_state.scenarios[sel_sc_idx]

            new_base = st.number_input(f"Base SOFR (%)", value=float(sc['base_sofr']),
                                        step=0.01, format="%.4f", key=f"sc_base_{sel_sc_idx}")
            st.session_state.scenarios[sel_sc_idx]['base_sofr'] = new_base

            st.markdown("""<div style="color:#888;font-size:0.62rem;font-family:'JetBrains Mono',mono;
                margin:4px 0;">FOMC MEETING CHANGES (bps)</div>""", unsafe_allow_html=True)

            for j, mtg in enumerate(meetings):
                cc = st.columns([1.5, 1])
                with cc[0]:
                    st.markdown(f'<div style="color:#555;font-size:0.62rem;'
                                f'font-family:JetBrains Mono,mono;padding-top:8px;">'
                                f'{mtg.strftime("%d %b %y")}</div>', unsafe_allow_html=True)
                with cc[1]:
                    opts = [-75, -50, -25, 0, 25, 50, 75]
                    cur = sc['changes'].get(mtg, 0)
                    val = st.selectbox("", opts,
                                       index=opts.index(cur) if cur in opts else 3,
                                       key=f"sc_{sel_sc_idx}_m{j}",
                                       label_visibility="collapsed",
                                       format_func=lambda x: f"{x:+d}" if x != 0 else "0")
                    st.session_state.scenarios[sel_sc_idx]['changes'][mtg] = val

            del_col1, del_col2 = st.columns(2)
            with del_col1:
                if st.button("🗑 DELETE", key=f"sc_del_{sel_sc_idx}") and len(st.session_state.scenarios) > 1:
                    st.session_state.scenarios.pop(sel_sc_idx)
                    st.rerun()
            with del_col2:
                # Duplicate
                if st.button("⧉ DUPLICATE", key=f"sc_dup_{sel_sc_idx}") and len(st.session_state.scenarios) < 30:
                    import copy
                    dup = copy.deepcopy(sc)
                    dup['name'] = sc['name'] + " (copy)"
                    st.session_state.scenarios.append(dup)
                    st.rerun()

    with sc_right:
        bp = get_basis_params()
        contracts = st.session_state.contracts[:8]

        # Price all scenarios
        scenario_prices = {}
        for sc in st.session_state.scenarios:
            sc_chg = {d: v for d, v in sc['changes'].items()}
            df = price_all_contracts(contracts, sc['base_sofr'] / 100, sc_chg,
                                      bp['me_basis'], bp['qe_basis'], bp['ye_basis'],
                                      bp['apply_me'], bp['apply_qe'], bp['apply_ye'])
            scenario_prices[sc['name']] = df['Price'].tolist()

        contract_names = [c['name'] for c in contracts]

        # Comparison table
        comp_rows = []
        base_prices = scenario_prices.get(st.session_state.scenarios[0]['name'], [])
        for sc in st.session_state.scenarios:
            row = {'Scenario': sc['name'], 'Base SOFR': f"{sc['base_sofr']:.2f}%"}
            prices = scenario_prices.get(sc['name'], [])
            for i, cname in enumerate(contract_names):
                if i < len(prices):
                    row[cname] = round(prices[i], 3)
            comp_rows.append(row)

        comp_df = pd.DataFrame(comp_rows)

        # Display scenario comparison table
        st.markdown(bb_card("◈ SCENARIO PRICE COMPARISON", ""), unsafe_allow_html=True)

        # HTML table with color coding
        html = """<div style="overflow-x:auto;font-family:'JetBrains Mono',monospace;font-size:0.7rem;">
        <table style="width:100%;border-collapse:collapse;">
        <thead><tr>"""
        for col in comp_df.columns:
            html += f'<th style="background:#1a1a1a;color:#ff6d00;padding:5px 8px;'
            html += f'border-bottom:1px solid #ff6d00;text-align:left;white-space:nowrap;'
            html += f'font-size:0.63rem;">{col}</th>'
        html += "</tr></thead><tbody>"

        base_row_prices = [comp_df.iloc[0][c] for c in contract_names if c in comp_df.columns]

        for i, row in comp_df.iterrows():
            sc = st.session_state.scenarios[i]
            html += f'<tr style="background:{"#0a0a0a" if i%2==0 else "#101010"};">'
            for col in comp_df.columns:
                val = row[col]
                if col in contract_names and isinstance(val, float):
                    ref = base_row_prices[contract_names.index(col)] if contract_names.index(col) < len(base_row_prices) else val
                    if isinstance(ref, float):
                        diff = val - ref
                        bg = f"rgba(0,230,118,0.1)" if diff > 0.002 else (
                            f"rgba(255,23,68,0.1)" if diff < -0.002 else "transparent")
                        color = "#00e676" if diff > 0.002 else ("#ff1744" if diff < -0.002 else "#d4d4d4")
                        diff_str = f" ({diff:+.2f})" if i > 0 else ""
                        html += f'<td style="color:{color};background:{bg};padding:4px 7px;'
                        html += f'border-right:1px solid #141414;">{val:.3f}{diff_str}</td>'
                    else:
                        html += f'<td style="color:#d4d4d4;padding:4px 7px;">{val}</td>'
                elif col == 'Scenario':
                    html += f'<td style="color:{sc["color"]};padding:4px 7px;font-weight:700;'
                    html += f'border-right:1px solid #141414;">{val}</td>'
                else:
                    html += f'<td style="color:#888;padding:4px 7px;border-right:1px solid #141414;">{val}</td>'
            html += "</tr>"
        html += "</tbody></table></div>"
        st.markdown(html, unsafe_allow_html=True)

        # Multi-line scenario chart
        sc_fig = go.Figure()
        for sc in st.session_state.scenarios:
            prices = scenario_prices.get(sc['name'], [])
            if prices:
                sc_fig.add_trace(go.Scatter(
                    x=contract_names[:len(prices)],
                    y=[100 - p for p in prices],
                    mode='lines+markers',
                    name=sc['name'],
                    line=dict(color=sc['color'], width=1.8),
                    marker=dict(size=5),
                    hovertemplate=f"<b>{sc['name']}</b><br>%{{x}}: %{{y:.4f}}%<extra></extra>"
                ))

        sc_layout = make_plotly_dark()
        sc_layout.update(
            title=dict(text='◈ SCENARIO COMPARISON — IMPLIED RATE CURVE',
                       font=dict(color='#ff6d00', size=13), x=0.02),
            yaxis=dict(title='Implied Rate (%)', tickformat='.3f', ticksuffix='%'),
            xaxis=dict(title='Contract'),
            height=320,
            legend=dict(bgcolor='#0d0d0d', bordercolor='#2a2a2a')
        )
        sc_fig.update_layout(sc_layout)
        # Export scenarios
        _sc_e1, _sc_e2 = st.columns(2)
        with _sc_e1:
            _sc_export_rows = []
            for _sc_e in st.session_state.scenarios:
                _sc_e_df = price_all_contracts(
                    st.session_state.contracts[:8], _sc_e["base_sofr"]/100, _sc_e["changes"],
                    bp["me_basis"], bp["qe_basis"], bp["ye_basis"],
                    bp["apply_me"], bp["apply_qe"], bp["apply_ye"])
                _row_e = {"Scenario": _sc_e["name"], "Base SOFR": _sc_e["base_sofr"]}
                for _, _re in _sc_e_df.iterrows():
                    _row_e[_re["Contract"]] = round(_re["Price"], 5)
                _sc_export_rows.append(_row_e)
            _sc_export_df = pd.DataFrame(_sc_export_rows)
            export_btn_csv(_sc_export_df, "sr3_scenarios.csv", "⬇ CSV")
        with _sc_e2:
            export_btn_excel({"Scenarios": _sc_export_df}, "sr3_scenarios.xlsx", "⬇ EXCEL")

        st.plotly_chart(sc_fig, use_container_width=True, config={'displayModeBar': False})

# ═══════════════════════════════════════════════════════════════
# TAB 3 — FOMC IMPACT MATRIX
# ═══════════════════════════════════════════════════════════════

with tabs[3]:
    st.markdown("""<div style="font-family:'JetBrains Mono',monospace;color:#ff6d00;
        font-size:0.65rem;letter-spacing:0.15em;padding:8px 0;">
        ◈ FOMC MEETING IMPACT MATRIX — WEIGHTAGE × RATE CHANGE = PRICE IMPACT (bp)</div>""",
        unsafe_allow_html=True)

    im_col1, im_col2, im_col3 = st.columns([1, 1, 1])
    with im_col1:
        impact_bps = st.number_input("Rate Move to Model (bps)", value=25.0, step=1.0,
                                      min_value=1.0, max_value=100.0, key="im_bps")
    with im_col2:
        impact_direction = st.selectbox("Direction", ["Cut (−)", "Hike (+)"],
                                         key="im_dir")
    with im_col3:
        num_contracts_im = st.slider("Contracts to Show", 4, 12, 8, key="im_nc")

    sign = -1 if "Cut" in impact_direction else 1
    contracts_im = st.session_state.contracts[:num_contracts_im]
    meetings_im = DEFAULT_FOMC_DATES_2026_2027[:10]

    # Build impact matrix
    impact_df = build_impact_matrix(meetings_im, contracts_im, impact_bps)

    # Display weighted impact table
    contract_cols = [c['name'] for c in contracts_im]

    # Heatmap version
    z_vals = []
    for _, row in impact_df.iterrows():
        z_row = []
        for cname in contract_cols:
            w = impact_df.loc[impact_df['Meeting'] == row['Meeting'], f'_w_{cname}'].values
            z_row.append(float(w[0]) if len(w) > 0 else 0)
        z_vals.append(z_row)

    # Weightage heatmap
    heat_fig = go.Figure(go.Heatmap(
        z=z_vals,
        x=contract_cols,
        y=impact_df['Meeting'].tolist(),
        colorscale=[[0, '#0a0a0a'], [0.3, '#1a3a2a'], [0.7, '#00884a'], [1.0, '#00e676']],
        text=[[f"{v:.3f}" for v in row] for row in z_vals],
        texttemplate="%{text}",
        textfont=dict(size=9, color='#fff'),
        colorbar=dict(
            title='Weightage',
            tickfont=dict(color='#888', size=9),
            title_font=dict(color='#888', size=9)
        ),
        hoverongaps=False,
        hovertemplate='Meeting: %{y}<br>Contract: %{x}<br>Weightage: %{z:.4f}<extra></extra>'
    ))

    heat_layout = make_plotly_dark()
    heat_layout.update(
        title=dict(text=f'◈ FOMC IMPACT WEIGHTAGE MATRIX (25bp = Full Effect)',
                   font=dict(color='#ff6d00', size=13), x=0.02),
        height=380,
        xaxis=dict(side='top', tickfont=dict(color='#ff9100', size=10)),
        yaxis=dict(tickfont=dict(color='#888', size=9)),
        margin=dict(l=100, r=30, t=80, b=20)
    )
    heat_fig.update_layout(heat_layout)
    st.plotly_chart(heat_fig, use_container_width=True, config={'displayModeBar': False})

    # Price impact table ($)
    st.markdown("<hr>", unsafe_allow_html=True)

    im_t1, im_t2 = st.columns(2)

    with im_t1:
        st.markdown("""<div style="color:#00b4d8;font-size:0.65rem;font-family:'JetBrains Mono',mono;
            margin-bottom:6px;">◈ PRICE IMPACT (bp) PER MEETING</div>""", unsafe_allow_html=True)
        price_impact_df = impact_df[['Meeting'] + contract_cols].copy()
        for c in contract_cols:
            price_impact_df[c] = price_impact_df[c].map(lambda x: f"{x:.2f}")

        st.markdown(bb_table(price_impact_df), unsafe_allow_html=True)

    with im_t2:
        st.markdown("""<div style="color:#00b4d8;font-size:0.65rem;font-family:'JetBrains Mono',mono;
            margin-bottom:6px;">◈ DOLLAR IMPACT ($ PER CONTRACT)</div>""", unsafe_allow_html=True)

        dollar_impact_rows = []
        for _, row in impact_df.iterrows():
            dr = {'Meeting': row['Meeting']}
            for cname in contract_cols:
                dr[cname] = f"${row[cname] * 25:.2f}"
            dollar_impact_rows.append(dr)

        dollar_df = pd.DataFrame(dollar_impact_rows)
        st.markdown(bb_table(dollar_df), unsafe_allow_html=True)

    # Cumulative impact if all meetings move by impact_bps
    st.markdown("<hr>", unsafe_allow_html=True)
    st.markdown(f"""<div style="color:#ff9100;font-size:0.65rem;font-family:'JetBrains Mono',mono;
        margin-bottom:6px;">◈ CUMULATIVE IMPACT IF ALL MEETINGS = {sign*impact_bps:+.0f}bp</div>""",
        unsafe_allow_html=True)

    cum_impact = {}
    for cname in contract_cols:
        total = impact_df[cname].sum() * sign
        cum_impact[cname] = {
            'Total bp': round(total, 2),
            'Total $': round(total * 25, 2),
            'Price Pts': round(total / 100, 5)
        }

    cum_html = """<div style="display:flex;flex-wrap:wrap;gap:8px;">"""
    for cname, data in cum_impact.items():
        color = "#00e676" if data['Total bp'] > 0 else "#ff1744" if data['Total bp'] < 0 else "#888"
        cum_html += f"""
        <div style="background:#101010;border:1px solid #1f1f1f;border-top:2px solid {color};
                    padding:8px 12px;min-width:110px;">
            <div style="color:#ff6d00;font-size:0.62rem;font-family:'JetBrains Mono',mono;">{cname}</div>
            <div style="color:{color};font-size:0.95rem;font-weight:700;font-family:'JetBrains Mono',mono;">
                {data['Total bp']:+.1f}bp</div>
            <div style="color:#555;font-size:0.62rem;font-family:'JetBrains Mono',mono;">
                ${data['Total $']:,.2f}/contract</div>
        </div>"""
    cum_html += "</div>"
    st.markdown(cum_html, unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════
# TAB 4 — P&L CALCULATOR
# ═══════════════════════════════════════════════════════════════

with tabs[4]:
    st.markdown("""<div style="font-family:'JetBrains Mono',monospace;color:#ff6d00;
        font-size:0.65rem;letter-spacing:0.15em;padding:8px 0;">
        ◈ MULTI-LEG P&L ENGINE — SCENARIO-BASED EXIT PRICES — LIVE RISK METRICS</div>""",
        unsafe_allow_html=True)

    pnl_left, pnl_right = st.columns([1.2, 2])

    with pnl_left:
        st.markdown("""<div style="color:#ff9100;font-size:0.65rem;font-family:'JetBrains Mono',mono;
            margin-bottom:6px;">◈ POSITION ENTRY</div>""", unsafe_allow_html=True)

        pnl_cols = st.columns([1.5, 0.8, 0.8, 0.8])
        contract_names_all = [c['name'] for c in st.session_state.contracts[:12]]
        with pnl_cols[0]:
            pos_contract = st.selectbox("Contract", contract_names_all, key="pnl_contract")
        with pnl_cols[1]:
            pos_dir = st.selectbox("Dir", ["Long", "Short"], key="pnl_dir")
        with pnl_cols[2]:
            pos_qty = st.number_input("Qty", value=10, min_value=1, step=1, key="pnl_qty")
        with pnl_cols[3]:
            pos_entry = st.number_input("Entry", value=95.000, step=0.001, format="%.3f", key="pnl_entry")

        if st.button("+ ADD POSITION", key="pnl_add"):
            st.session_state.positions.append({
                'contract': pos_contract,
                'direction': pos_dir.lower(),
                'quantity': pos_qty,
                'entry_price': pos_entry
            })

        # Show current positions
        if st.session_state.positions:
            st.markdown("""<div style="color:#888;font-size:0.62rem;font-family:'JetBrains Mono',mono;
                margin:8px 0 4px 0;">◈ CURRENT POSITIONS</div>""", unsafe_allow_html=True)
            for i, pos in enumerate(st.session_state.positions):
                pc = st.columns([2, 0.8, 0.8, 0.8, 0.5])
                with pc[0]:
                    clr = "#00e676" if pos['direction'] == 'long' else "#ff1744"
                    st.markdown(f'<div style="color:{clr};font-size:0.65rem;'
                                f'font-family:JetBrains Mono,mono;padding-top:6px;">'
                                f'{"▲" if pos["direction"]=="long" else "▼"} {pos["contract"]}</div>',
                                unsafe_allow_html=True)
                with pc[1]:
                    st.markdown(f'<div style="color:#888;font-size:0.65rem;'
                                f'font-family:JetBrains Mono,mono;padding-top:6px;">'
                                f'{pos["quantity"]}ct</div>', unsafe_allow_html=True)
                with pc[2]:
                    st.markdown(f'<div style="color:#d4d4d4;font-size:0.65rem;'
                                f'font-family:JetBrains Mono,mono;padding-top:6px;">'
                                f'{pos["entry_price"]:.3f}</div>', unsafe_allow_html=True)
                with pc[3]:
                    new_ep = st.number_input("", value=float(pos['entry_price']),
                                              step=0.001, format="%.3f",
                                              key=f"ep_{i}", label_visibility="collapsed")
                    st.session_state.positions[i]['entry_price'] = new_ep
                with pc[4]:
                    if st.button("×", key=f"del_pos_{i}"):
                        st.session_state.positions.pop(i)
                        st.rerun()

            if st.button("CLEAR ALL", key="pnl_clear"):
                st.session_state.positions = []
                st.rerun()
        else:
            st.info("No positions. Add using the form above.")

    with pnl_right:
        if st.session_state.positions:
            bp_p = get_basis_params()

            # P&L under each scenario
            pnl_results = []
            for sc in st.session_state.scenarios:
                sc_chg = sc['changes']
                sc_prices_df = price_all_contracts(
                    st.session_state.contracts[:12],
                    sc['base_sofr'] / 100, sc_chg,
                    bp_p['me_basis'], bp_p['qe_basis'], bp_p['ye_basis'],
                    bp_p['apply_me'], bp_p['apply_qe'], bp_p['apply_ye']
                )
                price_lookup = dict(zip(sc_prices_df['Contract'], sc_prices_df['Price']))

                total_pnl = 0
                leg_pnls = []
                for pos in st.session_state.positions:
                    exit_p = price_lookup.get(pos['contract'], pos['entry_price'])
                    pnl = calculate_pnl(pos['entry_price'], exit_p,
                                         pos['quantity'], pos['direction'])
                    leg_pnls.append({
                        'contract': pos['contract'],
                        'entry': pos['entry_price'],
                        'exit': exit_p,
                        'qty': pos['quantity'],
                        'dir': pos['direction'],
                        'pnl': pnl['dollar_pnl']
                    })
                    total_pnl += pnl['dollar_pnl']

                pnl_results.append({
                    'Scenario': sc['name'],
                    'Total P&L': total_pnl,
                    'color': sc['color']
                })

            # P&L bar chart
            pnl_bar = go.Figure(go.Bar(
                x=[r['Scenario'] for r in pnl_results],
                y=[r['Total P&L'] for r in pnl_results],
                marker_color=[r['color'] for r in pnl_results],
                text=[f"${r['Total P&L']:,.0f}" for r in pnl_results],
                textposition='outside',
                textfont=dict(size=9, color='#888')
            ))
            pnl_layout = make_plotly_dark()
            pnl_layout.update(
                title=dict(text='◈ PORTFOLIO P&L BY SCENARIO',
                           font=dict(color='#ff6d00', size=13), x=0.02),
                yaxis=dict(title='P&L ($)', tickformat='$,.0f',
                           zeroline=True, zerolinecolor='#333'),
                xaxis=dict(tickangle=-30, tickfont=dict(size=8)),
                height=320,
                shapes=[dict(type='line', x0=-0.5, x1=len(pnl_results)-0.5,
                             y0=0, y1=0, line=dict(color='#555', width=1))]
            )
            pnl_bar.update_layout(pnl_layout)
            st.plotly_chart(pnl_bar, use_container_width=True, config={'displayModeBar': False})

            # Detailed P&L table
            pnl_table_rows = []
            for r in pnl_results:
                color = "#00e676" if r['Total P&L'] > 0 else "#ff1744" if r['Total P&L'] < 0 else "#888"
                pnl_table_rows.append({
                    'Scenario': r['Scenario'],
                    'Total P&L': f"${r['Total P&L']:,.2f}",
                    'Per Contract': f"${r['Total P&L']/max(1,sum(p['quantity'] for p in st.session_state.positions)):,.2f}",
                    'BP Equiv': f"{r['Total P&L']/25:.1f}bp"
                })

            pnl_show_df = pd.DataFrame(pnl_table_rows)
            st.markdown(bb_card("◈ P&L SUMMARY TABLE",
                bb_table(pnl_show_df, green_cols=['Total P&L'])),
                unsafe_allow_html=True)

        else:
            st.markdown("""<div style="color:#555;font-size:0.8rem;font-family:'JetBrains Mono',mono;
                padding:40px;text-align:center;">ADD POSITIONS ON THE LEFT TO SEE P&L ANALYSIS</div>""",
                unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════
# TAB 5 — CURVE & ANALYTICS
# ═══════════════════════════════════════════════════════════════

with tabs[5]:
    st.markdown("""<div style="font-family:'JetBrains Mono',monospace;color:#ff6d00;
        font-size:0.65rem;letter-spacing:0.15em;padding:8px 0;">
        ◈ SOFR FORWARD CURVE ANALYTICS — TERM RATES — CONVEXITY ADJUSTMENTS</div>""",
        unsafe_allow_html=True)

    bp_c = get_basis_params()
    all_prices = price_all_contracts(
        st.session_state.contracts[:16],
        st.session_state.base_sofr / 100,
        get_fomc_changes_decimal(),
        **bp_c
    )

    ca_t1, ca_t2 = st.columns(2)

    with ca_t1:
        # Forward rate curve with multiple scenarios
        curve_fig = go.Figure()

        # Base case (current settings)
        curve_fig.add_trace(go.Scatter(
            x=all_prices['Contract'],
            y=all_prices['Rate (%)'],
            mode='lines+markers',
            name='Current',
            line=dict(color='#ff6d00', width=2.5),
            marker=dict(size=7, symbol='diamond'),
            hovertemplate='<b>%{x}</b><br>Rate: %{y:.5f}%<extra></extra>'
        ))

        # Show 2-3 scenarios for comparison
        colors_sc = ['#00e676', '#ff1744', '#00b4d8']
        for si, sc in enumerate(st.session_state.scenarios[:3]):
            sc_df = price_all_contracts(
                st.session_state.contracts[:16],
                sc['base_sofr'] / 100, sc['changes'],
                bp_c['me_basis'], bp_c['qe_basis'], bp_c['ye_basis'],
                bp_c['apply_me'], bp_c['apply_qe'], bp_c['apply_ye']
            )
            curve_fig.add_trace(go.Scatter(
                x=sc_df['Contract'],
                y=sc_df['Rate (%)'],
                mode='lines',
                name=sc['name'],
                line=dict(color=colors_sc[si % 3], width=1.5, dash='dot'),
                opacity=0.7,
                hovertemplate=f'<b>{sc["name"]}</b><br>%{{x}}: %{{y:.4f}}%<extra></extra>'
            ))

        cur_layout = make_plotly_dark()
        cur_layout.update(
            title=dict(text='◈ SR3 FORWARD RATE CURVE (with scenarios)',
                       font=dict(color='#ff6d00', size=13), x=0.02),
            yaxis=dict(title='Rate (%)', tickformat='.3f', ticksuffix='%'),
            height=340,
        )
        curve_fig.update_layout(cur_layout)
        st.plotly_chart(curve_fig, use_container_width=True, config={'displayModeBar': False})

    with ca_t2:
        # Price curve (not rate)
        price_fig = go.Figure()
        price_fig.add_trace(go.Scatter(
            x=all_prices['Contract'],
            y=all_prices['Price'],
            mode='lines+markers',
            fill='tozeroy',
            fillcolor='rgba(255,109,0,0.05)',
            name='Price',
            line=dict(color='#ff9100', width=2),
            marker=dict(size=6, color='#ff6d00')
        ))
        price_layout = make_plotly_dark()
        price_layout.update(
            title=dict(text='◈ SR3 PRICE CURVE (IMM Index)',
                       font=dict(color='#ff6d00', size=13), x=0.02),
            yaxis=dict(title='Price', tickformat='.3f'),
            height=340
        )
        price_fig.update_layout(price_layout)
        st.plotly_chart(price_fig, use_container_width=True, config={'displayModeBar': False})

    st.markdown("<hr>", unsafe_allow_html=True)

    ca_b1, ca_b2, ca_b3 = st.columns(3)

    with ca_b1:
        # Implied term SOFR rates
        st.markdown("""<div style="color:#00b4d8;font-size:0.65rem;font-family:'JetBrains Mono',mono;
            margin-bottom:6px;">◈ IMPLIED TERM SOFR RATES</div>""", unsafe_allow_html=True)
        term_rows = []
        for months in [3, 6, 9, 12, 18, 24]:
            n = months // 3
            cs = st.session_state.contracts[:n]
            ps = all_prices['Price'].tolist()[:n]
            if cs and ps:
                term_rate = implied_term_sofr(cs, ps, months)
                term_rows.append({
                    'Term': f"{months}M",
                    'Implied Rate': f"{term_rate:.4f}%",
                    'vs Base': f"{term_rate - st.session_state.base_sofr:+.4f}%"
                })
        term_df = pd.DataFrame(term_rows)
        st.markdown(bb_table(term_df, green_cols=['vs Base']), unsafe_allow_html=True)

    with ca_b2:
        # Convexity adjustments
        st.markdown("""<div style="color:#e040fb;font-size:0.65rem;font-family:'JetBrains Mono',mono;
            margin-bottom:6px;">◈ CONVEXITY ADJUSTMENTS (est.)</div>""", unsafe_allow_html=True)

        vol_input = st.slider("Vol Assumption (bps)", 30, 100, 50, key="vol_slider")
        sigma = vol_input / 10000

        conv_rows = []
        for i, c in enumerate(st.session_state.contracts[:8]):
            t1 = i * 0.25
            conv = estimate_convexity_adj(t1, sigma)
            conv_rows.append({
                'Contract': c['name'],
                'T to Expiry': f"{t1:.2f}Y",
                'Convex Adj (bp)': f"{conv:.2f}",
                'OIS-Futures Bias': f"{conv:.2f}bp"
            })

        conv_df = pd.DataFrame(conv_rows)
        st.markdown(bb_table(conv_df), unsafe_allow_html=True)

    with ca_b3:
        # DV01 profile
        st.markdown("""<div style="color:#ffd600;font-size:0.65rem;font-family:'JetBrains Mono',mono;
            margin-bottom:6px;">◈ DV01 PROFILE BY CONTRACT</div>""", unsafe_allow_html=True)

        dv01_rows = []
        for c, (_, row) in zip(st.session_state.contracts[:8], all_prices.iterrows()):
            dv01_approx = c['days'] / 360 * 10000  # bps per year equivalent
            dv01_rows.append({
                'Contract': c['name'],
                'Days': c['days'],
                'DV01 ($)': '$25.00',
                'DV01 (pts)': f"{c['days']/360*0.01:.5f}",
                'Approx Notional': f"${c['days']/360*1e6:,.0f}"
            })

        dv01_df = pd.DataFrame(dv01_rows)
        st.markdown(bb_table(dv01_df), unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════
# TAB 6 — SPREADS & FLIES
# ═══════════════════════════════════════════════════════════════

with tabs[6]:
    st.markdown("""<div style="font-family:'JetBrains Mono',monospace;color:#ff6d00;
        font-size:0.65rem;letter-spacing:0.15em;padding:8px 0;">
        ◈ CALENDAR SPREADS · BUTTERFLY ANALYSIS · PACK & BUNDLE PRICING</div>""",
        unsafe_allow_html=True)

    bp_s = get_basis_params()
    spread_prices = price_all_contracts(
        st.session_state.contracts[:12],
        st.session_state.base_sofr / 100,
        get_fomc_changes_decimal(),
        **bp_s
    )
    prices_list = spread_prices['Price'].tolist()
    cn_list = spread_prices['Contract'].tolist()

    sf_t1, sf_t2 = st.columns(2)

    with sf_t1:
        st.markdown("""<div style="color:#00b4d8;font-size:0.65rem;font-family:'JetBrains Mono',mono;
            margin-bottom:6px;">◈ CALENDAR SPREADS (bps, Front − Back)</div>""", unsafe_allow_html=True)

        spread_rows = []
        for i in range(len(prices_list) - 1):
            sp = calculate_spread(prices_list[i], prices_list[i+1])
            spread_rows.append({
                'Spread': f"{cn_list[i]} / {cn_list[i+1]}",
                'Spread (bp)': f"{sp['spread']:.2f}",
                'Spread (pts)': f"{sp['spread_pts']:.5f}",
                'Dollar Value': f"${sp['dollar_value']:.2f}"
            })

        spread_df = pd.DataFrame(spread_rows)
        st.markdown(bb_table(spread_df, green_cols=['Spread (bp)']), unsafe_allow_html=True)

    with sf_t2:
        st.markdown("""<div style="color:#e040fb;font-size:0.65rem;font-family:'JetBrains Mono',mono;
            margin-bottom:6px;">◈ BUTTERFLY VALUES (bps)</div>""", unsafe_allow_html=True)

        fly_rows = []
        for i in range(len(prices_list) - 2):
            fly = calculate_butterfly(prices_list[i], prices_list[i+1], prices_list[i+2])
            fly_rows.append({
                'Fly': f"{cn_list[i]} / {cn_list[i+1]} / {cn_list[i+2]}",
                'Fly (bp)': f"{fly['fly']:.2f}",
                'Fly (pts)': f"{fly['fly_pts']:.6f}",
                'Dollar Value': f"${fly['dollar_value']:.2f}"
            })

        fly_df = pd.DataFrame(fly_rows)
        st.markdown(bb_table(fly_df, green_cols=['Fly (bp)']), unsafe_allow_html=True)

    st.markdown("<hr>", unsafe_allow_html=True)

    # Pack and Bundle pricing
    sf_b1, sf_b2 = st.columns(2)

    with sf_b1:
        st.markdown("""<div style="color:#ffd600;font-size:0.65rem;font-family:'JetBrains Mono',mono;
            margin-bottom:6px;">◈ PACK PRICING (Quarterly Strip Average Price Change)</div>""",
            unsafe_allow_html=True)

        packs = {
            'Red (Yr 1)': prices_list[:4],
            'Green (Yr 2)': prices_list[4:8],
            'Blue (Yr 3)': prices_list[8:12] if len(prices_list) >= 12 else prices_list[8:],
        }

        pack_rows = []
        for pack_name, pack_prices in packs.items():
            if pack_prices:
                avg_price = sum(pack_prices) / len(pack_prices)
                avg_rate = 100 - avg_price
                pack_rows.append({
                    'Pack': pack_name,
                    'Legs': len(pack_prices),
                    'Avg Price': f"{avg_price:.4f}",
                    'Avg Rate': f"{avg_rate:.4f}%",
                    'DV01 ($)': f"${len(pack_prices) * 25:.0f}"
                })

        pack_df = pd.DataFrame(pack_rows)
        st.markdown(bb_table(pack_df), unsafe_allow_html=True)

    with sf_b2:
        st.markdown("""<div style="color:#ffd600;font-size:0.65rem;font-family:'JetBrains Mono',mono;
            margin-bottom:6px;">◈ CUSTOM SPREAD CALCULATOR</div>""", unsafe_allow_html=True)

        cs_col1, cs_col2 = st.columns(2)
        with cs_col1:
            leg1_c = st.selectbox("Leg 1", cn_list[:8], key="cs_leg1")
            leg1_qty = st.number_input("Qty 1", value=1, min_value=1, key="cs_qty1")
            leg1_dir = st.selectbox("Dir 1", ["Buy", "Sell"], key="cs_dir1")
        with cs_col2:
            leg2_c = st.selectbox("Leg 2", cn_list[:8], index=1, key="cs_leg2")
            leg2_qty = st.number_input("Qty 2", value=1, min_value=1, key="cs_qty2")
            leg2_dir = st.selectbox("Dir 2", ["Sell", "Buy"], key="cs_dir2")

        p1 = prices_list[cn_list.index(leg1_c)] if leg1_c in cn_list else 0
        p2 = prices_list[cn_list.index(leg2_c)] if leg2_c in cn_list else 0

        s1 = 1 if leg1_dir == "Buy" else -1
        s2 = 1 if leg2_dir == "Buy" else -1

        spread_val = (s1 * p1 * leg1_qty - s2 * p2 * leg2_qty) * 100
        dollar_val = spread_val * 25

        cs_val_color = "#00e676" if spread_val > 0 else "#ff1744" if spread_val < 0 else "#888"
        st.markdown(f"""
        <div style="background:#0d0d0d;border:1px solid #1f1f1f;border-left:3px solid {cs_val_color};
                    padding:12px;margin-top:8px;">
            <div style="color:#555;font-size:0.62rem;font-family:'JetBrains Mono',mono;">SPREAD VALUE</div>
            <div style="color:{cs_val_color};font-size:1.6rem;font-weight:700;
                        font-family:'JetBrains Mono',mono;">{spread_val:+.2f} bp</div>
            <div style="color:#888;font-size:0.75rem;font-family:'JetBrains Mono',mono;">
                ${dollar_val:+,.2f} per spread</div>
            <div style="color:#555;font-size:0.65rem;font-family:'JetBrains Mono',mono;margin-top:4px;">
                {leg1_dir} {leg1_qty}x {leg1_c} @ {p1:.3f} | 
                {leg2_dir} {leg2_qty}x {leg2_c} @ {p2:.3f}</div>
        </div>""", unsafe_allow_html=True)

    # Spread chart over scenarios
    st.markdown("<hr>", unsafe_allow_html=True)
    st.markdown("""<div style="color:#888;font-size:0.65rem;font-family:'JetBrains Mono',mono;
        margin-bottom:6px;">◈ CALENDAR SPREAD CHART ACROSS SCENARIOS</div>""", unsafe_allow_html=True)

    spread_sel_c = st.columns(2)
    with spread_sel_c[0]:
        sp_leg1 = st.selectbox("Spread: Front Leg", cn_list[:8], key="sp_leg1_chart")
    with spread_sel_c[1]:
        sp_leg2 = st.selectbox("Spread: Back Leg", cn_list[:8], index=1, key="sp_leg2_chart")

    sp_sc_vals = []
    for sc in st.session_state.scenarios:
        sc_df = price_all_contracts(
            st.session_state.contracts[:12],
            sc['base_sofr'] / 100, sc['changes'],
            bp_s['me_basis'], bp_s['qe_basis'], bp_s['ye_basis'],
            bp_s['apply_me'], bp_s['apply_qe'], bp_s['apply_ye']
        )
        sc_price_map = dict(zip(sc_df['Contract'], sc_df['Price']))
        sp1 = sc_price_map.get(sp_leg1, 0)
        sp2 = sc_price_map.get(sp_leg2, 0)
        sp_sc_vals.append({
            'scenario': sc['name'],
            'spread': (sp1 - sp2) * 100,
            'color': sc['color']
        })

    sp_bar_fig = go.Figure(go.Bar(
        x=[v['scenario'] for v in sp_sc_vals],
        y=[v['spread'] for v in sp_sc_vals],
        marker_color=[v['color'] for v in sp_sc_vals],
        text=[f"{v['spread']:.1f}bp" for v in sp_sc_vals],
        textposition='outside',
        textfont=dict(size=9, color='#888')
    ))
    sp_bar_layout = make_plotly_dark()
    sp_bar_layout.update(
        title=dict(text=f'◈ {sp_leg1}/{sp_leg2} SPREAD BY SCENARIO',
                   font=dict(color='#ff6d00', size=12), x=0.02),
        yaxis=dict(title='Spread (bp)', zeroline=True, zerolinecolor='#333'),
        xaxis=dict(tickangle=-30, tickfont=dict(size=8)),
        height=280
    )
    sp_bar_fig.update_layout(sp_bar_layout)
    st.plotly_chart(sp_bar_fig, use_container_width=True, config={'displayModeBar': False})

# ═══════════════════════════════════════════════════════════════
# TAB 7 — RISK MONITOR
# ═══════════════════════════════════════════════════════════════

with tabs[7]:
    st.markdown("""<div style="font-family:'JetBrains Mono',monospace;color:#ff6d00;
        font-size:0.65rem;letter-spacing:0.15em;padding:8px 0;">
        ◈ RISK DASHBOARD — DV01 PROFILE — CARRY ANALYSIS — MEETING PROBABILITIES</div>""",
        unsafe_allow_html=True)

    bp_r = get_basis_params()
    risk_prices = price_all_contracts(
        st.session_state.contracts[:12],
        st.session_state.base_sofr / 100,
        get_fomc_changes_decimal(),
        **bp_r
    )

    rm_t1, rm_t2, rm_t3 = st.columns(3)

    with rm_t1:
        # DV01 profile chart
        st.markdown("""<div style="color:#ffd600;font-size:0.65rem;font-family:'JetBrains Mono',mono;
            margin-bottom:4px;">◈ CONTRACT DV01 PROFILE</div>""", unsafe_allow_html=True)

        dv_fig = go.Figure(go.Bar(
            x=risk_prices['Contract'].tolist(),
            y=[25.0] * len(risk_prices),
            marker_color='#ff6d00',
            name='DV01 ($25/bp)',
            text=['$25'] * len(risk_prices),
            textposition='outside',
            textfont=dict(size=8, color='#888')
        ))
        dv_layout = make_plotly_dark()
        dv_layout.update(
            title=dict(text='DV01 per contract', font=dict(color='#ffd600', size=10), x=0.02),
            yaxis=dict(title='$ per bp', range=[0, 35]),
            height=200, margin=dict(l=40, r=10, t=35, b=60)
        )
        dv_fig.update_layout(dv_layout)
        st.plotly_chart(dv_fig, use_container_width=True, config={'displayModeBar': False})

    with rm_t2:
        # Approximate carry analysis
        st.markdown("""<div style="color:#00e676;font-size:0.65rem;font-family:'JetBrains Mono',mono;
            margin-bottom:4px;">◈ CARRY INDICATORS (SOFR LEVEL)</div>""", unsafe_allow_html=True)

        carry_rows = []
        for i, c in enumerate(st.session_state.contracts[:6]):
            # Carry = SOFR rate at start of period (approximation)
            # Positive carry when SOFR > (100 - price) at period start
            contract_rate = risk_prices.iloc[i]['Rate (%)'] if i < len(risk_prices) else 0
            carry_bps = (st.session_state.base_sofr - contract_rate) * 100
            carry_rows.append({
                'Contract': c['name'],
                'Rate (%)': f"{contract_rate:.4f}%",
                'vs Base': f"{carry_bps:+.1f}bp",
                'Daily P&L ($)': f"${carry_bps * 25 / 365:.2f}"
            })

        carry_df = pd.DataFrame(carry_rows)
        st.markdown(bb_table(carry_df, green_cols=['vs Base', 'Daily P&L ($)']),
                    unsafe_allow_html=True)

    with rm_t3:
        # Implied meeting probabilities
        st.markdown("""<div style="color:#00b4d8;font-size:0.65rem;font-family:'JetBrains Mono',mono;
            margin-bottom:4px;">◈ MEETING CUT PROBABILITIES (IMPLIED)</div>""", unsafe_allow_html=True)

        prob_rows = []
        for mtg in DEFAULT_FOMC_DATES_2026_2027[:6]:
            chg = st.session_state.fomc_changes.get(mtg, 0)
            # Simple implied probability from rate changes
            if chg == 0:
                prob = 0.0
            elif chg == -25:
                prob = 100.0
            elif chg == -50:
                prob = 100.0
            else:
                prob = max(0, min(100, chg * -4.0))

            color = "#00e676" if prob > 50 else "#ffd600" if prob > 20 else "#555"
            prob_rows.append({
                'Meeting': mtg.strftime('%d %b %y'),
                'Change (bp)': f"{chg:+d}",
                'Cut Prob': f"{prob:.0f}%",
                'Exp Move': f"{chg:.0f}bp" if chg != 0 else "HOLD"
            })

        prob_df = pd.DataFrame(prob_rows)
        st.markdown(bb_table(prob_df, green_cols=['Cut Prob']), unsafe_allow_html=True)

    st.markdown("<hr>", unsafe_allow_html=True)

    # Bottom: full risk summary
    rm_b1, rm_b2 = st.columns(2)

    with rm_b1:
        # Rate change sensitivity table
        st.markdown("""<div style="color:#ff9100;font-size:0.65rem;font-family:'JetBrains Mono',mono;
            margin-bottom:6px;">◈ PARALLEL SHIFT SENSITIVITY ($ per contract)</div>""",
            unsafe_allow_html=True)

        shifts = [-100, -75, -50, -25, +25, +50, +75, +100]
        sens_rows = []
        for shift in shifts:
            row = {'Shift (bp)': f"{shift:+d}bp"}
            for c_name, base_p in zip(cn_list[:6], risk_prices['Price'].tolist()[:6]):
                pnl_val = shift * 25  # simplified: $25 per bp regardless of direction
                if shift > 0:
                    pnl_val = -shift * 25  # price falls when rates rise
                row[c_name] = f"${pnl_val:,.0f}"
            sens_rows.append(row)

        sens_df = pd.DataFrame(sens_rows)
        st.markdown(bb_table(sens_df), unsafe_allow_html=True)

    with rm_b2:
        # Scenario P&L heat (positions)
        if st.session_state.positions:
            st.markdown("""<div style="color:#e040fb;font-size:0.65rem;font-family:'JetBrains Mono',mono;
                margin-bottom:6px;">◈ POSITION P&L HEAT MAP</div>""", unsafe_allow_html=True)

            pos_names = [f"{p['direction'][0].upper()} {p['contract']}" for p in st.session_state.positions]
            sc_names_heat = [sc['name'] for sc in st.session_state.scenarios[:8]]

            z_heat = []
            for sc in st.session_state.scenarios[:8]:
                sc_df = price_all_contracts(
                    st.session_state.contracts[:12],
                    sc['base_sofr'] / 100, sc['changes'],
                    bp_r['me_basis'], bp_r['qe_basis'], bp_r['ye_basis'],
                    bp_r['apply_me'], bp_r['apply_qe'], bp_r['apply_ye']
                )
                price_map = dict(zip(sc_df['Contract'], sc_df['Price']))
                row_pnl = []
                for pos in st.session_state.positions:
                    exit_p = price_map.get(pos['contract'], pos['entry_price'])
                    pnl = calculate_pnl(pos['entry_price'], exit_p, pos['quantity'], pos['direction'])
                    row_pnl.append(pnl['dollar_pnl'])
                z_heat.append(row_pnl)

            heat2 = go.Figure(go.Heatmap(
                z=z_heat,
                x=pos_names,
                y=sc_names_heat,
                colorscale=[[0, '#ff1744'], [0.5, '#0a0a0a'], [1, '#00e676']],
                text=[[f"${v:,.0f}" for v in row] for row in z_heat],
                texttemplate="%{text}",
                textfont=dict(size=9),
                colorbar=dict(tickfont=dict(color='#888', size=9))
            ))
            heat2_layout = make_plotly_dark()
            heat2_layout.update(
                title=dict(text='Position P&L by Scenario', font=dict(color='#e040fb', size=11), x=0.02),
                height=300,
                margin=dict(l=150, r=30, t=50, b=60)
            )
            heat2.update_layout(heat2_layout)
            st.plotly_chart(heat2, use_container_width=True, config={'displayModeBar': False})
        else:
            # Contract specs reference
            st.markdown("""<div style="color:#555;font-size:0.65rem;font-family:'JetBrains Mono',mono;
                margin-bottom:6px;">◈ CONTRACT SPECIFICATIONS REFERENCE</div>""", unsafe_allow_html=True)

            specs = [
                ["Product", "CME Three-Month SOFR Futures (SR3)"],
                ["Delivery Months", "Mar, Jun, Sep, Dec (quarterly)"],
                ["Reference Quarter", "3rd Wed of named month → 3rd Wed of named+3 months"],
                ["Settlement", "Cash-settled, 100 − R"],
                ["R Definition", "Compounded daily SOFR (actual/360)"],
                ["Contract Value", "$2,500 per index point"],
                ["DV01", "$25 per basis point per contract"],
                ["Min Tick (near)", "0.005 (½bp) = $12.50"],
                ["Min Tick (defer)", "0.01 (1bp) = $25.00"],
                ["Trading Hours", "CME Globex: Sun–Fri 17:00–16:00 CT"],
                ["Last Trade", "Business day before 3rd Wed of delivery month"],
                ["Listings", "39 consecutive quarterly months"],
            ]
            specs_df = pd.DataFrame(specs, columns=["Spec", "Detail"])
            st.markdown(bb_table(specs_df), unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════
# TAB 8 — LIVE DATA (NYFRB SOFR FEED)
# ═══════════════════════════════════════════════════════════════

with tabs[8]:
    st.markdown("""<div style="font-family:'JetBrains Mono',monospace;color:#00b4d8;
        font-size:0.65rem;letter-spacing:0.15em;padding:8px 0;">
        ◈ NYFRB LIVE SOFR FEED · AUTO-REFRESH EACH MORNING · SEED TERMINAL WITH LATEST FIXING
        </div>""", unsafe_allow_html=True)

    # ── Auto-refresh logic ──
    if should_auto_refresh():
        with st.spinner("Fetching latest SOFR data from NYFRB..."):
            sofr_result = fetch_nyfrb_rates("sofr", 30)
            effr_result = fetch_nyfrb_rates("effr", 30)
            st.session_state.live_sofr_data = {"sofr": sofr_result, "effr": effr_result}
            st.session_state.live_data_fetch_date = date.today()
            st.session_state.live_data_error = sofr_result.get("error")

    ld = st.session_state.live_sofr_data
    sofr_rates = ld["sofr"]["rates"] if ld and ld["sofr"]["rates"] else []
    effr_rates = ld["effr"]["rates"] if ld and ld["effr"]["rates"] else []
    live_error = st.session_state.live_data_error

    # Status bar
    fetch_dt = st.session_state.live_data_fetch_date
    status_color = "#00e676" if (sofr_rates and not live_error) else "#ff1744"
    status_text  = f"LIVE  ·  Last fetch: {fetch_dt}  ·  {len(sofr_rates)} days loaded" if sofr_rates else "NO DATA"

    ld_h1, ld_h2, ld_h3 = st.columns([2, 1, 1])
    with ld_h1:
        st.markdown(f"""
        <div style="background:#050505;border:1px solid #1f1f1f;border-left:3px solid {status_color};
                    padding:8px 12px;font-family:'JetBrains Mono',monospace;">
            <span style="color:{status_color};font-size:0.65rem;font-weight:700;">● {status_text}</span>
            {'<br><span style="color:#ff1744;font-size:0.6rem;">' + live_error + '</span>' if live_error else ''}
        </div>""", unsafe_allow_html=True)
    with ld_h2:
        if st.button("↺  REFRESH NOW", key="ld_refresh"):
            st.session_state.live_sofr_data = None
            st.session_state.live_data_fetch_date = None
            st.rerun()
    with ld_h3:
        # Seed terminal with latest SOFR
        if sofr_rates:
            latest_rate = sofr_rates[0].get("percentRate", sofr_rates[0].get("rate", None))
            if latest_rate:
                if st.button(f"⬆  USE {latest_rate:.4f}% AS BASE", key="ld_use_rate"):
                    st.session_state.base_sofr = float(latest_rate)
                    for sc in st.session_state.scenarios:
                        sc["base_sofr"] = float(latest_rate)
                    st.success(f"Base SOFR updated to {latest_rate:.4f}%")
                    st.rerun()

    st.markdown("<hr>", unsafe_allow_html=True)

    if live_error and not sofr_rates:
        st.markdown(f"""
        <div style="background:#0d0d0d;border:1px solid #ff1744;padding:20px 24px;
                    font-family:'JetBrains Mono',monospace;margin:20px 0;">
            <div style="color:#ff1744;font-size:0.7rem;font-weight:700;margin-bottom:8px;">
                ⚠ NYFRB API UNAVAILABLE</div>
            <div style="color:#888;font-size:0.65rem;">Error: {live_error}</div>
            <div style="color:#555;font-size:0.62rem;margin-top:12px;line-height:1.8;">
                The NYFRB public API may be temporarily unavailable or the app is running
                without internet access (e.g. locally without network). The terminal remains
                fully functional using manually configured rates.<br><br>
                NYFRB API URL: markets.newyorkfed.org/api/rates/sofr/last/30.json
            </div>
        </div>""", unsafe_allow_html=True)

    elif sofr_rates:
        # ── Key metrics ──
        latest = sofr_rates[0]
        prev   = sofr_rates[1] if len(sofr_rates) > 1 else sofr_rates[0]

        latest_sofr  = float(latest.get("percentRate", latest.get("rate", 0)))
        prev_sofr    = float(prev.get("percentRate",   prev.get("rate", 0)))
        sofr_chg     = latest_sofr - prev_sofr
        vol_30d      = float(np.std([float(r.get("percentRate", r.get("rate", 0))) for r in sofr_rates]))
        sofr_30d_avg = float(np.mean([float(r.get("percentRate", r.get("rate", 0))) for r in sofr_rates]))

        latest_effr  = float(effr_rates[0].get("percentRate", effr_rates[0].get("rate", 0))) if effr_rates else None
        sofr_effr_spread = round(latest_sofr - latest_effr, 4) if latest_effr else None

        m1, m2, m3, m4, m5 = st.columns(5)
        chg_color = "#00e676" if sofr_chg > 0 else "#ff1744" if sofr_chg < 0 else "#888"
        with m1:
            st.metric("LATEST SOFR", f"{latest_sofr:.4f}%",
                      delta=f"{sofr_chg:+.4f}%" if sofr_chg != 0 else "unchanged")
        with m2:
            st.metric("30D AVG SOFR", f"{sofr_30d_avg:.4f}%")
        with m3:
            st.metric("30D VOL (σ)", f"{vol_30d*100:.2f}bp")
        with m4:
            if latest_effr:
                st.metric("EFFR", f"{latest_effr:.4f}%")
        with m5:
            if sofr_effr_spread is not None:
                spread_color = "normal" if sofr_effr_spread >= 0 else "inverse"
                st.metric("SOFR−EFFR", f"{sofr_effr_spread:+.4f}%")

        st.markdown("<hr>", unsafe_allow_html=True)
        ld_l, ld_r = st.columns([1, 1.4])

        with ld_l:
            # SOFR history table
            hist_rows = []
            for r in sofr_rates[:20]:
                rate_val = float(r.get("percentRate", r.get("rate", 0)))
                chg_val  = rate_val - float(sofr_rates[sofr_rates.index(r)+1].get("percentRate",
                            sofr_rates[sofr_rates.index(r)+1].get("rate", rate_val))
                            ) if sofr_rates.index(r) < len(sofr_rates)-1 else 0.0
                hist_rows.append({
                    "Date":       r.get("effectiveDate", ""),
                    "SOFR (%)":   f"{rate_val:.4f}",
                    "Change":     f"{chg_val:+.4f}%" if chg_val != 0 else "—",
                    "1st %tile":  r.get("percentile1", "—"),
                    "25th %tile": r.get("percentile25", "—"),
                    "75th %tile": r.get("percentile75", "—"),
                    "99th %tile": r.get("percentile99", "—"),
                    "Volume ($B)":r.get("volumeInBillions", "—"),
                })

            hist_df = pd.DataFrame(hist_rows)
            st.markdown(bb_card("◈ SOFR FIXING HISTORY (NYFRB)",
                bb_table(hist_df, green_cols=["Change"]),
                color="#00b4d8"), unsafe_allow_html=True)

            # Export
            ld_exp1, ld_exp2 = st.columns(2)
            with ld_exp1:
                export_btn_csv(hist_df, "sofr_history.csv", "⬇ CSV")
            with ld_exp2:
                effr_rows = []
                for r in effr_rates[:20]:
                    effr_rows.append({
                        "Date":      r.get("effectiveDate", ""),
                        "EFFR (%)":  r.get("percentRate", r.get("rate", "")),
                        "Volume ($B)": r.get("volumeInBillions", "—"),
                    })
                effr_df = pd.DataFrame(effr_rows) if effr_rows else pd.DataFrame()
                export_btn_excel(
                    {"SOFR History": hist_df, "EFFR History": effr_df},
                    "nyfrb_rates.xlsx", "⬇ EXCEL"
                )

        with ld_r:
            # SOFR time-series chart
            chart_dates  = [r.get("effectiveDate", "") for r in reversed(sofr_rates)]
            chart_values = [float(r.get("percentRate", r.get("rate", 0))) for r in reversed(sofr_rates)]

            p1_vals  = [r.get("percentile1",  None) for r in reversed(sofr_rates)]
            p99_vals = [r.get("percentile99", None) for r in reversed(sofr_rates)]

            live_fig = go.Figure()

            # P1–P99 band (if data available)
            if any(v is not None for v in p1_vals):
                live_fig.add_trace(go.Scatter(
                    x=chart_dates + chart_dates[::-1],
                    y=[float(v) if v else chart_values[i] for i,v in enumerate(p99_vals)] +
                      [float(v) if v else chart_values[i] for i,v in enumerate(reversed(p1_vals))],
                    fill="toself",
                    fillcolor="rgba(0,180,216,0.07)",
                    line=dict(color="rgba(0,0,0,0)"),
                    name="P1–P99 Range",
                    showlegend=True,
                    hoverinfo="skip",
                ))

            live_fig.add_trace(go.Scatter(
                x=chart_dates,
                y=chart_values,
                mode="lines+markers",
                name="SOFR Fixing",
                line=dict(color="#00b4d8", width=2.5),
                marker=dict(size=5, color="#90e0ef"),
                hovertemplate="<b>%{x}</b><br>SOFR: %{y:.4f}%<extra></extra>"
            ))

            if effr_rates:
                effr_dates  = [r.get("effectiveDate","") for r in reversed(effr_rates)]
                effr_values = [float(r.get("percentRate", r.get("rate",0))) for r in reversed(effr_rates)]
                live_fig.add_trace(go.Scatter(
                    x=effr_dates, y=effr_values,
                    mode="lines", name="EFFR",
                    line=dict(color="#ffd600", width=1.5, dash="dot"),
                    hovertemplate="<b>%{x}</b><br>EFFR: %{y:.4f}%<extra></extra>"
                ))

            ll = make_plotly_dark()
            ll.update(
                title=dict(text="◈ SOFR & EFFR — 30-DAY HISTORY (NYFRB)",
                           font=dict(color="#00b4d8", size=13), x=0.02),
                yaxis=dict(title="Rate (%)", tickformat=".4f", ticksuffix="%"),
                xaxis=dict(title="Date", tickangle=-30),
                height=320,
                legend=dict(bgcolor="#0d0d0d")
            )
            live_fig.update_layout(ll)
            st.plotly_chart(live_fig, use_container_width=True, config={"displayModeBar": False})

            # SOFR distribution (histogram of last 30 fixings)
            dist_fig = go.Figure(go.Histogram(
                x=chart_values,
                nbinsx=15,
                marker_color="#00b4d8",
                marker_line=dict(color="#0a0a0a", width=0.5),
                name="SOFR Distribution",
                hovertemplate="Rate: %{x:.4f}%<br>Count: %{y}<extra></extra>"
            ))
            dl = make_plotly_dark()
            dl.update(
                title=dict(text="◈ 30-DAY SOFR FIXING DISTRIBUTION",
                           font=dict(color="#00b4d8", size=11), x=0.02),
                xaxis=dict(title="SOFR (%)", tickformat=".4f"),
                yaxis=dict(title="Occurrences"),
                height=220,
                margin=dict(l=50, r=10, t=40, b=50),
                showlegend=False,
            )
            dist_fig.update_layout(dl)
            st.plotly_chart(dist_fig, use_container_width=True, config={"displayModeBar": False})

    # Data source credit
    st.markdown("""
    <div style="color:#333;font-size:0.6rem;font-family:'JetBrains Mono',monospace;
                margin-top:12px;border-top:1px solid #1a1a1a;padding-top:8px;">
        Data source: Federal Reserve Bank of New York (NYFRB) — markets.newyorkfed.org
        · SOFR: Secured Overnight Financing Rate · EFFR: Effective Federal Funds Rate
        · Rates are published by NYFRB each business day by approx. 8:00 AM ET
    </div>""", unsafe_allow_html=True)


# ───────────────────────────────────────────────────────────────
# GLOBAL EXPORT TOOLBAR (bottom of every page)
# ───────────────────────────────────────────────────────────────

st.markdown("<hr>", unsafe_allow_html=True)
st.markdown("""<div style="color:#555;font-size:0.62rem;letter-spacing:0.1em;
    font-family:'JetBrains Mono',monospace;margin-bottom:6px;">◈ EXPORT CURRENT STATE</div>""",
    unsafe_allow_html=True)

_ex_cols = st.columns(4)

# Build current pricing snapshot
_bp_ex = get_basis_params()
_prices_ex = price_all_contracts(
    st.session_state.contracts[:12],
    st.session_state.base_sofr / 100,
    get_fomc_changes_decimal(),
    **_bp_ex
)
_prices_ex_clean = _prices_ex[[c for c in _prices_ex.columns if not c.startswith("_")]].copy()

# Build scenario comparison snapshot
_sc_rows_ex = []
for _sc in st.session_state.scenarios:
    _sc_df = price_all_contracts(
        st.session_state.contracts[:8],
        _sc["base_sofr"] / 100, _sc["changes"],
        _bp_ex["me_basis"], _bp_ex["qe_basis"], _bp_ex["ye_basis"],
        _bp_ex["apply_me"], _bp_ex["apply_qe"], _bp_ex["apply_ye"]
    )
    _row = {"Scenario": _sc["name"], "Base SOFR": _sc["base_sofr"]}
    for _, _r in _sc_df.iterrows():
        _row[_r["Contract"]] = round(_r["Price"], 5)
    _sc_rows_ex.append(_row)
_sc_comp_ex = pd.DataFrame(_sc_rows_ex)

# FOMC path snapshot
_fomc_rows_ex = [{"Meeting": str(d), "Change (bp)": v,
                  "Cumulative (bp)": sum(list(get_fomc_changes_decimal().values())[:i+1])}
                 for i, (d, v) in enumerate(get_fomc_changes_decimal().items())]
_fomc_ex = pd.DataFrame(_fomc_rows_ex)

with _ex_cols[0]:
    export_btn_csv(_prices_ex_clean, "sr3_prices.csv", "⬇  PRICES CSV")

with _ex_cols[1]:
    export_btn_csv(_sc_comp_ex, "sr3_scenarios.csv", "⬇  SCENARIOS CSV")

with _ex_cols[2]:
    export_btn_excel({
        "SR3 Prices":     _prices_ex_clean,
        "Scenarios":      _sc_comp_ex,
        "FOMC Path":      _fomc_ex,
    }, "sr3_terminal_export.xlsx", "⬇  FULL EXCEL")

with _ex_cols[3]:
    if st.session_state.live_sofr_data and st.session_state.live_sofr_data["sofr"]["rates"]:
        _live_rows = [{"Date": r.get("effectiveDate",""),
                       "SOFR (%)": r.get("percentRate", r.get("rate","")),
                       "Volume ($B)": r.get("volumeInBillions","—")}
                      for r in st.session_state.live_sofr_data["sofr"]["rates"]]
        export_btn_csv(pd.DataFrame(_live_rows), "sofr_live.csv", "⬇  LIVE SOFR CSV")
    else:
        st.markdown('<div style="color:#333;font-size:0.62rem;font-family:JetBrains Mono,mono;'
                    'padding-top:6px;">No live data loaded</div>', unsafe_allow_html=True)


# Footer
st.markdown("""
<div style="text-align:center;padding:16px;color:#333;font-size:0.6rem;
            font-family:'JetBrains Mono',monospace;border-top:1px solid #1a1a1a;margin-top:8px;">
◈ SR3 SOFR TERMINAL · CME THREE-MONTH SOFR FUTURES · FOR PROFESSIONAL USE ONLY ·
NOT INVESTMENT ADVICE · ALL CALCULATIONS ARE INDICATIVE ◈
</div>""", unsafe_allow_html=True)

