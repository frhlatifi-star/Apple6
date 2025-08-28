# app.py
import streamlit as st
import pandas as pd
from datetime import datetime
import bcrypt
import sqlalchemy as sa
from sqlalchemy import Column, Integer, String, Table, MetaData, ForeignKey
from PIL import Image, ImageStat
import numpy as np
import io
import os

# Optional ML imports (only used if model file exists)
try:
    import tensorflow as tf
    from tensorflow.keras.preprocessing import image as kimage
    TF_AVAILABLE = True
except Exception:
    TF_AVAILABLE = False

# ---------- Config ----------
st.set_page_config(page_title="سیبتک 🍎 مدیریت نهال", page_icon="🍎", layout="wide")

# RTL style for Persian
st.markdown(
    """
    <style>
    html, body, [class*="css"]  {
        direction: rtl !important;
        text-align: right !important;
    }
    .stButton>button { cursor: pointer; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------- Database (SQLite via SQLAlchemy) ----------
DB_FILE = "users_data.db"
engine = sa.create_engine(f"sqlite:///{DB_FILE}", connect_args={"check_same_thread": False})
meta = MetaData()

# Users table
users_table = Table(
    'users', meta,
    Column('id', Integer, primary_key=True),
    Column('username', String, unique=True, nullable=False),
    Column('password_hash', String, nullable=False)
)

# Measurements table (پایش)
measurements = Table(
    'measurements', meta,
    Column('id', Integer, primary_key=True),
    Column('user_id', Integer, ForeignKey('users.id')),
    Column('date', String),
    Column('height', Integer),
    Column('leaves', Integer),
    Column('notes', String),
    Column('prune_needed', Integer)
)

# Schedule table (برنامه‌ها)
schedule_table = Table(
    'schedule', meta,
    Column('id', Integer, primary_key=True),
    Column('user_id', Integer, ForeignKey('users.id')),
    Column('task', String),
    Column('date', String),
    Column('notes', String)
)

# Prediction history (پیش‌بینی‌ها)
predictions_table = Table(
    'predictions', meta,
    Column('id', Integer, primary_key=True),
    Column('user_id', Integer, ForeignKey('users.id')),
    Column('file_name', String),
    Column('result', String),
    Column('confidence', String),
    Column('date', String)
)

# Disease notes table
disease_table = Table(
    'disease', meta,
    Column('id', Integer, primary_key=True),
    Column('user_id', Integer, ForeignKey('users.id')),
    Column('note', String),
    Column('date', String)
)

meta.create_all(engine)

# ---------- Session defaults ----------
if 'user_id' not in st.session_state:
    st.session_state['user_id'] = None
if 'username' not in st.session_state:
    st.session_state['username'] = None
if 'demo_history' not in st.session_state:
    st.session_state['demo_history'] = []

# ---------- Helpers ----------
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def check_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())

# Try to load model if exists
MODEL_PATH = "model/seedling_model.h5"
_model = None
_model_loaded = False
if TF_AVAILABLE and os.path.exists(MODEL_PATH):
    try:
        @st.cache_resource
        def _load_model(path):
            return tf.keras.models.load_model(path)
        _model = _load_model(MODEL_PATH)
        _model_loaded = True
    except Exception as e:
        st.warning(f"بارگذاری مدل با خطا مواجه شد: {e}")
        _model_loaded = False

# If model not loaded, we'll use a heuristic "پیش‌بینی پیشرفته شبیه‌سازی‌شده"
def heuristic_predict_potted_seedling(pil_img: Image.Image):
    """
    پیش‌بینی نمونه بر اساس ویژگی‌های ساده تصویر:
    - روشنایی متوسط خیلی کم => ممکنه کم‌آبی / ضعف نور
    - نسبت رنگ زرد/قهوه‌ای => ممکنه بیماری یا خشکیدگی
    - برگ‌های زیاد و سبز => سالم
    این تابع خروجی (label, confidence) برمی‌گرداند.
    """
    img = pil_img.convert("RGB").resize((224,224))
    stat = ImageStat.Stat(img)
    mean = np.mean(stat.mean)  # میانگین روشنایی کانال‌ها
    # درصد زردish: نسبت به کانال‌ها (R > G > B) علامت زردی
    arr = np.array(img).astype(int)
    r, g, b = arr[:,:,0], arr[:,:,1], arr[:,:,2]
    yellow_mask = ((r > g) & (g >= b)).astype(int)
    yellow_ratio = yellow_mask.mean()
    # greenness: G significantly larger than R and B
    green_mask = ((g > r+10) & (g > b+10)).astype(int)
    green_ratio = green_mask.mean()

    # simple rules
    if green_ratio > 0.12 and mean > 80:
        return "سالم", f"{min(99,int(50 + green_ratio*200))}%"
    if yellow_ratio > 0.12 or mean < 60:
        if yellow_ratio > 0.25:
            return "بیمار یا آفت‌زده", f"{min(95,int(40 + yellow_ratio*200))}%"
        else:
            return "نیاز به بررسی (کم‌آبی/کود)", f"{min(90,int(30 + (0.2 - mean/255)*200))}%"
    # default uncertain
    return "نامشخص — نیاز به تصاویر بیشتر", "50%"

def predict_with_model(pil_img: Image.Image):
    # assumes _model exists and expects 224x224 normalized inputs
    img = pil_img.convert("RGB").resize((224,224))
    x = np.array(img)/255.0
    x = np.expand_dims(x, 0)
    preds = _model.predict(x)
    # if model outputs probabilities for classes, adapt below:
    # try to map to classes; we'll assume model has these outputs:
    classes = ["سالم", "بیمار", "نیاز به هرس", "کم‌آبی"]
    idx = int(np.argmax(preds[0]))
    confidence = float(np.max(preds[0])) if preds is not None else 0.0
    return classes[idx] if idx < len(classes) else "نامشخص", f"{int(confidence*100)}%"

# ---------- UI: Header ----------
def app_header():
    st.markdown(
        """
        <div style='display:flex; align-items:center; justify-content:flex-start; direction:rtl;'>
            <img src='https://i.imgur.com/4Y2E2XQ.png' width='64' style='margin-left:12px;border-radius:8px;'/>
            <div>
                <h2 style='margin:0;'>سیبتک</h2>
                <div style='color: #666;'>سیبتک — مدیریت و پایش نهال</div>
            </div>
        </div>
        <hr/>
        """,
        unsafe_allow_html=True
    )

app_header()

# ---------- Auth screens ----------
if st.session_state['user_id'] is None:
    st.write("")  # spacer
    col1, col2 = st.columns([1,2])
    with col1:
        mode = st.radio("حالت:", ["ورود", "ثبت‌نام", "دمو"])
    with col2:
        st.write("")  # keep layout

    if mode == "ثبت‌نام":
        st.subheader("ثبت‌نام کاربر جدید")
        username = st.text_input("نام کاربری", key="signup_username")
        password = st.text_input("رمز عبور", type="password", key="signup_password")
        if st.button("ثبت‌نام"):
            if not username or not password:
                st.error("نام کاربری و رمز عبور را وارد کنید.")
            else:
                try:
                    with engine.connect() as conn:
                        sel = sa.select(users_table).where(users_table.c.username == username)
                        r = conn.execute(sel).mappings().first()
                        if r:
                            st.error("این نام کاربری قبلاً ثبت شده است.")
                        else:
                            hashed = hash_password(password)
                            conn.execute(users_table.insert().values(username=username, password_hash=hashed))
                            st.success("ثبت‌نام انجام شد. اکنون وارد شوید.")
                except Exception as e:
                    st.error(f"خطا در ثبت‌نام: {e}")

    elif mode == "ورود":
        st.subheader("ورود به حساب کاربری")
        username = st.text_input("نام کاربری", key="login_username")
        password = st.text_input("رمز عبور", type="password", key="login_password")
        if st.button("ورود"):
            try:
                with engine.connect() as conn:
                    sel = sa.select(users_table).where(users_table.c.username == username)
                    r = conn.execute(sel).mappings().first()
                    if not r:
                        st.error("نام کاربری یافت نشد.")
                    elif check_password(password, r['password_hash']):
                        st.session_state['user_id'] = int(r['id'])
                        st.session_state['username'] = r['username']
                        st.success(f"خوش آمدید، {r['username']} — منو در سمت چپ فعال می‌شود.")
                        st.experimental_rerun = lambda: None  # compatibility guard (no-op)
                    else:
                        st.error("رمز عبور اشتباه است.")
            except Exception as e:
                st.error(f"خطا در ورود: {e}")

    else:  # Demo
        st.subheader("حالت دمو — پیش‌بینی نمونه")
        st.info("در حالت دمو داده‌ها در سرور ذخیره نمی‌شوند. این بخش برای تست و نمایش عملکرد است.")
        f = st.file_uploader("یک تصویر از نهال یا بخشی از آن آپلود کنید", type=["jpg","jpeg","png"])
        if f:
            img = Image.open(f)
            st.image(img, use_container_width=True)
            # use model if available else heuristic
            if _model_loaded:
                label, conf = predict_with_model(img)
            else:
                label, conf = heuristic_predict_potted_seedling(img)
            st.success(f"نتیجه (دمو): {label} — اعتماد: {conf}")
            st.write("توصیه اولیه:")
            if label == "سالم":
                st.write("- نگهداری آبیاری و کوددهی منظم.")
            elif "کم‌آبی" in label or "آبی" in label:
                st.write("- بررسی برنامه آبدهی؛ آبیاری منظم.")
            elif "بیمار" in label:
                st.write("- نمونه‌برداری از برگ/شاخه و بررسی آفات/قارچ.")
            else:
                st.write("- بررسی دقیق‌تر با تصاویر بیشتر.")
            # add to demo history (session only)
            st.session_state['demo_history'].append({'file': getattr(f, "name", "uploaded"), 'result': label, 'time': datetime.now().strftime("%Y-%m-%d %H:%M:%S")})
            if st.session_state['demo_history']:
                st.subheader("تاریخچه دمو (فعلی)")
                st.dataframe(pd.DataFrame(st.session_state['demo_history']))

# ---------- Main app (after login) ----------
else:
    # Sidebar menu
    st.sidebar.header(f"خوش آمدید، {st.session_state['username']}")
    menu = st.sidebar.selectbox("منو", [
        "🏠 خانه",
        "🌱 پایش نهال",
        "📅 زمان‌بندی",
        "📈 پیش‌بینی سلامت نهال (تصویر)",
        "🍎 ثبت بیماری / یادداشت",
        "📥 دانلود داده‌ها",
        "🚪 خروج"
    ])
    user_id = st.session_state['user_id']

    if menu == "🚪 خروج":
        st.session_state['user_id'] = None
        st.session_state['username'] = None
        st.success("شما از حساب کاربری خارج شدید.")
        st.experimental_rerun = lambda: None

    # --- Home ---
    if menu == "🏠 خانه":
        st.header("خانه")
        st.write("خلاصه وضعیت و دسترسی سریع:")
        # quick stats
        try:
            with engine.connect() as conn:
                m_sel = sa.select(measurements).where(measurements.c.user_id == user_id)
                ms = conn.execute(m_sel).mappings().all()
                p_sel = sa.select(predictions_table).where(predictions_table.c.user_id == user_id)
                ps = conn.execute(p_sel).mappings().all()
                st.metric("تعداد اندازه‌گیری‌ها", len(ms))
                st.metric("تعداد پیش‌بینی‌ها", len(ps))
        except Exception:
            pass

    # --- Tracking / Measurements ---
    elif menu == "🌱 پایش نهال":
        st.header("پایش نهال — ثبت رشد و یادداشت")
        with st.expander("➕ افزودن اندازه‌گیری جدید"):
            date = st.date_input("تاریخ", value=datetime.today())
            height = st.number_input("ارتفاع (سانتی‌متر)", min_value=0, step=1)
            leaves = st.number_input("تعداد برگ", min_value=0, step=1)
            notes = st.text_area("یادداشت (مثلاً: آبیاری، کوددهی، علائم)")
            prune = st.checkbox("نیاز به هرس؟")
            if st.button("ثبت اندازه‌گیری"):
                try:
                    with engine.connect() as conn:
                        conn.execute(measurements.insert().values(
                            user_id=user_id,
                            date=str(date),
                            height=int(height),
                            leaves=int(leaves),
                            notes=notes,
                            prune_needed=int(prune)
                        ))
                        st.success("اندازه‌گیری ثبت شد.")
                except Exception as e:
                    st.error(f"خطا در ثبت اندازه‌گیری: {e}")

        # نمایش تاریخچه پایش
        try:
            with engine.connect() as conn:
                sel = sa.select(measurements).where(measurements.c.user_id == user_id).order_by(measurements.c.date.desc())
                rows = conn.execute(sel).mappings().all()
                if rows:
                    df = pd.DataFrame(rows)
                    st.subheader("تاریخچه اندازه‌گیری‌ها")
                    st.dataframe(df)
                    # نمایش دو نمودار ساده (ارتفاع و تعداد برگ) اگر داده‌ها عددی باشند
                    if 'height' in df.columns and not df['height'].isnull().all():
                        df_plot = df.copy()
                        try:
                            df_plot['date'] = pd.to_datetime(df_plot['date'])
                        except Exception:
                            pass
                        st.line_chart(df_plot.set_index('date')['height'])
                        st.line_chart(df_plot.set_index('date')['leaves'])
                else:
                    st.info("هیچ اندازه‌گیری‌ای ثبت نشده است.")
        except Exception as e:
            st.error(f"خطا در بارگذاری پایش: {e}")

    # --- Schedule ---
    elif menu == "📅 زمان‌بندی":
        st.header("زمان‌بندی فعالیت‌ها")
        with st.expander("➕ افزودن برنامه"):
            task = st.text_input("فعالیت")
            task_date = st.date_input("تاریخ برنامه")
            task_notes = st.text_area("یادداشت")
            if st.button("ثبت برنامه"):
                try:
                    with engine.connect() as conn:
                        conn.execute(schedule_table.insert().values(
                            user_id=user_id,
                            task=task,
                            date=str(task_date),
                            notes=task_notes
                        ))
                        st.success("برنامه ثبت شد.")
                except Exception as e:
                    st.error(f"خطا در ثبت برنامه: {e}")

        try:
            with engine.connect() as conn:
                sel = sa.select(schedule_table).where(schedule_table.c.user_id == user_id).order_by(schedule_table.c.date.desc())
                rows = conn.execute(sel).mappings().all()
                if rows:
                    df = pd.DataFrame(rows)
                    st.subheader("برنامه‌های ثبت‌شده")
                    st.dataframe(df)
                else:
                    st.info("هیچ برنامه‌ای ثبت نشده است.")
        except Exception as e:
            st.error(f"خطا در بارگذاری برنامه‌ها: {e}")

    # --- Prediction (advanced, whole-seedling) ---
    elif menu == "📈 پیش‌بینی سلامت نهال (تصویر)":
        st.header("پیش‌بینی سلامت کل نهال (آپلود تصویر کامل نهال)")
        st.write("آپلود یک تصویر از کل نهال (زاویه‌ای که ساقه، شاخه‌ها و نمای کلی دیده شود) برای پیش‌بینی وضعیت کلی.")
        uploaded = st.file_uploader("انتخاب تصویر نهال", type=["jpg","jpeg","png"])
        if uploaded is not None:
            try:
                pil_img = Image.open(uploaded)
                st.image(pil_img, use_container_width=True)
                st.write("در حال تحلیل تصویر...")
                # if model loaded use it, otherwise use heuristic
                if _model_loaded:
                    label, conf = predict_with_model(pil_img)
                else:
                    label, conf = heuristic_predict_potted_seedling(pil_img)
                st.success(f"نتیجه پیش‌بینی: {label} — اعتماد: {conf}")

                # basic recommendations
                st.subheader("توصیه‌های اولیه")
                if "سالم" in label:
                    st.write("- نگهداری برنامه آبیاری و کوددهی فعلی.")
                elif "کم‌آبی" in label or "آبی" in label:
                    st.write("- افزایش بازه آبیاری و بررسی رطوبت خاک.")
                elif "بیمار" in label or "آفت" in label:
                    st.write("- بررسی نزدیک‌تر برگ‌ها و شاخه‌ها، استفاده از راهنمای مقابله با آفات.")
                else:
                    st.write("- بررسی‌های تکمیلی و ثبت چند تصویر از زوایای مختلف.")

                # Save prediction into DB
                try:
                    with engine.connect() as conn:
                        conn.execute(predictions_table.insert().values(
                            user_id=user_id,
                            file_name=getattr(uploaded, "name", f"img_{datetime.now().timestamp()}"),
                            result=label,
                            confidence=conf,
                            date=str(datetime.now())
                        ))
                        st.info("پیش‌بینی در تاریخچه ذخیره شد.")
                except Exception as e:
                    st.error(f"خطا در ذخیره پیش‌بینی: {e}")

                # show history counts if any
                try:
                    with engine.connect() as conn:
                        sel = sa.select(predictions_table).where(predictions_table.c.user_id == user_id).order_by(predictions_table.c.date.desc())
                        rows = conn.execute(sel).mappings().all()
                        if rows:
                            df_hist = pd.DataFrame(rows)
                            st.subheader("تاریخچه پیش‌بینی‌ها")
                            st.dataframe(df_hist)
                except Exception:
                    pass

            except Exception as e:
                st.error(f"خطا در پردازش تصویر: {e}")

    # --- Disease notes ---
    elif menu == "🍎 ثبت بیماری / یادداشت":
        st.header("ثبت بیماری یا یادداشت‌های مشکل")
        note = st.text_area("شرح مشکل یا علائم مشاهده شده")
        if st.button("ثبت یادداشت"):
            try:
                with engine.connect() as conn:
                    conn.execute(disease_table.insert().values(
                        user_id=user_id,
                        note=note,
                        date=str(datetime.now())
                    ))
                    st.success("یادداشت ثبت شد.")
            except Exception as e:
                st.error(f"خطا در ثبت یادداشت: {e}")
        # show disease notes
        try:
            with engine.connect() as conn:
                sel = sa.select(disease_table).where(disease_table.c.user_id == user_id).order_by(disease_table.c.date.desc())
                rows = conn.execute(sel).mappings().all()
                if rows:
                    st.subheader("یادداشت‌های ثبت‌شده")
                    st.dataframe(pd.DataFrame(rows))
        except Exception as e:
            st.error(f"خطا در بارگذاری یادداشت‌ها: {e}")

    # --- Download data ---
    elif menu == "📥 دانلود داده‌ها":
        st.header("دانلود داده‌ها (CSV)")
        try:
            with engine.connect() as conn:
                sel = sa.select(measurements).where(measurements.c.user_id == user_id)
                rows = conn.execute(sel).mappings().all()
                if rows:
                    df = pd.DataFrame(rows)
                    csv = df.to_csv(index=False).encode('utf-8-sig')
                    st.download_button("دانلود اندازه‌گیری‌ها (CSV)", csv, "measurements.csv", "text/csv")
                else:
                    st.info("داده‌ای برای دانلود وجود ندارد.")
        except Exception as e:
            st.error(f"خطا در آماده‌سازی داده‌ها برای دانلود: {e}")
