# app_seedling_pro_full_bilingual_fixed.py
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
st.set_page_config(page_title="🍎 Seedling Pro Bilingual", layout="wide")

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

# ---------- Database ----------
DB_FILE = "users_seedling_full_bilingual_fixed.db"
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
    "apple_black_spot": {"name": t("لکه سیاه ⚫️","Black Spot ⚫️"), "desc": t("لکه‌های سیاه روی برگ و میوه.","Black spots on leaves/fruit."), "treatment": t("قارچ‌کش، هرس و جمع‌آوری برگ‌ها","Fungicide, prune, remove fallen leaves")},
    "apple_powdery_mildew": {"name": t("سفیدک پودری ❄️","Powdery Mildew ❄️"), "desc": t("سطح برگ سفید و پودری می‌شود.","White powdery surface on leaves."), "treatment": t("گوگرد، هرس و تهویه","Sulfur spray, pruning, ventilation")},
    "apple_healthy": {"name": t("برگ سالم ✅","Healthy ✅"), "desc": t("برگ سالم است.","Leaf is healthy."), "treatment": t("ادامه مراقبت‌های معمول","Continue standard care")}
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
            schedule.append({'username':username,'date':str(date.date()),'height':None,'leaves':None,'notes':None,'prune':None,'task':t('آبیاری','Watering'),'task_done':'False'})
            if week % 4 == 0: schedule.append({'username':username,'date':str(date.date()),'height':None,'leaves':None,'notes':None,'prune':None,'task':t('کوددهی','Fertilization'),'task_done':'False'})
            if week % 12 == 0: schedule.append({'username':username,'date':str(date.date()),'height':None,'leaves':None,'notes':None,'prune':None,'task':t('هرس','Pruning'),'task_done':'False'})
        for item in schedule: conn.execute(data_table.insert().values(**item))

def login(username, password):
    with engine.begin() as conn:
        r = conn.execute(sa.select(users_table).where(users_table.c.username==username)).first()
        if r:
            stored_hash = r._mapping['password_hash']
            role = r._mapping['role']
            if bcrypt.checkpw(password.encode(), stored_hash.encode()):
                return role
        return None

def load_user_data(username=None):
    with engine.begin() as conn:
        if username:
            rows = conn.execute(sa.select(data_table).where(data_table.c.username==username)).fetchall()
        else:
            rows = conn.execute(sa.select(data_table)).fetchall()
    return pd.DataFrame([r._mapping for r in rows])
