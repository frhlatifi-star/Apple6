# app.py
import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import os
import base64
from PIL import Image, ImageStat
import bcrypt
import sqlalchemy as sa
from sqlalchemy import Column, Integer, String, Table, MetaData, ForeignKey

# TensorFlow (اختیاری)
try:
    import tensorflow as tf
    TF_AVAILABLE = True
except:
    TF_AVAILABLE = False

# ---------- صفحه و استایل ----------
st.set_page_config(page_title="سیبتک 🍎 مدیریت نهال", page_icon="🍎", layout="wide")

st.markdown("""
<style>
body, html {direction: rtl; font-family: Vazirmatn, Tahoma, sans-serif; background: #eaf9e7;}
.stButton>button {background-color:#4CAF50;color:white;border-radius:8px;padding:6px 14px;font-weight:bold;}
.stButton>button:hover {background-color:#45a049;}
.card {background:white;border-radius:12px;padding:12px;margin-bottom:12px;box-shadow:0 4px 8px rgba(0,0,0,0.1);}
.card h3 {margin:0;}
.card .metric {font-size:24px;font-weight:bold;}
</style>
""", unsafe_allow_html=True)

# ---------- دیتابیس ----------
DB_FILE = "users_data.db"
engine = sa.create_engine(f"sqlite:///{DB_FILE}", connect_args={"check_same_thread": False})
meta = MetaData()

users_table = Table('users', meta,
    Column('id', Integer, primary_key=True),
    Column('username', String, unique=True, nullable=False),
    Column('password_hash', String, nullable=False)
)
measurements = Table('measurements', meta,
    Column('id', Integer, primary_key=True),
    Column('user_id', Integer, ForeignKey('users.id')),
    Column('date', String),
    Column('height', Integer),
    Column('leaves', Integer),
    Column('notes', String),
    Column('prune_needed', Integer)
)
schedule_table = Table('schedule', meta,
    Column('id', Integer, primary_key=True),
    Column('user_id', Integer, ForeignKey('users.id')),
    Column('task', String),
    Column('date', String),
    Column('notes', String)
)
predictions_table = Table('predictions', meta,
    Column('id', Integer, primary_key=True),
    Column('user_id', Integer, ForeignKey('users.id')),
    Column('file_name', String),
    Column('result', String),
    Column('confidence', String),
    Column('date', String)
)
disease_table = Table('disease', meta,
    Column('id', Integer, primary_key=True),
    Column('user_id', Integer, ForeignKey('users.id')),
    Column('note', String),
    Column('date', String)
)
meta.create_all(engine)

# ---------- Helpers ----------
def hash_password(password): return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
def check_password(password, hashed): return bcrypt.checkpw(password.encode(), hashed.encode())

# ---------- مدل ----------
MODEL_PATH = "model/seedling_model.h5"
_model = None
_model_loaded = False
if TF_AVAILABLE and os.path.exists(MODEL_PATH):
    try:
        @st.cache_resource
        def _load_model(path): return tf.keras.models.load_model(path)
        _model = _load_model(MODEL_PATH)
        _model_loaded = True
    except Exception as e:
        st.warning(f"بارگذاری مدل با خطا مواجه شد: {e}")

def heuristic_predict(img: Image.Image):
    img = img.convert("RGB").resize((224,224))
    stat = ImageStat.Stat(img)
    mean = np.mean(stat.mean)
    arr = np.array(img)
    r,g,b = arr[:,:,0], arr[:,:,1], arr[:,:,2]
    yellow_ratio = ((r>g)&(g>=b)).mean()
    green_ratio = ((g>r+10)&(g>b+10)).mean()
    if green_ratio>0.12 and mean>80: return "سالم", f"{min(99,int(50+green_ratio*200))}%"
    if yellow_ratio>0.12 or mean<60:
        if yellow_ratio>0.25: return "بیمار", f"{min(95,int(40+yellow_ratio*200))}%"
        else: return "کم‌آبی/نیاز هرس", f"{min(90,int(30+(0.2-mean/255)*200))}%"
    return "نامشخص","50%"

def predict_with_model(img: Image.Image):
    x = np.expand_dims(np.array(img.convert("RGB").resize((224,224)))/255.0,0)
    preds = _model.predict(x)
    classes = ["سالم","بیمار","نیاز به هرس","کم‌آبی"]
    idx = int(np.argmax(preds[0]))
    confidence = int(float(np.max(preds[0]))*100)
    return classes[idx], f"{confidence}%"

# ---------- Session ----------
for key in ['user_id','username']: 
    if key not in st.session_state: st.session_state[key] = None

# ---------- Header ----------
def app_header():
    logo_path = "logo.png"
    if os.path.exists(logo_path):
        with open(logo_path,"rb") as f:
            encoded = base64.b64encode(f.read()).decode()
        img_html = f"<img src='data:image/png;base64,{encoded}' width='64' style='border-radius:12px;margin-left:12px;'>"
    else:
        img_html = "<div style='font-size:36px;'>🍎</div>"
    st.markdown(f"""
    <div style='display:flex;align-items:center;margin-bottom:12px;'>{img_html}<div>
    <h2 style='margin:0'>سیبتک</h2>
    <small style='color:#666'>مدیریت و پایش نهال</small></div></div><hr/>
    """, unsafe_allow_html=True)
app_header()

# ---------- Authentication ----------
def auth_ui():
    st.subheader("ورود / ثبت‌نام")
    mode = st.radio("حالت:", ["ورود","ثبت‌نام","ورود مهمان"])
    if mode=="ثبت‌نام":
        u = st.text_input("نام کاربری", key="signup_u")
        p = st.text_input("رمز عبور", type="password", key="signup_p")
        if st.button("ثبت‌نام"):
            if not u or not p: st.error("نام کاربری و رمز عبور را وارد کنید.")
            else:
                with engine.connect() as conn:
                    r = conn.execute(sa.select(users_table).where(users_table.c.username==u)).mappings().first()
                    if r: st.error("این نام کاربری قبلاً ثبت شده.")
                    else: conn.execute(users_table.insert().values(username=u,password_hash=hash_password(p)))
                    st.success("ثبت‌نام انجام شد. حالا وارد شوید.")
    elif mode=="ورود":
        u = st.text_input("نام کاربری", key="login_u")
        p = st.text_input("رمز عبور", type="password", key="login_p")
        if st.button("ورود"):
            with engine.connect() as conn:
                r = conn.execute(sa.select(users_table).where(users_table.c.username==u)).mappings().first()
                if not r: st.error("نام کاربری یافت نشد.")
                elif check_password(p,r['password_hash']):
                    st.session_state.user_id = r['id']
                    st.session_state.username = r['username']
                    st.experimental_rerun()
                else: st.error("رمز اشتباه است.")
    else:  # مهمان
        if st.button("ورود مهمان"):
            st.session_state.user_id = 0
            st.session_state.username = "مهمان"
            st.experimental_rerun()

if st.session_state.user_id is None:
    st.info("برای ادامه وارد شوید یا ثبت‌نام کنید.")
    auth_ui()
    st.stop()

# ---------- Dashboard ----------
def dashboard_ui():
    st.subheader("داشبورد")
    cards = [("🏠 خانه","home"),("🌱 پایش نهال","tracking"),("📅 زمان‌بندی","schedule"),
             ("📈 پیش‌بینی سلامت","predict"),("🍎 ثبت بیماری","disease"),
             ("📥 دانلود داده‌ها","download"),("🚪 خروج","logout")]
    cols = st.columns(len(cards))
    for idx,(label,key) in enumerate(cards):
        c = cols[idx % len(cols)]
        with c:
            if st.button(label,key=f"btn_{key}"):
                st.session_state.page = key
                st.experimental_rerun()

# ---------- Pages ----------
def page_home():
    st.header("🏠 خانه")
    with engine.connect() as conn:
        last = conn.execute(sa.select(measurements).where(measurements.c.user_id==st.session_state.user_id).order_by(measurements.c.id.desc()).limit(1)).mappings().first()
        count_measure = conn.execute(sa.select(measurements).where(measurements.c.user_id==st.session_state.user_id)).mappings().all()
    col1,col2 = st.columns(2)
    with col1:
        st.markdown(f"<div class='card'><h3>آخرین اندازه‌گیری</h3>"
                    f"<div class='metric'>{last['height'] if last else '-'} سانتی‌متر</div>"
                    f"تعداد برگ: {last['leaves'] if last else '-'}</div>", unsafe_allow_html=True)
    with col2:
        st.markdown(f"<div class='card'><h3>تعداد اندازه‌گیری‌ها</h3><div class='metric'>{len(count_measure)}</div></div>", unsafe_allow_html=True)

def page_tracking():
    st.header("🌱 پایش نهال")
    with engine.connect() as conn:
        df = pd.DataFrame(conn.execute(sa.select(measurements).where(measurements.c.user_id==st.session_state.user_id)).mappings().all())
    if df.empty: st.info("هیچ داده‌ای ثبت نشده است.")
    else:
        df_plot = df[['date','height']]
        df_plot['date'] = pd.to_datetime(df_plot['date'])
        st.line_chart(df_plot.set_index('date')['height'])
    st.subheader("ثبت اندازه‌گیری جدید")
    h = st.number_input("ارتفاع (سانتی‌متر)", min_value=1, max_value=500, step=1, key="h_input")
    l = st.number_input("تعداد برگ‌ها", min_value=0, max_value=500, step=1, key="l_input")
    notes = st.text_area("یادداشت (اختیاری)", key="m_note")
    prune = st.checkbox("نیاز به هرس", key="prune_input")
    if st.button("ثبت اندازه‌گیری", key="save_measure"):
        with engine.connect() as conn:
            conn.execute(measurements.insert().values(
                user_id=st.session_state.user_id,
                date=str(datetime.now().date()),
                height=h,
                leaves=l,
                notes=notes,
                prune_needed=int(prune)
            ))
        st.success("اندازه‌گیری ثبت شد.")
        st.experimental_rerun()

def page_schedule():
    st.header("📅 زمان‌بندی فعالیت‌ها")
    with engine.connect() as conn:
        df = pd.DataFrame(conn.execute(sa.select(schedule_table).where(schedule_table.c.user_id==st.session_state.user_id)).mappings().all())
    if df.empty: st.info("هیچ برنامه‌ای ثبت نشده است.")
    else: st.table(df[['task','date','notes']])
    st.subheader("ثبت فعالیت جدید")
    task = st.text_input("نام فعالیت", key="task_input")
    date = st.date_input("تاریخ", key="date_input")
    notes = st.text_area("یادداشت", key="task_note")
    if st.button("ثبت فعالیت", key="save_task"):
        with engine.connect() as conn:
            conn.execute(schedule_table.insert().values(
                user_id=st.session_state.user_id,
                task=task,
                date=str(date),
                notes=notes
            ))
        st.success("فعالیت ثبت شد.")
        st.experimental_rerun()

def page_predict():
    st.header("📈 پیش‌بینی سلامت نهال")
    uploaded = st.file_uploader("آپلود تصویر نهال", type=["png","jpg","jpeg"], key="img_upload")
    if uploaded:
        img = Image.open(uploaded)
        st.image(img, caption="تصویر آپلود شده", use_container_width=True)
        if st.button("پیش‌بینی سلامت", key="predict_btn"):
            if _model_loaded: result, conf = predict_with_model(img)
            else: result, conf = heuristic_predict(img)
            with engine.connect() as conn:
                conn.execute(predictions_table.insert().values(
                    user_id=st.session_state.user_id,
                    file_name=uploaded.name,
                    result=result,
                    confidence=conf,
                    date=str(datetime.now().date())
                ))
            st.success(f"نتیجه پیش‌بینی: {result} ({conf})")

def page_disease():
    st.header("🍎 ثبت یادداشت بیماری")
    note = st.text_area("یادداشت بیماری", key="d_note")
    if st.button("ثبت", key="d_save"):
        with engine.connect() as conn:
            conn.execute(disease_table.insert().values(
                user_id=st.session_state.user_id,
                note=note,
                date=str(datetime.now().date())
            ))
        st.success("ثبت شد.")
    with engine.connect() as conn:
        df = pd.DataFrame(conn.execute(sa.select(disease_table).where(disease_table.c.user_id==st.session_state.user_id)).mappings().all())
    if not df.empty: st.table(df[['date','note']])

def page_download():
    st.header("📥 دانلود داده‌ها")
    with engine.connect() as conn:
        df = pd.DataFrame(conn.execute(sa.select(measurements).where(measurements.c.user_id==st.session_state.user_id)).mappings().all())
    if df.empty: st.info("هیچ داده‌ای برای دانلود وجود ندارد.")
    else:
        csv = df.to_csv(index=False)
        b64 = base64.b64encode(csv.encode()).decode()
        st.markdown(f"<a href='data:text/csv;base64,{b64}' download='measurements.csv'>دانلود CSV</a>", unsafe_allow_html=True)

def page_logout():
    for key in ['user_id','username','page']: st.session_state[key]=None
    st.experimental_rerun()

# ---------- Router ----------
pages = {
    "home": page_home,
    "tracking": page_tracking,
    "schedule": page_schedule,
    "predict": page_predict,
    "disease": page_disease,
    "download": page_download,
    "logout": page_logout
}

if 'page' not in st.session_state: st.session_state.page = "home"
dashboard_ui()
pages.get(st.session_state.page, page_home)()
