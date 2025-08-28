import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import os, base64
import bcrypt
import sqlalchemy as sa
from sqlalchemy import Column, Integer, String, Table, MetaData, ForeignKey
from PIL import Image, ImageStat

# TensorFlow مدل اختیاری
try:
    import tensorflow as tf
    TF_AVAILABLE = True
except:
    TF_AVAILABLE = False

# ---------- Config ----------
st.set_page_config(page_title="سیبتک 🍎 مدیریت نهال", page_icon="🍎", layout="wide")

# ---------- CSS حرفه‌ای و RTL ----------
st.markdown("""
<style>
:root {
    --accent: #2e7d32;
    --accent-2: #388e3c;
    --bg-1: #eaf9e7;
    --card: #ffffff;
}
body, html, [class*="css"] {direction: rtl !important; text-align: right !important; font-family: 'Vazirmatn', Tahoma, sans-serif;}
.block-container {padding: 1rem 2rem; background: linear-gradient(135deg,#eaf9e7,#f7fff8);}
.stButton>button {background-color: var(--accent-2)!important; color:white!important; border-radius:8px;}
.stButton>button:hover {background-color: #2e7d32!important;}
.card {background: var(--card); padding: 1rem; border-radius:12px; box-shadow: 0 6px 18px rgba(20,20,20,0.06); margin-bottom:12px;}
.card h3 {margin:0;}
.card .metric {font-size:22px; font-weight:bold;}
</style>
""", unsafe_allow_html=True)

# ---------- Database ----------
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
    Column('date', String), Column('height', Integer),
    Column('leaves', Integer), Column('notes', String),
    Column('prune_needed', Integer)
)
schedule_table = Table('schedule', meta,
    Column('id', Integer, primary_key=True),
    Column('user_id', Integer, ForeignKey('users.id')),
    Column('task', String), Column('date', String),
    Column('notes', String)
)
predictions_table = Table('predictions', meta,
    Column('id', Integer, primary_key=True),
    Column('user_id', Integer, ForeignKey('users.id')),
    Column('file_name', String), Column('result', String),
    Column('confidence', String), Column('date', String)
)
disease_table = Table('disease', meta,
    Column('id', Integer, primary_key=True),
    Column('user_id', Integer, ForeignKey('users.id')),
    Column('note', String), Column('date', String)
)
meta.create_all(engine)

# ---------- Session defaults ----------
for key in ['user_id', 'username', 'demo_history']:
    if key not in st.session_state:
        st.session_state[key] = None if key != 'demo_history' else []

# ---------- Password helpers ----------
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
def check_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())

# ---------- Load model ----------
MODEL_PATH = "model/seedling_model.h5"
_model = None
_model_loaded = False
if TF_AVAILABLE and os.path.exists(MODEL_PATH):
    try:
        @st.cache_resource
        def _load_model(path):
            return tf.keras.models.load_model(path)
        _model = _load_model(MODEL_PATH)
        _model_loaded = True
    except Exception as e:
        st.warning(f"بارگذاری مدل با خطا مواجه شد: {e}")

# ---------- Heuristic prediction ----------
def heuristic_predict(img: Image.Image):
    img = img.convert("RGB").resize((224,224))
    stat = ImageStat.Stat(img)
    mean = np.mean(stat.mean)
    arr = np.array(img).astype(int)
    r,g,b = arr[:,:,0], arr[:,:,1], arr[:,:,2]
    yellow_ratio = ((r>g)&(g>=b)).mean()
    green_ratio = ((g>r+10)&(g>b+10)).mean()
    if green_ratio>0.12 and mean>80: return "سالم", f"{min(99,int(50+green_ratio*200))}%"
    if yellow_ratio>0.12 or mean<60:
        if yellow_ratio>0.25: return "بیمار", f"{min(95,int(40+yellow_ratio*200))}%"
        else: return "کم‌آبی/نیاز هرس", f"{min(90,int(30+(0.2-mean/255)*200))}%"
    return "نامشخص", "50%"

def predict_with_model(img: Image.Image):
    x = np.expand_dims(np.array(img.convert("RGB").resize((224,224)))/255.0,0)
    preds = _model.predict(x)
    classes = ["سالم","بیمار","نیاز به هرس","کم‌آبی"]
    idx = int(np.argmax(preds[0]))
    confidence = int(float(np.max(preds[0]))*100)
    return classes[idx], f"{confidence}%"

# ---------- UI Header ----------
def app_header():
    logo_path = "logo.png"
    if os.path.exists(logo_path):
        with open(logo_path,"rb") as f:
            encoded = base64.b64encode(f.read()).decode()
        img_html = f"<img src='data:image/png;base64,{encoded}' width='64' style='border-radius:12px;margin-left:12px;'>"
    else: img_html = "🍎"
    st.markdown(f"""
    <div style='display:flex;align-items:center;margin-bottom:12px;'>
        {img_html}
        <div style='margin-right:8px;'>
            <h2 style='margin:0'>سیبتک</h2>
            <small style='color:#555'>مدیریت و پایش نهال</small>
        </div>
    </div><hr/>
    """, unsafe_allow_html=True)
app_header()

# ---------- Authentication ----------
def auth_ui():
    st.write("")
    col1,col2 = st.columns([1,2])
    with col1:
        mode = st.radio("حالت:", ["ورود","ثبت‌نام","دمو"])
    with col2: st.write("")
    if mode=="ثبت‌نام":
        st.subheader("ثبت‌نام کاربر جدید")
        username = st.text_input("نام کاربری", key="signup_username")
        password = st.text_input("رمز عبور", type="password", key="signup_password")
        if st.button("ثبت‌نام"):
            if not username or not password:
                st.error("نام کاربری و رمز عبور را وارد کنید.")
            else:
                try:
                    with engine.connect() as conn:
                        sel = sa.select(users_table).where(users_table.c.username==username)
                        if conn.execute(sel).mappings().first():
                            st.error("این نام کاربری قبلاً ثبت شده است.")
                        else:
                            conn.execute(users_table.insert().values(username=username,password_hash=hash_password(password)))
                            st.success("ثبت‌نام انجام شد. اکنون وارد شوید.")
                except Exception as e: st.error(f"خطا در ثبت‌نام: {e}")
    elif mode=="ورود":
        st.subheader("ورود به حساب کاربری")
        username = st.text_input("نام کاربری", key="login_username")
        password = st.text_input("رمز عبور", type="password", key="login_password")
        if st.button("ورود"):
            try:
                with engine.connect() as conn:
                    r = conn.execute(sa.select(users_table).where(users_table.c.username==username)).mappings().first()
                    if not r: st.error("نام کاربری یافت نشد.")
                    elif check_password(password,r['password_hash']):
                        st.session_state['user_id']=int(r['id'])
                        st.session_state['username']=r['username']
                        st.experimental_rerun()
                    else: st.error("رمز عبور اشتباه است.")
            except Exception as e: st.error(f"خطا در ورود: {e}")
    else: # Demo
        st.subheader("حالت دمو — پیش‌بینی نمونه")
        uploaded = st.file_uploader("یک تصویر آپلود کنید", type=["jpg","jpeg","png"])
        if uploaded:
            img = Image.open(uploaded)
            st.image(img,use_container_width=True)
            if _model_loaded: label,conf = predict_with_model(img)
            else: label,conf = heuristic_predict(img)
            color = "#4CAF50" if "سالم" in label else "#FF9800" if "کم‌آبی" in label else "#F44336"
            st.markdown(f"<div class='card' style='border-left:6px solid {color};'><h3>نتیجه: {label}</h3><div>اعتماد: {conf}</div></div>",unsafe_allow_html=True)

# اگر کاربر لاگین نکرده باشد
if st.session_state['user_id'] is None:
    auth_ui()
    st.stop()

# ---------- Sidebar Menu ----------
menu = st.sidebar.selectbox("منو",[
    "🏠 خانه","🌱 پایش نهال","📅 زمان‌بندی","📈 پیش‌بینی سلامت نهال",
    "🍎 ثبت بیماری / یادداشت","📥 دانلود داده‌ها","🚪 خروج"
])
user_id = st.session_state['user_id']

# ---------- Dashboard ----------
if menu=="🏠 خانه":
    st.subheader(f"سلام، {st.session_state['username']}")
    with engine.connect() as conn:
        total_measurements = conn.execute(sa.select(sa.func.count()).select_from(measurements).where(measurements.c.user_id==user_id)).scalar()
        latest = conn.execute(sa.select(measurements).where(measurements.c.user_id==user_id).order_by(measurements.c.date.desc())).mappings().first()
    col1,col2,col3 = st.columns(3)
    col1.markdown(f"<div class='card'><h3>تعداد رکوردها</h3><div class='metric'>{total_measurements}</div></div>",unsafe_allow_html=True)
    if latest:
        col2.markdown(f"<div class='card'><h3>آخرین ارتفاع</h3><div class='metric'>{latest['height']} cm</div></div>",unsafe_allow_html=True)
        col3.markdown(f"<div class='card'><h3>تعداد برگ</h3><div class='metric'>{latest['leaves']}</div></div>",unsafe_allow_html=True)

# ---------- پایش نهال ----------
elif menu=="🌱 پایش نهال":
    st.subheader("ثبت داده‌های نهال")
    with st.form("measurement_form"):
        date = st.date_input("تاریخ",datetime.today())
        height = st.number_input("ارتفاع (cm)",min_value=0,max_value=500,value=10)
        leaves = st.number_input("تعداد برگ",min_value=0,max_value=500,value=5)
        notes = st.text_area("یادداشت")
        prune_needed = st.checkbox("نیاز به هرس")
        submitted = st.form_submit_button("ثبت")
        if submitted:
            with engine.connect() as conn:
                conn.execute(measurements.insert().values(user_id=user_id,date=str(date),height=height,leaves=leaves,notes=notes,prune_needed=int(prune_needed)))
                st.success("داده‌ها ثبت شد.")

    # نمایش جدول و نمودار
    with engine.connect() as conn:
        df = pd.DataFrame(conn.execute(sa.select(measurements).where(measurements.c.user_id==user_id)).mappings().all())
    if not df.empty:
        st.dataframe(df[['date','height','leaves','notes','prune_needed']])
        st.line_chart(df.set_index('date')[['height','leaves']])

# ---------- زمان‌بندی ----------
elif menu=="📅 زمان‌بندی":
    st.subheader("ثبت فعالیت‌های زمان‌بندی شده")
    with st.form("schedule_form"):
        task = st.text_input("نام فعالیت")
        date = st.date_input("تاریخ")
        notes = st.text_area("یادداشت")
        submitted = st.form_submit_button("ثبت")
        if submitted:
            with engine.connect() as conn:
                conn.execute(schedule_table.insert().values(user_id=user_id,task=task,date=str(date),notes=notes))
                st.success("فعالیت ثبت شد.")
    with engine.connect() as conn:
        df = pd.DataFrame(conn.execute(sa.select(schedule_table).where(schedule_table.c.user_id==user_id)).mappings().all())
    if not df.empty: st.dataframe(df[['date','task','notes']])

# ---------- پیش‌بینی سلامت نهال ----------
elif menu=="📈 پیش‌بینی سلامت نهال":
    st.subheader("آپلود تصویر برای پیش‌بینی")
    uploaded = st.file_uploader("تصویر نهال", type=["jpg","jpeg","png"])
    if uploaded:
        img = Image.open(uploaded)
        st.image(img,use_container_width=True)
        if _model_loaded: label,conf = predict_with_model(img)
        else: label,conf = heuristic_predict(img)
        st.markdown(f"<div class='card'><h3>نتیجه: {label}</h3><div>اعتماد: {conf}</div></div>",unsafe_allow_html=True)
        with engine.connect() as conn:
            conn.execute(predictions_table.insert().values(user_id=user_id,file_name=uploaded.name,result=label,confidence=conf,date=str(datetime.today())))

# ---------- ثبت بیماری / یادداشت ----------
elif menu=="🍎 ثبت بیماری / یادداشت":
    st.subheader("ثبت یادداشت یا بیماری")
    note = st.text_area("یادداشت")
    if st.button("ثبت"):
        with engine.connect() as conn:
            conn.execute(disease_table.insert().values(user_id=user_id,note=note,date=str(datetime.today())))
            st.success("ثبت شد.")
    with engine.connect() as conn:
        df = pd.DataFrame(conn.execute(sa.select(disease_table).where(disease_table.c.user_id==user_id)).mappings().all())
    if not df.empty: st.dataframe(df[['date','note']])

# ---------- دانلود داده‌ها ----------
elif menu=="📥 دانلود داده‌ها":
    st.subheader("دانلود داده‌ها به CSV")
    with engine.connect() as conn:
        df1 = pd.DataFrame(conn.execute(sa.select(measurements).where(measurements.c.user_id==user_id)).mappings().all())
        df2 = pd.DataFrame(conn.execute(sa.select(schedule_table).where(schedule_table.c.user_id==user_id)).mappings().all())
        df3 = pd.DataFrame(conn.execute(sa.select(predictions_table).where(predictions_table.c.user_id==user_id)).mappings().all())
        df4 = pd.DataFrame(conn.execute(sa.select(disease_table).where(disease_table.c.user_id==user_id)).mappings().all())
    for name,df in [("measurements.csv",df1),("schedule.csv",df2),("predictions.csv",df3),("disease.csv",df4)]:
        if not df.empty:
            csv = df.to_csv(index=False).encode('utf-8-sig')
            st.download_button(f"دانلود {name}", csv, file_name=name, mime='text/csv')

# ---------- خروج ----------
elif menu=="🚪 خروج":
    st.session_state['user_id']=None
    st.session_state['username']=None
    st.experimental_rerun()
