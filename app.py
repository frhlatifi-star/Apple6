# app.py
import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
from PIL import Image, ImageStat
import base64
import os
import bcrypt
import sqlalchemy as sa
from sqlalchemy import Column, Integer, String, Table, MetaData, ForeignKey

# --- Optional TensorFlow (model) ---
try:
    import tensorflow as tf
    TF_AVAILABLE = True
except Exception:
    TF_AVAILABLE = False

# ---------- Config ----------
st.set_page_config(page_title="سیبتک 🍎 مدیریت نهال", page_icon="🍎", layout="wide")

# ---------- CSS / RTL ----------
def inject_css():
    st.markdown("""
    <style>
    :root { --accent: #2e7d32; --accent-2: #388e3c; --bg-1: #eaf9e7; --card: #ffffff; }
    .block-container { direction: rtl !important; text-align: right !important; padding: 1.2rem 2rem; background: linear-gradient(135deg, #eaf9e7, #f7fff8); }
    body { font-family: Vazirmatn, Tahoma, sans-serif; background: linear-gradient(135deg, #eaf9e7, #f7fff8) !important; }
    .app-header { display:flex; align-items:center; gap: 0.8rem; margin-bottom: 0.6rem; }
    .app-header .title { margin: 0; color: var(--accent); }
    .app-sub { color: #555; font-size:14px; margin-top:2px; }
    .dashboard-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 1rem; margin-top: 0.8rem; }
    .card { background: var(--card); padding: 1.1rem; border-radius: 14px; box-shadow: 0 6px 18px rgba(20,20,20,0.06); text-align:center; transition: all 0.15s ease-in-out; cursor: pointer; }
    .card:hover { transform: translateY(-6px); box-shadow: 0 10px 26px rgba(20,20,20,0.09); }
    .card-icon { font-size: 28px; color: var(--accent-2); margin-bottom: 6px; }
    .stButton>button { background-color: var(--accent-2) !important; color: white !important; border-radius: 8px !important; }
    .st-badge { direction: rtl !important; }
    table { direction: rtl !important; text-align: right !important; }
    </style>
    """, unsafe_allow_html=True)
inject_css()

# ---------- Database ----------
DB_FILE = "users_data.db"
engine = sa.create_engine(f"sqlite:///{DB_FILE}", connect_args={"check_same_thread": False})
meta = MetaData()

# users
users_table = Table(
    'users', meta,
    Column('id', Integer, primary_key=True),
    Column('username', String, unique=True, nullable=False),
    Column('password_hash', String, nullable=False)
)

# measurements
measurements = Table(
    'measurements', meta,
    Column('id', Integer, primary_key=True),
    Column('user_id', Integer, ForeignKey('users.id')),
    Column('date', String),
    Column('height', Integer),
    Column('leaves', Integer),
    Column('notes', String),
    Column('prune_needed', Integer)
)

# schedule
schedule_table = Table(
    'schedule', meta,
    Column('id', Integer, primary_key=True),
    Column('user_id', Integer, ForeignKey('users.id')),
    Column('task', String),
    Column('date', String),
    Column('notes', String)
)

# predictions
predictions_table = Table(
    'predictions', meta,
    Column('id', Integer, primary_key=True),
    Column('user_id', Integer, ForeignKey('users.id')),
    Column('file_name', String),
    Column('result', String),
    Column('confidence', String),
    Column('date', String)
)

# disease notes
disease_table = Table(
    'disease', meta,
    Column('id', Integer, primary_key=True),
    Column('user_id', Integer, ForeignKey('users.id')),
    Column('note', String),
    Column('date', String)
)

meta.create_all(engine)

# ---------- Session defaults ----------
for key in ['user_id','username','demo_history']:
    if key not in st.session_state:
        st.session_state[key] = None if key != 'demo_history' else []

# ---------- Password helpers ----------
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def check_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())

# ---------- Model setup ----------
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
    if green_ratio>0.12 and mean>80:
        return "سالم", f"{min(99,int(50+green_ratio*200))}%"
    if yellow_ratio>0.12 or mean<60:
        if yellow_ratio>0.25:
            return "بیمار", f"{min(95,int(40+yellow_ratio*200))}%"
        else:
            return "کم‌آبی/نیاز هرس", f"{min(90,int(30+(0.2-mean/255)*200))}%"
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
            img_html = f"<img src='data:image/png;base64,{encoded}' width='64' style='border-radius:12px;'>"
    else:
        img_html = "<div style='font-size:36px;'>🍎</div>"
    st.markdown(f"""
    <div class="app-header">
        {img_html}
        <div>
            <h2 class="title">سیبتک</h2>
            <div class="app-sub">مدیریت و پایش نهال</div>
        </div>
    </div>
    <hr/>
    """,unsafe_allow_html=True)
app_header()

# ---------- Authentication ----------
def auth_ui():
    st.write("")
    col1, col2 = st.columns([1,2])
    with col1:
        mode = st.radio("حالت:", ["ورود","ثبت‌نام","دمو"])
    with col2:
        st.write("")

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
                except Exception as e:
                    st.error(f"خطا در ثبت‌نام: {e}")

    elif mode=="ورود":
        st.subheader("ورود به حساب کاربری")
        username = st.text_input("نام کاربری", key="login_username")
        password = st.text_input("رمز عبور", type="password", key="login_password")
        if st.button("ورود"):
            try:
                with engine.connect() as conn:
                    r = conn.execute(sa.select(users_table).where(users_table.c.username==username)).mappings().first()
                    if not r:
                        st.error("نام کاربری یافت نشد.")
                    elif check_password(password,r['password_hash']):
                        st.session_state['user_id']=int(r['id'])
                        st.session_state['username']=r['username']
                        st.experimental_rerun()
                    else:
                        st.error("رمز عبور اشتباه است.")
            except Exception as e:
                st.error(f"خطا در ورود: {e}")
    else:
        # Demo
        st.subheader("حالت دمو — پیش‌بینی نمونه")
        uploaded = st.file_uploader("یک تصویر آپلود کنید", type=["jpg","jpeg","png"])
        if uploaded:
            img = Image.open(uploaded)
            st.image(img,use_container_width=True)
            if _model_loaded:
                label,conf = predict_with_model(img)
            else:
                label,conf = heuristic_predict(img)
            color = "#4CAF50" if "سالم" in label else "#FF9800" if "کم‌آبی" in label else "#F44336"
            st.markdown(f"<div class='card' style='border-left:6px solid {color};'><h3>نتیجه: {label}</h3><div>اعتماد: {conf}</div></div>",unsafe_allow_html=True)

# اگر کاربر وارد نشده، نمایش احراز هویت
if st.session_state['user_id'] is None:
    auth_ui()
    st.stop()

# ---------- Dashboard ----------
def dashboard_ui():
    st.subheader(f"خوش آمدید، {st.session_state['username']}")
    menu = st.sidebar.selectbox("منو",[
        "🏠 خانه",
        "🌱 پایش نهال",
        "📅 زمان‌بندی",
        "📈 پیش‌بینی سلامت نهال",
        "🍎 ثبت بیماری / یادداشت",
        "📥 دانلود داده‌ها",
        "🚪 خروج"
    ])
    return menu

# ---------- Pages ----------

def page_home():
    st.header("🏠 خانه — خلاصه وضعیت")
    user_id = st.session_state['user_id']
    try:
        with engine.connect() as conn:
            last = conn.execute(sa.select(measurements).where(measurements.c.user_id==user_id).order_by(measurements.c.id.desc()).limit(1)).mappings().first()
            count_measure = conn.execute(sa.select(measurements).where(measurements.c.user_id==user_id)).rowcount
            count_sched = conn.execute(sa.select(schedule_table).where(schedule_table.c.user_id==user_id)).rowcount
    except:
        last = None
        count_measure = 0
        count_sched = 0
    st.write(f"تعداد اندازه‌گیری ثبت‌شده: {count_measure}")
    st.write(f"تعداد برنامه‌ها: {count_sched}")
    if last:
        st.write(f"آخرین اندازه‌گیری: ارتفاع {last['height']} سانتی‌متر، تعداد برگ {last['leaves']}")

# ---------- پایش نهال ----------
def page_measurements():
    st.header("🌱 ثبت رشد نهال")
    user_id = st.session_state['user_id']
    with st.form("measure_form"):
        h = st.number_input("ارتفاع (سانتی‌متر)",min_value=0,max_value=500)
        l = st.number_input("تعداد برگ",min_value=0,max_value=500)
        prune = st.selectbox("نیاز به هرس",["خیر","بله"])
        notes = st.text_area("یادداشت")
        submit = st.form_submit_button("ثبت اندازه‌گیری")
        if submit:
            try:
                with engine.connect() as conn:
                    conn.execute(measurements.insert().values(
                        user_id=user_id,
                        date=str(datetime.today().date()),
                        height=h,
                        leaves=l,
                        notes=notes,
                        prune_needed=1 if prune=="بله" else 0
                    ))
                st.success("اندازه‌گیری ثبت شد.")
            except Exception as e:
                st.error(f"خطا در ثبت: {e}")

# ---------- زمان‌بندی ----------
def page_schedule():
    st.header("📅 زمان‌بندی فعالیت‌ها")
    user_id = st.session_state['user_id']
    if user_id is None:
        st.warning("برای مشاهده زمان‌بندی باید وارد شوید.")
        return

    # افزودن برنامه جدید
    with st.expander("➕ افزودن برنامه"):
        with st.form("add_sched"):
            task = st.text_input("فعالیت")
            task_date = st.date_input("تاریخ برنامه")
            task_notes = st.text_area("یادداشت")
            submit = st.form_submit_button("ثبت برنامه")
            if submit:
                if not task:
                    st.error("عنوان فعالیت را وارد کنید.")
                else:
                    try:
                        with engine.connect() as conn:
                            conn.execute(
                                schedule_table.insert().values(
                                    user_id=user_id,
                                    task=task,
                                    date=str(task_date),
                                    notes=task_notes
                                )
                            )
                        st.success("برنامه ثبت شد.")
                    except Exception as e:
                        st.error(f"خطا در ثبت برنامه: {e}")

    # نمایش برنامه‌های ثبت‌شده
    st.subheader("برنامه‌های ثبت‌شده")
    try:
        with engine.connect() as conn:
            stmt = sa.select(schedule_table).where(schedule_table.c.user_id==user_id).order_by(schedule_table.c.date.desc())
            rows = conn.execute(stmt).mappings().all()
            if rows:
                df = pd.DataFrame(rows)
                try:
                    df['date'] = pd.to_datetime(df['date'])
                except:
                    pass
                st.dataframe(df,use_container_width=True)
            else:
                st.info("هیچ برنامه‌ای ثبت نشده است.")
    except Exception as e:
        st.error(f"خطا در بارگذاری برنامه‌ها: {e}")

# ---------- پیش‌بینی ----------
def page_prediction():
    st.header("📈 پیش‌بینی سلامت نهال")
    uploaded = st.file_uploader("یک تصویر آپلود کنید", type=["jpg","jpeg","png"])
    if uploaded:
        img = Image.open(uploaded)
        st.image(img,use_container_width=True)
        if _model_loaded:
            label,conf = predict_with_model(img)
        else:
            label,conf = heuristic_predict(img)
        color = "#4CAF50" if "سالم" in label else "#FF9800" if "کم‌آبی" in label else "#F44336"
        st.markdown(f"<div class='card' style='border-left:6px solid {color};'><h3>نتیجه: {label}</h3><div>اعتماد: {conf}</div></div>",unsafe_allow_html=True)

# ---------- بیماری / یادداشت ----------
def page_disease_notes():
    st.header("🍎 ثبت بیماری یا یادداشت")
    user_id = st.session_state['user_id']
    with st.form("disease_form"):
        note = st.text_area("یادداشت بیماری یا نکته")
        submit = st.form_submit_button("ثبت یادداشت")
        if submit:
            try:
                with engine.connect() as conn:
                    conn.execute(disease_table.insert().values(
                        user_id=user_id,
                        note=note,
                        date=str(datetime.today().date())
                    ))
                st.success("یادداشت ثبت شد.")
            except Exception as e:
                st.error(f"خطا در ثبت: {e}")

# ---------- دانلود داده ----------
def page_download():
    st.header("📥 دانلود داده‌ها")
    user_id = st.session_state['user_id']
    try:
        with engine.connect() as conn:
            df_m = pd.DataFrame(conn.execute(sa.select(measurements).where(measurements.c.user_id==user_id)).mappings().all())
        if not df_m.empty:
            csv = df_m.to_csv(index=False).encode()
            st.download_button("دانلود CSV اندازه‌گیری‌ها", csv, "measurements.csv","text/csv")
        else:
            st.info("هیچ داده‌ای برای دانلود وجود ندارد.")
    except Exception as e:
        st.error(f"خطا در دانلود: {e}")

# ---------- Main ----------
menu = dashboard_ui()

if menu=="🏠 خانه":
    page_home()
elif menu=="🌱 پایش نهال":
    page_measurements()
elif menu=="📅 زمان‌بندی":
    page_schedule()
elif menu=="📈 پیش‌بینی سلامت نهال":
    page_prediction()
elif menu=="🍎 ثبت بیماری / یادداشت":
    page_disease_notes()
elif menu=="📥 دانلود داده‌ها":
    page_download()
elif menu=="🚪 خروج":
    st.session_state['user_id']=None
    st.session_state['username']=None
    st.experimental_rerun()
