# app_seedling_pro_auto_alerts.py
import streamlit as st
import pandas as pd
import numpy as np
from PIL import Image
import tensorflow as tf
from tensorflow.keras.utils import img_to_array
from datetime import datetime, timedelta
import io
import plotly.express as px
import os

# ---------- تنظیمات صفحه ----------
st.set_page_config(page_title="داشبورد نهال سیب 🍎", layout="wide")

# ---------- تابع ترجمه ----------
def t(fa, en):
    lang = st.session_state.get('lang', 'FA')
    return en if lang=='EN' else fa

# ---------- انتخاب زبان ----------
if 'lang' not in st.session_state: st.session_state['lang'] = 'FA'
lang_choice = st.sidebar.selectbox("زبان / Language", ['فارسی','English'])
st.session_state['lang'] = 'EN' if lang_choice=='English' else 'FA'

# ---------- آماده‌سازی داده‌ها ----------
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
        # هشدار هرس
        if last['نیاز به هرس']:
            alerts.append(t("هشدار: نیاز به هرس وجود دارد","Pruning Needed"))
        # هشدار رشد کم
        if last['ارتفاع(cm)'] < 20:
            alerts.append(t("هشدار: ارتفاع نهال کمتر از حد معمول است","Height Below Normal"))
        # هشدار تعداد برگ کم
        if last['تعداد برگ'] < 10:
            alerts.append(t("هشدار: تعداد برگ کم است","Leaves Low"))
    if alerts:
        st.warning("\n".join(alerts))

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
        st.dataframe(st.session_state['tree_data'])

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
elif menu == t("🍎 تشخیص بیماری","Disease"):
    st.header(t("تشخیص بیماری برگ","Leaf Disease Detection"))
    f = st.file_uploader(t("آپلود تصویر","Upload leaf image"), type=["jpg","jpeg","png"])
    if f:
        st.image(f, use_container_width=True)
        if model:
            img = Image.open(f).convert("RGB")
            img = img.resize(model.input_shape[1:3])
            arr = img_to_array(img)/255.0
            arr = np.expand_dims(arr, axis=0)
            preds = model.predict(arr)[0]
        else:
            preds = np.array([1.0,0.0,0.0])
        idx = int(np.argmax(preds))
        st.write(f"**{t('نتیجه','Result')}:** {disease_info[class_labels[idx]]['name']}")
        st.write(f"**{t('شدت بیماری (%)','Severity (%)')}:** {preds[idx]*100:.1f}%")
        st.write(f"**{t('توضیح','Description')}:** {disease_info[class_labels[idx]]['desc']}")
        st.write(f"**{t('درمان / راهنمایی','Treatment / Guidance')}:** {disease_info[class_labels[idx]]['treatment']}")

# ---------- دانلود گزارش ----------
elif menu == t("📥 دانلود گزارش","Download"):
    st.header(t("دانلود گزارش","Download"))
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
        if not st.session_state['tree_data'].empty:
            st.session_state['tree_data'].to_excel(writer, sheet_name='growth', index=False)
        if not st.session_state['schedule'].empty:
            st.session_state['schedule'].to_excel(writer, sheet_name='schedule', index=False)
        if not st.session_state['df_future'].empty:
            st.session_state['df_future'].to_excel(writer, sheet_name='prediction', index=False)
    data = buffer.getvalue()
    st.download_button(label=t("دانلود Excel داشبورد","Download Excel Dashboard"), data=data, file_name="apple_dashboard.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
