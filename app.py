import streamlit as st
import tensorflow as tf
from tensorflow.keras.utils import img_to_array
from PIL import Image
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import plotly.express as px

# ------------------- تنظیمات صفحه -------------------
st.set_page_config(
    page_title="🍎 داشبورد حرفه‌ای نهال سیب",
    page_icon="🍎",
    layout="wide"
)

# ------------------- CSS حرفه‌ای -------------------
st.markdown("""
<style>
@import url('https://cdn.jsdelivr.net/gh/rastikerdar/vazir-font@v30.1.0/dist/font-face.css');
body {font-family: 'Vazir', sans-serif; direction: rtl; background-color: #f0f4f8;}
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

# ------------------- بارگذاری مدل -------------------
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

# ------------------- منو -------------------
menu = ["🏠 خانه", "🍎 تشخیص بیماری", "🌱 ثبت و رصد", "📅 برنامه زمان‌بندی", "📈 پیش‌بینی رشد", "📥 دانلود گزارش"]
choice = st.sidebar.selectbox("منو", menu)

# ------------------- خانه -------------------
if choice == "🏠 خانه":
    st.markdown("## 🍎 داشبورد حرفه‌ای موبایلی نهال سیب")
    st.write("روند رشد و سلامت نهال‌ها را با کارت‌های تعاملی و نمودارهای جذاب مشاهده کنید.")

    if 'tree_data' in st.session_state and not st.session_state['tree_data'].empty:
        df = st.session_state['tree_data'].sort_values('تاریخ')
        latest = df.iloc[-1]
        col1, col2, col3 = st.columns(3)
        # رنگ پویا کارت بر اساس هشدار هرس
        col1_color = "#a3e635" # سبز
        col3_color = "#fcd34d" if latest['هشدار هرس'] else "#a3e635"
        col1.markdown(f"<div class='kpi-card' style='background:{col1_color}'><div class='card-title'>ارتفاع آخرین اندازه‌گیری</div><div class='card-value'>{latest['ارتفاع(cm)']} cm</div></div>", unsafe_allow_html=True)
        col2.markdown(f"<div class='kpi-card'><div class='card-title'>تعداد برگ‌ها</div><div class='card-value'>{latest['تعداد برگ']}</div></div>", unsafe_allow_html=True)
        col3.markdown(f"<div class='kpi-card' style='background:{col3_color}'><div class='card-title'>هشدار هرس</div><div class='card-value'>{'⚠️' if latest['هشدار هرس'] else '✅'}</div></div>", unsafe_allow_html=True)

        fig = px.line(df, x='تاریخ', y=['ارتفاع(cm)','تعداد برگ'], markers=True,
                      labels={'value':'مقدار', 'variable':'پارامتر', 'تاریخ':'تاریخ'})
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("داده‌ای ثبت نشده است. لطفاً ابتدا رشد نهال را ثبت کنید.")

# ------------------- تشخیص بیماری -------------------
elif choice == "🍎 تشخیص بیماری":
    st.header("🍎 تشخیص بیماری برگ")
    uploaded_file = st.file_uploader("📸 آپلود تصویر برگ", type=["jpg","jpeg","png"])
    if uploaded_file:
        st.image(uploaded_file, caption="📷 تصویر آپلود شده", use_column_width=True)
        probs = predict_probs(uploaded_file)
        label_idx = np.argmax(probs)
        label = class_labels[label_idx]

        st.write("احتمال بیماری (٪) با انیمیشن:")
        for i, c in enumerate(class_labels):
            width = int(probs[i]*100)
            color = "#38a169" if c=="apple_healthy" else "#f87171"
            st.markdown(f"<div class='progress-bar'><div class='progress-fill' style='width:{width}%; background:{color}'>{probs[i]*100:.1f}% {disease_info[c]['name']}</div></div>", unsafe_allow_html=True)

        info = disease_info[label]
        st.markdown(f"<div class='kpi-card'><div class='card-title'>نتیجه:</div><div class='card-value'>{info['name']}</div><br><strong>توضیح:</strong> {info['desc']}<br><strong>درمان:</strong> {info['treatment']}</div>", unsafe_allow_html=True)

# ------------------- ثبت و رصد -------------------
elif choice == "🌱 ثبت و رصد":
    st.header("🌱 ثبت و رصد رشد نهال")
    if 'tree_data' not in st.session_state:
        st.session_state['tree_data'] = pd.DataFrame(columns=['تاریخ','ارتفاع(cm)','تعداد برگ','توضیحات','هشدار هرس'])

    with st.expander("➕ ثبت اندازه‌گیری رشد"):
        date = st.date_input("تاریخ", value=datetime.today())
        height = st.number_input("ارتفاع (cm)", min_value=0.0, step=0.5)
        leaves = st.number_input("تعداد برگ‌ها", min_value=0, step=1)
        desc = st.text_area("توضیحات")
        prune_warning = st.checkbox("هشدار هرس؟")
        if st.button("ثبت"):
            st.session_state['tree_data'] = pd.concat([
                st.session_state['tree_data'],
                pd.DataFrame([[date, height, leaves, desc, prune_warning]], columns=['تاریخ','ارتفاع(cm)','تعداد برگ','توضیحات','هشدار هرس'])
            ], ignore_index=True)
            st.success("✅ ثبت شد")

    if not st.session_state['tree_data'].empty:
        st.dataframe(st.session_state['tree_data'])

# ------------------- برنامه زمان‌بندی -------------------
elif choice == "📅 برنامه زمان‌بندی":
    st.header("📅 برنامه یک ساله فعالیت‌ها")
    if 'schedule' not in st.session_state:
        start_date = datetime.today()
        schedule_list = []
        for week in range(52):
            date = start_date + timedelta(weeks=week)
            schedule_list.append([date.date(), "آبیاری", "آبیاری منظم", False])
            if week % 4 == 0:
                schedule_list.append([date.date(), "کوددهی", "تغذیه متعادل", False])
            if week % 12 == 0:
                schedule_list.append([date.date(), "هرس", "هرس شاخه‌های اضافه یا خشک", False])
            if week % 6 == 0:
                schedule_list.append([date.date(), "بازرسی بیماری", "بررسی برگ‌ها", False])
        st.session_state['schedule'] = pd.DataFrame(schedule_list, columns=['تاریخ','فعالیت','توضیحات','انجام شد'])

    df_schedule = st.session_state['schedule']
    today = datetime.today().date()
    today_tasks = df_schedule[(df_schedule['تاریخ']==today) & (df_schedule['انجام شد']==False)]
    if not today_tasks.empty:
        for i, row in today_tasks.iterrows():
            st.warning(f"⚠️ {row['فعالیت']} - {row['توضیحات']}")
    else:
        st.success("امروز همه فعالیت‌ها انجام شده ✅")

    for i in df_schedule.index:
        df_schedule.at[i,'انجام شد'] = st.checkbox(f"{df_schedule.at[i,'تاریخ']} - {df_schedule.at[i,'فعالیت']}", value=df_schedule.at[i,'انجام شد'], key=i)
    st.dataframe(df_schedule)

# ------------------- پیش‌بینی رشد -------------------
elif choice == "📈 پیش‌بینی رشد":
    st.header("📈 پیش‌بینی رشد نهال")
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
        fig = px.line(df_future, x='تاریخ', y=['ارتفاع پیش‌بینی شده(cm)','تعداد برگ پیش‌بینی شده'], markers=True)
        st.plotly_chart(fig, use_container_width=True)

# ------------------- دانلود گزارش -------------------
elif choice == "📥 دانلود گزارش":
    st.header("📥 دانلود گزارش کامل")
    if st.button("دانلود Excel"):
        with pd.ExcelWriter("apple_dashboard_full.xlsx") as writer:
            if 'tree_data' in st.session_state and not st.session_state['tree_data'].empty:
                st.session_state['tree_data'].to_excel(writer, sheet_name="رشد نهال", index=False)
            if 'schedule' in st.session_state and not st.session_state['schedule'].empty:
                st.session_state['schedule'].to_excel(writer, sheet_name="برنامه رشد", index=False)
            if 'df_future' in locals() and not df_future.empty:
                df_future.to_excel(writer, sheet_name="پیش‌بینی رشد", index=False)
        st.success("✅ گزارش آماده شد: apple_dashboard_full.xlsx")
