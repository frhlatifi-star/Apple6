import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from PIL import Image
import bcrypt
import sqlalchemy as sa
from sqlalchemy import Column, Integer, String, Table, MetaData, ForeignKey
import io

# ---------- Config ----------
st.set_page_config(page_title="🍎 Seedling Pro", page_icon="🍎", layout="wide")

# ---------- Database ----------
DB_FILE = "users_data.db"
engine = sa.create_engine(f"sqlite:///{DB_FILE}", connect_args={"check_same_thread": False})
meta = MetaData()

users_table = Table('users', meta,
                    Column('id', Integer, primary_key=True),
                    Column('username', String, unique=True, nullable=False),
                    Column('password_hash', String, nullable=False))

measurements = Table('measurements', meta,
                     Column('id', Integer, primary_key=True),
                     Column('user_id', Integer, ForeignKey('users.id')),
                     Column('date', String),
                     Column('height', Integer),
                     Column('leaves', Integer),
                     Column('notes', String),
                     Column('prune_needed', Integer))

meta.create_all(engine)
conn = engine.connect()

# ---------- Session ----------
if 'user_id' not in st.session_state: st.session_state['user_id'] = None
if 'username' not in st.session_state: st.session_state['username'] = None
if 'lang' not in st.session_state: st.session_state['lang'] = 'فارسی'

# ---------- Language ----------
def t(fa, en):
    return en if st.session_state['lang'] == 'English' else fa

def change_lang():
    st.experimental_rerun()

st.sidebar.selectbox("Language / زبان", ["فارسی", "English"], key='lang', on_change=change_lang)

# ---------- Password helpers ----------
def hash_password(password):
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def check_password(password, hashed):
    return bcrypt.checkpw(password.encode(), hashed.encode())

# ---------- Auth ----------
if st.session_state['user_id'] is None:
    st.sidebar.header(t("Authentication", "Authentication"))
    mode = st.sidebar.radio(t("Mode", "Mode"), [t("Login", "Login"), t("Sign Up", "Sign Up"), t("Demo", "Demo")])

    if mode == t("Sign Up", "Sign Up"):
        st.header(t("Sign Up", "Sign Up"))
        username = st.text_input(t("Username", "Username"))
        password = st.text_input(t("Password", "Password"), type="password")
        if st.button(t("Register", "Register")):
            if not username or not password:
                st.error(t("Provide username & password.", "Provide username & password."))
            else:
                sel = sa.select(users_table).where(users_table.c.username==username)
                r = conn.execute(sel).mappings().first()
                if r:
                    st.error(t("Username already exists.", "Username already exists."))
                else:
                    hashed = hash_password(password)
                    conn.execute(users_table.insert().values(username=username, password_hash=hashed))
                    st.success(t("Registered. Please login.", "Registered. Please login."))

    elif mode == t("Login", "Login"):
        st.header(t("Login", "Login"))
        username = st.text_input(t("Username", "Username"))
        password = st.text_input(t("Password", "Password"), type="password")
        if st.button(t("Login", "Login")):
            sel = sa.select(users_table).where(users_table.c.username==username)
            r = conn.execute(sel).mappings().first()
            if not r:
                st.error(t("Username not found.", "Username not found."))
            elif check_password(password, r['password_hash']):
                st.session_state['user_id'] = r['id']
                st.session_state['username'] = r['username']
                st.experimental_rerun()
            else:
                st.error(t("Wrong password.", "Wrong password."))

    else:
        # Demo
        st.header(t("Demo Mode", "Demo Mode"))
        st.info(t("In demo mode, data is not saved.", "In demo mode, data is not saved."))
        f = st.file_uploader(t("Upload leaf/fruit/stem image", "Upload leaf/fruit/stem image"), type=["jpg","jpeg","png"])
        if f:
            st.image(f, use_container_width=True)
            st.success(t("Demo prediction: Healthy", "Demo prediction: Healthy"))

else:
    st.sidebar.header(f"{t('Welcome', 'Welcome')}, {st.session_state['username']}")
    menu = st.sidebar.selectbox(t("Menu", "Menu"), [t("🏠 Home", "🏠 Home"), t("🌱 Tracking", "🌱 Tracking"), t("📅 Schedule", "📅 Schedule"), t("📈 Prediction", "📈 Prediction"), t("🍎 Disease", "🍎 Disease"), t("📥 Download", "📥 Download"), t("🚪 Logout", "🚪 Logout")])

    user_id = st.session_state['user_id']

    if menu == t("🚪 Logout", "🚪 Logout"):
        st.session_state['user_id'] = None
        st.session_state['username'] = None
        st.experimental_rerun()
