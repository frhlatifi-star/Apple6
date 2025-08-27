# app_seedling_pro_full.py
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

# ---------- Config ----------
st.set_page_config(page_title="🍎 Seedling Pro Ultimate", layout="wide")

# ---------- Styles ----------
st.markdown("""
<style>
.kpi-card{background:#ffffffdd;border-radius:14px;padding:14px;margin-bottom:16px;box-shadow:0 6px 20px rgba(0,0,0,0.15);transition:transform 0.2s;}
.kpi-card:hover{transform:scale(1.03);}
.kpi-title{font-size:16px;font-weight:bold;color:#333;}
.kpi-value{font-size:28px;font-weight:bold;color:#2d9f3f;}
.task-done{background:#d1ffd1;}
.task-pending{background:#ffe6e6;}
</style>
""", unsafe_allow_html=True)

# ---------- Database ----------
DB_FILE = "users_seedling_full.db"
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

# ---------- Model ----------
@st.cache_resource
def load_model_cached(path="leaf_model.h5"):
    try: return tf.keras.models.load_model(path)
    except: return None
model = load_model_cached("leaf_model.h5")

class_labels = ["apple_healthy", "apple_black_spot", "apple_powdery_mildew"]
disease_info = {
    "apple_black_spot": {"name": "Black Spot ⚫️", "desc": "Black spots on leaves/fruit.", "treatment": "Fungicide, prune, remove fallen leaves"},
    "apple_powdery_mildew": {"name": "Powdery Mildew ❄️", "desc": "White powdery surface on leaves.", "treatment": "Sulfur spray, pruning, ventilation"},
    "apple_healthy": {"name": "Healthy ✅", "desc": "Leaf is healthy.", "treatment": "Continue standard care"}
}

def predict_probs(file):
    if model is None: return np.array([1.0,0.0,0.0])
    img = Image.open(file).convert("RGB")
    target_size = model.input_shape[1:3]
    img = img.resize(target_size)
    arr = img_to_array(img)/255.0
    arr = np.expand_dims(arr, axis=0)
    preds = model.predict(arr)[0]
    return preds

# ---------- Session ----------
if 'user' not in st.session_state: st.session_state['user'] = None
if 'role' not in st.session_state: st.session_state['role'] = None
if 'df_future' not in st.session_state: st.session_state['df_future'] = pd.DataFrame()

# ---------- Auth Functions ----------
def register(username, password, role='user'):
    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    with engine.begin() as conn:
        conn.execute(users_table.insert().values(username=username, password_hash=hashed, role=role))
        # Initialize schedule data for user
        start_date = datetime.today()
        schedule=[]
        for week in range(52):
            date = start_date + timedelta(weeks=week)
            schedule.append({'username':username,'date':str(date.date()),'height':None,'leaves':None,'notes':None,'prune':None,'task':'Watering','task_done':'False'})
            if week % 4 == 0: schedule.append({'username':username,'date':str(date.date()),'height':None,'leaves':None,'notes':None,'prune':None,'task':'Fertilization','task_done':'False'})
            if week % 12 == 0: schedule.append({'username':username,'date':str(date.date()),'height':None,'leaves':None,'notes':None,'prune':None,'task':'Pruning','task_done':'False'})
        for item in schedule: conn.execute(data_table.insert().values(**item))

def login(username, password):
    with engine.begin() as conn:
        r = conn.execute(sa.select(users_table).where(users_table.c.username==username)).first()
        if r and bcrypt.checkpw(password.encode(), r['password_hash'].encode()): return r['role']
        return None

def load_user_data(username=None):
    with engine.begin() as conn:
        if username:
            rows = conn.execute(sa.select(data_table).where(data_table.c.username==username)).fetchall()
        else:
            rows = conn.execute(sa.select(data_table)).fetchall()
    return pd.DataFrame(rows, columns=['id','username','date','height','leaves','notes','prune','task','task_done'])

# ---------- Auth UI ----------
if st.session_state['user'] is None:
    mode = st.sidebar.radio("Mode", ["Login", "Sign Up", "Demo"])
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    if mode=="Sign Up" and st.button("Register"):
        if username and password:
            register(username, password)
            st.success("Registered successfully. Please login.")
        else: st.error("Provide username & password.")
    if mode=="Login" and st.button("Login"):
        role = login(username, password)
        if role:
            st.session_state['user'] = username
            st.session_state['role'] = role
            st.success(f"Login successful ✅ Role: {role}")
        else:
            st.error("Wrong username or password.")
    if mode=="Demo":
        st.header("Demo Mode")
        f = st.file_uploader("Upload leaf image", type=["jpg","jpeg","png"])
        if f:
            st.image(f, use_column_width=True)
            preds = predict_probs(f)
            idx=int(np.argmax(preds))
            for i,cls in enumerate(class_labels):
                pct=preds[i]*100
                color="#2d9f3f" if cls=="apple_healthy" else "#e53935"
                st.markdown(f"<div style='margin-top:8px'><div style='background:#f1f5f9;border-radius:10px;padding:6px'><div style='background:{color};color:#fff;padding:6px;border-radius:6px;width:{int(pct)}%'>{pct:.1f}% {disease_info[cls]['name']}</div></div></div>",unsafe_allow_html=True)
            info=disease_info[class_labels[idx]]
            st.success(f"Result: {info['name']}")
            st.write(f"Description: {info['desc']}")
            st.write(f"Treatment: {info['treatment']}")

# ---------- Main App ----------
if st.session_state['user']:
    username = st.session_state['user']
    role = st.session_state.get('role','user')
    if role=='admin':
        menu = st.sidebar.selectbox("Admin Menu", ["Dashboard","Users","Download Reports","Logout"])
        if menu=="Logout":
            st.session_state['user']=None
            st.session_state['role']=None
            st.experimental_rerun()
        df_all = load_user_data()
        if menu=="Dashboard":
            st.header("Admin Dashboard")
            st.dataframe(df_all)
            fig = px.bar(df_all.groupby('username').agg({'height':'mean','leaves':'mean'}).reset_index(), x='username', y=['height','leaves'], barmode='group', title='Average Height & Leaves per User')
            st.plotly_chart(fig, use_container_width=True)
        if menu=="Users":
            st.header("User Management")
            df_users = pd.read_sql(users_table.select(), engine)
            st.dataframe(df_users)
        if menu=="Download Reports":
            st.header("Download All Users Data")
            buffer=io.BytesIO()
            with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                df_all.to_excel(writer, sheet_name='AllUsers', index=False)
            data=buffer.getvalue()
            st.download_button("Download Excel", data=data, file_name="all_users_dashboard.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    else:
        menu = st.sidebar.selectbox("Menu", ["Home","Tracking","Schedule","Disease","Growth Prediction","Download","Logout"])
        if menu=="Logout":
            st.session_state['user']=None
            st.experimental_rerun()
        df = load_user_data(username)
