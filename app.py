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

# ---------- Database ----------
DB_FILE = "users_data.db"
engine = sa.create_engine(f"sqlite:///{DB_FILE}", connect_args={"check_same_thread": False})
meta = MetaData()

# Users table
users_table = Table('users', meta,
                    Column('id', Integer, primary_key=True),
                    Column('username', String, unique=True, nullable=False),
                    Column('password_hash', String, nullable=False))

# Measurements table
measurements = Table('measurements', meta,
                     Column('id', Integer, primary_key=True),
                     Column('user_id', Integer, ForeignKey('users.id')),
                     Column('date', String),
                     Column('height', Integer),
                     Column('leaves', Integer),
                     Column('notes', String),
                     Column('prune_needed', Integer))

# Schedule table
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

# ---------- Helper Functions ----------
def hash_password(password):
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def check_password(password, hashed):
    return bcrypt.checkpw(password.encode(), hashed.encode())

# ---------- Auth ----------
if st.session_state['user_id'] is None:
    st.sidebar.header("Authentication")
    mode = st.sidebar.radio("Mode", ["Login", "Sign Up", "Demo"])

    if mode == "Sign Up":
        st.header("Sign Up")
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        if st.button("Register"):
            if not username or not password:
                st.error("Please provide username and password")
            else:
                sel = sa.select(users_table).where(users_table.c.username==username)
                r = conn.execute(sel).first()
                if r:
                    st.error("Username already exists")
                else:
                    hashed = hash_password(password)
                    conn.execute(users_table.insert().values(username=username, password_hash=hashed))
                    st.success("Registered. Please login.")

    elif mode == "Login":
        st.header("Login")
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        if st.button("Login"):
            sel = sa.select(users_table).where(users_table.c.username==username)
            r = conn.execute(sel).first()
            if not r:
                st.error("Username not found")
            elif check_password(password, r['password_hash']):
                st.session_state['user_id'] = r['id']
                st.session_state['username'] = r['username']
                st.experimental_rerun()
            else:
                st.error("Incorrect password")

    else:
        # Demo mode
        st.header("Demo Mode")
        st.info("Data will not be saved permanently")
        f = st.file_uploader("Upload leaf/fruit/stem image", type=["jpg","jpeg","png"])
        if f:
            st.image(f, use_container_width=True)
            st.success("Demo prediction: Healthy")

else:
    st.sidebar.header(f"Welcome, {st.session_state['username']}")
    menu = st.sidebar.selectbox("Menu", ["🏠 Home", "🌱 Tracking", "📅 Schedule", "📈 Prediction", "🍎 Disease", "📥 Download", "🚪 Logout"])

    user_id = st.session_state['user_id']

    # ---------- Logout ----------
    if menu == "🚪 Logout":
        st.session_state['user_id'] = None
        st.session_state['username'] = None
        st.experimental_rerun()

    # ---------- Home ----------
    if menu == "🏠 Home":
        st.header("Dashboard Overview")
        df = pd.read_sql(sa.select(measurements).where(measurements.c.user_id==user_id), conn)
        st.dataframe(df)

    # ---------- Tracking ----------
    elif menu == "🌱 Tracking":
        st.header("Seedling Tracking")
        with st.expander("Add Measurement"):
            date = st.date_input("Date", datetime.today())
            height = st.number_input("Height (cm)", 0, 500, 50)
            leaves = st.number_input("Leaves", 0, 1000, 10)
            notes = st.text_area("Notes")
            prune = st.checkbox("Prune needed?")
            if st.button("Submit Measurement"):
                conn.execute(measurements.insert().values(user_id=user_id, date=str(date), height=height, leaves=leaves, notes=notes, prune_needed=int(prune)))
                st.success("Measurement added")

    # ---------- Schedule ----------
    elif menu == "📅 Schedule":
        st.header("Schedule")
        df_s = pd.read_sql(sa.select(schedule).where(schedule.c.user_id==user_id), conn)
        st.dataframe(df_s)

    # ---------- Prediction ----------
    elif menu == "📈 Prediction":
        st.header("Growth Prediction")
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
                st.info("Not enough data to predict")
        else:
            st.info("No measurements available")

    # ---------- Disease ----------
    elif menu == "🍎 Disease":
        st.header("Disease Detection")
        f = st.file_uploader("Upload leaf/fruit/stem image", type=["jpg","jpeg","png"])
        if f:
            st.image(f, use_container_width=True)
            st.success("Prediction placeholder: Healthy")
            st.write("Name: Healthy")
            st.write("Description: No issues detected")
            st.write("Treatment: Continue normal care")

    # ---------- Download ----------
    elif menu == "📥 Download":
        st.header("Download Reports")
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
            df_meas = pd.read_sql(sa.select(measurements).where(measurements.c.user_id==user_id), conn)
            df_meas.to_excel(writer, sheet_name='measurements', index=False)
            df_sched = pd.read_sql(sa.select(schedule).where(schedule.c.user_id==user_id), conn)
            df_sched.to_excel(writer, sheet_name='schedule', index=False)
            writer.save()
        st.download_button(label="Download Excel", data=buffer.getvalue(), file_name="dashboard.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
