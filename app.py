# app_seedling_pro_final_auto.py
import streamlit as st
import pandas as pd
import numpy as np
from PIL import Image
from datetime import datetime, timedelta
import io
import plotly.express as px
import os

# --- Optional: Jalali dates ---
try:
    import jdatetime
    HAS_JDATETIME = True
except Exception:
    HAS_JDATETIME = False

# --- Optional: TensorFlow model (for disease). App still works without it ---
try:
    import tensorflow as tf
    from tensorflow.keras.utils import img_to_array
except Exception:
    tf = None
    img_to_array = None

# ==========================
# Config & Styles
# ==========================
st.set_page_config(page_title="داشبورد نهال سیب 🍎", layout="wide", page_icon="🍎")

# Background + RTL + font
st.markdown(
    """
    <style>
      @import url('https://cdn.jsdelivr.net/gh/rastikerdar/vazir-font@v30.1.0/dist/font-face.css');
      html, body, [class*="css"] { font-family: Vazir, sans-serif; direction: rtl; }
      body{ 
        background-image: linear-gradient(180deg, rgba(230,242,234,0.9) 0%, rgba(217,238,240,0.9) 40%, rgba(207,238,240,0.9) 100%),
                          url('https://images.unsplash.com/photo-1501004318641-b39e6451bec6?auto=format&fit=crop&w=1600&q=80');
        background-size: cover; background-attachment: fixed; color:#0f172a;
      }
      .kpi{background:rgba(255,255,255,0.95); border-radius:14px; padding:14px; box-shadow:0 8px 24px rgba(7,10,25,0.08); margin-bottom:10px}
      .card{background:linear-gradient(180deg, rgba(255,255,255,0.9), rgba(255,255,255,0.82)); border-radius:16px; padding:16px; box-shadow:0 12px 32px rgba(7,10,25,0.08)}
      .logo-row{display:flex; align-items:center; gap:10px}
      .alert-red{background:#fee2e2; border:1px solid #fecaca; padding:10px; border-radius:10px}
      .alert-amber{background:#fff7ed; border:1px solid #ffedd5; padding:10px; border-radius:10px}
      .alert-green{background:#ecfdf5; border:1px solid #d1fae5; padding:10px; border-radius:10px}
    </style>
    """,
    unsafe_allow_html=True,
)

# ==========================
# Language helper
# ==========================
if 'lang' not in st.session_state:
    st.session_state['lang'] = 'FA'
lang_choice = st.sidebar.selectbox("زبان / Language", ['فارسی','English'])
st.session_state['lang'] = 'EN' if lang_choice=='English' else 'FA'

def t(fa, en):
    return en if st.session_state['lang'] == 'EN' else fa

# ==========================
# Logo
# ==========================
logo_path = "logo.svg"
if os.path.exists(logo_path):
    with open(logo_path, 'r', encoding='utf-8') as f:
        svg = f.read()
    st.markdown(f"<div class='logo-row'>{svg}</div>", unsafe_allow_html=True)
else:
    st.markdown(f"<h1>🍎 {t('داشبورد نهال سیب','Apple Seedling Dashboard')}</h1>")

# ==========================
# Data stores (session)
# ==========================
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
if 'df_future' not in st.session_state:
    st.session_state['df_future'] = pd.DataFrame()
if 'last_watering' not in st.session_state:
    st.session_state['last_watering'] = None
if 'last_fertilize' not in st.session_state:
    st.session_state['last_fertilize'] = None
if 'last_disease' not in st.session_state:
    st.session_state['last_disease'] = {'label': 'apple_healthy', 'prob': 1.0}

# ==========================
# Disease model (optional)
# ==========================
@st.cache_resource
def load_model(path="leaf_model.h5"):
    if tf is None:
        return None
    try:
        return tf.keras.models.load_model(path)
    except Exception:
        return None

model = load_model()
class_labels = ["apple_healthy", "apple_black_spot", "apple_powdery_mildew", "apple_rust"]

disease_info = {
    "apple_black_spot": {
        "name": t("لکه سیاه ⚫️","Apple Scab ⚫️"),
        "desc": t("ایجاد لکه‌های سیاه و زیتونی روی برگ/میوه، باعث ریزش برگ.","Olive‑black spots on leaves/fruit; can cause defoliation."),
        "treatment": t("جمع‌آوری برگ‌های ریخته، قارچ‌کش‌های توصیه‌شده (مانکوزب/کاپتان)، هرس برای تهویه.",
                        "Remove fallen leaves, use recommended fungicides (e.g., mancozeb/captan), prune to improve airflow."),
    },
    "apple_powdery_mildew": {
        "name": t("سفیدک پودری ❄️","Powdery Mildew ❄️"),
        "desc": t("روکش سفید پودری روی بافت‌ها؛ رشد جوانه‌ها را کند می‌کند.","White powdery coating; stunts young shoots."),
        "treatment": t("گوگرد مرطوب/بی‌خطر، حذف بخش‌های شدیداً آلوده، افزایش تهویه.",
                        "Sulfur sprays, remove heavily infected tissue, improve ventilation."),
    },
    "apple_rust": {
        "name": t("زنگ سیب 🧡","Apple Rust 🧡"),
        "desc": t("لکه‌های نارنجی/زخمی با ساختارهای پودری در پشت برگ.","Orange rust spots with spore tubes on leaf undersides."),
        "treatment": t("حذف میزبان‌های واسط (سرو ژونیپروس)، قارچ‌کش در اوایل فصل.",
                        "Remove alternate hosts (junipers), early‑season fungicide."),
    },
    "apple_healthy": {
        "name": t("برگ سالم ✅","Healthy ✅"),
        "desc": t("نشانهٔ واضح بیماری دیده نشد.","No obvious disease signs."),
        "treatment": t("مراقبت عادی، پایش منظم.","Routine care; monitor regularly."),
    },
}

# Helper: Jalali string
ndef to_jalali_str(gdate):
    try:
        if not HAS_JDATETIME or pd.isna(gdate):
            return "-"
        if isinstance(gdate, datetime):
            gd = gdate.date()
        else:
            gd = gdate
        jd = jdatetime.date.fromgregorian(date=gd)
        return jd.strftime('%Y/%m/%d')
    except Exception:
        return "-"

# ==========================
# Auto-alert engine
# ==========================
def compute_alerts():
    alerts = []
    df = st.session_state['tree_data']
    # ---- Watering alert
    if st.session_state['last_watering'] is None:
        alerts.append({"type":"water", "level":"amber", "text": t("زمان آخرین آبیاری مشخص نیست — امروز آبیاری را ثبت کنید.",
                                                                     "Last watering unknown — please log watering today.")})
    else:
        days = (datetime.today().date() - st.session_state['last_watering']).days
        # simple seasonal threshold
        month = datetime.today().month
        thr = 2 if month in [6,7,8] else 4
        if days >= thr:
            alerts.append({"type":"water", "level":"red", "text": t(f"{days} روز از آخرین آبیاری گذشته — آبیاری لازم است.",
                                                                            f"{days} days since last watering — water now.")})

    # ---- Fertilization alert
    if st.session_state['last_fertilize'] is None:
        alerts.append({"type":"fert", "level":"amber", "text": t("برنامه کوددهی ثبت نشده — یک برنامه ماهانه تنظیم کنید.",
                                                                       "Fertilization not logged — plan monthly routine.")})
    else:
        daysf = (datetime.today().date() - st.session_state['last_fertilize']).days
        if 30 <= daysf < 40:
            alerts.append({"type":"fert", "level":"amber", "text": t("زمان کوددهی نزدیک است (هر ~۳۰ روز).",
                                                                             "Fertilization due soon (~30 days cycle).")})
        elif daysf >= 40:
            alerts.append({"type":"fert", "level":"red", "text": t("کوددهی عقب افتاده — اقدام کنید.",
                                                                            "Fertilization overdue — apply now.")})

    # ---- Growth abnormality (requires data)
    if not df.empty and len(df) >= 3:
        dfs = df.sort_values('تاریخ')
        # daily numeric X
        x = (pd.to_datetime(dfs['تاریخ']) - pd.to_datetime(dfs['تاریخ'].min())).dt.days.values.astype(float)
        y = dfs['ارتفاع(cm)'].astype(float).values
        # linear fit on all
        if x[-1] - x[0] > 0:
            a_all = (y[-1]-y[0])/(x[-1]-x[0])
        else:
            a_all = 0
        # recent slope using last 2 points
        if len(x) >= 2 and (x[-1]-x[-2])>0:
            a_recent = (y[-1]-y[-2])/(x[-1]-x[-2])
        else:
            a_recent = 0
        if a_recent < 0 or (a_all>0 and a_recent < 0.3*a_all):
            alerts.append({"type":"growth", "level":"amber", "text": t("رشد اخیر کند/منفی است — شرایط محیطی را بررسی کنید.",
                                                                               "Recent growth is slow/negative — check conditions.")})

    # ---- Pruning need (heuristic)
    if not df.empty:
        last = df.sort_values('تاریخ').iloc[-1]
        try:
            height = float(last['ارتفاع(cm)'])
            leaves = int(last['تعداد برگ'])
        except Exception:
            height, leaves = 0.0, 0
        leaf_density = (leaves / max(height, 1))  # leaves per cm
        disease_prob = st.session_state['last_disease']['prob']
        manual_flag = bool(last.get('نیاز به هرس', False))
        if manual_flag or disease_prob >= 0.45 or leaf_density > 0.8:
            alerts.append({"type":"prune", "level":"amber", "text": t("تراکم شاخه/برگ بالا یا شاخه‌های ناسالم — هرس سبک پیشنهاد می‌شود.",
                                                                               "High canopy density or unhealthy shoots — consider light pruning.")})

    # ---- Disease (from last detection)
    last_d = st.session_state['last_disease']
    if last_d['label'] != 'apple_healthy' and last_d['prob'] >= 0.35:
        di = disease_info.get(last_d['label'], {})
        alerts.append({"type":"disease", "level":"red", "text": f"{di.get('name', t('بیماری','Disease'))} — {int(last_d['prob']*100)}%"})

    return alerts

# ==========================
# Menu
# ==========================
menu = st.sidebar.selectbox(
    t("منو","Menu"),
    [t("🏠 خانه","Home"), t("🍎 تشخیص بیماری","Disease"), t("🌱 ثبت و رصد","Tracking"),
     t("📅 برنامه زمان‌بندی","Schedule"), t("📈 پیش‌بینی رشد","Prediction"), t("📥 دانلود گزارش","Download"), t("⚙️ تنظیمات نگهداری","Care Settings")]
)

# ==========================
# HOME
# ==========================
if menu == t("🏠 خانه","Home"):
    st.header(t("داشبورد عملیاتی نهال","Operational Seedling Dashboard"))

    # Quick actions
    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button(t("ثبت آبیاری امروز","Log watering today")):
            st.session_state['last_watering'] = datetime.today().date()
            st.success(t("آبیاری امروز ثبت شد","Watering logged for today"))
    with c2:
        if st.button(t("ثبت کوددهی امروز","Log fertilization today")):
            st.session_state['last_fertilize'] = datetime.today().date()
            st.success(t("کوددهی امروز ثبت شد","Fertilization logged for today"))
    with c3:
        lw = st.session_state['last_watering']
        lf = st.session_state['last_fertilize']
        st.markdown("<div class='kpi'>" +
                    t("**آخرین آبیاری:** ","**Last watering:** ") +
                    (to_jalali_str(lw) + " (" + str(lw) + ")" if lw else t("نامشخص","Unknown")) +
                    "<br>" +
                    t("**آخرین کوددهی:** ","**Last fertilization:** ") +
                    (to_jalali_str(lf) + " (" + str(lf) + ")" if lf else t("نامشخص","Unknown")) +
                    "</div>", unsafe_allow_html=True)

    # KPI + last record
    df = st.session_state['tree_data']
    c1, c2, c3, c4 = st.columns([1,1,1,2])
    last = df.sort_values('تاریخ').iloc[-1] if not df.empty else None
    with c1:
        st.markdown(
            f"<div class='kpi'><b>{t('ارتفاع آخرین اندازه','Last height')}</b><div style='font-size:20px'>{(str(last['ارتفاع(cm)'])+' cm') if last is not None else '--'}</div></div>",
            unsafe_allow_html=True,
        )
    with c2:
        st.markdown(
            f"<div class='kpi'><b>{t('تعداد برگ‌ها','Leaves')}</b><div style='font-size:20px'>{(int(last['تعداد برگ']) if last is not None else '--')}</div></div>",
            unsafe_allow_html=True,
        )
    with c3:
        status = t('⚠️ نیاز به هرس','⚠️ Prune needed') if (last is not None and last['نیاز به هرس']) else t('✅ سالم','✅ Healthy')
        st.markdown(
            f"<div class='kpi'><b>{t('وضعیت هرس','Prune Status')}</b><div style='font-size:18px'>{status}</div></div>",
            unsafe_allow_html=True,
        )
    with c4:
        st.markdown(
            f"<div class='card'><b>{t('راهنمای سریع','Quick Tips')}</b><br>{t('برای نگهداری بهتر، هفته‌ای یکبار بررسی کنید.','Check seedlings weekly for best care.')}</div>",
            unsafe_allow_html=True,
        )

    # Alerts
    alerts = compute_alerts()
    if alerts:
        for a in alerts:
            css = 'alert-red' if a['level']=='red' else ('alert-amber' if a['level']=='amber' else 'alert-green')
            st.markdown(f"<div class='{css}'>• {a['text']}</div>", unsafe_allow_html=True)
    else:
        st.success(t("هشداری وجود ندارد.","No active alerts."))

    # Chart
    if not df.empty:
        dfx = df.copy().sort_values('تاریخ')
        dfx['تاریخ شمسی'] = dfx['تاریخ'].apply(to_jalali_str)
        fig = px.line(dfx, x='تاریخ', y=['ارتفاع(cm)','تعداد برگ'], labels={'value':t('مقدار','Value'),'variable':t('پارامتر','Parameter'),'تاریخ':t('تاریخ میلادی','Date (Gregorian)')})
        st.plotly_chart(fig, use_container_width=True)

# ==========================
# DISEASE
# ==========================
elif menu == t("🍎 تشخیص بیماری","Disease"):
    st.header(t("تشخیص بیماری برگ","Leaf Disease Detection"))
    f = st.file_uploader(t("آپلود تصویر برگ","Upload leaf image"), type=["jpg","jpeg","png"])
    if f:
        st.image(f, use_container_width=True)
        # Predict via model if available, else demo heuristic
        if model is not None and img_to_array is not None:
            try:
                img = Image.open(f).convert("RGB")
                target = model.input_shape[1:3]
                img = img.resize(target)
                arr = img_to_array(img)/255.0
                arr = np.expand_dims(arr, axis=0)
                preds = model.predict(arr)[0]
                # if model has <4 classes, pad safely
                if len(preds) < len(class_labels):
                    preds = np.pad(preds, (0, len(class_labels)-len(preds)))
            except Exception:
                preds = None
        else:
            preds = None
        if preds is None:
            # Demo: simple heuristic using green channel
            img = Image.open(f).convert("RGB").resize((224,224))
            arr = np.array(img)/255.0
            g_mean = arr[...,1].mean()
            r_mean = arr[...,0].mean()
            o = np.array([
                0.2 + 0.6*(g_mean>0.5),               # healthy more probable when greener
                0.2 + 0.5*(r_mean<0.4),               # scab more if darker
                0.2 + 0.5*(g_mean<0.45),              # powdery when less greenish
                0.2 + 0.4*(abs(r_mean-g_mean)>0.2),   # rust heuristic
            ])
            o = np.clip(o, 0.01, 0.99)
            preds = o / o.sum()
        idx = int(np.argmax(preds))
        label = class_labels[idx]
        prob = float(preds[idx])
        st.session_state['last_disease'] = {'label': label, 'prob': prob}

        di = disease_info[label]
        # Progress bars per class
        for i, cls in enumerate(class_labels):
            pct = float(preds[i]*100)
            st.write(f"{disease_info[cls]['name']}: {pct:.1f}%")
            st.progress(min(max(preds[i],0.0),1.0))
        st.success(f"{t('نتیجه','Result')}: {di['name']} — {prob*100:.1f}%")
        st.write(f"**{t('توضیح','Description')}:** {di['desc']}")
        st.write(f"**{t('توصیه درمانی','Treatment / Guidance')}:** {di['treatment']}")

# ==========================
# TRACKING
# ==========================
elif menu == t("🌱 ثبت و رصد","Tracking"):
    st.header(t("ثبت و رصد رشد نهال","Seedling Tracking"))
    with st.expander(t("➕ ثبت اندازه‌گیری جدید","Add measurement"), expanded=True):
        date = st.date_input(t("تاریخ","Date"), value=datetime.today())
        height = st.number_input(t("ارتفاع (cm)","Height (cm)"), min_value=0.0, step=0.5)
        leaves = st.number_input(t("تعداد برگ‌ها","Leaves"), min_value=0, step=1)
        notes = st.text_area(t("توضیحات","Notes"))
        prune = st.checkbox(t("نیاز به هرس؟","Prune needed?"))
        if st.button(t("ثبت","Submit")):
            st.session_state['tree_data'] = pd.concat([
                st.session_state['tree_data'],
                pd.DataFrame([[date, height, leaves, notes, prune]], columns=['تاریخ','ارتفاع(cm)','تعداد برگ','توضیحات','نیاز به هرس'])
            ], ignore_index=True)
            st.success(t("ثبت شد ✅","Added ✅"))

    if not st.session_state['tree_data'].empty:
        df_show = st.session_state['tree_data'].copy()
        df_show['تاریخ شمسی'] = df_show['تاریخ'].apply(lambda d: to_jalali_str(d))
        st.dataframe(df_show)
        fig = px.line(df_show.sort_values('تاریخ'), x='تاریخ', y=['ارتفاع(cm)','تعداد برگ'], title=t("روند رشد","Growth trend"))
        st.plotly_chart(fig, use_container_width=True)

# ==========================
# SCHEDULE
# ==========================
elif menu == t("📅 برنامه زمان‌بندی","Schedule"):
    st.header(t("برنامه زمان‌بندی","Schedule"))
    df_s = st.session_state['schedule']
    today = datetime.today().date()
    today_tasks = df_s[(df_s['تاریخ']==today) & (df_s['انجام شد']==False)]
    if not today_tasks.empty:
        st.warning(t("فعالیت‌های امروز وجود دارد!","There are tasks for today!"))
        for _, r in today_tasks.iterrows():
            st.write(f"• {r['فعالیت']} — {r['تاریخ']}")
    else:
        st.success(t("امروز کاری برنامه‌ریزی نشده یا همه انجام شده","No pending tasks for today"))

    for i in df_s.index:
        df_s.at[i,'انجام شد'] = st.checkbox(f"{df_s.at[i,'تاریخ']} — {df_s.at[i,'فعالیت']}", value=df_s.at[i,'انجام شد'], key=f"sch{i}")

    df_s_show = df_s.copy()
    df_s_show['تاریخ شمسی'] = df_s_show['تاریخ'].apply(lambda d: to_jalali_str(d))
    st.dataframe(df_s_show)

# ==========================
# PREDICTION
# ==========================
elif menu == t("📈 پیش‌بینی رشد","Prediction"):
    st.header(t("پیش‌بینی رشد","Growth Prediction"))
    df = st.session_state['tree_data']
    if df.empty or len(df) < 2:
        st.info(t("ابتدا حداقل دو اندازه‌گیری ثبت کنید.","Please add at least two measurements first."))
    else:
        df_sorted = df.sort_values('تاریخ')
        X = (pd.to_datetime(df_sorted['تاریخ']) - pd.to_datetime(df_sorted['تاریخ'].min())).dt.days.values.astype(float)
        y = df_sorted['ارتفاع(cm)'].astype(float).values
        a = (y[-1]-y[0])/(X[-1]-X[0]) if (X[-1]-X[0])>0 else 0.0
        b = y[0] - a*X[0]
        future_days = np.array([(X.max()+7*i) for i in range(1,13)])
        preds = a*future_days + b
        future_dates = [df_sorted['تاریخ'].max() + timedelta(weeks=i) for i in range(1,13)]
        df_future = pd.DataFrame({'تاریخ': future_dates, t('ارتفاع پیش‌بینی شده(cm)','Predicted Height (cm)'): preds})
        df_future['تاریخ شمسی'] = df_future['تاریخ'].apply(lambda d: to_jalali_str(d))
        st.session_state['df_future'] = df_future
        st.dataframe(df_future)
        fig = px.line(df_future, x='تاریخ', y=df_future.columns[1], title=t("پیش‌بینی ارتفاع","Height forecast"))
        st.plotly_chart(fig, use_container_width=True)

# ==========================
# DOWNLOAD
# ==========================
elif menu == t("📥 دانلود گزارش","Download"):
    st.header(t("دانلود گزارش","Download"))
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
        if not st.session_state['tree_data'].empty:
            st.session_state['tree_data'].assign(**{'تاریخ شمسی': st.session_state['tree_data']['تاریخ'].apply(to_jalali_str)}).to_excel(writer, sheet_name='growth', index=False)
        if not st.session_state['schedule'].empty:
            st.session_state['schedule'].assign(**{'تاریخ شمسی': st.session_state['schedule']['تاریخ'].apply(to_jalali_str)}).to_excel(writer, sheet_name='schedule', index=False)
        if not st.session_state['df_future'].empty:
            st.session_state['df_future'].to_excel(writer, sheet_name='prediction', index=False)
    data = buffer.getvalue()
    st.download_button(label=t("دانلود Excel داشبورد","Download Excel Dashboard"), data=data, file_name="apple_dashboard.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

# ==========================
# SETTINGS
# ==========================
elif menu == t("⚙️ تنظیمات نگهداری","Care Settings"):
    st.header(t("تنظیمات نگهداری","Care Settings"))
    st.info(t("در اینجا می‌توانید تنظیمات دلخواه برای آستانه‌های هشدار را سفارشی کنید (نسخه ساده).",
             "Customize alert thresholds here (simple version)."))
    # For future expansion: we keep defaults in compute_alerts(), but you can add sliders here.
    st.write(t("در حال حاضر آستانه‌ها به صورت پیش‌فرض اعمال می‌شوند:","Currently using default thresholds:"))
    st.markdown(
        "- " + t("آبیاری: هر ۲ روز در تابستان، هر ۴ روز در سایر فصول.", "Watering: ~2d in summer, ~4d otherwise.") + "\n" +
        "- " + t("کوددهی: هر ۳۰ روز.", "Fertilization: every ~30 days.") + "\n" +
        "- " + t("هرس: تراکم زیاد/بیماری/علامت دستی.", "Pruning: high density/disease/manual flag.") + "\n" +
        "- " + t("رشد غیرطبیعی: شیب رشد اخیر < ۳۰٪ میانگین.", "Abnormal growth: recent slope < 30% of avg.")
    )
