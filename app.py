# app_seedling_pro_final_safe.py
import streamlit as st
import pandas as pd
import numpy as np
from PIL import Image
import tensorflow as tf
from tensorflow.keras.utils import img_to_array
from datetime import datetime, timedelta
import sqlalchemy as sa
from sqlalchemy import Column, Integer, String, Table, MetaData
import bcrypt
import io
import plotly.express as px
import os

# ---------- Config ----------
st.set_page_config(page_title="🍎 Seedling Pro Full Dashboard", layout="wide")

# ---------- Language Helper ----------
lang = st.sidebar.selectbox("Language / زبان", ["English", "فارسی"])
EN = (lang == "English")
def t(fa, en): return en if EN else fa

# ---------- Styles ----------
st.markdown("""
<style>
.kpi-card{background:#ffffffdd;border-radius:14px;padding:14px;margin-bottom:16px;box-shadow:0 6px 20px rgba(0,0,0,0.15);transition:transform 0.2s;}
.kpi-card:hover{transform:scale(1.03);}
.kpi-title{font-size:16px;font-weight:bold;color:#333;}
.kpi-value{font-size:28px;font-weight:bold;color:#2d9f3f;}
.task-done{background:#d1ffd1;}
.task-pending{background:#ffe6e6;}
body{font-family: 'Vazir', sans-serif; direction: rtl;}
</style>
""", unsafe_allow_html=True)

# ---------- Database (Persistent) ----------
DB_DIR = os.path.join(os.getcwd(), "data")
os.makedirs(DB_DIR, exist_ok=True)
DB_FILE = os.path.join(DB_DIR, "users_seedling_final_safe.db")
engine = sa.create_engine(f"sqlite:///{DB_FILE}", connect_args={"check_same_thread": False})
meta = MetaData()

users_table = Table('users', meta,
                    Column('id', Integer, primary_key=True),
                    Column('username', String, unique=True, nullable=False),
                    Column('password_hash', String, nullable=False),
                    Column('role', String, default='user'))

data_table = Table('user_data', meta,
                   Column('id', Integer, primary_key=True),
                   Column('username', String),
                   Column('date', String),
                   Column('height', Integer),
                   Column('leaves', Integer),
                   Column('notes', String),
                   Column('prune', String),
                   Column('task', String),
                   Column('task_done', String))

meta.create_all(engine)

# ---------- Session ----------
if 'user' not in st.session_state: st.session_state['user'] = None
if 'role' not in st.session_state: st.session_state['role'] = None
if 'tree_data' not in st.session_state: st.session_state['tree_data'] = pd.DataFrame(columns=['date','height','leaves','notes','prune'])
if 'schedule' not in st.session_state: st.session_state['schedule'] = pd.DataFrame(columns=['date','task','task_done'])
if 'df_future' not in st.session_state: st.session_state['df_future'] = pd.DataFrame()

# ---------- Auth Functions ----------
def register(username, password, role='user'):
    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    with engine.begin() as conn:
        conn.execute(users_table.insert().values(username=username, password_hash=hashed, role=role))

def login(username, password):
    with engine.begin() as conn:
        r = conn.execute(sa.select(users_table).where(users_table.c.username==username)).first()
        if r:
            stored_hash = r._mapping['password_hash']
            role = r._mapping['role']
            if bcrypt.checkpw(password.encode(), stored_hash.encode()):
                return role
        return None

def load_user_data(username):
    with engine.begin() as conn:
        rows = conn.execute(sa.select(data_table).where(data_table.c.username==username)).fetchall()
    df = pd.DataFrame([r._mapping for r in rows])
    if not df.empty:
        st.session_state['tree_data'] = df[['date','height','leaves','notes','prune']]
        st.session_state['schedule'] = df[['date','task','task_done']]
    else:
        st.session_state['tree_data'] = pd.DataFrame(columns=['date','height','leaves','notes','prune'])
        start_date = datetime.today()
        schedule_list = []
        for week in range(52):
            date = start_date + timedelta(weeks=week)
            schedule_list.append([date.date(), t("آبیاری","Watering"), False])
            if week % 4 == 0: schedule_list.append([date.date(), t("کوددهی","Fertilization"), False])
            if week % 12 == 0: schedule_list.append([date.date(), t("هرس","Pruning"), False])
            if week % 6 == 0: schedule_list.append([date.date(), t("بازرسی بیماری","Disease Check"), False])
        st.session_state['schedule'] = pd.DataFrame(schedule_list, columns=['date','task','task_done'])

# ---------- Auth UI ----------
mode = st.sidebar.radio(t("حالت","Mode"), [t("ورود","Login"), t("ثبت نام","Sign Up"), t("دمو","Demo")])
username = st.text_input(t("نام کاربری","Username"))
password = st.text_input(t("رمز عبور","Password"), type="password")

if mode == t("ثبت نام","Sign Up") and st.button(t("ثبت نام","Register")):
    if username and password:
        register(username, password)
        st.success(t("ثبت نام انجام شد. اکنون وارد شوید.","Registered successfully. Please login."))
    else:
        st.error(t("نام کاربری و رمز را وارد کنید.","Provide username & password."))

if mode == t("ورود","Login") and st.button(t("ورود","Login")):
    role = login(username, password)
    if role:
        st.session_state['user'] = username
        st.session_state['role'] = role
        if 'tree_data' not in st.session_state:
            st.session_state['tree_data'] = pd.DataFrame(columns=['date','height','leaves','notes','prune'])
        if 'schedule' not in st.session_state:
            st.session_state['schedule'] = pd.DataFrame(columns=['date','task','task_done'])
        load_user_data(username)
        st.success(t("ورود موفق ✅","Login successful ✅"))

# ---------- Dashboard ----------
if st.session_state['user']:
    st.write(f"{t('خوش آمدید','Welcome')}, {st.session_state['user']}!")
    # اینجا می‌توانید تمام بخش‌های Home, Tracking, Schedule, Prediction, Download, Logout را اضافه کنید
