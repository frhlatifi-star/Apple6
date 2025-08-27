import streamlit as st
import tensorflow as tf
from tensorflow.keras.utils import img_to_array
from PIL import Image
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import io
import plotly.express as px

# ---------------- صفحه و CSS ----------------
st.set_page_config(
    page_title="🍎 داشبورد حرفه‌ای نهال سیب",
    page_icon="🍎",
    layout="wide"
)
st.markdown("""
<style>
@import url('https://cdn.jsdelivr.net/gh/rastikerdar/vazir-font@v30.1.0/dist/font-face.css');
body {font-family: 'Vazir', sans-serif; direction: rtl; 
      background-image: url('https://images.unsplash.com/photo-1567306226416-28f0efdc88ce?auto=format&fit=crop&w=1470&q=80');
      background-size: cover; background-attachment: fixed;}
h1,h2,h3,h4,h5,h6 {color:#ffffff; text-shadow:2px 2px 6px rgba(0,0,0,0.6);}
.stButton>button {background-color: #38a169; color: white; border-radius: 12px; padding: 0.6em 1.2em; font-size: 16px; box-shadow: 2px 2px 6px rgba(0,0,0,0.3);}
.kpi-card {background:rgba(255,255,255,0.9); border-radius:15px; padding:15px; margin:10px; box-shadow:2px 2px 15px rgba(0,0,0,0.2); transition:0.3s;}
.kpi-card:hover {transform: scale(1.05);}
.card-title {font-weight:bold; font-size:18px; margin-bottom:5px;}
.card-value {font-size:24px; color:#2d3748;}
.progress-bar {height:25px; border-radius:12px; background:#e2e8f0; overflow:hidden;}
.progress-fill {height:100%; text-align:center; color:white; line-height:25px; font-weight:bold; transition: width 1s;}
.logo {text-align:center; margin-bottom:20px;}
</style>
""", unsafe_allow_html=True)

# ---------------- زبان ----------------
lang = st.sidebar.selectbox("🌐 زبان / Language", ["فارسی", "English"])
def t(fa, en):
    return fa if lang=="فارسی" else en

# ---------------- لوگو ----------------
st.markdown(f"<div class='logo'><h1>🍎 {t('داشبورد نهال سیب','Apple Seedling Dashboard')}</h1></div>", unsafe_allow_html=True)

# ---------------- مدل ----------------
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

# ---------------- فرم Login/Signup ----------------
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
if 'users' not in st.session_state:
    st.session_state['users'] = {}

if not st.session_state['logged_in']:
    tab = st.sidebar.radio(t("حالت","Mode"), [t("ورود","Login"), t("ثبت نام","Sign Up"), t("دمو","Demo")])
    
    if tab==t("ثبت نام","Sign Up"):
        st.subheader(t("ثبت نام کاربر جدید","Register New User"))
        username = st.text_input(t("نام کاربری","Username"))
        password = st.text_input(t("رمز عبور","Password"), type="password")
        if st.button(t("ثبت نام","Sign Up")):
            if username in st.session_state['users']:
                st.error(t("نام کاربری موجود است","Username already exists"))
            else:
                st.session_state['users'][username] = password
                st.success(t("ثبت نام با موفقیت انجام شد","Registered successfully"))
    
    elif tab==t("ورود","Login"):
        st.subheader(t("ورود کاربر","User Login"))
        username = st.text_input(t("نام کاربری","Username"))
        password = st.text_input(t("رمز عبور","Password"), type="password")
        if st.button(t("ورود","Login")):
            if username in st.session_state['users'] and st.session_state['users'][username]==password:
                st.session_state['logged_in'] = True
                st.success(t("ورود موفق ✅","Login successful ✅"))
            else:
                st.error(t("نام کاربری یا رمز عبور اشتباه است","Wrong username or password"))
    
    elif tab==t("دمو","Demo"):
        st.subheader(t("دمو - آپلود تصویر نمونه","Demo - Upload Sample Image"))
        uploaded_file = st.file_uploader(t("📸 آپلود تصویر برگ","Upload Leaf Image"), type=["jpg","jpeg","png"])
        if uploaded_file:
            st.image(uploaded_file, caption=t("تصویر آپلود شده","Uploaded Image"), use_column_width=True)
            probs = predict_probs(uploaded_file)
            label_idx = np.argmax(probs)
            label = class_labels[label_idx]
            st.write(t("احتمال بیماری (٪)","Disease probability (%)"))
            for i, c in enumerate(class_labels):
                st.write(f"{disease_info[c]['name']}: {probs[i]*100:.1f}%")
            info = disease_info[label]
            st.success(f"{t('نتیجه','Result')}: {info['name']}")
            st.info(f"{t('توضیح','Description')}: {info['desc']}")
            st.warning(f"{t('درمان','Treatment')}: {info['treatment']}")
else:
    # ---------------- منو اصلی ----------------
    menu = [t("🏠 خانه","🏠 Home"), t("🍎 تشخیص بیماری","🍎 Disease Detection"), t("🌱 ثبت و رصد","🌱 Tracking"),
            t("📅 برنامه زمان‌بندی","📅 Schedule"), t("📈 پیش‌بینی رشد","📈 Growth Prediction"),
            t("📥 دانلود گزارش","📥 Download Report"), t("🚪 خروج","Logout")]
    choice = st.sidebar.selectbox(t("منو","Menu"), menu)
    
    if choice==t("🚪 خروج","Logout"):
        st.session_state['logged_in'] = False
        st.success(t("خروج انجام شد","Logged out successfully"))

    # ----------------🏠 خانه ----------------
    if choice==t("🏠 خانه","🏠 Home"):
        st.subheader(t("خانه","Home"))
        st.markdown("<div class='kpi-card'><div class='card-title'>🌱 رشد نهال</div><div class='card-value'>اطلاعات ثبت شده و پیش‌بینی‌ها</div></div>", unsafe_allow_html=True)
        st.markdown("<div class='kpi-card'><div class='card-title'>🍎 سلامت برگ‌ها</div><div class='card-value'>تشخیص بیماری و آمار سلامت</div></div>", unsafe_allow_html=True)
    
    # ----------------🍎 تشخیص بیماری ----------------
    elif choice==t("🍎 تشخیص بیماری","🍎 Disease Detection"):
        st.header(t("تشخیص بیماری برگ","Leaf Disease Detection"))
        uploaded_file = st.file_uploader(t("📸 آپلود تصویر برگ سیب","Upload Leaf Image"), type=["jpg","jpeg","png"])
        if uploaded_file:
            st.image(uploaded_file, caption=t("تصویر آپلود شده","Uploaded Image"), use_column_width=True)
            probs = predict_probs(uploaded_file)
            label_idx = np.argmax(probs)
            label = class_labels[label_idx]
            st.write(t("احتمال هر بیماری (٪):","Probability (%)"))
            for i, c in enumerate(class_labels):
                st.write(f"{disease_info[c]['name']}: {probs[i]*100:.1f}%")
            info = disease_info[label]
            st.success(f"{t('نتیجه','Result')}: {info['name']}")
            st.info(f"{t('توضیح','Description')}: {info['desc']}")
            st.warning(f"{t('درمان','Treatment')}: {info['treatment']}")
    
    # ----------------🌱 ثبت و رصد ----------------
    elif choice==t("🌱 ثبت و رصد","🌱 Tracking"):
        st.header(t("ثبت و رصد رشد نهال","Record Seedling Growth"))
        if 'tree_data' not in st.session_state:
            st.session_state['tree_data'] = pd.DataFrame(columns=['تاریخ','ارتفاع(cm)','تعداد برگ','توضیحات','هشدار هرس'])
        with st.expander(t("➕ ثبت اندازه‌گیری رشد نهال","Add Measurement")):
            date = st.date_input(t("تاریخ","Date"), value=datetime.today())
            height = st.number_input(t("ارتفاع نهال (cm)","Height (cm)"), min_value=0.0, step=0.5)
            leaves = st.number_input(t("تعداد برگ‌ها","Number of Leaves"), min_value=0, step=1)
            desc = st.text_area(t("توضیحات","Description"))
            prune_warning = st.checkbox(t("هشدار هرس لازم است؟","Prune Needed?"))
            if st.button(t("ثبت اندازه‌گیری","Submit Measurement")):
                st.session_state['tree_data'] = pd.concat([
                    st.session_state['tree_data'],
                    pd.DataFrame([[date, height, leaves, desc, prune_warning]], columns=['تاریخ','ارتفاع(cm)','تعداد برگ','توضیحات','هشدار هرس'])
                ], ignore_index=True)
                st.success(t("✅ ثبت شد","✅ Submitted"))
        if not st.session_state['tree_data'].empty:
            df = st.session_state['tree_data'].sort_values('تاریخ')
            st.write(t("روند ثبت شده رشد نهال:","Recorded Growth Data"))
            st.dataframe(df)
            fig = px.line(df, x='تاریخ', y='ارتفاع(cm)', title=t("نمودار رشد ارتفاع","Height Growth"))
            st.plotly_chart(fig, use_container_width=True)
    
    # ----------------📅 برنامه زمان‌بندی ----------------
    elif choice==t("📅 برنامه زمان‌بندی","📅 Schedule"):
        st.header(t("برنامه زمان‌بندی یک ساله","One Year Schedule"))
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
        st.subheader(t("⚠️ هشدار فعالیت‌های امروز","Today's Tasks"))
        today_tasks = df_schedule[(df_schedule['تاریخ']==today) & (df_schedule['انجام شد']==False)]
        if not today_tasks.empty:
            for i, row in today_tasks.iterrows():
                st.warning(f"{row['فعالیت']} - {row['توضیحات']}")
        else:
            st.success(t("امروز همه فعالیت‌ها انجام شده ✅","All tasks done today ✅"))
        for i in df_schedule.index:
            df_schedule.at[i,'انجام شد'] = st.checkbox(f"{df_schedule.at[i,'تاریخ']} - {df_schedule.at[i,'فعالیت']}", value=df_schedule.at[i,'انجام شد'], key=i)
        st.dataframe(df_schedule)
    
    # ----------------📈 پیش‌بینی رشد ----------------
    elif choice==t("📈 پیش‌بینی رشد","📈 Growth Prediction"):
        st.header(t("پیش‌بینی رشد نهال","Seedling Growth Prediction"))
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
            st.dataframe(df_future)
            fig = px.line(df_future, x='تاریخ', y='ارتفاع پیش‌بینی شده(cm)', title=t("پیش‌بینی ارتفاع","Height Prediction"))
            st.plotly_chart(fig, use_container_width=True)
    
    # ----------------📥 دانلود گزارش ----------------
    elif choice==t("📥 دانلود گزارش","📥 Download Report"):
        st.header(t("دانلود گزارش کامل","Download Full Report"))
        if st.button(t("دانلود Excel داشبورد کامل","Download Full Dashboard Excel")):
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                if 'tree_data' in st.session_state and not st.session_state['tree_data'].empty:
                    st.session_state['tree_data'].to_excel(writer, sheet_name="رشد نهال", index=False)
                if 'schedule' in st.session_state and not st.session_state['schedule'].empty:
                    st.session_state['schedule'].to_excel(writer, sheet_name="برنامه رشد", index=False)
                if 'df_future' in locals() and not df_future.empty:
                    df_future.to_excel(writer, sheet_name="پیش‌بینی رشد", index=False)
                writer.save()
                st.download_button(t("📥 دانلود فایل Excel","Download Excel File"), data=buffer, file_name="apple_dashboard_full.xlsx")
