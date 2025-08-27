# app.py (FULL, SQLite + bcrypt + final UI)
import streamlit as st
import tensorflow as tf
from tensorflow.keras.utils import img_to_array
from PIL import Image
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import io
import plotly.express as px
import sqlalchemy as sa
from sqlalchemy import Column, Integer, String, Table, MetaData
import bcrypt
import os
import json

# ---------- Config ----------
st.set_page_config(page_title="🍎 Seedling Pro", page_icon="🍎", layout="wide")

# ---------- Styles ----------
st.markdown("""
<style>
@import url('https://cdn.jsdelivr.net/gh/rastikerdar/vazir-font@v30.1.0/dist/font-face.css');
:root{--accent:#2d9f3f;--card-bg:rgba(255,255,255,0.95)}
body{font-family:'Vazir',sans-serif;direction:rtl;
background-image: linear-gradient(180deg, #e6f2ea 0%, #d9eef0 40%, #cfeef0 100%), url('https://images.unsplash.com/photo-1506806732259-39c2d0268443?auto=format&fit=crop&w=1470&q=80');
background-size:cover;background-attachment:fixed;color:#0f172a;}
.kpi-card{background:var(--card-bg);border-radius:12px;padding:12px;box-shadow:0 8px 24px rgba(7,10,25,0.08);margin-bottom:8px}
.section{background:linear-gradient(180deg, rgba(255,255,255,0.86), rgba(255,255,255,0.78));border-radius:12px;padding:12px}
.logo-row{display:flex;align-items:center;gap:10px}
</style>
""", unsafe_allow_html=True)

# ---------- Helpers & Translations ----------
lang = st.sidebar.selectbox("🌐 Language / زبان", ["فارسی", "English"])
EN = (lang == "English")
def t(fa, en): return en if EN else fa

# ---------- Logo display ----------
logo_path = "logo.svg"
if os.path.exists(logo_path):
    # embed svg
    with open(logo_path, 'r', encoding='utf-8') as f:
        svg = f.read()
    st.markdown(f"<div class='logo-row'>{svg}</div>", unsafe_allow_html=True)
else:
    st.markdown(f"<h1>🍎 Seedling Pro — {t('داشبورد نهال سیب','Apple Seedling Dashboard')}</h1>")

# ---------- Model loading ----------
@st.cache_resource
def load_model_cached(path="leaf_model.h5"):
    try:
        return tf.keras.models.load_model(path)
    except Exception as e:
        return None

model = load_model_cached("leaf_model.h5")
if model is None:
    st.info(t("مدل تشخیص پیدا نشد؛ بخش تشخیص غیرفعال است. برای فعال‌سازی فایل leaf_model.h5 را قرار دهید.","Detection model not found; place leaf_model.h5 to enable detection."))

# ---------- disease metadata ----------
class_labels = ["apple_healthy", "apple_black_spot", "apple_powdery_mildew"]
disease_info = {
    "apple_black_spot": {"name": t("لکه سیاه ⚫️","Black Spot ⚫️"), "desc": t("لکه‌های سیاه روی برگ و میوه.","Black spots on leaves/fruit."), "treatment": t("قارچ‌کش، هرس و جمع‌آوری برگ‌ها","Fungicide, prune, remove fallen leaves")},
    "apple_powdery_mildew": {"name": t("سفیدک پودری ❄️","Powdery Mildew ❄️"), "desc": t("سطح برگ سفید و پودری می‌شود.","White powdery surface on leaves."), "treatment": t("گوگرد، هرس و تهویه","Sulfur spray, pruning, ventilation")},
    "apple_healthy": {"name": t("برگ سالم ✅","Healthy ✅"), "desc": t("برگ سالم است.","Leaf is healthy."), "treatment": t("ادامه مراقبت‌های معمول","Continue standard care")}
}

def predict_probs(file):
    if model is None:
        # fallback demo: uniform or healthy
        return np.array([1.0, 0.0, 0.0])
    img = Image.open(file).convert("RGB")
    target_size = model.input_shape[1:3]
    img = img.resize(target_size)
    arr = img_to_array(img)/255.0
    arr = np.expand_dims(arr, axis=0)
    preds = model.predict(arr)[0]
    return preds

# ---------- SQLite (SQLAlchemy) for users ----------
DB_FILE = "users.db"
engine = sa.create_engine(f"sqlite:///{DB_FILE}", connect_args={"check_same_thread": False})
meta = MetaData()
users_table = Table('users', meta,
                    Column('id', Integer, primary_key=True),
                    Column('username', String, unique=True, nullable=False),
                    Column('password_hash', String, nullable=False))
meta.create_all(engine)
conn = engine.connect()

# ---------- Session state init ----------
if 'user' not in st.session_state: st.session_state['user'] = None
if 'tree_data' not in st.session_state:
    st.session_state['tree_data'] = pd.DataFrame(columns=['تاریخ','ارتفاع(cm)','تعداد برگ','توضیحات','هشدار هرس'])
if 'schedule' not in st.session_state:
    # initialize schedule once
    start_date = datetime.today()
    schedule_list = []
    for week in range(52):
        date = start_date + timedelta(weeks=week)
        schedule_list.append([date.date(), t("آبیاری","Watering"), t("آبیاری منظم","Regular watering"), False])
        if week % 4 == 0:
            schedule_list.append([date.date(), t("کوددهی","Fertilization"), t("تغذیه متعادل","Balanced feeding"), False])
        if week % 12 == 0:
            schedule_list.append([date.date(), t("هرس","Pruning"), t("هرس شاخه‌های اضافه یا خشک","Prune extra/dry branches"), False])
        if week % 6 == 0:
            schedule_list.append([date.date(), t("بازرسی بیماری","Disease Check"), t("بررسی برگ‌ها","Check leaves for disease"), False])
    st.session_state['schedule'] = pd.DataFrame(schedule_list, columns=['تاریخ','فعالیت','توضیحات','انجام شد'])

# ---------- Auth UI ----------
if st.session_state['user'] is None:
    mode = st.sidebar.radio(t("حالت","Mode"), (t("ورود","Login"), t("ثبت نام","Sign Up"), t("دمو","Demo")))
    if mode == t("ثبت نام","Sign Up"):
        st.header(t("ثبت نام","Sign Up"))
        username = st.text_input(t("نام کاربری","Username"))
        password = st.text_input(t("رمز عبور","Password"), type="password")
        if st.button(t("ثبت نام","Register")):
            if not username or not password:
                st.error(t("نام کاربری و رمز را وارد کنید.","Provide username & password."))
            else:
                # check existence
                sel = sa.select(users_table).where(users_table.c.username == username)
                r = conn.execute(sel).first()
                if r:
                    st.error(t("نام کاربری قبلا ثبت شده است.","Username already exists."))
                else:
                    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
                    ins = users_table.insert().values(username=username, password_hash=hashed)
                    conn.execute(ins)
                    st.success(t("ثبت نام انجام شد. اکنون وارد شوید.","Registered. Please login."))
    elif mode == t("ورود","Login"):
        st.header(t("ورود","Login"))
        username = st.text_input(t("نام کاربری","Username"))
        password = st.text_input(t("رمز عبور","Password"), type="password")
        if st.button(t("ورود","Login")):
            sel = sa.select(users_table).where(users_table.c.username == username)
            r = conn.execute(sel).first()
            if not r:
                st.error(t("نام کاربری وجود ندارد.","Username not found."))
            else:
                stored = r['password_hash']
                if bcrypt.checkpw(password.encode(), stored.encode()):
                    st.session_state['user'] = username
                    st.success(t("ورود موفق ✅","Login successful ✅"))
                else:
                    st.error(t("رمز صحیح نیست.","Wrong password."))
    else:
        # Demo mode — allow quick upload and test
        st.header(t("دمو","Demo"))
        st.info(t("در حالت دمو بدون ثبت نام می‌توانید تصویر آپلود کنید و مدل (در صورت وجود) را تست کنید.","In demo you can upload image and test the model."))
        f = st.file_uploader(t("آپلود تصویر برگ","Upload leaf image"), type=["jpg","jpeg","png"])
        if f:
            st.image(f, use_column_width=True)
            preds = predict_probs(f)
            idx = int(np.argmax(preds))
            for i, cls in enumerate(class_labels):
                pct = preds[i]*100
                color = "#2d9f3f" if cls=="apple_healthy" else "#e53935"
                st.markdown(f"<div style='margin-top:8px'><div style='background:#f1f5f9;border-radius:10px;padding:6px'><div style='background:{color};color:#fff;padding:6px;border-radius:6px;width:{int(pct)}%'>{pct:.1f}% {disease_info[cls]['name']}</div></div></div>", unsafe_allow_html=True)
            info = disease_info[class_labels[idx]]
            st.success(f"{t('نتیجه','Result')}: {info['name']}")
            st.write(f"**{t('توضیح','Description')}:** {info['desc']}")
            st.write(f"**{t('درمان','Treatment')}:** {info['treatment']}")
else:
    # ---------- Main app ----------
    menu = st.sidebar.selectbox(t("منو","Menu"),
        [t("🏠 خانه","🏠 Home"), t("🍎 تشخیص بیماری","🍎 Disease"),
         t("🌱 ثبت و رصد","🌱 Tracking"), t("📅 برنامه زمان‌بندی","📅 Schedule"),
         t("📈 پیش‌بینی رشد","📈 Prediction"), t("📥 دانلود گزارش","📥 Download"),
         t("🚪 خروج","Logout")])
    if menu == t("🚪 خروج","Logout"):
        st.session_state['user'] = None
        st.experimental_rerun()

    # ---------- HOME ----------
    if menu == t("🏠 خانه","🏠 Home"):
        st.header(t("داشبورد","Overview"))
        df = st.session_state['tree_data']
        last = df.sort_values('تاریخ').iloc[-1] if not df.empty else None
        c1,c2,c3,c4 = st.columns([1,1,1,2])
        with c1:
            st.markdown(f"<div class='kpi-card'><b>{t('ارتفاع آخرین اندازه','Last height')}</b><div style='font-size:20px'>{(str(last['ارتفاع(cm)'])+' cm') if last is not None else '--'}</div></div>", unsafe_allow_html=True)
        with c2:
            st.markdown(f"<div class='kpi-card'><b>{t('تعداد برگ‌ها','Leaves')}</b><div style='font-size:20px'>{(int(last['تعداد برگ']) if last is not None else '--')}</div></div>", unsafe_allow_html=True)
        with c3:
            status = t('⚠️ نیاز به هرس','⚠️ Prune needed') if (last is not None and last['هشدار هرس']) else t('✅ سالم','✅ Healthy')
            st.markdown(f"<div class='kpi-card'><b>{t('وضعیت هرس','Prune Status')}</b><div style='font-size:18px'>{status}</div></div>", unsafe_allow_html=True)
        with c4:
            st.markdown(f"<div class='section'><b>{t('نکته','Quick Tip')}</b><br>{t('برای نگهداری بهتر، هفته‌ای یکبار بررسی کنید.','Check seedlings weekly for best care.')}</div>", unsafe_allow_html=True)
        if not df.empty:
            fig = px.line(df.sort_values('تاریخ'), x='تاریخ', y=['ارتفاع(cm)','تعداد برگ'], labels={'value':t('مقدار','Value'),'variable':t('پارامتر','Parameter'),'تاریخ':t('تاریخ','Date')})
            st.plotly_chart(fig, use_container_width=True)

    # ---------- DISEASE ----------
    elif menu == t("🍎 تشخیص بیماری","🍎 Disease"):
        st.header(t("تشخیص بیماری برگ","Leaf Disease Detection"))
        st.info(t("آپلود تصویر با کیفیت بهتر => نتیجه دقیق‌تر","Higher quality images => better results"))
        f = st.file_uploader(t("آپلود تصویر","Upload image"), type=["jpg","jpeg","png"])
        if f:
            st.image(f, use_column_width=True)
            preds = predict_probs(f)
            idx = int(np.argmax(preds))
            for i, cls in enumerate(class_labels):
                pct = preds[i]*100
                color = "#2d9f3f" if cls=="apple_healthy" else "#e53935"
                st.markdown(f"<div style='margin-top:8px'><div style='background:#f1f5f9;border-radius:10px;padding:6px'><div style='background:{color};color:#fff;padding:6px;border-radius:6px;width:{int(pct)}%'>{pct:.1f}% {disease_info[cls]['name']}</div></div></div>", unsafe_allow_html=True)
            info = disease_info[class_labels[idx]]
            st.success(f"{t('نتیجه','Result')}: {info['name']}")
            st.write(f"**{t('توضیح','Description')}:** {info['desc']}")
            st.write(f"**{t('درمان','Treatment')}:** {info['treatment']}")

    # ---------- TRACKING ----------
    elif menu == t("🌱 ثبت و رصد","🌱 Tracking"):
        st.header(t("ثبت و رصد رشد نهال","Seedling Tracking"))
        with st.expander(t("➕ ثبت اندازه‌گیری جدید","➕ Add measurement")):
            date = st.date_input(t("تاریخ","Date"), value=datetime.today())
            height = st.number_input(t("ارتفاع (cm)","Height (cm)"), min_value=0.0, step=0.5)
            leaves = st.number_input(t("تعداد برگ‌ها","Leaves"), min_value=0, step=1)
            desc = st.text_area(t("توضیحات","Notes"))
            prune = st.checkbox(t("نیاز به هرس؟","Prune needed?"))
            if st.button(t("ثبت","Submit")):
                st.session_state['tree_data'] = pd.concat([st.session_state['tree_data'],
                    pd.DataFrame([[date, height, leaves, desc, prune]], columns=['تاریخ','ارتفاع(cm)','تعداد برگ','توضیحات','هشدار هرس'])], ignore_index=True)
                st.success(t("ثبت شد ✅","Added ✅"))
        if not st.session_state['tree_data'].empty:
            df = st.session_state['tree_data'].sort_values('تاریخ')
            st.dataframe(df)
            fig = px.line(df, x='تاریخ', y='ارتفاع(cm)', title=t("روند ارتفاع","Height trend"))
            st.plotly_chart(fig, use_container_width=True)

    # ---------- SCHEDULE ----------
    elif menu == t("📅 برنامه زمان‌بندی","📅 Schedule"):
        st.header(t("برنامه زمان‌بندی","Schedule"))
        df_s = st.session_state['schedule']
        today = datetime.today().date()
        today_tasks = df_s[(df_s['تاریخ']==today) & (df_s['انجام شد']==False)]
        if not today_tasks.empty:
            st.warning(t("فعالیت‌های امروز وجود دارد!","There are tasks for today!"))
            for _, r in today_tasks.iterrows():
                st.write(f"• {r['فعالیت']} — {r['توضیحات']}")
        else:
            st.success(t("امروز کاری برنامه‌ریزی نشده یا همه انجام شده","No pending tasks for today"))
        for i in df_s.index:
            df_s.at[i,'انجام شد'] = st.checkbox(f"{df_s.at[i,'تاریخ']} — {df_s.at[i,'فعالیت']}", value=df_s.at[i,'انجام شد'], key=f"sch{i}")
        st.dataframe(df_s)

    # ---------- PREDICTION ----------
    elif menu == t("📈 پیش‌بینی رشد","📈 Prediction"):
        st.header(t("پیش‌بینی رشد","Growth Prediction"))
        if st.session_state['tree_data'].empty:
            st.info(t("ابتدا اندازه‌گیری‌های رشد را ثبت کنید.","Add growth records first."))
        else:
            df = st.session_state['tree_data'].sort_values('تاریخ')
            df['روز'] = (df['تاریخ'] - df['تاریخ'].min()).dt.days
            X = df['روز'].values
            y = df['ارتفاع(cm)'].values
            def linear_fit(x,y):
                if len(x) < 2: return lambda z: y[-1] if len(y)>0 else 0
                a = (y[-1]-y[0])/(x[-1]-x[0]); b = y[0] - a*x[0]; return lambda z: a*z + b
            f_lin = linear_fit(X,y)
            future_days = np.array([(df['روز'].max() + 7*i) for i in range(1,13)])
            future_dates = [df['تاریخ'].max() + timedelta(weeks=i) for i in range(1,13)]
            preds = [f_lin(d) for d in future_days]
            df_future = pd.DataFrame({'تاریخ': future_dates, t('ارتفاع پیش‌بینی شده(cm)','Predicted Height (cm)'): preds})
            st.dataframe(df_future)
            fig = px.line(df_future, x='تاریخ', y=df_future.columns[1], title=t("پیش‌بینی ارتفاع","Height forecast"))
            st.plotly_chart(fig, use_container_width=True)
            st.session_state['df_future'] = df_future

    # ---------- DOWNLOAD ----------
    elif menu == t("📥 دانلود گزارش","📥 Download"):
        st.header(t("دانلود گزارش","Download"))
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
            if not st.session_state['tree_data'].empty:
                st.session_state['tree_data'].to_excel(writer, sheet_name='growth', index=False)
            if not st.session_state['schedule'].empty:
                st.session_state['schedule'].to_excel(writer, sheet_name='schedule', index=False)
            if 'df_future' in st.session_state and not st.session_state['df_future'].empty:
                st.session_state['df_future'].to_excel(writer, sheet_name='prediction', index=False)
            writer.save()
        data = buffer.getvalue()
        st.download_button(label=t("دانلود Excel داشبورد","Download Excel Dashboard"), data=data, file_name="apple_dashboard_full.xlsx",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
