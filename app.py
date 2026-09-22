"""
OMR Barcode & QR Code Enterprise Print & Management System
Features:
- Modern & responsive UI design
- Secure Login & Session Authentication
- System Settings (Logo branding, Username & Password change)
- SQLite Database & Generation History with Search and Date Filtering
- Bilingual Support (English by default, 1-click toggle to Bengali)
- Rich Icon Navigation & Sidebar
- Executive Dashboard with metrics, charts & quick launchers
"""

import streamlit as st
import io
import os
import base64
import fitz  # PyMuPDF
import pandas as pd
from datetime import datetime, date, timedelta
from PIL import Image

import omr_qr_engine
import omr_pdf_overlay_system
import db_manager
from translations import t

# Resolve every app asset/output relative to this file. This keeps the app
# working when a hosting provider starts Streamlit from a different cwd.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(BASE_DIR)

def file_to_base64(filepath):
    """Converts an image file to Base64 data URL string."""
    if filepath and os.path.exists(filepath):
        with open(filepath, "rb") as f:
            b64_str = base64.b64encode(f.read()).decode("utf-8")
            ext = os.path.splitext(filepath)[1].lower().replace('.', '')
            if ext == 'svg':
                mime = 'image/svg+xml'
            elif ext in ['jpg', 'jpeg']:
                mime = 'image/jpeg'
            elif ext == 'webp':
                mime = 'image/webp'
            else:
                mime = 'image/png'
            return f"data:{mime};base64,{b64_str}"
    return ""

# ----------------- Page Configuration ----------------- #
st.set_page_config(
    page_title="OMR Barcode & QR Print System",
    page_icon="🖨️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ----------------- Database Initialization ----------------- #
db_manager.init_db()

# ----------------- Session State Initialization ----------------- #
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "username" not in st.session_state:
    st.session_state.username = "admin"
if "user_role" not in st.session_state:
    st.session_state.user_role = "admin"
if "lang" not in st.session_state:
    # Rule 5: UI is English by default, button to toggle to Bengali
    st.session_state.lang = "EN"
if "nav_page" not in st.session_state:
    st.session_state.nav_page = "Dashboard"
if "date_preset" not in st.session_state:
    st.session_state.date_preset = "All Time"

lang = st.session_state.lang

# ----------------- Global Helper: Current Logo ----------------- #
def get_current_logo():
    """Returns path to the currently active logo or None."""
    custom_logo = db_manager.get_setting("logo_path", "")
    if custom_logo and os.path.exists(custom_logo):
        return custom_logo
    if os.path.exists("default_logo.png"):
        return "default_logo.png"
    return None

# ----------------- Bengali & Global Typography (Ador Noirrit / Lipighor) ----------------- #
def get_font_css():
    """Injects Ador Noirrit font (as shown in user screenshot) with local base64 fallback."""
    font_file = "AdorNoirrit.woff2"
    if os.path.exists(font_file):
        try:
            with open(font_file, "rb") as f:
                b64_font = base64.b64encode(f.read()).decode("utf-8")
            src_font = f"url('data:font/woff2;base64,{b64_font}') format('woff2'), url('https://lipighor.com/webfont/newNoirritWeb.woff2?V=2.0') format('woff2')"
        except Exception:
            src_font = "url('https://lipighor.com/webfont/newNoirritWeb.woff2?V=2.0') format('woff2')"
    else:
        src_font = "url('https://lipighor.com/webfont/newNoirritWeb.woff2?V=2.0') format('woff2')"
    
    return f"""
    <style>
    @font-face {{
        font-family: 'AdorNoirrit';
        src: {src_font};
        font-weight: normal;
        font-style: normal;
        font-display: swap;
    }}
    html, body, .stMarkdown p, h1, h2, h3, h4, h5, h6, label, button, input, select, textarea {{
        font-family: 'AdorNoirrit', 'Hind Siliguri', 'Kalpurush', -apple-system, sans-serif !important;
    }}
    /* Protect Material Symbols icons & eliminate any stray expand_more text */
    [data-testid="stIconMaterial"],
    .material-symbols-rounded,
    .material-symbols-outlined {{
        font-family: 'Material Symbols Rounded', 'Material Icons' !important;
    }}
    [data-testid="stExpanderToggleIcon"],
    summary [data-testid="stIconMaterial"] {{
        display: none !important;
        visibility: hidden !important;
    }}
    code, pre, .code-display-box, [data-testid="stCodeBlock"], [data-testid="stCodeBlock"] * {{
        font-family: 'Consolas', 'Courier New', monospace !important;
    }}
    </style>
    """

# ----------------- Custom Styling & CSS ----------------- #
CUSTOM_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=Hind+Siliguri:wght@400;600;700&display=swap');


/* App Background & Padding */
.main .block-container {
    padding-top: 1.8rem;
    padding-bottom: 3rem;
    max-width: 1250px;
}

/* Metric Cards - Sleek Executive Dark Navy Cards (Non-White) */
.metric-card {
    background: #1e293b !important;
    border-radius: 12px;
    padding: 20px 22px;
    border: 1px solid #334155 !important;
    box-shadow: 0 4px 14px rgba(0, 0, 0, 0.25);
    position: relative;
    overflow: hidden;
    transition: transform 0.2s, box-shadow 0.2s;
}
.metric-card:hover {
    transform: translateY(-2px);
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.35);
    border-color: #475569 !important;
}
.metric-card::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    width: 4px;
    height: 100%;
}
.card-blue::before { background: #38bdf8; }
.card-green::before { background: #34d399; }
.card-amber::before { background: #fbbf24; }
.card-purple::before { background: #a78bfa; }

.metric-title {
    font-size: 0.82rem;
    font-weight: 700;
    color: #94a3b8 !important;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin-bottom: 8px;
}
.metric-value {
    font-size: 1.9rem;
    font-weight: 800;
    color: #f8fafc !important;
    line-height: 1.2;
}
.metric-subtitle {
    font-size: 0.8rem;
    color: #cbd5e1 !important;
    margin-top: 6px;
}

/* Custom Glass Panels - Executive Dark */
.glass-panel {
    background: #1e293b !important;
    border: 1px solid #334155 !important;
    border-radius: 14px;
    padding: 24px;
    box-shadow: 0 4px 14px rgba(0, 0, 0, 0.25);
    margin-bottom: 20px;
    color: #f8fafc !important;
}

/* Quick Action Button Cards */
.action-box {
    background: #0f172a !important;
    border: 1px solid #334155 !important;
    border-radius: 10px;
    padding: 16px;
    text-align: center;
    cursor: pointer;
    transition: all 0.2s;
    color: #f8fafc !important;
}
.action-box:hover {
    background: #24324d !important;
    border-color: #38bdf8 !important;
    transform: translateY(-2px);
}

/* Badges */
.badge-tag {
    display: inline-block;
    padding: 3px 8px;
    border-radius: 6px;
    font-size: 0.75rem;
    font-weight: 600;
}
.badge-blue { background: #1e3a8a; color: #93c5fd; }
.badge-green { background: #064e3b; color: #6ee7b7; }
.badge-amber { background: #78350f; color: #fde68a; }

/* Executive Dark Navy Sidebar Polish */
section[data-testid="stSidebar"] {
    background-color: #0f172a !important;
    border-right: 1px solid #1e293b !important;
}
section[data-testid="stSidebar"] hr {
    border-color: rgba(255, 255, 255, 0.1) !important;
}
.sidebar-user-card {
    background: #1e293b !important;
    border: 1px solid rgba(255, 255, 255, 0.1) !important;
    border-radius: 12px !important;
    padding: 14px !important;
    margin-bottom: 16px !important;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.25) !important;
}

/* Sidebar Navigation Items - Beautiful Modern Dark Navy Cards with Strictly Uniform Tab Sizes */
section[data-testid="stSidebar"] div[data-testid="stRadio"] {
    background: transparent !important;
    padding: 0 !important;
    width: 100% !important;
}
section[data-testid="stSidebar"] div[data-testid="stRadio"] > div {
    gap: 8px !important;
    width: 100% !important;
    display: flex !important;
    flex-direction: column !important;
}
section[data-testid="stSidebar"] div[data-testid="stRadio"] label {
    width: 100% !important;
    min-height: 48px !important;
    height: 48px !important;
    box-sizing: border-box !important;
    background: #1e293b !important;
    border: 1px solid rgba(255, 255, 255, 0.08) !important;
    border-radius: 12px !important;
    padding: 0 16px !important;
    margin-bottom: 0px !important;
    transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1) !important;
    cursor: pointer !important;
    box-shadow: 0 2px 5px rgba(0, 0, 0, 0.2) !important;
    display: flex !important;
    align-items: center !important;
}
section[data-testid="stSidebar"] div[data-testid="stRadio"] label:hover {
    background: #24324d !important;
    border-color: #38bdf8 !important;
    transform: translateX(4px) !important;
    box-shadow: 0 4px 14px rgba(56, 189, 248, 0.2) !important;
}
section[data-testid="stSidebar"] div[data-testid="stRadio"] label div[data-testid="stMarkdownContainer"] {
    display: flex !important;
    align-items: center !important;
    width: 100% !important;
}
section[data-testid="stSidebar"] div[data-testid="stRadio"] label div[data-testid="stMarkdownContainer"] p {
    font-size: 0.95rem !important;
    font-weight: 700 !important;
    color: #f1f5f9 !important; /* Crisp, glowing readable text */
    line-height: 1.2 !important;
    margin: 0 !important;
}
/* Selected/Active Navigation Item */
section[data-testid="stSidebar"] div[data-testid="stRadio"] label:has(input:checked),
section[data-testid="stSidebar"] div[data-testid="stRadio"] label[data-checked="true"] {
    background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%) !important;
    border-color: #60a5fa !important;
    box-shadow: 0 4px 16px rgba(37, 99, 235, 0.45) !important;
}
section[data-testid="stSidebar"] div[data-testid="stRadio"] label:has(input:checked) div[data-testid="stMarkdownContainer"] p,
section[data-testid="stSidebar"] div[data-testid="stRadio"] label[data-checked="true"] div[data-testid="stMarkdownContainer"] p {
    color: #ffffff !important;
    font-weight: 800 !important;
}
section[data-testid="stSidebar"] div[data-testid="stRadio"] label:has(input:checked) div[data-testid="stRadioCircle"] {
    border-color: #ffffff !important;
    background-color: #ffffff !important;
}

/* Code Preview Box */
.code-display-box {
    background: #0f172a;
    color: #38bdf8;
    padding: 14px;
    border-radius: 8px;
    font-family: 'Consolas', 'Courier New', monospace;
    font-size: 0.95rem;
    overflow-x: auto;
    border: 1px solid #1e293b;
}

/* Primary Button Enhancements */
div.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%);
    color: white;
    border: none;
    font-weight: 600;
    border-radius: 8px;
    padding: 0.6rem 1.2rem;
    box-shadow: 0 4px 10px rgba(37, 99, 235, 0.25);
    transition: all 0.2s;
}
div.stButton > button[kind="primary"]:hover {
    box-shadow: 0 6px 14px rgba(37, 99, 235, 0.35);
    transform: translateY(-1px);
}

/* Clean Form Labels */
label {
    font-weight: 600 !important;
    color: #334155 !important;
}

/* 1. Login Form Card Styled in Executive Dark Navy (#0f172a - same as Navigation) */
div[data-testid="stForm"] {
    background: #0f172a !important;
    border: 1px solid #1e293b !important;
    border-radius: 16px !important;
    padding: 26px 24px !important;
    box-shadow: 0 20px 40px rgba(0, 0, 0, 0.5) !important;
    max-width: 380px !important;
    margin: 0 auto !important;
}
div[data-testid="stForm"] label,
div[data-testid="stForm"] label p {
    color: #f8fafc !important;
    font-weight: 700 !important;
}
div[data-testid="stForm"] input {
    background: #1e293b !important;
    color: #f8fafc !important;
    border: 1px solid #334155 !important;
    border-radius: 8px !important;
}
div[data-testid="stForm"] input:focus {
    border-color: #38bdf8 !important;
    box-shadow: 0 0 0 2px rgba(56, 189, 248, 0.3) !important;
}
div[data-testid="stForm"] [data-testid="stCheckbox"] label p {
    color: #cbd5e1 !important;
}

/* 4. Completely disable & hide "Deploy this app using..." button, popover, banner, and cards */
[data-testid="stAppDeployButton"],
div[data-testid="stAppDeployButton"],
.stAppDeployButton,
div[class*="stDeployButton"],
button[title*="Deploy"],
div:has(> [data-testid="stAppDeployButton"]),
.viewerBadge_container__r5tak,
.viewerBadge_link__1S137,
div[class*="viewerBadge"],
div[class*="deploy"],
footer {
    display: none !important;
    visibility: hidden !important;
    opacity: 0 !important;
    pointer-events: none !important;
}
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)
st.markdown(get_font_css(), unsafe_allow_html=True)


# =====================================================================
# 2. LOGIN PAGE (AUTHENTICATION)
# =====================================================================
def render_login_page():
    col_l, col_center, col_r = st.columns([1.6, 1.4, 1.6])
    with col_center:
        st.write("")

        with st.form("login_form", clear_on_submit=False):
            # Centered Bigger Brand Logo & Headings inside the card (Rule 1 & 2)
            logo_p = get_current_logo()
            logo_data = file_to_base64(logo_p) if logo_p else ""
            if logo_data:
                logo_img_tag = f'<img src="{logo_data}" style="max-height: 75px; max-width: 220px; object-fit: contain; margin-bottom: 12px; display: block; margin-left: auto; margin-right: auto;">'
            else:
                logo_img_tag = '<div style="font-size: 38px; margin-bottom: 8px; text-align: center;">🖨️</div>'

            st.markdown(f"""
            <div style="text-align: center; margin-bottom: 16px;">
                {logo_img_tag}
                <div style="font-size: 1.25rem; font-weight: 800; color: #f8fafc; line-height: 1.3; margin-bottom: 6px; text-align: center;">
                    {t('login_portal', lang)}
                </div>
                <div style="font-size: 0.84rem; color: #94a3b8; line-height: 1.4; text-align: center;">
                    {t('login_sub', lang)}
                </div>
            </div>
            """, unsafe_allow_html=True)

            username_input = st.text_input(f"👤 {t('username', lang)}", value="admin")
            password_input = st.text_input(f"🔒 {t('password', lang)}", type="password", value="")
            remember = st.checkbox(t('remember_me', lang), value=True)
            
            st.write("")
            submit_login = st.form_submit_button(f"🚀 {t('sign_in', lang)}", type="primary", use_container_width=True)

            if submit_login:
                user = db_manager.verify_user(username_input.strip(), password_input)
                if user:
                    st.session_state.authenticated = True
                    st.session_state.username = user["username"]
                    st.session_state.user_role = user.get("role", "admin")
                    st.success(t('success_login', lang))
                    st.rerun()
                else:
                    st.error(t('err_invalid_login', lang))

        # Copyright Notice instead of Default Credentials (Rule 1)
        st.markdown(f"""
        <div style="text-align: center; font-size: 0.75rem; color: #64748b; margin-top: 14px;">
            {t('copyright_text', lang)}
        </div>
        """, unsafe_allow_html=True)


# If not logged in, show login page and stop
if not st.session_state.authenticated:
    render_login_page()
    st.stop()



# =====================================================================
# 6. SIDEBAR & NAVIGATION (AUTHENTICATED)
# =====================================================================
with st.sidebar:
    # App Logo (Centered at the Top, Enlarged)
    active_logo = get_current_logo()
    logo_data = file_to_base64(active_logo) if active_logo else ""
    if logo_data:
        st.markdown(f"""
        <div style="text-align: center; margin: 10px auto 14px auto;">
            <img src="{logo_data}" style="max-height: 85px; max-width: 235px; object-fit: contain; display: block; margin: 0 auto;">
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div style="text-align: center; margin-bottom: 12px;">
            <div style="font-size: 38px;">🖨️</div>
            <div style="font-size: 1.2rem; font-weight: 800; color: #f8fafc;">OMR PRINT SYSTEM</div>
        </div>
        """, unsafe_allow_html=True)

    # 1. Enterprise Academic & Madrasah Board OMR Solution in two lines
    st.markdown("""
    <div style="text-align: center; font-size: 0.82rem; line-height: 1.4; color: #94a3b8; margin-bottom: 16px; font-weight: 700;">
        Enterprise Academic & Madrasah Board<br>OMR Solution
    </div>
    """, unsafe_allow_html=True)

    # Three-dots language selector in sidebar (Rule 3)
    side_l_col1, side_l_col2 = st.columns([3, 1])
    with side_l_col1:
        st.markdown(f"<div style='padding-top: 6px; font-size: 0.85rem; font-weight: 700; color: #94a3b8;'>🌐 {'বাংলা' if lang=='BN' else 'English'}</div>", unsafe_allow_html=True)
    with side_l_col2:
        with st.popover("⋮", help="Language / ভাষা"):
            if st.button("বাংলা (Bengali)", key="sb_pop_bn", use_container_width=True):
                st.session_state.lang = "BN"
                st.rerun()
            if st.button("English", key="sb_pop_en", use_container_width=True):
                st.session_state.lang = "EN"
                st.rerun()

    st.divider()

    # 2. Navigation Menu with Strictly Uniform Size Tabs
    st.markdown(f"**{t('nav_title', lang)}**")
    nav_options = [
        t('nav_dashboard', lang),
        t('nav_generator', lang),
        t('nav_calibrator', lang),
        t('nav_tester', lang),
        t('nav_history', lang),
        t('nav_settings', lang),
        t('nav_guide', lang)
    ]

    # Map current selection back if language changes
    nav_map_keys = ["Dashboard", "Generator", "Calibrator", "Tester", "History", "Settings", "Guide"]
    default_idx = 0
    if st.session_state.nav_page in nav_map_keys:
        default_idx = nav_map_keys.index(st.session_state.nav_page)

    selected_nav = st.radio(
        "Navigation",
        nav_options,
        index=default_idx,
        label_visibility="collapsed"
    )

    # Sync back to neutral key
    selected_idx = nav_options.index(selected_nav)
    st.session_state.nav_page = nav_map_keys[selected_idx]

    st.write("") # small spacing below Printing Guide

    # 3. Active User box placed below Printing Guide (Navigation Menu)
    st.markdown(f"""
    <div class="sidebar-user-card" style="margin-top: 6px; margin-bottom: 8px;">
        <div style="font-size: 0.72rem; color: #94a3b8; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px;">
            {t('user_profile', lang)}
        </div>
        <div style="font-size: 1.02rem; font-weight: 700; color: #f8fafc; margin-top: 2px;">
            👤 {st.session_state.username}
        </div>
        <div style="margin-top: 6px;">
            <span class="badge-tag badge-green">● Online</span>
            <span class="badge-tag badge-blue">{t('role_admin', lang)}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.divider()

    # Sign Out Button
    if st.button(f"{t('nav_logout', lang)}", use_container_width=True):
        st.session_state.authenticated = False
        st.session_state.username = "admin"
        st.rerun()

    # 5. Footer copyright: Army Printing Prass
    st.caption("Copyright © 2026 Army Printing Prass. All rights reserved.")


# =====================================================================
# 7. DASHBOARD PAGE
# =====================================================================
if st.session_state.nav_page == "Dashboard":
    st.markdown(f"## {t('dash_title', lang)}")
    st.markdown(f"**{t('dash_welcome', lang, user=st.session_state.username)}** — {t('dash_sub', lang)}")

    stats = db_manager.get_dashboard_stats()

    # 4 Executive Metric Cards
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(f"""
        <div class="metric-card card-blue">
            <div class="metric-title">{t('card_total_batches', lang)}</div>
            <div class="metric-value">{stats['total_batches']}</div>
            <div class="metric-subtitle">📦 Completed batches</div>
        </div>
        """, unsafe_allow_html=True)

    with c2:
        st.markdown(f"""
        <div class="metric-card card-green">
            <div class="metric-title">{t('card_total_sheets', lang)}</div>
            <div class="metric-value">{stats['total_sheets']}</div>
            <div class="metric-subtitle">📑 Total printable pages</div>
        </div>
        """, unsafe_allow_html=True)

    with c3:
        st.markdown(f"""
        <div class="metric-card card-amber">
            <div class="metric-title">{t('card_today_sheets', lang)}</div>
            <div class="metric-value">{stats['today_sheets']}</div>
            <div class="metric-subtitle">📅 Generated today</div>
        </div>
        """, unsafe_allow_html=True)

    with c4:
        latest = stats.get('latest_batch')
        latest_text = f"{latest['start_roll']} - {latest['end_roll']}" if latest else "None"
        st.markdown(f"""
        <div class="metric-card card-purple">
            <div class="metric-title">{t('card_latest_batch', lang)}</div>
            <div class="metric-value" style="font-size: 1.25rem; font-weight: 700; word-break: break-all;">{latest_text}</div>
            <div class="metric-subtitle">🔢 Latest serial range</div>
        </div>
        """, unsafe_allow_html=True)

    st.write("")

    # Quick Action Launchers
    st.markdown(f"### {t('quick_actions_title', lang)}")
    q_col1, q_col2, q_col3, q_col4 = st.columns(4)
    
    with q_col1:
        if st.button(f"🖨️ {t('action_new_batch', lang)}", use_container_width=True, type="primary"):
            st.session_state.nav_page = "Generator"
            st.rerun()
    with q_col2:
        if st.button(f"📜 {t('action_search_history', lang)}", use_container_width=True):
            st.session_state.nav_page = "History"
            st.rerun()
    with q_col3:
        if st.button(f"🔍 {t('action_test_code', lang)}", use_container_width=True):
            st.session_state.nav_page = "Tester"
            st.rerun()
    with q_col4:
        if st.button(f"⚙️ {t('action_change_settings', lang)}", use_container_width=True):
            st.session_state.nav_page = "Settings"
            st.rerun()

    st.write("")

    # Analytics and Charts Section
    col_chart1, col_chart2 = st.columns([1.6, 1])
    with col_chart1:
        st.markdown(f"#### 📈 {t('distribution_title', lang)}")
        trends = stats.get("trends", [])
        if trends:
            df_trends = pd.DataFrame(trends)
            df_trends["gen_date"] = pd.to_datetime(df_trends["gen_date"]).dt.strftime("%b %d")
            df_trends = df_trends.set_index("gen_date")
            st.bar_chart(df_trends[["sheet_count"]], height=240, color="#2563eb")
        else:
            st.info("No generation trend data yet. Sheets generated will appear here.")

    with col_chart2:
        st.markdown("#### 🎯 Print Mode Share")
        modes = stats.get("mode_breakdown", [])
        if modes:
            df_modes = pd.DataFrame(modes)
            df_modes["mode_label"] = df_modes["print_mode"].apply(
                lambda x: "Full Sheet" if "Full" in x or "সম্পূর্ণ" in x else "Overlay Only"
            )
            df_modes_agg = df_modes.groupby("mode_label")["sheets_count"].sum().reset_index()
            df_modes_agg = df_modes_agg.set_index("mode_label")
            st.bar_chart(df_modes_agg, height=240, color="#10b981")
        else:
            st.info("Mode distribution will display after generating batches.")

    st.write("")

    # Recent Generation Batches Table
    st.markdown(f"### {t('recent_batches_title', lang)}")
    recent_history = db_manager.get_history(limit=5)
    if recent_history:
        rec_data = []
        for r in recent_history:
            rec_data.append({
                t('col_batch_id', lang): f"#{r['id']}",
                t('col_date', lang): r['timestamp'],
                t('col_roll_range', lang): f"{r['start_roll']} → {r['end_roll']}",
                t('col_sheets', lang): r['sheet_count'],
                t('col_mode', lang): "Overlay Only" if "Overlay" in r['print_mode'] else "Full Sheet",
                t('col_file', lang): r['filename']
            })
        st.dataframe(pd.DataFrame(rec_data), use_container_width=True, hide_index=True)
    else:
        st.info(t('no_activity_yet', lang))


# =====================================================================
# 1. & 4. OMR PRINT GENERATOR (WITH DB ARCHIVING)
# =====================================================================
elif st.session_state.nav_page == "Generator":
    st.markdown(f"## {t('gen_title', lang)}")
    st.caption(t('gen_sub', lang))
    st.write("")

    TEMPLATE_DEFAULT = "omr_template.pdf"
    default_off_x = float(db_manager.get_setting('default_offset_x_mm', 0.2))
    default_off_y = float(db_manager.get_setting('default_offset_y_mm', 0.8))
    offset_x_mm = default_off_x
    offset_y_mm = default_off_y

    col_t1, col_t2 = st.columns([1.6, 1.2])

    with col_t1:
        st.markdown(f"#### {t('sec_template_mode', lang)}")
        uploaded_template = st.file_uploader(
            t('custom_template_label', lang),
            type=["pdf"],
            help="Leave empty to use the official Madrasah Board master template."
        )
        template_to_use = TEMPLATE_DEFAULT
        if uploaded_template is not None:
            template_to_use = "user_uploaded_template.pdf"
            with open(template_to_use, "wb") as f:
                f.write(uploaded_template.read())

        print_mode = st.radio(
            t('print_mode_label', lang),
            [
                t('mode_full', lang),
                t('mode_overlay', lang)
            ],
            index=0
        )
        is_overlay_only = "Overlay" in print_mode or "শুধু কালো" in print_mode

        # Micro-millimeter offset calibration for pre-printed paper
        with st.expander("📐 পেপার কাটিং ও মার্জিন এডজাস্টমেন্ট (Offset Calibration)", expanded=is_overlay_only):
            st.caption("প্রি-প্রিন্টেড কাগজের বক্সের সাথে কিউআর ও বারকোড নিখুঁতভাবে মেলাতে ডানে/বামে বা উপরে/নিচে সরান:")
            c_off1, c_off2 = st.columns(2)
            with c_off1:
                offset_x_mm = st.number_input("ডানে (+) / বামে (-) সরান (mm)", min_value=-20.0, max_value=20.0, value=default_off_x, step=0.5, format="%.1f")
            with c_off2:
                offset_y_mm = st.number_input("নিচে (+) / উপরে (-) সরান (mm)", min_value=-20.0, max_value=30.0, value=default_off_y, step=0.5, format="%.1f")

            import calibration_test
            if st.button("🎯 ১ পাতার টেস্ট শিট তৈরি করুন (Test Alignment Sheet)", use_container_width=True):
                calib_pdf = calibration_test.generate_calibration_sheet(
                    template_path=template_to_use,
                    output_path="omr_calibration_test.pdf",
                    sample_roll=str(2512100001),
                    offset_x_mm=offset_x_mm,
                    offset_y_mm=offset_y_mm
                )
                with open(calib_pdf, "rb") as f_calib:
                    st.download_button(
                        label="⬇️ টেস্ট শিট ডাউনলোড করুন (Download Alignment Test PDF)",
                        data=f_calib.read(),
                        file_name="omr_calibration_test.pdf",
                        mime="application/pdf",
                        type="primary",
                        use_container_width=True
                    )

    with col_t2:
        st.markdown(f"#### {t('sec_roll_settings', lang)}")
        start_roll = st.number_input(
            t('start_roll_label', lang),
            min_value=1,
            max_value=9999999999,
            value=2512100077,
            step=1
        )
        sheet_count = st.number_input(
            t('sheet_count_label', lang),
            min_value=1,
            max_value=500,
            value=5,
            step=1
        )
        include_qr3 = st.checkbox(
            t('include_qr3_label', lang),
            value=False
        )

    st.write("")
    btn_generate_pdf = st.button(t('btn_generate_pdf', lang), type="primary", use_container_width=True)

    if btn_generate_pdf:
        # Reserve globally unique 30-bit payload IDs. The visible roll number
        # remains independent, while the barcode's first/last bits stay fixed.
        code_sequence_start = db_manager.allocate_barcode_sequence(int(sheet_count))
        with st.spinner(t('generating_wait', lang)):
            items = []
            items_meta = []
            for i in range(sheet_count):
                curr_roll = str(start_roll + i)
                code_data = omr_qr_engine.create_full_omr_code_pair(
                    curr_roll,
                    unique_code_id=code_sequence_start + i
                )
                items.append({'roll': curr_roll, 'binary': code_data['binary_32']})
                items_meta.append({
                    'roll': curr_roll,
                    'unique_code_id': code_sequence_start + i,
                    'binary': code_data['binary_32'],
                    'hex': code_data['hex_suffix'],
                    'qr_payload': code_data['qr_payload']
                })

            end_roll = str(start_roll + sheet_count - 1)
            out_filename = f"omr_print_ready_{start_roll}_to_{end_roll}.pdf"
            mode_param = "overlay_only" if is_overlay_only else "full"

            # Execute generation
            omr_pdf_overlay_system.generate_overlaid_pdf(
                template_pdf_path=template_to_use,
                output_pdf_path=out_filename,
                items=items,
                mode=mode_param,
                include_qr3=include_qr3,
                offset_x_mm=offset_x_mm,
                offset_y_mm=offset_y_mm
            )

            # Calculate file size
            file_size_kb = os.path.getsize(out_filename) / 1024.0 if os.path.exists(out_filename) else 0.0

            # Store in Database! (Rule 4 requirement)
            batch_id = db_manager.add_generation_batch(
                start_roll=str(start_roll),
                end_roll=end_roll,
                sheet_count=sheet_count,
                print_mode="Overlay Only" if is_overlay_only else "Full Sheet",
                qr3_included=include_qr3,
                filename=out_filename,
                file_size_kb=file_size_kb,
                created_by=st.session_state.username,
                items_meta=items_meta
            )

            st.success(t('success_gen', lang, count=sheet_count))

            # Read generated PDF bytes
            with open(out_filename, "rb") as f:
                pdf_bytes = f.read()

            # Download and 1-Click Direct Print Buttons
            import streamlit.components.v1 as components
            col_dl1, col_dl2 = st.columns(2)
            with col_dl1:
                st.download_button(
                    label=t('btn_download_pdf', lang, filename=out_filename),
                    data=pdf_bytes,
                    file_name=out_filename,
                    mime="application/pdf",
                    use_container_width=True
                )
            with col_dl2:
                b64_pdf = base64.b64encode(pdf_bytes).decode("utf-8")
                print_component_html = f"""
                <button onclick="doDirectPrint()" style="width: 100%; height: 42px; background: #10b981; color: #022c22; font-weight: 700; border: none; border-radius: 8px; cursor: pointer; font-size: 0.95rem; display: flex; align-items: center; justify-content: center; gap: 8px; transition: all 0.2s;">
                    🖨️ সরাসরি প্রিন্ট করুন (1-Click Print Dialog)
                </button>
                <iframe id="directPrintFrame" style="position: absolute; width: 0; height: 0; border: 0; visibility: hidden;" src="data:application/pdf;base64,{b64_pdf}"></iframe>
                <script>
                function doDirectPrint() {{
                    var pf = document.getElementById('directPrintFrame');
                    if (pf) {{
                        pf.contentWindow.focus();
                        pf.contentWindow.print();
                    }}
                }}
                </script>
                """
                components.html(print_component_html, height=48)

            # High-res Visual Preview of Page 1
            doc_preview = fitz.open(out_filename)
            pix = doc_preview[0].get_pixmap(dpi=130)
            preview_img_path = "temp_page_preview.png"
            pix.save(preview_img_path)
            doc_preview.close()

            st.write("")
            st.markdown(f"#### {t('preview_heading', lang)}")
            st.image(preview_img_path, caption=t('first_page_caption', lang), use_container_width=True)


# =====================================================================
# 3. GRAPHICAL MARGIN CALIBRATOR (VISUAL INTERACTIVE OVERLAY)
# =====================================================================
elif st.session_state.nav_page == "Calibrator":
    st.markdown(f"## {t('nav_calibrator', lang)}")
    st.caption("প্রি-প্রিন্টেড ওএমআর পেপারের উপর কিউআর ও বারকোডের অবস্থান ইন্টারঅ্যাক্টিভভাবে দেখে নিখুঁতভাবে সমন্বয় করুন।")
    st.write("")

    import streamlit.components.v1 as components

    if os.path.exists("visual_calibrator.html"):
        with open("visual_calibrator.html", "r", encoding="utf-8") as f_calib:
            calib_html = f_calib.read()
        components.html(calib_html, height=840, scrolling=True)
    else:
        st.warning("visual_calibrator.html ফাইলটি পাওয়া যায়নি।")


# =====================================================================
# 4. GENERATION HISTORY & DATABASE SEARCH (WITH DATE FILTERING)
# =====================================================================
elif st.session_state.nav_page == "History":
    st.markdown(f"## {t('hist_title', lang)}")
    st.caption(t('hist_sub', lang))
    st.write("")

    # Filter Box Container (No expander, no expand_more)
    with st.container():
        st.markdown(f"""
        <div style="background: #1e293b; border: 1px solid #334155; border-radius: 12px; padding: 10px 16px; margin-bottom: 14px; font-weight: 700; color: #f8fafc;">
            🔍 Filters & Search Options
        </div>
        """, unsafe_allow_html=True)
        f_col1, f_col2, f_col3 = st.columns([1.5, 1.5, 1])

        with f_col1:
            search_query = st.text_input(t('search_label', lang), placeholder=t('search_placeholder', lang))

        with f_col2:
            # Preset Date Filter
            preset = st.selectbox(
                t('quick_filters', lang),
                [t('preset_all', lang), t('preset_today', lang), t('preset_7days', lang), t('preset_month', lang)]
            )
            
            today = date.today()
            if preset == t('preset_today', lang):
                start_d = today
                end_d = today
            elif preset == t('preset_7days', lang):
                start_d = today - timedelta(days=7)
                end_d = today
            elif preset == t('preset_month', lang):
                start_d = today.replace(day=1)
                end_d = today
            else:
                start_d = None
                end_d = None

        with f_col3:
            mode_filter = st.selectbox(
                t('mode_filter', lang),
                ["All", "Full Sheet", "Overlay Only"]
            )

        # Custom Date Range pickers
        d_col1, d_col2 = st.columns(2)
        with d_col1:
            custom_start = st.date_input(t('start_date', lang), value=start_d if start_d else today - timedelta(days=30))
        with d_col2:
            custom_end = st.date_input(t('end_date', lang), value=end_d if end_d else today)

        # Use custom range if user picked preset All or customized
        effective_start = start_d if preset != t('preset_all', lang) else custom_start
        effective_end = end_d if preset != t('preset_all', lang) else custom_end

    # Fetch from SQLite database
    history_records = db_manager.get_history(
        search_query=search_query,
        start_date=effective_start,
        end_date=effective_end,
        print_mode=mode_filter if mode_filter != "All" else None
    )

    st.markdown(f"**{t('records_found', lang, count=len(history_records))}**")

    if history_records:
        # Display summary & export button
        df_hist = pd.DataFrame(history_records)
        csv_data = df_hist.to_csv(index=False).encode('utf-8')
        st.download_button(
            label=f"📥 {t('btn_export_csv', lang)}",
            data=csv_data,
            file_name=f"omr_generation_history_{date.today()}.csv",
            mime="text/csv"
        )

        st.write("")

        # Interactive Table & Inspection
        for rec in history_records:
            with st.container():
                b_col1, b_col2, b_col3, b_col4 = st.columns([1, 2.5, 1.2, 1.5])
                with b_col1:
                    st.markdown(f"### #{rec['id']}")
                    st.caption(rec['timestamp'])
                with b_col2:
                    st.markdown(f"**Rolls:** `{rec['start_roll']}` → `{rec['end_roll']}`")
                    st.markdown(f"**Sheets:** {rec['sheet_count']} | **Mode:** `{rec['print_mode']}` | **Size:** {rec['file_size_kb']} KB")
                with b_col3:
                    qr3_badge = "Yes" if rec['qr3_included'] else "No"
                    st.markdown(f"QR3: **{qr3_badge}**")
                    st.caption(f"By: {rec['created_by']}")
                with b_col4:
                    # Direct Download button if file exists on disk
                    file_path = rec['filename']
                    if os.path.exists(file_path):
                        with open(file_path, "rb") as f_down:
                            pdf_raw = f_down.read()
                        st.download_button(
                            label=f"📥 Download PDF",
                            data=pdf_raw,
                            file_name=os.path.basename(file_path),
                            mime="application/pdf",
                            key=f"dl_btn_{rec['id']}"
                        )
                    else:
                        st.caption("PDF file archived/moved")

                # Details Popover to view individual QR codes & rolls (eliminates expander & expand_more)
                with st.popover(f"📋 {t('details_for_batch', lang, id=rec['id'], start=rec['start_roll'], end=rec['end_roll'])}", use_container_width=True):
                    batch_codes = db_manager.get_batch_records(rec['id'])
                    if batch_codes:
                        df_codes = pd.DataFrame(batch_codes)[['roll_number', 'binary_code', 'hex_suffix', 'qr_payload']]
                        st.dataframe(df_codes, use_container_width=True, hide_index=True)
                    else:
                        st.caption("No individual code item records stored for this batch.")

                st.divider()

    else:
        st.info(t('no_history', lang))


# =====================================================================
# 3. SETTINGS PAGE (LOGO, USERNAME, PASSWORD, DATABASE)
# =====================================================================
elif st.session_state.nav_page == "Settings":
    st.markdown(f"## {t('set_title', lang)}")
    st.caption(t('set_sub', lang))
    st.write("")

    tabs_set = st.tabs([
        t('tab_branding', lang),
        t('tab_security', lang),
        t('tab_db_maintenance', lang)
    ])

    # Tab 1: Logo, Left Banner & Background Wallpaper
    with tabs_set[0]:
        # --- 1. MAIN SYSTEM LOGO ---
        st.markdown(f"#### {t('curr_logo_title', lang)}")
        c_logo = get_current_logo()
        if c_logo:
            st.image(c_logo, width=180)
        else:
            st.info("Currently using default system title without custom logo.")

        st.markdown(f"**{t('upload_logo_label', lang)}**")
        new_logo_file = st.file_uploader(
            "Upload logo file",
            type=["png", "jpg", "jpeg", "svg", "webp"],
            key="uploader_logo",
            label_visibility="collapsed"
        )

        col_b1, col_b2 = st.columns(2)
        with col_b1:
            if st.button(t('btn_save_logo', lang), type="primary", key="btn_save_logo_btn"):
                if new_logo_file is not None:
                    os.makedirs("uploads", exist_ok=True)
                    ext = os.path.splitext(new_logo_file.name)[1]
                    saved_path = os.path.join("uploads", f"app_logo{ext}")
                    with open(saved_path, "wb") as f_out:
                        f_out.write(new_logo_file.read())
                    db_manager.set_setting("logo_path", saved_path)
                    st.success(t('logo_updated', lang))
                    st.rerun()
                else:
                    st.warning("Please choose a file to upload first.")

        with col_b2:
            if st.button(t('btn_reset_logo', lang), key="btn_reset_logo_btn"):
                db_manager.set_setting("logo_path", "")
                st.success(t('logo_reset', lang))
                st.rerun()

        st.divider()


    # Tab 2: Username & Password
    with tabs_set[1]:
        st.markdown(f"#### {t('change_credentials_title', lang)}")
        st.markdown(t('current_username_display', lang, user=st.session_state.username))
        st.write("")

        with st.form("cred_update_form"):
            new_user_val = st.text_input(t('new_username_label', lang), value="")
            curr_pwd_val = st.text_input(t('curr_password_label', lang), type="password")
            new_pwd_val = st.text_input(t('new_password_label', lang), type="password")
            confirm_pwd_val = st.text_input(t('confirm_password_label', lang), type="password")

            btn_update_cred = st.form_submit_button(t('btn_update_credentials', lang), type="primary")

            if btn_update_cred:
                # 1. Check current password
                verified = db_manager.verify_user(st.session_state.username, curr_pwd_val)
                if not verified:
                    st.error(t('err_wrong_curr_pwd', lang))
                elif new_pwd_val and new_pwd_val != confirm_pwd_val:
                    st.error(t('err_pwd_mismatch', lang))
                elif new_pwd_val and len(new_pwd_val) < 4:
                    st.error(t('err_pwd_too_short', lang))
                else:
                    target_user = new_user_val.strip() if new_user_val.strip() else st.session_state.username
                    target_pwd = new_pwd_val if new_pwd_val else None

                    ok, msg = db_manager.update_user_credentials(
                        current_username=st.session_state.username,
                        new_username=target_user,
                        new_password=target_pwd
                    )
                    if ok:
                        st.session_state.username = target_user
                        st.success(t('cred_updated_success', lang))
                    else:
                        st.error(f"Error: {msg}")

    # Tab 3: Database & Maintenance
    with tabs_set[2]:
        st.markdown(f"#### {t('db_info_title', lang)}")
        st.write(f"**{t('db_path_label', lang)}** `{db_manager.DB_PATH}`")
        if os.path.exists(db_manager.DB_PATH):
            db_sz = os.path.getsize(db_manager.DB_PATH) / 1024.0
            st.write(f"**Database Size:** {db_sz:.2f} KB")

            with open(db_manager.DB_PATH, "rb") as db_f:
                st.download_button(
                    label=t('btn_download_db', lang),
                    data=db_f.read(),
                    file_name="omr_system_backup.db",
                    mime="application/x-sqlite3"
                )

        st.write("")
        st.divider()
        st.markdown(f"#### {t('clear_history_label', lang)}")
        confirm_clear = st.checkbox(t('clear_history_confirm', lang), value=False)
        if st.button(t('btn_clear_history', lang), type="secondary"):
            if confirm_clear:
                db_manager.clear_all_history()
                st.success(t('history_cleared', lang))
                st.rerun()
            else:
                st.warning("Please check the confirmation box before clearing history.")


# =====================================================================
# SINGLE CODE TESTER PAGE
# =====================================================================
elif st.session_state.nav_page == "Tester":
    st.markdown(f"## {t('tester_title', lang)}")
    st.caption(t('tester_sub', lang))
    st.write("")

    test_input = st.text_input(
        t('tester_input_label', lang),
        value="2512100077"
    )

    if test_input.strip():
        res = omr_qr_engine.create_full_omr_code_pair(test_input.strip())

        # Display Decoded Data
        st.markdown("#### 🔬 Decoded Code Specifications")
        st.markdown(f"""
        <div class="code-display-box">
            <div><strong>32-Bit Binary :</strong> {res['binary_32']}</div>
            <div style="margin-top: 6px;"><strong>Hex Verifier :</strong> {res['hex_suffix']}</div>
            <div style="margin-top: 6px;"><strong>QR Payload   :</strong> {res['qr_payload']} (Length: {len(res['qr_payload'])})</div>
        </div>
        """, unsafe_allow_html=True)

        st.write("")
        col_c1, col_c2 = st.columns([2.5, 1.2])

        with col_c1:
            st.markdown(f"#### {t('barcode_preview_title', lang)}")
            st.image(res['barcode_png'], use_container_width=True)

            b_btn1, b_btn2 = st.columns(2)
            with b_btn1:
                # PNG download
                img_byte_arr = io.BytesIO()
                res['barcode_png'].save(img_byte_arr, format='PNG')
                st.download_button(
                    label=t('download_barcode_png', lang),
                    data=img_byte_arr.getvalue(),
                    file_name=f"omr_barcode_{res['hex_suffix']}.png",
                    mime="image/png",
                    use_container_width=True
                )
            with b_btn2:
                st.download_button(
                    label=t('download_barcode_svg', lang),
                    data=res['barcode_svg'],
                    file_name=f"omr_barcode_{res['hex_suffix']}.svg",
                    mime="image/svg+xml",
                    use_container_width=True
                )

        with col_c2:
            st.markdown(f"#### {t('qr_preview_title', lang)}")
            st.image(res['qr_png'], width=200)

            qr_byte_arr = io.BytesIO()
            res['qr_png'].save(qr_byte_arr, format='PNG')
            st.download_button(
                label=t('download_qr_png', lang),
                data=qr_byte_arr.getvalue(),
                file_name=f"omr_qr_{res['hex_suffix']}.png",
                mime="image/png",
                use_container_width=True
            )


# =====================================================================
# PRINTING GUIDE PAGE
# =====================================================================
elif st.session_state.nav_page == "Guide":
    st.markdown(f"## {t('guide_title', lang)}")
    st.caption(t('guide_sub', lang))
    st.write("")

    st.markdown(f"""
    ### 🖨️ {t('guide_scale_title', lang)}
    {t('guide_scale_desc', lang)}

    ---

    ### 📄 {t('guide_paper_title', lang)}
    {t('guide_paper_desc', lang)}

    ---

    ### 🎯 {t('guide_overlay_title', lang)}
    {t('guide_overlay_desc', lang)}
    """)
