import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from PIL import Image
import bcrypt
import sqlalchemy as sa
from sqlalchemy import Column, Integer, String, Table, MetaData, ForeignKey
import io

# ---------- Config ----------
st.set_page_config(page_title="🍎 Seedling Pro", page_icon="🍎", layout="wide")

# ---------- Language selection ----------
lang = st.sidebar.selectbox("Language / زبان", ["فارسی", "English"])
EN = (lang == "English")

def t(fa, en):
    return en if EN else fa

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

schedule = Table('schedule', meta,
                 Column('id', Integer, primary_key=True),
                 Column('user_id', Integer, ForeignKey('users.id')),
                 Column('task_date', String),
                 Column('activity', String),
                 Column('done', Integer))

meta.create_all(engine)
conn = engine.connect()

# ---------- Session state ----------
if 'user_id' not in st.session_state: st.session_state['user_id'] = None
if 'username' not in st.session_state: st.session_state['username'] = None

# ---------- Password helpers ----------
def hash_password(password):
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def check_password(password, hashed):
    return bcrypt.checkpw(password.encode(), hashed.encode())

# ---------- Authentication ----------
if st.session_state['user_id'] is None:
    st.sidebar.header(t("Authentication", "Authentication"))
    mode = st.sidebar.radio(t("Mode", "Mode"), [t("Login", "Login"), t("Sign Up", "Sign Up"), t("Demo", "Demo")])

    if mode == t("Sign Up", "Sign Up"):
        st.header(t("Sign Up", "Sign Up"))
        username = st.text_input(t("Username", "Username"))
        password = st.text_input(t("Password", "Password"), type="password")
        if st.button(t("Register", "Register")):
            if not username or not password:
                st.error(t("Provide username & password.", "Provide username & password."))
            else:
                sel = sa.select(users_table).where(users_table.c.username==username)
                r = conn.execute(sel).mappings().first()
                if r:
                    st.error(t("Username already exists.", "Username already exists."))
                else:
                    hashed = hash_password(password)
                    conn.execute(users_table.insert().values(username=username, password_hash=hashed))
                    st.success(t("Registered. Please login.", "Registered. Please login."))

    elif mode == t("Login", "Login"):
        st.header(t("Login", "Login"))
        username = st.text_input(t("Username", "Username"))
        password = st.text_input(t("Password", "Password"), type="password")
        if st.button(t("Login", "Login")):
            sel = sa.select(users_table).where(users_table.c.username==username)
            r = conn.execute(sel).mappings().first()
            if not r:
                st.error(t("Username not found.", "Username not found."))
            elif check_password(password, r['password_hash']):
                st.session_state['user_id'] = r['id']
                st.session_state['username'] = r['username']
                st.experimental_rerun()
            else:
                st.error(t("Wrong password.", "Wrong password."))

    else:
        # Demo mode
        st.header(t("Demo Mode", "Demo Mode"))
        st.info(t("In demo mode, data is not saved.", "In demo mode, data is not saved."))
        f = st.file_uploader(t("Upload leaf/fruit/stem image", "Upload leaf/fruit/stem image"), type=["jpg","jpeg","png"])
        if f:
            st.image(f, use_container_width=True)
            st.success(t("Demo prediction: Healthy", "Demo prediction: Healthy"))

else:
    st.sidebar.header(f"{t('Welcome', 'Welcome')}, {st.session_state['username']}")
    menu = st.sidebar.selectbox(t("Menu", "Menu"), [t("🏠 Home", "🏠 Home"), t("🌱 Tracking", "🌱 Tracking"), t("📅 Schedule", "📅 Schedule"), t("📈 Prediction", "📈 Prediction"), t("🍎 Disease", "🍎 Disease"), t("📥 Download", "📥 Download"), t("🚪 Logout", "🚪 Logout")])

    user_id = st.session_state['user_id']

    if menu == t("🚪 Logout", "🚪 Logout"):
        st.session_state['user_id'] = None
        st.session_state['username'] = None
        st.experimental_rerun()

    elif menu == t("🏠 Home", "🏠 Home"):
        st.header(t("Dashboard Overview", "Dashboard Overview"))
        df = pd.read_sql(sa.select(measurements).where(measurements.c.user_id==user_id), conn)
        st.dataframe(df)

    elif menu == t("🌱 Tracking", "🌱 Tracking"):
        st.header(t("Seedling Tracking", "Seedling Tracking"))
        with st.expander(t("Add Measurement", "Add Measurement")):
            date = st.date_input(t("Date", "Date"), datetime.today())
            height = st.number_input(t("Height (cm)", "Height (cm)"), 0, 500, 50)
            leaves = st.number_input(t("Leaves", "Leaves"), 0, 1000, 10)
            notes = st.text_area(t("Notes", "Notes"))
            prune = st.checkbox(t("Prune needed?", "Prune needed?"))
            if st.button(t("Submit Measurement", "Submit Measurement")):
                conn.execute(measurements.insert().values(user_id=user_id, date=str(date), height=height, leaves=leaves, notes=notes, prune_needed=int(prune)))
                st.success(t("Measurement added", "Measurement added"))

    elif menu == t("📅 Schedule", "📅 Schedule"):
        st.header(t("Schedule", "Schedule"))
        df_s = pd.read_sql(sa.select(schedule).where(schedule.c.user_id==user_id), conn)
        st.dataframe(df_s)

    elif menu == t("📈 Prediction", "📈 Prediction"):
        st.header(t("Growth Prediction", "Growth Prediction"))
        df = pd.read_sql(sa.select(measurements).where(measurements.c.user_id==user_id), conn)
        if not df.empty:
            df['day'] = pd.to_datetime(df['date']).apply(lambda x: (x - pd.to_datetime(df['date'].min())).days)
            X = df['day'].values
            y = df['height'].values
            if len(X)>1:
                a = (y[-1]-y[0])/(X[-1]-X[0])
                b = y[0] - a*X[0]
                future_days = np.array([X[-1]+7*i for i in range(1,13)])
                preds = a*future_days + b
                future_dates = [pd.to_datetime(df['date'].max()) + timedelta(weeks=i) for i in range(1,13)]
                df_future = pd.DataFrame({'date':future_dates, 'predicted_height':preds})
                st.dataframe(df_future)
            else:
                st.info(t("Not enough data to predict", "Not enough data to predict"))
        else:
            st.info(t("No measurements available", "No measurements available"))

    elif menu == t("🍎 Disease", "🍎 Disease"):
        st.header(t("Disease Detection", "Disease Detection"))
        f = st.file_uploader(t("Upload leaf/fruit/stem image", "Upload leaf/fruit/stem image"), type=["jpg","jpeg","png"])
        if f:
            st.image(f, use_container_width=True)
            st.success(t("Prediction placeholder: Healthy", "Prediction placeholder: Healthy"))
            st.write(t("Name: Healthy", "Name: Healthy"))
            st.write(t("Description: No issues detected", "Description: No issues detected"))
            st.write(t("Treatment: Continue normal care", "Treatment: Continue normal care"))

    elif menu == t("📥 Download", "📥 Download"):
        st.header(t("Download Reports", "Download Reports"))
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
            df_meas = pd.read_sql(sa.select(measurements).where(measurements.c.user_id==user_id), conn)
            df_meas.to_excel(writer, sheet_name='measurements', index=False)
            df_sched = pd.read_sql(sa.select(schedule).where(schedule.c.user_id==user_id), conn)
            df_sched.to_excel(writer, sheet_name='schedule', index=False)
            writer.save()
        st.download_button(label=t("Download Excel", "Download Excel"), data=buffer.getvalue(), file_name="dashboard.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
