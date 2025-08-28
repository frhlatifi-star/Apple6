import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import bcrypt
import sqlalchemy as sa
from sqlalchemy import Column, Integer, String, Table, MetaData, ForeignKey
import altair as alt

# ---------- Config ----------
st.set_page_config(page_title="🍎 Seedling Pro", page_icon="🍎", layout="wide")

# ---------- Custom CSS for UI ----------
st.markdown("""
<style>
body {
    background: linear-gradient(to right, #e0f7fa, #ffffff);
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
}
.rtl {
    direction: rtl;
    text-align: right;
}
.ltr {
    direction: ltr;
    text-align: left;
}
.section-card {
    background-color: #ffffff;
    border-radius: 15px;
    padding: 20px;
    box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    margin-bottom: 20px;
}
h1, h2, h3 {
    color: #00796b;
}
</style>
""", unsafe_allow_html=True)

# ---------- Database ----------
DB_FILE = "users_data.db"
engine = sa.create_engine(f"sqlite:///{DB_FILE}", connect_args={"check_same_thread": False})
meta = MetaData()

users_table = Table('users', meta,
                    Column('id', Integer, primary_key=True),
                    Column('username', String, unique=True, nullable=False),
                    Column('password_hash', String, nullable=False))

measurements = Table('measurements', meta,
                     Column('id', Integer, primary_key=True),
                     Column('user_id', Integer, ForeignKey('users.id')),
                     Column('date', String),
                     Column('height', Integer),
                     Column('leaves', Integer),
                     Column('notes', String),
                     Column('prune_needed', Integer))

meta.create_all(engine)
conn = engine.connect()

# ---------- Session ----------
if 'user_id' not in st.session_state: st.session_state['user_id'] = None
if 'username' not in st.session_state: st.session_state['username'] = None
if 'lang' not in st.session_state: st.session_state['lang'] = 'فارسی'
if 'demo_data' not in st.session_state: st.session_state['demo_data'] = []

# ---------- Language ----------
def t(fa, en):
    return en if st.session_state['lang'] == 'English' else fa

lang = st.sidebar.selectbox("Language / زبان", ["فارسی", "English"], index=0 if st.session_state.get('lang','فارسی')=='فارسی' else 1)
if st.session_state.get('lang','فارسی') != lang:
    st.session_state['lang'] = lang
    st.experimental_rerun()

text_class = 'rtl' if st.session_state['lang'] == 'فارسی' else 'ltr'

# ---------- Password helpers ----------
def hash_password(password):
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def check_password(password, hashed):
    return bcrypt.checkpw(password.encode(), hashed.encode())

# ---------- Auth ----------
if st.session_state['user_id'] is None:
    st.sidebar.header(t("احراز هویت", "Authentication"))
    mode = st.sidebar.radio(t("حالت", "Mode"), [t("ورود", "Login"), t("ثبت‌نام", "Sign Up"), t("دمو", "Demo")])

    if mode == t("ثبت‌نام", "Sign Up"):
        st.header(t("ثبت‌نام", "Sign Up"))
        username = st.text_input(t("نام کاربری", "Username"))
        password = st.text_input(t("رمز عبور", "Password"), type="password")
        if st.button(t("ثبت", "Register")):
            if not username or not password:
                st.error(t("نام کاربری و رمز عبور را وارد کنید.", "Provide username & password."))
            else:
                sel = sa.select(users_table).where(users_table.c.username==username)
                r = conn.execute(sel).mappings().first()
                if r:
                    st.error(t("نام کاربری وجود دارد.", "Username already exists."))
                else:
                    hashed = hash_password(password)
                    conn.execute(users_table.insert().values(username=username, password_hash=hashed))
                    st.success(t("ثبت شد. لطفا وارد شوید.", "Registered. Please login."))

    elif mode == t("ورود", "Login"):
        st.header(t("ورود", "Login"))
        username = st.text_input(t("نام کاربری", "Username"))
        password = st.text_input(t("رمز عبور", "Password"), type="password")
        if st.button(t("ورود", "Login")):
            sel = sa.select(users_table).where(users_table.c.username==username)
            r = conn.execute(sel).mappings().first()
            if not r:
                st.error(t("نام کاربری یافت نشد.", "Username not found."))
            elif check_password(password, r['password_hash']):
                st.session_state['user_id'] = r['id']
                st.session_state['username'] = r['username']
                st.experimental_rerun()
            else:
                st.error(t("رمز عبور اشتباه است.", "Wrong password."))

    else:
        st.header(t("حالت دمو", "Demo Mode"))
        st.info(t("در حالت دمو داده ذخیره نمی‌شود.", "In demo mode, data is not saved."))
        f = st.file_uploader(t("آپلود تصویر برگ/میوه/ساقه", "Upload leaf/fruit/stem image"), type=["jpg","jpeg","png"])
        if f:
            st.image(f, use_container_width=True)
            st.success(t("پیش‌بینی دمو: سالم", "Demo prediction: Healthy"))
            st.write(t("یادداشت: این نتیجه آزمایشی است.", "Notes: This is a demo result."))
            st.session_state['demo_data'].append({'file': f.name, 'result': 'Healthy', 'time': datetime.now()})
            if st.session_state['demo_data']:
                st.subheader(t("تاریخچه دمو", "Demo History"))
                df_demo = pd.DataFrame(st.session_state['demo_data'])
                st.dataframe(df_demo)

else:
    st.sidebar.header(f"{t('خوش آمدید', 'Welcome')}, {st.session_state['username']}")
    menu = st.sidebar.selectbox(t("منو", "Menu"), [t("🏠 خانه", "🏠 Home"), t("🌱 پایش", "🌱 Tracking"), t("📅 زمان‌بندی", "📅 Schedule"), t("📈 پیش‌بینی", "📈 Prediction"), t("🍎 بیماری", "🍎 Disease"), t("📥 دانلود", "📥 Download"), t("🚪 خروج", "🚪 Logout")])

    user_id = st.session_state['user_id']

    if menu == t("🚪 خروج", "🚪 Logout"):
        st.session_state['user_id'] = None
        st.session_state['username'] = None
        st.experimental_rerun()

    # ---------- Home ----------
    elif menu == t("🏠 خانه", "🏠 Home"):
        st.markdown(f'<div class="section-card {text_class}">', unsafe_allow_html=True)
        st.header(t("داشبورد", "Dashboard"))
        sel = sa.select(measurements).where(measurements.c.user_id==user_id).order_by(measurements.c.date.asc())
        df = pd.DataFrame(conn.execute(sel).mappings().all())
        if not df.empty:
            st.metric(t("تعداد اندازه‌گیری‌ها", "Measurements"), len(df))
            st.metric(t("میانگین ارتفاع", "Avg Height"), round(df['height'].mean(),1))
            chart = alt.Chart(df).mark_line(point=True).encode(
                x='date:T',
                y='height:Q',
                tooltip=['date','height']
            ).properties(width=700, height=300)
            st.altair_chart(chart, use_container_width=True)
        else:
            st.info(t("هیچ داده‌ای ثبت نشده است.", "No data yet."))
        st.markdown('</div>', unsafe_allow_html=True)

    # ---------- Tracking ----------
    elif menu == t("🌱 پایش", "🌱 Tracking"):
        st.markdown(f'<div class="section-card {text_class}">', unsafe_allow_html=True)
        st.header(t("پایش نهال", "Seedling Tracking"))
        with st.expander(t("➕ افزودن اندازه‌گیری", "➕ Add Measurement")):
            date = st.date_input(t("تاریخ", "Date"), value=datetime.today())
            height = st.number_input(t("ارتفاع (سانتی‌متر)", "Height (cm)"), min_value=0, step=1)
            leaves = st.number_input(t("تعداد برگ", "Leaves"), min_value=0, step=1)
            notes = st.text_area(t("یادداشت", "Notes"), placeholder=t("وضعیت آبیاری، کوددهی، علائم...", "Irrigation status, fertilization, symptoms..."))
            prune = st.checkbox(t("نیاز به هرس؟", "Prune needed?"))
            if st.button(t("ثبت", "Submit")):
                conn.execute(measurements.insert().values(user_id=user_id, date=str(date), height=height, leaves=leaves, notes=notes, prune_needed=int(prune)))
                st.success(t("اندازه‌گیری ذخیره شد.", "Measurement saved."))
        df = pd.DataFrame(conn.execute(sa.select(measurements).where(measurements.c.user_id==user_id).order_by(measurements.c.date.desc())).mappings().all())
        if not df.empty:
            st.dataframe(df)
        st.markdown('</div>', unsafe_allow_html=True)

    # ---------- Schedule ----------
    elif menu == t("📅 زمان‌بندی", "📅 Schedule"):
        st.markdown(f'<div class="section-card {text_class}">', unsafe_allow_html=True)
        st.header(t("زمان‌بندی فعالیت‌ها", "Activity Schedule"))
        schedule_df = pd.DataFrame({
            t("تاریخ", "Date"): [(datetime.today() + timedelta(days=i)).strftime('%Y-%m-%d') for i in range(5)],
            t("کار", "Task"): ["آبیاری", "کوددهی", "بررسی بیماری", "هرس", "بازرسی رشد"]
        })
        st.table(schedule_df)
        st.markdown('</div>', unsafe_allow_html=True)

    # ---------- Prediction ----------
    elif menu == t("📈 پیش‌بینی", "📈 Prediction"):
        st.markdown(f'<div class="section-card {text_class}">', unsafe_allow_html=True)
        st.header(t("پیش‌بینی رشد", "Growth Prediction"))
        df_pred = pd.DataFrame(conn.execute(sa.select(measurements).where(measurements.c.user_id==user_id).order_by(measurements.c.date.asc())).mappings().all())
        if not df_pred.empty:
            df_pred['pred_height'] = df_pred['height'] * 1.05
            chart_pred = alt.Chart(df_pred).mark_line(color='orange', point=True).encode(
                x='date:T', y='pred_height:Q', tooltip=['date','pred_height']
            ).properties(width=700, height=300)
            st.altair_chart(chart_pred, use_container_width=True)
        else:
            st.info(t("هیچ داده‌ای برای پیش‌بینی موجود نیست.", "No data for prediction."))
        st.markdown('</div>', unsafe_allow_html=True)

    # ---------- Disease ----------
    elif menu == t("🍎 بیماری", "🍎 Disease"):
        st.markdown(f'<div class="section-card {text_class}">', unsafe_allow_html=True)
        st.header(t("وضعیت بیماری‌ها", "Disease Status"))
        st.info(t("در این بخش می‌توانید وضعیت سلامت نهال‌ها را بررسی کنید.", "Check your seedlings health status here."))
        st.markdown('</div>', unsafe_allow_html=True)

    # ---------- Download ----------
    elif menu == t("📥 دانلود", "📥 Download"):
        st.markdown(f'<div class="section-card {text_class}">', unsafe_allow_html=True)
        st.header(t("دانلود داده‌ها", "Download Data"))
        df_dl = pd.DataFrame(conn.execute(sa.select(measurements).where(measurements.c.user_id==user_id)).mappings().all())
        if not df_dl.empty:
            csv = df_dl.to_csv(index=False).encode('utf-8')
            st.download_button(label=t("دانلود CSV", "Download CSV"), data=csv, file_name='measurements.csv', mime='text/csv')
        else:
            st.info(t("هیچ داده‌ای برای دانلود موجود نیست.", "No data to download."))
        st.markdown('</div>', unsafe_allow_html=True)
