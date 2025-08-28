# app.py
import streamlit as st
import pandas as pd
import numpy as np
from PIL import Image
from datetime import datetime, date, timedelta
import io
import os
import sqlalchemy as sa
from sqlalchemy import Column, Integer, String, Table, MetaData, Date, Float, Boolean, Text
try:
    import jdatetime
    HAS_JDATETIME = True
except Exception:
    HAS_JDATETIME = False

# optional tensorflow (if you have a model)
try:
    import tensorflow as tf
    from tensorflow.keras.utils import img_to_array
    HAS_TF = True
except Exception:
    tf = None
    img_to_array = None
    HAS_TF = False

# ---------- page config & styles ----------
st.set_page_config(page_title="داشبورد نهال سیب 🍎", layout="wide", page_icon="🍎")

st.markdown("""
<style>
@import url('https://cdn.jsdelivr.net/gh/rastikerdar/vazir-font@v30.1.0/dist/font-face.css');
html, body, [class*="css"] { font-family: Vazir, sans-serif; direction: rtl; }
body{
  background-image: linear-gradient(180deg, rgba(230,242,234,0.92) 0%, rgba(217,238,240,0.92) 40%, rgba(207,238,240,0.92) 100%),
                    url('https://images.unsplash.com/photo-1501004318641-b39e6451bec6?auto=format&fit=crop&w=1600&q=80');
  background-size: cover; background-attachment: fixed; color:#0f172a;
}
.kpi{background:rgba(255,255,255,0.95); border-radius:14px; padding:14px; box-shadow:0 8px 24px rgba(7,10,25,0.08); margin-bottom:10px}
.card{background:linear-gradient(180deg, rgba(255,255,255,0.9), rgba(255,255,255,0.82)); border-radius:16px; padding:16px; box-shadow:0 12px 32px rgba(7,10,25,0.08)}
.logo-row{display:flex; align-items:center; gap:10px; margin-bottom:10px;}
.alert-red{background:#fee2e2; border:1px solid #fecaca; padding:10px; border-radius:10px; margin-bottom:8px}
.alert-amber{background:#fff7ed; border:1px solid #ffedd5; padding:10px; border-radius:10px; margin-bottom:8px}
.alert-green{background:#ecfdf5; border:1px solid #d1fae5; padding:10px; border-radius:10px; margin-bottom:8px}
</style>
""", unsafe_allow_html=True)

# ---------- i18n helper ----------
if 'lang' not in st.session_state:
    st.session_state['lang'] = 'FA'
lang_choice = st.sidebar.selectbox("زبان / Language", ['فارسی','English'])
st.session_state['lang'] = 'EN' if lang_choice=='English' else 'FA'
def t(fa, en): return en if st.session_state['lang']=='EN' else fa

# ---------- logo ----------
logo_path = "logo.svg"
if os.path.exists(logo_path):
    try:
        with open(logo_path,'r',encoding='utf-8') as f:
            svg = f.read()
        st.markdown(f"<div class='logo-row'>{svg}</div>", unsafe_allow_html=True)
    except Exception:
        st.markdown(f"<h1>🍎 {t('داشبورد نهال سیب','Apple Seedling Dashboard')}</h1>")
else:
    st.markdown(f"<h1>🍎 {t('داشبورد نهال سیب','Apple Seedling Dashboard')}</h1>")

# ---------- DB (SQLite via SQLAlchemy) ----------
DB_DIR = os.path.join(os.getcwd(), "data")
os.makedirs(DB_DIR, exist_ok=True)
DB_FILE = os.path.join(DB_DIR, "seedling_data.db")
engine = sa.create_engine(f"sqlite:///{DB_FILE}", connect_args={"check_same_thread": False})
meta = MetaData()

measurements = Table('measurements', meta,
    Column('id', Integer, primary_key=True),
    Column('date', Date, nullable=False),
    Column('height', Float, nullable=False),
    Column('leaves', Integer, nullable=False),
    Column('notes', Text),
    Column('prune', Boolean, default=False)
)

schedule = Table('schedule', meta,
    Column('id', Integer, primary_key=True),
    Column('task_date', Date, nullable=False),
    Column('activity', String, nullable=False),
    Column('done', Boolean, default=False)
)

diseases = Table('diseases', meta,
    Column('id', Integer, primary_key=True),
    Column('date', Date, nullable=False),
    Column('label', String),
    Column('prob', Float)
)

meta.create_all(engine)
conn = engine.connect()

# ---------- helpers ----------
def to_jalali_str(gdate):
    try:
        if not HAS_JDATETIME or pd.isna(gdate):
            return "-"
        if isinstance(gdate, datetime):
            gd = gdate.date()
        elif isinstance(gdate, date):
            gd = gdate
        else:
            gd = pd.to_datetime(gdate).date()
        jd = jdatetime.date.fromgregorian(date=gd)
        return jd.strftime('%Y/%m/%d')
    except Exception:
        return "-"

def load_measurements():
    sel = sa.select(measurements).order_by(measurements.c.date)
    rows = conn.execute(sel).fetchall()
    if not rows:
        return pd.DataFrame(columns=['تاریخ','ارتفاع(cm)','تعداد برگ','توضیحات','نیاز به هرس'])
    data = []
    for r in rows:
        m = r._mapping
        data.append([m['date'], m['height'], m['leaves'], m['notes'] or '', bool(m['prune'])])
    df = pd.DataFrame(data, columns=['تاریخ','ارتفاع(cm)','تعداد برگ','توضیحات','نیاز به هرس'])
    return df

def insert_measurement(gdate, height, leaves, notes, prune):
    ins = measurements.insert().values(date=gdate, height=float(height), leaves=int(leaves), notes=notes, prune=bool(prune))
    conn.execute(ins)

def load_schedule():
    sel = sa.select(schedule).order_by(schedule.c.task_date)
    rows = conn.execute(sel).fetchall()
    if not rows:
        # initialize schedule into DB
        start_date = datetime.today().date()
        schedule_list = []
        for week in range(52):
            d = start_date + timedelta(weeks=week)
            schedule_list.append((d, t("آبیاری","Watering"), False))
            if week % 4 == 0:
                schedule_list.append((d, t("کوددهی","Fertilization"), False))
            if week % 12 == 0:
                schedule_list.append((d, t("هرس","Pruning"), False))
            if week % 6 == 0:
                schedule_list.append((d, t("بازرسی بیماری","Disease Check"), False))
        for d,a,done in schedule_list:
            conn.execute(schedule.insert().values(task_date=d, activity=a, done=done))
        rows = conn.execute(sa.select(schedule).order_by(schedule.c.task_date)).fetchall()
    data = []
    for r in rows:
        m = r._mapping
        data.append([m['task_date'], m['activity'], bool(m['done']), m['id']])
    df = pd.DataFrame(data, columns=['تاریخ','فعالیت','انجام شد','_id'])
    return df

def update_schedule_done(row_id, done_value):
    upd = schedule.update().where(schedule.c.id==row_id).values(done=bool(done_value))
    conn.execute(upd)

def insert_disease_log(gdate, label, prob):
    conn.execute(diseases.insert().values(date=gdate, label=label, prob=float(prob)))

def load_last_disease():
    sel = sa.select(diseases).order_by(diseases.c.date.desc()).limit(1)
    r = conn.execute(sel).first()
    if r:
        return r._mapping
    return None

# ---------- load initial data into session ----------
if 'tree_data' not in st.session_state:
    st.session_state['tree_data'] = load_measurements()
if 'schedule_df' not in st.session_state:
    st.session_state['schedule_df'] = load_schedule()
if 'df_future' not in st.session_state:
    st.session_state['df_future'] = pd.DataFrame()

# derive last watering/fertilize from schedule done rows if any
if 'last_watering' not in st.session_state:
    sdone = st.session_state['schedule_df']
    done_water = sdone[(sdone['فعالیت']==t("آبیاری","Watering")) & (sdone['انجام شد']==True)]
    st.session_state['last_watering'] = done_water['تاریخ'].max() if not done_water.empty else None

if 'last_fertilize' not in st.session_state:
    done_f = st.session_state['schedule_df'][(st.session_state['schedule_df']['فعالیت']==t("کوددهی","Fertilization")) & (st.session_state['schedule_df']['انجام شد']==True)]
    st.session_state['last_fertilize'] = done_f['تاریخ'].max() if not done_f.empty else None

ld = load_last_disease()
if ld:
    st.session_state['last_disease'] = {'label': ld['label'], 'prob': ld['prob']}
else:
    st.session_state['last_disease'] = {'label': 'apple_healthy', 'prob': 1.0}

# ---------- disease metadata ----------
class_labels = ["apple_healthy","apple_black_spot","apple_powdery_mildew","apple_rust"]
disease_info = {
    "apple_black_spot": {"name": t("لکه سیاه ⚫️","Apple Scab ⚫️"), "desc": t("لکه‌های سیاه/زیتونی روی برگ‌ها و میوه.", "Olive-black spots on leaves/fruit."), "treatment": t("جمع‌آوری برگ‌های ریخته، هرس و استفاده از قارچ‌کش مناسب.","Remove fallen leaves, prune, use recommended fungicide.")},
    "apple_powdery_mildew": {"name": t("سفیدک پودری ❄️","Powdery Mildew ❄️"), "desc": t("پوشش سفید پودری روی برگ‌ها.", "White powdery coating on leaves."), "treatment": t("گوگرد/اسپری‌های مناسب، حذف بخش‌های آلوده، تهویه بهتر.","Sulfur sprays; remove infected tissue; improve ventilation.")},
    "apple_rust": {"name": t("زنگ سیب 🧡","Apple Rust 🧡"), "desc": t("لکه‌های نارنجی/زنگ‌مانند روی پشت برگ.", "Orange rust spots on leaf underside."), "treatment": t("حذف میزبان‌های واسط، درمان زودهنگام با قارچ‌کش.","Remove alternate hosts; early-season fungicide.")},
    "apple_healthy": {"name": t("برگ سالم ✅","Healthy ✅"), "desc": t("نشانهٔ آشکار بیماری یافت نشد.","No obvious disease signs."), "treatment": t("مراقبت معمول و پایش منظم.","Routine care; monitor regularly.")}
}

# ---------- compute alerts ----------
def compute_alerts():
    alerts = []
    df = st.session_state['tree_data']
    # watering
    lw = st.session_state.get('last_watering', None)
    if lw is None:
        alerts.append({"type":"water","level":"amber","text": t("آخرین آبیاری ثبت نشده — لطفاً ثبت کنید.","Last watering not logged — please log watering.")})
    else:
        days = (datetime.today().date() - pd.to_datetime(lw).date()).days
        month = datetime.today().month
        thr = 2 if month in [6,7,8] else 4
        if days >= thr:
            alerts.append({"type":"water","level":"red","text": t(f"{days} روز از آخرین آبیاری گذشته — آبیاری لازم است.","{0} days since last watering — water now.").format(days)})

    # fertilize
    lf = st.session_state.get('last_fertilize', None)
    if lf is None:
        alerts.append({"type":"fert","level":"amber","text": t("کوددهی ثبت نشده — برنامه‌ریزی کنید.","Fertilization not logged — plan routine.")})
    else:
        daysf = (datetime.today().date() - pd.to_datetime(lf).date()).days
        if daysf >= 40:
            alerts.append({"type":"fert","level":"red","text": t("کوددهی بیش از زمان معمول گذشته است — کوددهی انجام دهید.","Fertilization overdue — apply now.")})
        elif daysf >= 25:
            alerts.append({"type":"fert","level":"amber","text": t("کوددهی نزدیک است.","Fertilization due soon.")})

    # growth abnormality
    if len(df) >= 3:
        dfs = df.sort_values('تاریخ')
        x = (pd.to_datetime(dfs['تاریخ']) - pd.to_datetime(dfs['تاریخ'].min())).dt.days.values.astype(float)
        y = dfs['ارتفاع(cm)'].astype(float).values
        if x[-1]-x[0] > 0:
            a_all = (y[-1]-y[0])/(x[-1]-x[0])
        else:
            a_all = 0
        if len(x) >= 2 and (x[-1]-x[-2])>0:
            a_recent = (y[-1]-y[-2])/(x[-1]-x[-2])
        else:
            a_recent = 0
        if a_recent < 0 or (a_all>0 and a_recent < 0.3*a_all):
            alerts.append({"type":"growth","level":"amber","text": t("رشد اخیر کند یا منفی است — شرایط بررسی شود.","Recent growth is slow/negative — check conditions.")})

    # pruning heuristic
    if not df.empty:
        last = df.sort_values('تاریخ').iloc[-1]
        try:
            height = float(last['ارتفاع(cm)'])
            leaves = int(last['تعداد برگ'])
        except Exception:
            height, leaves = 0.0, 0
        density = leaves / max(height, 1.0)
        last_disease = st.session_state.get('last_disease', {'label':'apple_healthy','prob':1.0})
        if last.get('نیاز به هرس', False) or last_disease.get('prob',0) >= 0.45 or density > 0.8:
            alerts.append({"type":"prune","level":"amber","text": t("تراکم برگ/شاخه بالا یا بیماری — هرس سبک پیشنهاد می‌شود.","High canopy density or disease — consider light pruning.")})

    # disease from last detection
    last_d = st.session_state.get('last_disease', {'label':'apple_healthy','prob':1.0})
    if last_d['label'] != 'apple_healthy' and last_d['prob'] >= 0.35:
        di = disease_info.get(last_d['label'], {})
        alerts.append({"type":"disease","level":"red","text": f"{di.get('name',t('بیماری','Disease'))} — {int(last_d['prob']*100)}%"})

    return alerts

# ---------- menu ----------
menu = st.sidebar.selectbox(t("منو","Menu"),
    [t("🏠 خانه","Home"), t("🍎 تشخیص بیماری","Disease"), t("🌱 ثبت و رصد","Tracking"),
     t("📅 برنامه زمان‌بندی","Schedule"), t("📈 پیش‌بینی رشد","Prediction"), t("📥 دانلود گزارش","Download"),
     t("⚙️ تنظیمات نگهداری","Care Settings")]
)

# ---------- HOME ----------
if menu == t("🏠 خانه","Home"):
    st.header(t("داشبورد عملیاتی نهال","Operational Seedling Dashboard"))
    c1,c2,c3 = st.columns(3)
    with c1:
        if st.button(t("ثبت آبیاری امروز","Log watering today")):
            st.session_state['last_watering'] = datetime.today().date()
            st.success(t("آبیاری امروز ثبت شد","Watering logged for today"))
    with c2:
        if st.button(t("ثبت کوددهی امروز","Log fertilization today")):
            st.session_state['last_fertilize'] = datetime.today().date()
            st.success(t("کوددهی امروز ثبت شد","Fertilization logged for today"))
    with c3:
        lw = st.session_state.get('last_watering', None)
        lf = st.session_state.get('last_fertilize', None)
        st.markdown("<div class='kpi'>"+
                    t("**آخرین آبیاری:** ","**Last watering:** ")+
                    (to_jalali_str(lw)+" ("+str(lw)+")" if lw else t("نامشخص","Unknown"))+
                    "<br>" +
                    t("**آخرین کوددهی:** ","**Last fertilization:** ")+
                    (to_jalali_str(lf)+" ("+str(lf)+")" if lf else t("نامشخص","Unknown"))+
                    "</div>", unsafe_allow_html=True)
    df = st.session_state['tree_data']
    c1,c2,c3,c4 = st.columns([1,1,1,2])
    last = df.sort_values('تاریخ').iloc[-1] if not df.empty else None
    with c1:
        st.markdown(f"<div class='kpi'><b>{t('ارتفاع آخرین اندازه','Last height')}</b><div style='font-size:20px'>{(str(last['ارتفاع(cm)'])+' cm') if last is not None else '--'}</div></div>", unsafe_allow_html=True)
    with c2:
        st.markdown(f"<div class='kpi'><b>{t('تعداد برگ‌ها','Leaves')}</b><div style='font-size:20px'>{(int(last['تعداد برگ']) if last is not None else '--')}</div></div>", unsafe_allow_html=True)
    with c3:
        status = t('⚠️ نیاز به هرس','⚠️ Prune needed') if (last is not None and last['نیاز به هرس']) else t('✅ سالم','✅ Healthy')
        st.markdown(f"<div class='kpi'><b>{t('وضعیت هرس','Prune Status')}</b><div style='font-size:18px'>{status}</div></div>", unsafe_allow_html=True)
    with c4:
        st.markdown(f"<div class='card'><b>{t('راهنمای سریع','Quick Tips')}</b><br>{t('برای نگهداری بهتر، هفته‌ای یکبار بررسی کنید.','Check seedlings weekly for best care.')}</div>", unsafe_allow_html=True)
    alerts = compute_alerts()
    if alerts:
        for a in alerts:
            css = 'alert-red' if a['level']=='red' else ('alert-amber' if a['level']=='amber' else 'alert-green')
            st.markdown(f"<div class='{css}'>• {a['text']}</div>", unsafe_allow_html=True)
    else:
        st.success(t("هشداری وجود ندارد.","No active alerts."))
    if not df.empty:
        dfx = df.copy().sort_values('تاریخ')
        dfx['تاریخ شمسی'] = dfx['تاریخ'].apply(lambda d: to_jalali_str(d))
        fig = px.line(dfx, x='تاریخ', y=['ارتفاع(cm)','تعداد برگ'], labels={'value':t('مقدار','Value'),'variable':t('پارامتر','Parameter'),'تاریخ':t('تاریخ میلادی','Date (Gregorian)')})
        st.plotly_chart(fig, use_container_width=True)

# ---------- DISEASE ----------
elif menu == t("🍎 تشخیص بیماری","Disease"):
    st.header(t("تشخیص بیماری برگ","Leaf Disease Detection"))
    f = st.file_uploader(t("آپلود تصویر برگ","Upload leaf image"), type=["jpg","jpeg","png"])
    if f:
        st.image(f, use_container_width=True)
        preds = None
        if HAS_TF and img_to_array is not None:
            try:
                model = tf.keras.models.load_model("leaf_model.h5")
                img = Image.open(f).convert("RGB")
                target = model.input_shape[1:3] if hasattr(model, 'input_shape') else (224,224)
                img = img.resize(target)
                arr = img_to_array(img)/255.0
                arr = np.expand_dims(arr, axis=0)
                preds = model.predict(arr)[0]
                if len(preds) < len(class_labels):
                    preds = np.pad(preds, (0, len(class_labels)-len(preds)))
            except Exception:
                preds = None
        if preds is None:
            img = Image.open(f).convert("RGB").resize((224,224))
            arr = np.array(img)/255.0
            g_mean = arr[...,1].mean()
            r_mean = arr[...,0].mean()
            o = np.array([
                0.2 + 0.6*(g_mean>0.5),
                0.2 + 0.5*(r_mean<0.4),
                0.2 + 0.5*(g_mean<0.45),
                0.2 + 0.4*(abs(r_mean-g_mean)>0.2),
            ])
            o = np.clip(o, 0.01, 0.99)
            preds = o / o.sum()
        idx = int(np.argmax(preds))
        label = class_labels[idx]
        prob = float(preds[idx])
        insert_disease_log(datetime.today().date(), label, prob)
        st.session_state['last_disease'] = {'label':label,'prob':prob}
        di = disease_info.get(label, disease_info['apple_healthy'])
        for i, cls in enumerate(class_labels):
            pct = float(preds[i]*100)
            st.write(f"{disease_info.get(cls, {'name':cls})['name']}: {pct:.1f}%")
            st.progress(min(max(preds[i],0.0),1.0))
        st.success(f"{t('نتیجه','Result')}: {di['name']} — {prob*100:.1f}%")
        st.write(f"**{t('توضیح','Description')}:** {di['desc']}")
        st.write(f"**{t('توصیه درمانی','Treatment / Guidance')}:** {di['treatment']}")

# ---------- TRACKING ----------
elif menu == t("🌱 ثبت و رصد","Tracking"):
    st.header(t("ثبت و رصد رشد نهال","Seedling Tracking"))
    with st.expander(t("➕ ثبت اندازه‌گیری جدید","Add measurement"), expanded=True):
        date_input = st.date_input(t("تاریخ","Date"), value=datetime.today().date())
        height = st.number_input(t("ارتفاع (cm)","Height (cm)"), min_value=0.0, step=0.5)
        leaves = st.number_input(t("تعداد برگ‌ها","Leaves"), min_value=0, step=1)
        notes = st.text_area(t("توضیحات","Notes"))
        prune = st.checkbox(t("نیاز به هرس؟","Prune needed?"))
        if st.button(t("ثبت","Submit")):
            insert_measurement(date_input, height, leaves, notes, prune)
            st.session_state['tree_data'] = load_measurements()
            st.success(t("ثبت شد ✅","Added ✅"))
    if not st.session_state['tree_data'].empty:
        df_show = st.session_state['tree_data'].copy()
        df_show['تاریخ شمسی'] = df_show['تاریخ'].apply(lambda d: to_jalali_str(d))
        st.dataframe(df_show)

# ---------- SCHEDULE ----------
elif menu == t("📅 برنامه زمان‌بندی","Schedule"):
    st.header(t("برنامه زمان‌بندی","Schedule"))
    df_s = st.session_state['schedule_df']
    today = datetime.today().date()
    today_tasks = df_s[(df_s['تاریخ']==today) & (df_s['انجام شد']==False)]
    if not today_tasks.empty:
        st.warning(t("فعالیت‌های امروز وجود دارد!","There are tasks for today!"))
        for _, r in today_tasks.iterrows():
            st.write(f"• {r['فعالیت']} — {r['تاریخ']}")
    else:
        st.success(t("امروز کاری برنامه‌ریزی نشده یا همه انجام شده","No pending tasks for today"))
    for i, row in df_s.iterrows():
        checked = st.checkbox(f"{row['تاریخ']} — {row['فعالیت']}", value=row['انجام شد'], key=f"sch_{row['_id']}")
        if checked != row['انجام شد']:
            update_schedule_done(row['_id'], checked)
            st.session_state['schedule_df'] = load_schedule()
            st.experimental_rerun()

# ---------- PREDICTION ----------
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

# ---------- DOWNLOAD ----------
elif menu == t("📥 دانلود گزارش","Download"):
    st.header(t("دانلود گزارش","Download"))
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
        if not st.session_state['tree_data'].empty:
            st.session_state['tree_data'].assign(**{'تاریخ شمسی': st.session_state['tree_data']['تاریخ'].apply(to_jalali_str)}).to_excel(writer, sheet_name='growth', index=False)
        if not st.session_state['schedule_df'].empty:
            st.session_state['schedule_df'].assign(**{'تاریخ شمسی': st.session_state['schedule_df']['تاریخ'].apply(to_jalali_str)}).to_excel(writer, sheet_name='schedule', index=False)
        if not st.session_state['df_future'].empty:
            st.session_state['df_future'].to_excel(writer, sheet_name='prediction', index=False)
    data = buffer.getvalue()
    st.download_button(label=t("دانلود Excel داشبورد","Download Excel Dashboard"), data=data, file_name="apple_dashboard.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

# ---------- SETTINGS ----------
elif menu == t("⚙️ تنظیمات نگهداری","Care Settings"):
    st.header(t("تنظیمات نگهداری","Care Settings"))
    st.info(t("در این بخش می‌توانید پارامترهای هشدار را تغییر دهید (نسخه ساده).","Customize alert thresholds here (simple version)."))
    st.write(t("در حال حاضر مقادیر پیش‌فرض به کار برده شده‌اند. برای سفارشی‌سازی بیشتر بفرمایید چه مقادیری بخواهید.","Currently using default thresholds; tell me which values you'd like to change."))

