import streamlit as st
import pandas as pd
import numpy as np
from PIL import Image
from datetime import datetime, timedelta
import io
import plotly.express as px
import os
import jdatetime
import tensorflow as tf
from tensorflow.keras.utils import img_to_array

# ---------- تنظیمات صفحه ----------
st.set_page_config(page_title="داشبورد نهال سیب 🍎", layout="wide")

# ---------- RTL و استایل ----------
st.markdown("""
<style>
body {direction: rtl; font-family: 'Vazir', sans-serif; background-image: linear-gradient(180deg, #e6f2ea 0%, #d9eef0 40%, #cfeef0 100%), url('https://images.unsplash.com/photo-1506806732259-39c2d0268443?auto=format&fit=crop&w=1470&q=80'); background-size: cover; background-attachment: fixed; color: #0f172a;}
.kpi-card {background: rgba(255,255,255,0.95); border-radius: 12px; padding: 12px; box-shadow: 0 8px 24px rgba(7,10,25,0.08); margin-bottom: 8px;}
.section {background: linear-gradient(180deg, rgba(255,255,255,0.86), rgba(255,255,255,0.78)); border-radius: 12px; padding: 12px;}
.logo-row {display:flex; align-items:center; gap:10px;}
</style>
""", unsafe_allow_html=True)

# ---------- زبان ----------
if 'lang' not in st.session_state: st.session_state['lang'] = 'FA'
lang_choice = st.sidebar.selectbox("زبان / Language", ['فارسی','English'])
st.session_state['lang'] = 'EN' if lang_choice=='English' else 'FA'
def t(fa,en): return en if st.session_state['lang']=='EN' else fa

# ---------- لوگو ----------
logo_path = "logo.svg"
if os.path.exists(logo_path):
    with open(logo_path, 'r', encoding='utf-8') as f:
        svg = f.read()
    st.markdown(f"<div class='logo-row'>{svg}</div>", unsafe_allow_html=True)
else:
    st.markdown(f"<h1>🍎 Seedling Pro — {t('داشبورد نهال سیب','Apple Seedling Dashboard')}</h1>")

# ---------- داده‌ها ----------
if 'tree_data' not in st.session_state:
    st.session_state['tree_data'] = pd.DataFrame(columns=['تاریخ','ارتفاع(cm)','تعداد برگ','توضیحات','نیاز به هرس'])
if 'schedule' not in st.session_state:
    start_date = datetime.today()
    schedule_list = []
    for week in range(52):
        date = start_date + timedelta(weeks=week)
        schedule_list.append([date.date(), t("آبیاری","Watering"), False])
        if week % 4 == 0:
            schedule_list.append([date.date(), t("کوددهی","Fertilization"), False])
        if week % 12 == 0:
            schedule_list.append([date.date(), t("هرس","Pruning"), False])
        if week % 6 == 0:
            schedule_list.append([date.date(), t("بازرسی بیماری","Disease Check"), False])
    st.session_state['schedule'] = pd.DataFrame(schedule_list, columns=['تاریخ','فعالیت','انجام شد'])
if 'df_future' not in st.session_state: st.session_state['df_future'] = pd.DataFrame()

# ---------- مدل تشخیص بیماری ----------
@st.cache_resource
def load_model_cached(path="leaf_model.h5"):
    try:
        return tf.keras.models.load_model(path)
    except:
        return None
model = load_model_cached()
class_labels = ["apple_healthy", "apple_black_spot", "apple_powdery_mildew"]
disease_info = {
    "apple_black_spot": {"name": t("لکه سیاه ⚫️","Black Spot ⚫️"), "desc": t("لکه‌های سیاه روی برگ و میوه.","Black spots on leaves/fruit."), "treatment": t("قارچ‌کش، هرس و جمع‌آوری برگ‌ها","Fungicide, prune, remove fallen leaves")},
    "apple_powdery_mildew": {"name": t("سفیدک پودری ❄️","Powdery Mildew ❄️"), "desc": t("سطح برگ سفید و پودری می‌شود.","White powdery surface on leaves."), "treatment": t("گوگرد، هرس و تهویه","Sulfur spray, pruning, ventilation")},
    "apple_healthy": {"name": t("برگ سالم ✅","Healthy ✅"), "desc": t("برگ سالم است.","Leaf is healthy."), "treatment": t("ادامه مراقبت‌های معمول","Continue standard care")}
}

# ---------- منو ----------
menu = st.sidebar.selectbox(t("منو","Menu"), [t("🏠 خانه","Home"), t("🍎 تشخیص بیماری","Disease"), t("🌱 ثبت و رصد","Tracking"), t("📅 برنامه زمان‌بندی","Schedule"), t("📈 پیش‌بینی رشد","Prediction"), t("📥 دانلود گزارش","Download")])

# ---------- داشبورد خانه ----------
if menu == t("🏠 خانه","Home"):
    st.header(t("داشبورد عملیاتی نهال","Operational Seedling Dashboard"))
    df = st.session_state['tree_data']
    alerts = []
    if not df.empty:
        last = df.sort_values('تاریخ').iloc[-1]
        # هشدارها
        if last['نیاز به هرس']: alerts.append(t("هشدار: نیاز به هرس وجود دارد","Pruning Needed"))
        if last['ارتفاع(cm)'] < 20: alerts.append(t("هشدار: ارتفاع نهال کمتر از حد معمول است","Height Below Normal"))
        if last['تعداد برگ'] < 10: alerts.append(t("هشدار: تعداد برگ کم است","Leaves Low"))
    if alerts: st.warning("\n".join(alerts))

# ---------- ثبت و رصد ----------
elif menu == t("🌱 ثبت و رصد","Tracking"):
    st.header(t("ثبت و رصد رشد نهال","Seedling Tracking"))
    with st.expander(t("➕ ثبت اندازه‌گیری جدید","Add Measurement")):
        date = st.date_input(t("تاریخ","Date"), value=datetime.today())
        height = st.number_input(t("ارتفاع (cm)","Height (cm)"), min_value=0.0, step=0.5)
        leaves = st.number_input(t("تعداد برگ‌ها","Leaves"), min_value=0, step=1)
        notes = st.text_area(t("توضیحات","Notes"))
        prune = st.checkbox(t("نیاز به هرس؟","Prune needed?"))
        if st.button(t("ثبت","Submit")):
            st.session_state['tree_data'] = pd.concat([st.session_state['tree_data'], pd.DataFrame([[date, height, leaves, notes, prune]], columns=['تاریخ','ارتفاع(cm)','تعداد برگ','توضیحات','نیاز به هرس'])], ignore_index=True)
            st.success(t("ثبت شد ✅","Added ✅"))
    if not st.session_state['tree_data'].empty:
        df_display = st.session_state['tree_data'].copy()
        df_display['تاریخ شمسی'] = df_display['تاریخ'].apply(lambda x: jdatetime.date.fromgregorian(date=x).strftime('%Y/%m/%d'))
        st.dataframe(df_display)

# ---------- برنامه زمان‌بندی ----------
elif menu == t("📅 برنامه زمان‌بندی","Schedule"):
    st.header(t("برنامه زمان‌بندی","Schedule"))
    df_s = st.session_state['schedule']
    for i in df_s.index:
        df_s.at[i,'انجام شد'] = st.checkbox(f"{df_s.at[i,'تاریخ']} — {df_s.at[i,'فعالیت']}", value=df_s.at[i,'انجام شد'], key=f"sch{i}")
    st.dataframe(df_s)

# ---------- پیش‌بینی رشد ----------
elif menu == t("📈 پیش‌بینی رشد","Prediction"):
    st.header(t("پیش‌بینی رشد","Growth Prediction"))
    df = st.session_state['tree_data']
    if df.empty:
        st.info(t("ابتدا اندازه‌گیری‌های رشد را ثبت کنید.","Add growth records first."))
    else:
        df_sorted = df.sort_values('تاریخ')
        X = (df_sorted['تاریخ'] - df_sorted['تاریخ'].min()).dt.days.values
        y = df_sorted['ارتفاع(cm)'].values
        if len(X) >= 2:
            a = (y[-1]-y[0])/(X[-1]-X[0]); b = y[0]-a*X[0]
            future_days = np.array([(X.max()+7*i) for i in range(1,13)])
            preds = a*future_days + b
            future_dates = [df_sorted['تاریخ'].max() + timedelta(weeks=i) for i in range(1,13)]
            df_future = pd.DataFrame({'تاریخ': future_dates, t('ارتفاع پیش‌بینی شده(cm)','Predicted Height (cm)'): preds})
            st.session_state['df_future'] = df_future
            st.dataframe(df_future)

# ---------- تشخیص بیماری ----------
elif menu == t("🍎 تشخیص بیماری
