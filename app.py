import streamlit as st
import pandas as pd
from datetime import datetime
import bcrypt
import sqlalchemy as sa
from sqlalchemy import Column, Integer, String, Table, MetaData, ForeignKey

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
if 'demo_data' not in st.session_state: st.session_state['demo_data'] = []

# ---------- Language ----------
def t(fa, en):
    return en if st.session_state['lang'] == 'English' else fa

# Language selection
lang = st.sidebar.selectbox("Language / زبان", ["فارسی", "English"], index=0 if st.session_state.get('lang','فارسی')=='فارسی' else 1)
if st.session_state.get('lang','فارسی') != lang:
    st.session_state['lang'] = lang
    st.experimental_rerun()

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
        # Demo Mode
        st.header(t("Demo Mode", "Demo Mode"))
        st.info(t("In demo mode, data is not saved.", "In demo mode, data is not saved."))
        f = st.file_uploader(t("Upload leaf/fruit/stem image", "Upload leaf/fruit/stem image"), type=["jpg","jpeg","png"])
        if f:
            st.image(f, use_container_width=True)
            st.success(t("Demo prediction: Healthy", "Demo prediction: Healthy"))
            st.write(t("Notes: This is a demo result.", "Notes: This is a demo result."))
            st.session_state['demo_data'].append({'file': f.name, 'result': 'Healthy', 'time': datetime.now()})
            if st.session_state['demo_data']:
                st.subheader(t("Demo History", "Demo History"))
                df_demo = pd.DataFrame(st.session_state['demo_data'])
                st.dataframe(df_demo)

else:
    st.sidebar.header(f"{t('Welcome', 'Welcome')}, {st.session_state['username']}")
    menu = st.sidebar.selectbox(t("Menu", "Menu"), [t("🏠 Home", "🏠 Home"), t("🌱 Tracking", "🌱 Tracking"), t("📅 Schedule", "📅 Schedule"), t("📈 Prediction", "📈 Prediction"), t("🍎 Disease", "🍎 Disease"), t("📥 Download", "📥 Download"), t("🚪 Logout", "🚪 Logout")])

    user_id = st.session_state['user_id']

    if menu == t("🚪 Logout", "🚪 Logout"):
        st.session_state['user_id'] = None
        st.session_state['username'] = None
        st.experimental_rerun()

    # ---------- Tracking ----------
    elif menu == t("🌱 Tracking", "🌱 Tracking"):
        st.header(t("Seedling Tracking", "Seedling Tracking"))
        with st.expander(t("➕ Add Measurement", "➕ Add Measurement")):
            date = st.date_input(t("Date", "Date"), value=datetime.today())
            height = st.number_input(t("Height (cm)", "Height (cm)"), min_value=0, step=1)
            leaves = st.number_input(t("Leaves", "Leaves"), min_value=0, step=1)
            notes = st.text_area(t("Notes", "Notes"))
            prune = st.checkbox(t("Prune needed?", "Prune needed?"))
            if st.button(t("Submit", "Submit")):
                conn.execute(measurements.insert().values(user_id=user_id, date=str(date), height=height, leaves=leaves, notes=notes, prune_needed=int(prune)))
                st.success(t("Measurement saved.", "Measurement saved."))
        sel = sa.select(measurements).where(measurements.c.user_id==user_id).order_by(measurements.c.date.desc())
        df = pd.DataFrame(conn.execute(sel).mappings().all())
        if not df.empty:
            st.dataframe(df)
