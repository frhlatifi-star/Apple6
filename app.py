# sebetek_dashboard_pro.py
import streamlit as st
import pandas as pd
from datetime import datetime
import bcrypt
import sqlalchemy as sa
from sqlalchemy import Column, Integer, String, Table, MetaData, ForeignKey
from PIL import Image, ImageStat
import numpy as np
import os

# ---------- Config ----------
st.set_page_config(page_title="سیبتک 🍎 مدیریت نهال", page_icon="🍎", layout="wide")

# ---------- CSS حرفه‌ای ----------
st.markdown("""
<style>
html, body, [class*="css"] { direction: rtl !important; text-align: right !important; font-family: 'Vazirmatn', sans-serif; background-color: #e6f2e6;}
.stButton>button { cursor: pointer; background-color: #4CAF50; color: white; border-radius: 12px; padding: 10px 20px; font-weight: bold; margin-top:5px;}
.stButton>button:hover { background-color: #45a049; }
.card { background-color: #ffffff; border-radius: 16px; padding: 20px; box-shadow: 0 6px 20px rgba(0,0,0,0.12); margin-bottom: 20px; }
.card h3 { margin: 0; font-size:18px;}
.card .metric { font-size: 28px; font-weight: bold; }
.card .icon { font-size: 28px; margin-left:10px; }
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

# ---------- Session ----------
for key in ['user_id','username','demo_history']:
    if key not in st.session_state:
        st.session_state[key] = None if key != 'demo_history' else []

# ---------- Password Helpers ----------
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
def check_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())

# ---------- Header ----------
def app_header():
    st.markdown(f"""
    <div style='display:flex;align-items:center;margin-bottom:20px;'>
        <img src='https://i.imgur.com/4Y2E2XQ.png' width='64' style='margin-left:12px;border-radius:16px;'>
        <div>
            <h2 style='margin:0'>سیبتک</h2>
            <small style='color:#666'>مدیریت و پایش نهال</small>
        </div>
    </div><hr/>
    """, unsafe_allow_html=True)
app_header()

# ---------- Main ----------
if st.session_state['user_id'] is None:
    col1,col2 = st.columns([1,2])
    with col1: mode = st.radio("حالت:", ["ورود","ثبت‌نام","دمو"])
    with col2: st.write("")
    st.info("برای مشاهده داشبورد، لطفاً وارد شوید یا ثبت‌نام کنید.")
else:
    st.sidebar.header(f"خوش آمدید، {st.session_state['username']}")
    menu = st.sidebar.selectbox("منو",[
        "🏠 خانه","🌱 پایش نهال","📅 زمان‌بندی","📈 پیش‌بینی سلامت نهال",
        "🍎 ثبت بیماری / یادداشت","📥 دانلود داده‌ها","🚪 خروج"])
    user_id = st.session_state['user_id']

    if menu=="🚪 خروج":
        st.session_state['user_id']=None
        st.session_state['username']=None
        st.experimental_rerun = lambda: None

    # ---------- Home ----------
    if menu=="🏠 خانه":
        st.header("🏡 داشبورد اصلی")
        with engine.connect() as conn:
            ms = conn.execute(sa.select(measurements).where(measurements.c.user_id==user_id)).mappings().all()
            ps = conn.execute(sa.select(predictions_table).where(predictions_table.c.user_id==user_id)).mappings().all()
            ds = conn.execute(sa.select(disease_table).where(disease_table.c.user_id==user_id)).mappings().all()
        col1,col2,col3 = st.columns(3)
        col1.markdown(f"<div class='card'><span class='icon'>🌱</span><h3>اندازه‌گیری‌ها</h3><div class='metric'>{len(ms)}</div></div>",unsafe_allow_html=True)
        col2.markdown(f"<div class='card'><span class='icon'>📈</span><h3>پیش‌بینی‌ها</h3><div class='metric'>{len(ps)}</div></div>",unsafe_allow_html=True)
        col3.markdown(f"<div class='card'><span class='icon'>🍎</span><h3>یادداشت‌ها</h3><div class='metric'>{len(ds)}</div></div>",unsafe_allow_html=True)
        if ms:
            df = pd.DataFrame(ms)
            try: df['date']=pd.to_datetime(df['date'])
            except: pass
            st.subheader("📊 روند رشد نهال")
            st.line_chart(df.set_index('date')[['height','leaves']])

    # ---------- پایش نهال ----------
    elif menu=="🌱 پایش نهال":
        st.header("پایش نهال — ثبت رشد")
        with st.expander("➕ افزودن اندازه‌گیری"):
            date = st.date_input("تاریخ",value=datetime.today())
            height = st.number_input("ارتفاع (سانتی‌متر)", min_value=0, step=1)
            leaves = st.number_input("تعداد برگ", min_value=0, step=1)
            notes = st.text_area("یادداشت")
            prune = st.checkbox("نیاز به هرس؟")
            if st.button("ثبت اندازه‌گیری"):
                with engine.connect() as conn:
                    conn.execute(measurements.insert().values(user_id=user_id,date=str(date),height=int(height),leaves=int(leaves),notes=notes,prune_needed=int(prune)))
                    st.success("اندازه‌گیری ثبت شد.")
        with engine.connect() as conn:
            rows = conn.execute(sa.select(measurements).where(measurements.c.user_id==user_id).order_by(measurements.c.date.desc())).mappings().all()
        if rows:
            df = pd.DataFrame(rows)
            st.subheader("تاریخچه اندازه‌گیری‌ها")
            st.dataframe(df)
            try: df_plot = df.copy(); df_plot['date']=pd.to_datetime(df_plot['date'])
            st.line_chart(df_plot.set_index('date')['height'])
            st.line_chart(df_plot.set_index('date')['leaves'])
            except: pass
        else: st.info("هیچ اندازه‌گیری‌ای ثبت نشده است.")

    # ---------- زمان‌بندی ----------
    elif menu=="📅 زمان‌بندی":
        st.header("زمان‌بندی فعالیت‌ها")
        with st.expander("➕ افزودن برنامه"):
            task = st.text_input("فعالیت")
            task_date = st.date_input("تاریخ برنامه")
            task_notes = st.text_area("یادداشت")
            if st.button("ثبت برنامه"):
                with engine.connect() as conn:
                    conn.execute(schedule_table.insert().values(user_id=user_id,task=task,date=str(task_date),notes=task_notes))
                    st.success("برنامه ثبت شد.")
        with engine.connect() as conn:
            rows = conn.execute(sa.select(schedule_table).where(schedule_table.c.user_id==user_id).order_by(schedule_table.c.date.desc())).mappings().all()
        if rows:
            st.subheader("برنامه‌های ثبت‌شده")
            st.dataframe(pd.DataFrame(rows))
        else: st.info("هیچ برنامه‌ای ثبت نشده است.")

    # ---------- پیش‌بینی ----------
    elif menu=="📈 پیش‌بینی سلامت نهال":
        st.header("پیش‌بینی سلامت نهال")
        uploaded = st.file_uploader("آپلود تصویر نهال", type=["jpg","jpeg","png"])
        if uploaded:
            img = Image.open(uploaded)
            st.image(img,use_container_width=True)
            # مدل یا heuristic
            def heuristic_predict(img: Image.Image):
                stat = ImageStat.Stat(img.convert("RGB"))
                mean = np.mean(stat.mean)
                return "سالم" if mean>100 else "نیاز بررسی", "80%"
            label,conf = heuristic_predict(img)
            color = "#4CAF50" if "سالم" in label else "#FF9800"
            st.markdown(f"<div class='card' style='border-left:6px solid {color};'><h3>نتیجه: {label}</h3><div>اعتماد: {conf}</div></div>",unsafe_allow_html=True)
            with engine.connect() as conn:
                conn.execute(predictions_table.insert().values(user_id=user_id,file_name=getattr(uploaded,'name',str(datetime.now().timestamp())),result=label,confidence=conf,date=str(datetime.now())))

    # ---------- یادداشت ----------
    elif menu=="🍎 ثبت بیماری / یادداشت":
        st.header("ثبت یادداشت / بیماری")
        note = st.text_area("شرح مشکل یا یادداشت")
        if st.button("ثبت یادداشت"):
            with engine.connect() as conn:
                conn.execute(disease_table.insert().values(user_id=user_id,note=note,date=str(datetime.today())))
                st.success("یادداشت ثبت شد.")
        with engine.connect() as conn:
            rows = conn.execute(sa.select(disease_table).where(disease_table.c.user_id==user_id).order_by(disease_table.c.date.desc())).mappings().all()
        if rows:
            st.subheader("یادداشت‌های ثبت‌شده")
            st.dataframe(pd.DataFrame(rows))

    # ---------- دانلود ----------
    elif menu=="📥 دانلود داده‌ها":
        st.header("دانلود داده‌ها (CSV)")
        with engine.connect() as conn:
            df_measurements = pd.DataFrame(conn.execute(sa.select(measurements).where(measurements.c.user_id==user_id)).mappings().all())
            df_schedule = pd.DataFrame(conn.execute(sa.select(schedule_table).where(schedule_table.c.user_id==user_id)).mappings().all())
            df_predictions = pd.DataFrame(conn.execute(sa.select(predictions_table).where(predictions_table.c.user_id==user_id)).mappings().all())
            df_disease = pd.DataFrame(conn.execute(sa.select(disease_table).where(disease_table.c.user_id==user_id)).mappings().all())
        for df,name in [(df_measurements,"measurements"),(df_schedule,"schedule"),(df_predictions,"predictions"),(df_disease,"disease")]:
            if not df.empty:
                st.download_button(f"دانلود {name}.csv", df.to_csv(index=False).encode('utf-8-sig'), file_name=f"{name}.csv", mime='text/csv')
