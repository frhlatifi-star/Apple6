import streamlit as st
import tensorflow as tf
from tensorflow.keras.utils import img_to_array
from PIL import Image
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import io

# ---------------- تنظیمات صفحه ----------------
st.set_page_config(
    page_title="🍎 داشبورد نهال سیب",
    page_icon="🍎",
    layout="wide"
)

# ---------------- CSS حرفه‌ای و بک‌گراند ----------------
st.markdown("""
<style>
@import url('https://cdn.jsdelivr.net/gh/rastikerdar/vazir-font@v30.1.0/dist/font-face.css');
body {font-family: 'Vazir', sans-serif; direction: rtl; 
      background: linear-gradient(to bottom, #f0f4f8, #d9e2ec);}
h1,h2,h3,h4,h5,h6 {color:#2c3e50;}
.stButton>button {background-color: #38a169; color: white; border-radius: 12px; padding: 0.6em 1.2em; font-size: 16px; box-shadow: 2px 2px 6px rgba(0,0,0,0.2);}
.kpi-card {background:#ffffff; border-radius:15px; padding:15px; margin:10px; box-shadow:2px 2px 15px rgba(0,0,0,0.2); transition: 0.3s;}
.kpi-card:hover {transform: scale(1.05);}
.card-title {font-weight:bold; font-size:18px; margin-bottom:5px;}
.card-value {font-size:24px; color:#2d3748;}
.progress-bar {height:25px; border-radius:12px; background:#e2e8f0; overflow:hidden;}
.progress-fill {height:100%; text-align:center; color:white; line-height:25px; font-weight:bold; transition: width 1s;}
</style>
""", unsafe_allow_html=True)

# ---------------- انتخاب زبان ----------------
lang = st.sidebar.selectbox("🌐 زبان / Language", ["فارسی", "English"])

def t(fa_text, en_text):
    return fa_text if lang == "فارسی" else en_text

# ---------------- بارگذاری مدل ----------------
@st.cache_resource
def load_model():
    return tf.keras.models.load_model("leaf_model.h5")

model = load_model()
class_labels = ["apple_healthy", "apple_black_spot", "apple_powdery_mildew"]
disease_info = {
    "apple_black_spot": {"name":"لکه سیاه ⚫️","desc":"لکه‌های سیاه روی برگ و میوه.","treatment":"قارچ‌کش، هرس شاخه‌ها و جمع‌آوری برگ‌ها"},
    "apple_powdery_mildew":{"name":"سفیدک پودری ❄️","desc":"برگ‌ها سفید و پودری می‌شوند.","treatment":"قارچ‌کش گوگردی، هرس و تهویه باغ"},
    "apple_healthy":{"name":"برگ سالم ✅","desc":"برگ سالم است.","treatment":"ادامه مراقبت‌های معمول"}
}

def predict_probs(file):
    img = Image.open(file).convert("RGB")
    target_size = model.input_shape[1:3]
    img = img.resize(target_size)
    array = img_to_array(img)/255.0
    array = np.expand_dims(array, axis=0)
    return model.predict(array)[0]

# ---------------- منو ----------------
menu = [t("🏠 خانه","🏠 Home"), t("🍎 تشخیص بیماری","🍎 Disease Detection"), t("🌱 ثبت و رصد","🌱 Tracking"),
        t("📅 برنامه زمان‌بندی","📅 Schedule"), t("📈 پیش‌بینی رشد","📈 Growth Prediction"),
        t("📥 دانلود گزارش","📥 Download Report")]

choice = st.sidebar.selectbox(t("منو","Menu"), menu)

# ---------------- خانه ----------------
if choice == t("🏠 خانه","🏠 Home"):
    st.markdown(f"## 🍎 {t('داشبورد حرفه‌ای نهال سیب','Apple Seedling Dashboard')}")
    st.write(t("روند رشد و سلامت نهال‌ها را مشاهده کنید.","Track seedling growth and health."))

    if 'tree_data' in st.session_state and not st.session_state['tree_data'].empty:
        df = st.session_state['tree_data'].sort_values('تاریخ')
        latest = df.iloc[-1]
        col1, col2, col3 = st.columns(3)
        col1_color = "#a3e635"
        col3_color = "#fcd34d" if latest['هشدار هرس'] else "#a3e635"
        col1.markdown(f"<div class='kpi-card' style='background:{col1_color}'><div class='card-title'>{t('ارتفاع آخرین اندازه‌گیری','Last Height')}</div><div class='card-value'>{latest['ارتفاع(cm)']} cm</div></div>", unsafe_allow_html=True)
        col2.markdown(f"<div class='kpi-card'><div class='card-title'>{t('تعداد برگ‌ها','Leaves Count')}</div><div class='card-value'>{latest['تعداد برگ']}</div></div>", unsafe_allow_html=True)
        col3.markdown(f"<div class='kpi-card' style='background:{col3_color}'><div class='card-title'>{t('هشدار هرس','Prune Alert')}</div><div class='card-value'>{'⚠️' if latest['هشدار هرس'] else '✅'}</div></div>", unsafe_allow_html=True)
    else:
        st.info(t("داده‌ای ثبت نشده است. لطفاً ابتدا رشد نهال را ثبت کنید.","No data yet. Please add growth records first."))

# ---------------- تشخیص بیماری ----------------
elif choice == t("🍎 تشخیص بیماری","🍎 Disease Detection"):
    st.header(t("🍎 تشخیص بیماری برگ","🍎 Leaf Disease Detection"))
    uploaded_file = st.file_uploader(t("📸 آپلود تصویر برگ","📸 Upload Leaf Image"), type=["jpg","jpeg","png"])
    if uploaded_file:
        st.image(uploaded_file, caption=t("📷 تصویر آپلود شده","Uploaded Image"), use_column_width=True)
        probs = predict_probs(uploaded_file)
        label_idx = np.argmax(probs)
        label = class_labels[label_idx]

        st.write(t("احتمال بیماری (٪)","Disease probability (%)"))
        for i, c in enumerate(class_labels):
            width = int(probs[i]*100)
            color = "#38a169" if c=="apple_healthy" else "#f87171"
            st.markdown(f"<div class='progress-bar'><div class='progress-fill' style='width:{width}%; background:{color}'>{probs[i]*100:.1f}% {disease_info[c]['name']}</div></div>", unsafe_allow_html=True)

        info = disease_info[label]
        st.markdown(f"<div class='kpi-card'><div class='card-title'>{t('نتیجه','Result')}</div><div class='card-value'>{info['name']}</div><br><strong>{t('توضیح','Description')}:</strong> {info['desc']}<br><strong>{t('درمان','Treatment')}:</strong> {info['treatment']}</div>", unsafe_allow_html=True)

# ---------------- ثبت و رصد ----------------
elif choice == t("🌱 ثبت و رصد","🌱 Tracking"):
    st.header(t("🌱 ثبت و رصد رشد نهال","🌱 Seedling Tracking"))
    if 'tree_data' not in st.session_state:
        st.session_state['tree_data'] = pd.DataFrame(columns=['تاریخ','ارتفاع(cm)','تعداد برگ','توضیحات','هشدار هرس'])

    with st.expander(t("➕ ثبت اندازه‌گیری رشد","➕ Add Growth Record")):
        date = st.date_input(t("تاریخ","Date"), value=datetime.today())
        height = st.number_input(t("ارتفاع (cm)","Height (cm)"), min_value=0.0, step=0.5)
        leaves = st.number_input(t("تعداد برگ‌ها","Leaves count"), min_value=0, step=1)
        desc = st.text_area(t("توضیحات","Description"))
        prune_warning = st.checkbox(t("هشدار هرس؟","Prune alert?"))
        if st.button(t("ثبت","Add")):
            st.session_state['tree_data'] = pd.concat([
                st.session_state['tree_data'],
                pd.DataFrame([[date, height, leaves, desc, prune_warning]], columns=['تاریخ','ارتفاع(cm)','تعداد برگ','توضیحات','هشدار هرس'])
            ], ignore_index=True)
            st.success("✅ " + t("ثبت شد","Added"))

    if not st.session_state['tree_data'].empty:
        st.dataframe(st.session_state['tree_data'])

# ---------------- برنامه زمان‌بندی ----------------
elif choice == t("📅 برنامه زمان‌بندی","📅 Schedule"):
    st.header(t("📅 برنامه یک ساله فعالیت‌ها","📅 Yearly Schedule"))
    if 'schedule' not in st.session_state:
        start_date = datetime.today()
        schedule_list = []
        for week in range(52):
            date = start_date + timedelta(weeks=week)
            schedule_list.append([date.date(), t("آبیاری","Watering"), t("آبیاری منظم","Regular watering"), False])
            if week % 4 == 0:
                schedule_list.append([date.date(), t("کوددهی","Fertilization"), t("تغذیه متعادل","Balanced feeding"), False])
            if week % 12 == 0:
                schedule_list.append([date.date(), t("هرس","Pruning"), t("Prune extra/dry branches"), False])
            if week % 6 == 0:
                schedule_list.append([date.date(), t("بازرسی بیماری","Disease Check"), t("Check leaves for disease"), False])
        st.session_state['schedule'] = pd.DataFrame(schedule_list, columns=['تاریخ','فعالیت','توضیحات','انجام شد'])

    df_schedule = st.session_state['schedule']
    today = datetime.today().date()
    today_tasks = df_schedule[(df_schedule['تاریخ']==today) & (df_schedule['انجام شد']==False)]
    if not today_tasks.empty:
        for i, row in today_tasks.iterrows():
            st.warning(f"⚠️ {row['فعالیت']} - {row['توضیحات']}")
    else:
        st.success(t("امروز همه فعالیت‌ها انجام شده ✅","All tasks completed today ✅"))

    for i in df_schedule.index:
        df_schedule.at[i,'انجام شد'] = st.checkbox(f"{df_schedule.at[i,'تاریخ']} - {df_schedule.at[i,'فعالیت']}", value=df_schedule.at[i,'انجام شد'], key=i)
    st.dataframe(df_schedule)

# ---------------- پیش‌بینی رشد ----------------
elif choice == t("📈 پیش‌بینی رشد","📈 Growth Prediction"):
    st.header(t("📈 پیش‌بینی رشد نهال","📈 Seedling Growth Prediction"))
    if 'tree_data' in st.session_state and not st.session_state['tree_data'].empty:
        df = st.session_state['tree_data'].sort_values('تاریخ')
        df['روز'] = (df['تاریخ'] - df['تاریخ'].min()).dt.days
        X = df['روز'].values
        y_height = df['ارتفاع(cm)'].values
        y_leaves = df['تعداد برگ'].values

        def linear_fit(x, y):
            if len(x) < 2:
                return lambda z: y[-1] if len(y)>0 else 0
            a = (y[-1]-y[0])/(x[-1]-x[0])
            b = y[0] - a*x[0]
            return lambda z: a*z + b

        pred_height_func = linear_fit(X, y_height)
        pred_leaves_func = linear_fit(X, y_leaves)

        future_days = np.array([(df['روز'].max() + 7*i) for i in range(1, 13)])
        future_dates = [df['تاریخ'].max() + timedelta(weeks=i) for i in range(1, 13)]
        pred_height = [pred_height_func(d) for d in future_days]
        pred_leaves = [pred_leaves_func(d) for d in future_days]

        df_future = pd.DataFrame({
            'تاریخ': future_dates,
            'ارتفاع پیش‌بینی شده(cm)': pred_height,
            'تعداد برگ پیش‌بینی شده': pred_leaves
        })
        st.dataframe(df_future)

# ---------------- دانلود گزارش ----------------
elif choice == t("📥 دانلود گزارش","📥 Download Report"):
    st.header(t("📥 دانلود گزارش کامل","📥 Download Full Report"))
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        if 'tree_data' in st.session_state and not st.session_state['tree_data'].empty:
            st.session_state['tree_data'].to_excel(writer, sheet_name="رشد نهال", index=False)
        if 'schedule' in st.session_state and not st.session_state['schedule'].empty:
            st.session_state['schedule'].to_excel(writer, sheet_name="برنامه رشد", index=False)
        if 'df_future' in locals() and not df_future.empty:
            df_future.to_excel(writer, sheet_name="پیش‌بینی رشد", index=False)
        writer.save()
        processed_data = output.getvalue()

    st.download_button(
        label=t("دانلود Excel داشبورد کامل","Download Excel Dashboard"),
        data=processed_data,
        file_name="apple_dashboard_full.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
