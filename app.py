import streamlit as st
import tensorflow as tf
from tensorflow.keras.utils import img_to_array
from PIL import Image
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

# 🖌️ تنظیمات صفحه
st.set_page_config(page_title="🍎 داشبورد سلامت و رشد نهال سیب", page_icon="🍎", layout="wide")

# 🎨 CSS سفارشی برای ظاهر زیبا و فونت فارسی
st.markdown("""
<style>
body {
    font-family: 'Vazir', sans-serif;
    direction: rtl;
    background-color: #f0f4f8;
}
.stButton>button {
    background-color: #38a169;
    color: white;
    border-radius: 10px;
    padding: 0.5em 1em;
    font-size: 16px;
}
</style>
""", unsafe_allow_html=True)

# 🔹 بارگذاری مدل
@st.cache_resource
def load_model():
    return tf.keras.models.load_model("leaf_model.h5")

model = load_model()
class_labels = ["apple_healthy", "apple_black_spot", "apple_powdery_mildew"]
disease_info = {
    "apple_black_spot": {"name":"لکه سیاه سیب ⚫️","desc":"لکه‌های سیاه روی برگ و میوه.","treatment":"استفاده از قارچ‌کش، هرس شاخه‌ها و جمع‌آوری برگ‌ها"},
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

# 🟢 منوی دسته‌بندی
menu = ["🏠 خانه", "🍎 تشخیص بیماری برگ", "🌱 ثبت و رصد رشد نهال", "📅 برنامه زمان‌بندی", "📈 پیش‌بینی رشد", "📥 دانلود گزارش"]
choice = st.sidebar.selectbox("منو", menu)

# 🏠 خانه
if choice == "🏠 خانه":
    st.title("🍎 سامانه هوشمند مدیریت سلامت و رشد نهال سیب")
    st.write("به داشبورد سلامت و رشد نهال سیب خوش آمدید. می‌توانید وضعیت برگ‌ها را بررسی، رشد نهال را ثبت و پیش‌بینی رشد آینده را مشاهده کنید.")

# 🍎 تشخیص بیماری برگ
elif choice == "🍎 تشخیص بیماری برگ":
    st.header("🍎 تشخیص بیماری برگ")
    uploaded_file = st.file_uploader("📸 آپلود تصویر برگ سیب", type=["jpg","jpeg","png"])
    if uploaded_file:
        st.image(uploaded_file, caption="📷 تصویر آپلود شده", use_column_width=True)
        probs = predict_probs(uploaded_file)
        label_idx = np.argmax(probs)
        label = class_labels[label_idx]

        st.write("احتمال هر بیماری (٪):")
        for i, c in enumerate(class_labels):
            st.write(f"{disease_info[c]['name']}: {probs[i]*100:.1f}%")

        info = disease_info[label]
        st.success(f"🔎 نتیجه: {info['name']}")
        st.write(f"📖 توضیح: {info['desc']}")
        st.info(f"🛠️ درمان و مراقبت: {info['treatment']}")

# 🌱 ثبت و رصد رشد نهال
elif choice == "🌱 ثبت و رصد رشد نهال":
    st.header("🌱 ثبت و رصد رشد نهال")
    if 'tree_data' not in st.session_state:
        st.session_state['tree_data'] = pd.DataFrame(columns=['تاریخ','ارتفاع(cm)','تعداد برگ','توضیحات','هشدار هرس'])

    with st.expander("➕ ثبت اندازه‌گیری رشد نهال"):
        date = st.date_input("تاریخ اندازه‌گیری", value=datetime.today())
        height = st.number_input("ارتفاع نهال (cm)", min_value=0.0, step=0.5)
        leaves = st.number_input("تعداد برگ‌ها", min_value=0, step=1)
        desc = st.text_area("توضیحات")
        prune_warning = st.checkbox("هشدار هرس لازم است؟")
        if st.button("ثبت اندازه‌گیری رشد"):
            st.session_state['tree_data'] = pd.concat([
                st.session_state['tree_data'],
                pd.DataFrame([[date, height, leaves, desc, prune_warning]], columns=['تاریخ','ارتفاع(cm)','تعداد برگ','توضیحات','هشدار هرس'])
            ], ignore_index=True)
            st.success("✅ ثبت شد")

    if not st.session_state['tree_data'].empty:
        df = st.session_state['tree_data'].sort_values('تاریخ')
        st.write("روند ثبت شده رشد نهال:")
        st.dataframe(df)

# 📅 برنامه زمان‌بندی
elif choice == "📅 برنامه زمان‌بندی":
    st.header("📅 برنامه زمان‌بندی یک ساله فعالیت‌ها")
    if 'schedule' not in st.session_state:
        start_date = datetime.today()
        schedule_list = []
        for week in range(52):
            date = start_date + timedelta(weeks=week)
            schedule_list.append([date.date(), "آبیاری", "آبیاری منظم نهال", False])
            if week % 4 == 0:
                schedule_list.append([date.date(), "کوددهی", "تغذیه با کود متعادل", False])
            if week % 12 == 0:
                schedule_list.append([date.date(), "هرس", "هرس شاخه‌های اضافه یا خشک", False])
            if week % 6 == 0:
                schedule_list.append([date.date(), "بازرسی بیماری", "بررسی علائم بیماری و برگ‌ها", False])
        st.session_state['schedule'] = pd.DataFrame(schedule_list, columns=['تاریخ','فعالیت','توضیحات','انجام شد'])

    df_schedule = st.session_state['schedule']
    today = datetime.today().date()
    st.subheader("⚠️ هشدار فعالیت‌های امروز")
    today_tasks = df_schedule[(df_schedule['تاریخ']==today) & (df_schedule['انجام شد']==False)]
    if not today_tasks.empty:
        for i, row in today_tasks.iterrows():
            st.warning(f"فعالیت امروز: {row['فعالیت']} - {row['توضیحات']}")
    else:
        st.success("امروز همه فعالیت‌ها انجام شده ✅")

    st.subheader("📋 جدول برنامه رشد")
    for i in df_schedule.index:
        df_schedule.at[i,'انجام شد'] = st.checkbox(f"{df_schedule.at[i,'تاریخ']} - {df_schedule.at[i,'فعالیت']}", value=df_schedule.at[i,'انجام شد'], key=i)
    st.dataframe(df_schedule)

# 📈 پیش‌بینی رشد
elif choice == "📈 پیش‌بینی رشد":
    st.header("📈 پیش‌بینی رشد نهال (روش ساده)")
    if not st.session_state['tree_data'].empty:
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

        st.write("پیش‌بینی رشد نهال برای 12 هفته آینده:")
        st.dataframe(df_future)

# 📥 دانلود گزارش
elif choice == "📥 دانلود گزارش":
    st.header("📥 دانلود گزارش کامل")
    if st.button("دانلود Excel داشبورد کامل"):
        with pd.ExcelWriter("apple_dashboard_full.xlsx") as writer:
            if not st.session_state['tree_data'].empty:
                st.session_state['tree_data'].to_excel(writer, sheet_name="رشد نهال", index=False)
            if not st.session_state['schedule'].empty:
                st.session_state['schedule'].to_excel(writer, sheet_name="برنامه رشد", index=False)
            if 'df_future' in locals() and not df_future.empty:
                df_future.to_excel(writer, sheet_name="پیش‌بینی رشد", index=False)
        st.success("✅ گزارش آماده شد: apple_dashboard_full.xlsx")
