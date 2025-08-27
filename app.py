# ادامه کد کامل اپلیکیشن با تمامی بخش‌ها

# ---------- DISEASE ----------
    if menu == t("🍎 تشخیص بیماری","Disease"):
        st.header(t("تشخیص بیماری برگ","Leaf Disease Detection"))
        f = st.file_uploader(t("آپلود تصویر","Upload image"), type=["jpg","jpeg","png"])
        if f:
            st.image(f, use_container_width=True)
            if model is not None:
                img = Image.open(f).convert("RGB")
                img = img.resize(model.input_shape[1:3])
                arr = img_to_array(img)/255.0
                arr = np.expand_dims(arr, axis=0)
                preds = model.predict(arr)[0]
            else:
                preds = np.array([1.0, 0.0, 0.0])
            idx = int(np.argmax(preds))
            st.write(f"**{t('نتیجه','Result')}:** {disease_info[class_labels[idx]]['name']}")
            st.write(f"**{t('شدت بیماری (%)','Severity (%)')}:** {preds[idx]*100:.1f}%")
            st.write(f"**{t('توضیح','Description')}:** {disease_info[class_labels[idx]]['desc']}")
            st.write(f"**{t('درمان / راهنمایی','Treatment / Guidance')}:** {disease_info[class_labels[idx]]['treatment']}")

# ---------- TRACKING ----------
    if menu == t("🌱 ثبت و رصد","Tracking"):
        st.header(t("ثبت و رصد رشد نهال","Seedling Tracking"))
        with st.expander(t("➕ ثبت اندازه‌گیری جدید","➕ Add measurement")):
            date = st.date_input(t("تاریخ","Date"), value=datetime.today())
            height = st.number_input(t("ارتفاع (cm)","Height (cm)"), min_value=0.0, step=0.5)
            leaves = st.number_input(t("تعداد برگ‌ها","Leaves"), min_value=0, step=1)
            notes = st.text_area(t("توضیحات","Notes"))
            prune = st.checkbox(t("نیاز به هرس؟","Prune needed?"))
            if st.button(t("ثبت","Submit")):
                st.session_state['tree_data'] = pd.concat([st.session_state['tree_data'], pd.DataFrame([[date, height, leaves, notes, prune]], columns=['date','height','leaves','notes','prune'])], ignore_index=True)
                st.success(t("ثبت شد ✅","Added ✅"))
        if not st.session_state['tree_data'].empty:
            df = st.session_state['tree_data'].sort_values('date')
            st.dataframe(df)
            fig = px.line(df, x='date', y=['height','leaves'], labels={'value':t('مقدار','Value'),'variable':t('پارامتر','Parameter'),'date':t('تاریخ','Date')})
            st.plotly_chart(fig, use_container_width=True)

# ---------- SCHEDULE ----------
    if menu == t("📅 برنامه زمان‌بندی","Schedule"):
        st.header(t("برنامه زمان‌بندی","Schedule"))
        df_s = st.session_state['schedule']
        today = datetime.today().date()
        for i in df_s.index:
            df_s.at[i,'task_done'] = st.checkbox(f"{df_s.at[i,'date']} — {df_s.at[i,'task']}", value=df_s.at[i,'task_done'], key=f"sch{i}")
        st.dataframe(df_s)

# ---------- PREDICTION ----------
    if menu == t("📈 پیش‌بینی رشد","Prediction"):
        st.header(t("پیش‌بینی رشد","Growth Prediction"))
        df = st.session_state['tree_data']
        if df.empty:
            st.info(t("ابتدا اندازه‌گیری‌های رشد را ثبت کنید.","Add growth records first."))
        else:
            df = df.sort_values('date')
            df['days'] = (df['date'] - df['date'].min()).dt.days
            X = df['days'].values
            y = df['height'].values
            if len(X) < 2: f_lin = lambda z: y[-1]
            else: a = (y[-1]-y[0])/(X[-1]-X[0]); b = y[0]-a*X[0]; f_lin = lambda z: a*z+b
            future_days = np.array([(X.max() + 7*i) for i in range(1,13)])
            future_dates = [df['date'].max() + timedelta(weeks=i) for i in range(1,13)]
            preds = [f_lin(d) for d in future_days]
            df_future = pd.DataFrame({'date':future_dates, t('ارتفاع پیش‌بینی شده(cm)','Predicted Height (cm)'): preds})
            st.session_state['df_future'] = df_future
            st.dataframe(df_future)
            fig = px.line(df_future, x='date', y=df_future.columns[1], title=t("پیش‌بینی ارتفاع","Height forecast"))
            st.plotly_chart(fig, use_container_width=True)

# ---------- DOWNLOAD ----------
    if menu == t("📥 دانلود گزارش","Download"):
        st.header(t("دانلود گزارش","Download"))
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
            if not st.session_state['tree_data'].empty:
                st.session_state['tree_data'].to_excel(writer, sheet_name='growth', index=False)
            if not st.session_state['schedule'].empty:
                st.session_state['schedule'].to_excel(writer, sheet_name='schedule', index=False)
            if not st.session_state['df_future'].empty:
                st.session_state['df_future'].to_excel(writer, sheet_name='prediction', index=False)
        st.download_button(label=t("دانلود Excel داشبورد","Download Excel Dashboard"), data=buffer.getvalue(), file_name="apple_dashboard_full.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
