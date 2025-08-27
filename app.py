import streamlit as st
import tensorflow as tf
from tensorflow.keras.utils import img_to_array
from PIL import Image
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import io

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

    # ---------------- بخش‌های اصلی ----------------
    # ✅ می‌توانید بخش‌های خانه، تشخیص بیماری، ثبت و رصد، زمان‌بندی، پیش‌بینی، دانلود گزارش را با همان استایل کارت‌ها ادامه دهید
