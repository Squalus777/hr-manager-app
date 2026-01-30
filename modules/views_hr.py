import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import time
import sqlite3
from datetime import datetime, date

from modules.database import get_connection, get_active_period_info, DB_FILE
from modules.utils import get_df_from_json, make_hashes

def render_hr_view():
    conn = get_connection()
    current_period, _ = get_active_period_info()
    
    menu = st.sidebar.radio("Izbornik", 
        ["📊 HR Dashboard", "🎯 Upravljanje Ciljevima", "🚀 Razvojni Planovi", "🗂️ Šifarnik & Korisnici", "⚙️ Postavke Razdoblja", "🛠️ Admin Panel", "📥 Export Podataka"])

    # --- 1. DASHBOARD ---
    if menu == "📊 HR Dashboard":
        st.header(f"📊 HR Analitika - {current_period}")
        
        # Učitavanje podataka
        df_evals = pd.read_sql_query("SELECT * FROM evaluations WHERE period=?", conn, params=(current_period,))
        df_master = pd.read_sql_query("SELECT * FROM employees_master", conn)
        df_idp = pd.read_sql_query("SELECT * FROM development_plans WHERE period=?", conn, params=(current_period,))
        
        # --- METRIKE VRH ---
        c1, c2, c3, c4 = st.columns(4)
        total_emps = len(df_master)
        
        # Izračun IDP statusa
        emps_with_idp = df_idp['kadrovski_broj'].nunique()
        idp_coverage = (emps_with_idp / total_emps * 100) if total_emps > 0 else 0
        
        c1.metric("Ukupno Zaposlenika", total_emps)
        c2.metric("Završene Procjene", len(df_evals[df_evals['status']=='Submitted']))
        c3.metric("Prosjek Ocjena", f"{df_evals['avg_performance'].mean():.2f}" if not df_evals.empty else "0.0")
        c4.metric("Pokrivenost IDP-om", f"{idp_coverage:.1f}%")
        
        st.markdown("---")
        
        # --- GRAFOVI RED 1 ---
        t1, t2, t3 = st.tabs(["9-Box Matrica", "Statusi po Odjelima", "IDP Status"])
        
        with t1:
            if not df_evals.empty:
                c_left, c_right = st.columns([3, 1])
                with c_left:
                    fig = px.scatter(df_evals, x="avg_performance", y="avg_potential", color="category", 
                                   hover_data=["ime_prezime", "manager_id"],
                                   range_x=[0.5, 5.5], range_y=[0.5, 5.5],
                                   title="Distribucija Talenata")
                    fig.add_hline(y=3.0, line_dash="dot"); fig.add_vline(x=3.0, line_dash="dot")
                    fig.add_hline(y=4.0, line_dash="dot"); fig.add_vline(x=4.0, line_dash="dot")
                    st.plotly_chart(fig, use_container_width=True)
                
                with c_right:
                    st.write("**Sažetak po Kategorijama**")
                    summary = df_evals['category'].value_counts().reset_index()
                    summary.columns = ['Kategorija', 'Broj']
                    st.dataframe(summary, hide_index=True, use_container_width=True)
            else:
                st.info("Nema podataka o procjenama.")

        with t2:
            # Spajamo master s evals da vidimo tko fali
            merged = pd.merge(df_master, df_evals[['kadrovski_broj', 'status']], on='kadrovski_broj', how='left')
            merged['status'] = merged['status'].fillna('Not Started')
            
            dept_stats = merged.groupby(['department', 'status']).size().reset_index(name='count')
            if not dept_stats.empty:
                fig2 = px.bar(dept_stats, x="department", y="count", color="status", title="Status Procesa po Odjelima", barmode='stack')
                st.plotly_chart(fig2, use_container_width=True)
        
        with t3:
            # Pie Chart IDP
            labels = ['Imaju IDP', 'Nemaju IDP']
            values = [emps_with_idp, total_emps - emps_with_idp]
            fig_pie = go.Figure(data=[go.Pie(labels=labels, values=values, hole=.3)])
            fig_pie.update_layout(title_text="Pokrivenost Razvojnim Planovima")
            st.plotly_chart(fig_pie, use_container_width=True)

        # --- GRAFOVI RED 2 (NAPREDNA ANALITIKA) ---
        st.markdown("### 📈 Analiza Učinka")
        
        if not df_evals.empty:
            # Odstupanje od prosjeka po odjelima
            global_avg = df_evals['avg_performance'].mean()
            dept_perf = df_evals.groupby('department')['avg_performance'].mean().reset_index()
            dept_perf['gap'] = dept_perf['avg_performance'] - global_avg
            dept_perf['color'] = dept_perf['gap'].apply(lambda x: 'Iznad prosjeka' if x >= 0 else 'Ispod prosjeka')
            
            fig_gap = px.bar(dept_perf.sort_values('gap'), x='gap', y='department', orientation='h', 
                           color='color', title="Odstupanje Učinka po Odjelima (u odnosu na tvrtku)",
                           color_discrete_map={'Iznad prosjeka': 'green', 'Ispod prosjeka': 'red'})
            st.plotly_chart(fig_gap, use_container_width=True)
        
        # --- GLOBAL SEARCH ---
        st.markdown("---")
        st.subheader("🔍 Pretraga Povijesti Zaposlenika")
        st.info("Ovdje možete vidjeti povijesni razvoj (Snail Trail) za bilo kojeg zaposlenika kroz sve periode.")
        search_all = st.selectbox("Odaberi zaposlenika:", ["Odaberi..."] + df_master['ime_prezime'].tolist())
        
        if search_all != "Odaberi...":
             kid = df_master[df_master['ime_prezime'] == search_all]['kadrovski_broj'].values[0]
             h_graph = pd.read_sql_query("SELECT period, avg_performance, avg_potential FROM evaluations WHERE kadrovski_broj=? ORDER BY period", conn, params=(kid,))
             if not h_graph.empty:
                 fig_line = px.line(h_graph, x='avg_performance', y='avg_potential', markers=True, text='period', title=f"Razvoj zaposlenika: {search_all}")
                 fig_line.update_layout(xaxis_range=[0.5, 5.5], yaxis_range=[0.5, 5.5])
                 # Dodajemo linije matrice
                 fig_line.add_hline(y=3.0, line_dash="dot", line_color="grey"); fig_line.add_vline(x=3.0, line_dash="dot", line_color="grey")
                 fig_line.add_hline(y=4.0, line_dash="dot", line_color="grey"); fig_line.add_vline(x=4.0, line_dash="dot", line_color="grey")
                 st.plotly_chart(fig_line, use_container_width=True)
             else:
                 st.warning("Nema povijesnih podataka za odabranog zaposlenika.")

    # --- 2. CILJEVI ---
    elif menu == "🎯 Upravljanje Ciljevima":
        st.header(f"🎯 Pregled Ciljeva i KPI")
        m = pd.read_sql_query("SELECT * FROM employees_master", conn)
        dept_list = sorted(m['department'].dropna().unique().tolist())
        d = st.selectbox("Filtriraj po odjelu:", ["Svi"] + dept_list)
        
        q_l = "SELECT DISTINCT g.kadrovski_broj, m.ime_prezime FROM goals g JOIN employees_master m ON g.kadrovski_broj=m.kadrovski_broj WHERE g.period=?"
        params = [current_period]
        if d != "Svi": 
            q_l += " AND m.department=?"
            params.append(d)
            
        emps = pd.read_sql_query(q_l, conn, params=params)
        
        if emps.empty:
            st.info("Nema ciljeva za odabrani kriterij.")
        
        for _, r in emps.iterrows():
            eid = r['kadrovski_broj']
            goals = pd.read_sql_query("SELECT * FROM goals WHERE kadrovski_broj=? AND period=?", conn, params=(eid, current_period))
            
            with st.expander(f"👤 {r['ime_prezime']} (Ciljeva: {len(goals)})"):
                for _, g in goals.iterrows():
                    st.markdown(f"#### 🚩 {g['title']} ({g['weight']}%)")
                    st.caption(f"Status: **{g['status']}** | Rok: {g['deadline']}")
                    st.write(f"Opis: {g['description']}")
                    
                    kpis = pd.read_sql_query("SELECT description as 'KPI', weight as 'Težina', progress as 'Ostvarenje %', deadline as 'Rok' FROM goal_kpis WHERE goal_id=?", conn, params=(g['id'],))
                    if not kpis.empty:
                        st.dataframe(kpis, hide_index=True, use_container_width=True)
                    else:
                        st.caption("Nema definiranih KPI-jeva.")
                    st.divider()

    # --- 3. IDP PREGLED ---
    elif menu == "🚀 Razvojni Planovi":
        st.header("🚀 Pregled IDP-a po Odjelima")
        m = pd.read_sql_query("SELECT * FROM employees_master", conn)
        
        dept_list = sorted(m['department'].dropna().unique().tolist())
        d = st.selectbox("Odaberi odjel:", ["Svi"] + dept_list)
        
        filtered_emps = m if d == "Svi" else m[m['department'] == d]
        
        st.markdown(f"Prikazano: **{len(filtered_emps)}** zaposlenika")
        st.markdown("---")

        for _, emp in filtered_emps.iterrows():
            kid = emp['kadrovski_broj']
            idp = pd.read_sql_query("SELECT * FROM development_plans WHERE kadrovski_broj=? AND period=?", conn, params=(kid, current_period))
            
            row_idp = None
            if not idp.empty:
                status_icon = "✅"
                row_idp = idp.iloc[0]
                strengths = row_idp.get('strengths', '-')
                areas = row_idp.get('areas_improve', '-')
                goal = row_idp.get('career_goal', '-')
                support = row_idp.get('support_needed', '-')
                notes = row_idp.get('support_notes', '-')
            else:
                status_icon = "⚠️"
            
            with st.expander(f"{status_icon} {emp['ime_prezime']} | {emp['radno_mjesto']}"):
                if row_idp is not None:
                    st.caption(f"Voditelj: {row_idp['manager_id']} | Kreirano: {current_period}")
                    st.markdown(f"🎯 **Cilj:** {goal}")
                    st.write(f"💪 **Snage:** {strengths}")
                    st.write(f"📈 **Razvoj:** {areas}")
                    st.markdown("---")
                    
                    st.markdown("**A) 70% ISKUSTVO**")
                    df70 = get_df_from_json(row_idp['json_70'], ["Što razviti?", "Aktivnost", "Rok", "Dokaz"])
                    if not df70.empty: st.dataframe(df70, use_container_width=True, hide_index=True)

                    st.markdown("**B) 20% FEEDBACK**")
                    df20 = get_df_from_json(row_idp['json_20'], ["Što razviti?", "Aktivnost", "Rok"])
                    if not df20.empty: st.dataframe(df20, use_container_width=True, hide_index=True)

                    st.markdown("**C) 10% EDUKACIJA**")
                    df10 = get_df_from_json(row_idp['json_10'], ["Edukacija", "Trošak", "Rok"])
                    if not df10.empty: st.dataframe(df10, use_container_width=True, hide_index=True)
                else:
                    st.warning("Nema IDP-a.")

    # --- 4. ŠIFARNIK & KORISNICI ---
    elif menu == "🗂️ Šifarnik & Korisnici":
        st.header("🗂️ Matični Podaci i Korisnički Računi")
        
        t1, t2, t3 = st.tabs(["👥 Pregled i Lozinke", "✍️ Ručni Unos", "📥 Import Excel"])
        
        # TAB 1: PREGLED
        with t1:
            st.info("Ovdje možete vidjeti tko ima login pristup i resetirati lozinke.")
            df_master = pd.read_sql_query("SELECT * FROM employees_master", conn)
            df_users = pd.read_sql_query("SELECT username, role FROM users", conn)
            df_full = pd.merge(df_master, df_users, left_on='kadrovski_broj', right_on='username', how='left')
            df_full['Ima Login'] = df_full['username'].apply(lambda x: '✅ DA' if pd.notnull(x) else '❌ NE')
            
            st.dataframe(df_full[['kadrovski_broj', 'ime_prezime', 'radno_mjesto', 'department', 'Ima Login', 'role']], use_container_width=True)
            
            st.markdown("---")
            st.subheader("🔐 Upravljanje Pristupom")
            selected_emp_str = st.selectbox("Odaberi zaposlenika za akciju:", df_full.apply(lambda x: f"{x['ime_prezime']} ({x['kadrovski_broj']}) - {x['Ima Login']}", axis=1))
            
            if selected_emp_str:
                sel_id = selected_emp_str.split("(")[1].split(")")[0]
                sel_name = selected_emp_str.split("(")[0]
                has_login = "✅ DA" in selected_emp_str
                
                c_act1, c_act2 = st.columns(2)
                with c_act1:
                    if not has_login:
                        st.warning(f"👤 {sel_name} nema korisnički račun.")
                        if st.button("➕ Kreiraj Login (Pass: user123)"):
                            try:
                                with sqlite3.connect(DB_FILE) as u_conn:
                                    def_pass = make_hashes("user123")
                                    dept = df_master[df_master['kadrovski_broj']==sel_id]['department'].values[0]
                                    u_conn.execute("INSERT INTO users (username, password, role, department) VALUES (?,?,?,?)", (sel_id, def_pass, 'Employee', dept))
                                    u_conn.commit()
                                st.success("Kreirano!"); time.sleep(1); st.rerun()
                            except Exception as e: st.error(f"Greška: {e}")
                    else: st.success(f"👤 {sel_name} već ima račun.")

                with c_act2:
                    if has_login:
                        st.write("🔑 Zaboravljena lozinka?")
                        new_p = st.text_input("Nova lozinka:", key="new_p_hr")
                        if st.button("Resetiraj Lozinku"):
                            if new_p:
                                try:
                                    with sqlite3.connect(DB_FILE) as u_conn:
                                        u_conn.execute("UPDATE users SET password=? WHERE username=?", (make_hashes(new_p), sel_id))
                                        u_conn.commit()
                                    st.success("Lozinka promijenjena!")
                                except Exception as e: st.error(f"Greška: {e}")
                            else: st.warning("Unesite novu lozinku.")

        # TAB 2: RUČNI UNOS
        with t2:
            try: mgrs = pd.read_sql_query("SELECT username FROM users WHERE role='Manager'", conn)['username'].tolist()
            except: mgrs = []
            with st.form("hr_add"):
                i = st.text_input("ID"); n = st.text_input("Ime"); r = st.text_input("Pozicija"); d = st.text_input("Odjel"); m = st.selectbox("Manager", [""]+mgrs)
                # Ovdje dodajemo i rolu
                new_role_hr = st.selectbox("Rola:", ["Employee", "Manager", "HR"])
                
                if st.form_submit_button("Dodaj"): 
                    try: 
                        clean_id = str(i).strip()
                        conn.cursor().execute("INSERT INTO employees_master VALUES (?,?,?,?,?)", (clean_id,n,r,d,m))
                        # Uvijek kreiramo login
                        conn.cursor().execute("INSERT OR IGNORE INTO users (username, password, role, department) VALUES (?,?,?,?)", 
                                             (clean_id, make_hashes("user123"), new_role_hr, d))
                        conn.commit(); st.success(f"Dodano! Login: {clean_id}/user123 ({new_role_hr})")
                    except Exception as e: st.error(f"Greška: {e}")
        
        # TAB 3: IMPORT (POPRAVLJENA LOGIKA ZA 'NAN')
        with t3:
            st.markdown("### Import Zaposlenika")
            st.info("Format: ID | Ime | Pozicija | Odjel | ManagerID | **Rola (opcionalno)**")
            auto_create = st.checkbox("✅ Automatski kreiraj Login za sve nove (Pass: user123)", value=True)
            f = st.file_uploader("Excel", type="xlsx")
            if f and st.button("Importiraj"):
                try:
                    df = pd.read_excel(f, header=None)
                    c = conn.cursor()
                    cnt, usr_cnt = 0, 0
                    def_pass = make_hashes("user123")
                    for _, r in df.iterrows():
                        first_col = str(r[0]).strip().lower()
                        if not first_col or first_col in ['id', 'kadrovski', 'kadrovski broj', 'nan']: continue
                        
                        kid = str(r[0]).strip()
                        
                        # --- POPRAVAK ZA 'nan' ---
                        raw_mgr = r[4] if len(r)>4 else None
                        val4 = str(raw_mgr).strip()
                        # Ako je 'nan', 'None' ili prazno -> pretvori u prazan string
                        if val4.lower() == 'nan' or val4 == 'none' or pd.isna(raw_mgr): 
                            val4 = ""

                        # Validacija role
                        val5 = str(r[5]).strip() if len(r)>5 else "Employee"
                        if val5 not in ['HR', 'Manager', 'Employee']: val5 = 'Employee'

                        # Insert u Master
                        c.execute("INSERT OR REPLACE INTO employees_master VALUES (?,?,?,?,?)", (kid, str(r[1]), str(r[2]), str(r[3]), val4))
                        cnt += 1
                        
                        if auto_create:
                            # Provjera postoji li user
                            c.execute("SELECT count(*) FROM users WHERE username=?", (kid,))
                            if c.fetchone()[0] == 0:
                                c.execute("INSERT INTO users (username, password, role, department) VALUES (?,?,?,?)", 
                                         (kid, def_pass, val5, str(r[3])))
                                usr_cnt += 1
                    conn.commit()
                    st.success(f"Uvezeno {cnt} ljudi. Kreirano {usr_cnt} novih loginova.")
                except Exception as e: st.error(f"Greška: {e}")

    # --- 5. POSTAVKE RAZDOBLJA ---
    elif menu == "⚙️ Postavke Razdoblja":
        st.header("🗓️ Postavke Razdoblja")
        t1, t2, t3 = st.tabs(["1. KREIRAJ NOVO", "2. UPRAVLJANJE", "3. UREDI ROK"])
        with t1:
            with st.form("np"):
                n = st.text_input("Naziv"); d = st.date_input("Rok")
                if st.form_submit_button("Kreiraj"): 
                    try: 
                        conn.execute("INSERT INTO periods VALUES (?,?)", (n, str(d)))
                        conn.commit()
                        st.success("Kreirano")
                    except: st.error("Već postoji.")
        with t2:
            ps = [x[0] for x in conn.execute("SELECT period_name FROM periods").fetchall()]
            if ps:
                s = st.selectbox("Aktiviraj:", ps, index=ps.index(current_period) if current_period in ps else 0)
                if st.button("Postavi AKTIVNO"): 
                    conn.execute("UPDATE app_settings SET setting_value=? WHERE setting_key='active_period'", (s,))
                    conn.commit()
                    st.rerun()
        with t3:
            if current_period:
                curr = conn.execute("SELECT deadline FROM periods WHERE period_name=?", (current_period,)).fetchone()
                nd = st.date_input("Novi rok", value=datetime.strptime(curr[0], "%Y-%m-%d").date() if curr else date.today())
                if st.button("Ažuriraj"): 
                    conn.execute("UPDATE periods SET deadline=? WHERE period_name=?", (str(nd), current_period))
                    conn.commit()
                    st.success("OK")

    elif menu == "🛠️ Admin Panel":
        try: from modules.views_admin import render_admin_view; render_admin_view()
        except: st.error("Admin modul nedostaje.")

    elif menu == "📥 Export Podataka":
        st.header("Export")
        if st.button("Excel"):
            import io
            try:
                o = io.BytesIO()
                with pd.ExcelWriter(o, engine='xlsxwriter') as w:
                    for t in ["evaluations", "goals", "development_plans", "employees_master", "users"]: 
                        pd.read_sql_query(f"SELECT * FROM {t}", conn).to_excel(w, sheet_name=t)
                st.download_button("Download", o.getvalue(), "export.xlsx")
            except: st.error("Greška exporta.")