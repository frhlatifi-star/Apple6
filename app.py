import streamlit as st
import pandas as pd
from datetime import datetime
import base64, os

# ---------- Config ----------
st.set_page_config(page_title="سیبتک 🍎 مدیریت نهال", page_icon="🍎", layout="wide")

# ---------- Custom Style ----------
def local_css():
    st.markdown("""
    <style>
    body {
        background: linear-gradient(135deg, #d9fdd3, #f0fff0) !important;
        font-family: "Vazirmatn", Tahoma, sans-serif;
        direction: rtl !important;
        text-align: right !important;
    }
    .block-container {
        direction: rtl !important;
        text-align: right !important;
    }
    .app-header {
        display: flex;
        align-items: center;
        justify-content: flex-start;
        margin-bottom: 1rem;
        direction: rtl !important;
    }
    .app-header h2 {
        margin: 0;
        color: #2e7d32;
    }
    .app-header .subtitle {
        color: #555;
        font-size: 14px;
    }
    .dashboard {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
        gap: 1rem;
        margin-top: 1rem;
        direction: rtl !important;
    }
    .card {
        background: white;
        padding: 1.5rem;
        border-radius: 16px;
        box-shadow: 0 4px 8px rgba(0,0,0,0.1);
        text-align: center;
        cursor: pointer;
        transition: all 0.2s ease-in-out;
    }
    .card:hover {
        transform: translateY(-4px);
        box-shadow: 0 6px 12px rgba(0,0,0,0.15);
        background: #f6fff6;
    }
    .card-icon {
        font-size: 32px;
        margin-bottom: 0.5rem;
        color: #388e3c;
    }
    .stButton>button {
        background-color: #388e3c !important;
        color: white !important;
        border-radius: 10px !important;
        padding: 0.5rem 1.2rem;
    }
    .stButton>button:hover {
        background-color: #2e7d32 !important;
    }
    </style>
    """, unsafe_allow_html=True)

local_css()

# ---------- Logo & Header ----------
def app_header():
    logo_path = "logo.png"  # لوگو کنار app.py ذخیره شود
    if os.path.exists(logo_path):
        with open(logo_path, "rb") as f:
            encoded_logo = base64.b64encode(f.read()).decode()
        logo_html = f"<img src='data:image/png;base64,{encoded_logo}' width='64' style='border-radius:12px;margin-left:12px;'>"
    else:
        logo_html = "<div style='font-size:40px;'>🍎</div>"

    st.markdown(
        f"""
        <div class="app-header">
            {logo_html}
            <div>
                <h2>سیبتک</h2>
                <div class="subtitle">مدیریت و پایش نهال</div>
            </div>
        </div>
        <hr/>
        """,
        unsafe_allow_html=True
    )

app_header()

# ---------- State ----------
if "page" not in st.session_state:
    st.session_state.page = "dashboard"
if "tracking_data" not in st.session_state:
    st.session_state.tracking_data = pd.DataFrame(columns=["تاریخ", "ارتفاع (cm)", "یادداشت"])

# ---------- Dashboard ----------
def dashboard():
    st.subheader("داشبورد اصلی")
    st.markdown("""
    <div class="dashboard">
        <div class="card" onclick="window.parent.postMessage({type: 'streamlit:setComponentValue', key: 'page', value: 'home'}, '*')">
            <div class="card-icon">🏠</div>
            <div>خانه</div>
        </div>
        <div class="card" onclick="window.parent.postMessage({type: 'streamlit:setComponentValue', key: 'page', value: 'tracking'}, '*')">
            <div class="card-icon">🌱</div>
            <div>پایش نهال</div>
        </div>
        <div class="card" onclick="window.parent.postMessage({type: 'streamlit:setComponentValue', key: 'page', value: 'schedule'}, '*')">
            <div class="card-icon">📅</div>
            <div>زمان‌بندی</div>
        </div>
        <div class="card" onclick="window.parent.postMessage({type: 'streamlit:setComponentValue', key: 'page', value: 'predict'}, '*')">
            <div class="card-icon">📈</div>
            <div>پیش‌بینی سلامت</div>
        </div>
        <div class="card" onclick="window.parent.postMessage({type: 'streamlit:setComponentValue', key: 'page', value: 'disease'}, '*')">
            <div class="card-icon">🍎</div>
            <div>ثبت بیماری</div>
        </div>
        <div class="card" onclick="window.parent.postMessage({type: 'streamlit:setComponentValue', key: 'page', value: 'download'}, '*')">
            <div class="card-icon">📥</div>
            <div>دانلود داده‌ها</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

# ---------- Pages ----------
def home():
    st.header("🏠 خانه")
    st.info("📊 اینجا خلاصه وضعیت نهال‌ها نمایش داده می‌شود.")

def tracking():
    st.header("🌱 پایش نهال")

    st.subheader("➕ ثبت داده جدید")
    with st.form("tracking_form", clear_on_submit=True):
        height = st.number_input("ارتفاع نهال (سانتی‌متر)", min_value=0, step=1)
        note = st.text_area("یادداشت (اختیاری)")
        submitted = st.form_submit_button("ثبت")

        if submitted:
            new_row = {
                "تاریخ": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "ارتفاع (cm)": height,
                "یادداشت": note
            }
            st.session_state.tracking_data = pd.concat(
                [st.session_state.tracking_data, pd.DataFrame([new_row])],
                ignore_index=True
            )
            st.success("✅ داده با موفقیت ثبت شد.")

    st.subheader("📋 تاریخچه پایش")
    if not st.session_state.tracking_data.empty:
        st.dataframe(st.session_state.tracking_data, use_container_width=True)
    else:
        st.warning("هنوز داده‌ای ثبت نشده است.")

# ---------- Router ----------
if st.session_state.page == "dashboard":
    dashboard()
elif st.session_state.page == "home":
    home()
elif st.session_state.page == "tracking":
    tracking()
elif st.session_state.page == "schedule":
    st.header("📅 زمان‌بندی فعالیت‌ها")
elif st.session_state.page == "predict":
    st.header("📈 پیش‌بینی سلامت نهال (آپلود تصویر)")
elif st.session_state.page == "disease":
    st.header("🍎 ثبت بیماری / یادداشت")
elif st.session_state.page == "download":
    st.header("📥 دانلود داده‌ها (CSV)")
    if st.button("📥 دانلود فایل"):
        st.download_button(
            "دانلود CSV",
            st.session_state.tracking_data.to_csv(index=False).encode("utf-8"),
            "tracking.csv",
            "text/csv",
            key="download-csv"
        )
