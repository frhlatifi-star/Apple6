import streamlit as st
import pandas as pd
from datetime import datetime
import bcrypt
import sqlalchemy as sa
from sqlalchemy import Column, Integer, String, Table, MetaData, ForeignKey
from PIL import Image, ImageStat
import numpy as np
import io, os, base64

# ---------- Config ----------
st.set_page_config(page_title="سیبتک 🍎 مدیریت نهال", page_icon="🍎", layout="wide")

# ---------- Custom Style ----------
def local_css():
    st.markdown("""
    <style>
    body {
        background: linear-gradient(135deg, #d9fdd3, #f0fff0) !important;
        font-family: "Vazirmatn", Tahoma, sans-serif;
    }
    .app-header {
        display: flex;
        align-items: center;
        justify-content: flex-start;
        margin-bottom: 1rem;
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
    logo_path = "logo.png"  # حتما لوگو کنار app.py ذخیره شده باشد
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

# ---------- Auth State ----------
if "page" not in st.session_state:
    st.session_state.page = "dashboard"
if "user" not in st.session_state:
    st.session_state.user = None

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
        <div class="card" onclick="window.parent.postMessage({type: 'streamlit:setComponentValue', key: 'page', value: 'logout'}, '*')">
            <div class="card-icon">🚪</div>
            <div>خروج</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

# ---------- Page Routing ----------
if st.session_state.page == "dashboard":
    dashboard()
elif st.session_state.page == "home":
    st.header("خانه")
    st.write("📊 اینجا خلاصه وضعیت نهال‌ها نمایش داده می‌شود.")
    if st.button("بازگشت به داشبورد"):
        st.session_state.page = "dashboard"
elif st.session_state.page == "tracking":
    st.header("🌱 پایش نهال")
    st.write("اینجا می‌توانید رشد و وضعیت نهال‌ها را ثبت کنید.")
    if st.button("بازگشت به داشبورد"):
        st.session_state.page = "dashboard"
elif st.session_state.page == "schedule":
    st.header("📅 زمان‌بندی فعالیت‌ها")
    if st.button("بازگشت به داشبورد"):
        st.session_state.page = "dashboard"
elif st.session_state.page == "predict":
    st.header("📈 پیش‌بینی سلامت نهال (آپلود تصویر)")
    if st.button("بازگشت به داشبورد"):
        st.session_state.page = "dashboard"
elif st.session_state.page == "disease":
    st.header("🍎 ثبت بیماری / یادداشت")
    if st.button("بازگشت به داشبورد"):
        st.session_state.page = "dashboard"
elif st.session_state.page == "download":
    st.header("📥 دانلود داده‌ها (CSV)")
    if st.button("بازگشت به داشبورد"):
        st.session_state.page = "dashboard"
elif st.session_state.page == "logout":
    st.success("✅ شما خارج شدید.")
    if st.button("بازگشت به داشبورد"):
        st.session_state.page = "dashboard"
