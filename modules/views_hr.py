import streamlit as st
import pandas as pd
import plotly.express as px
import time
from datetime import datetime, date

from modules.database import get_connection, get_active_period_info
from modules.utils import get_df_from_json

def render_hr_view():
    conn = get_connection()
    current_period, _ = get_active_period_info()
    
    menu = st.sidebar.radio("Izbornik", 
        ["📊 HR Dashboard", "🎯 Upravljanje Ciljevima", "🚀 Razvojni Planovi", "🗂️ Šifarnik Zaposlenika", "⚙️ Postavke Razdoblja", "🛠️ Admin Panel", "📥 Export Podataka"])

    # --- 1. DASHBOARD ---
    if menu == "📊 HR Dashboard":
        st.header("📊 HR Analitika")
        df = pd.read_sql_query(f"SELECT * FROM evaluations WHERE period='{current_period}'", conn)
        m = pd.read_sql_query("SELECT * FROM employees_master", conn)
        
        # SEARCH GLOBAL
        st.markdown("### 🔍 Globalna Povijest Zaposlenika")
        search_all = st.selectbox("Pretraži SVE zaposlenike:", ["Odaberi..."] + m['ime_prezime'].tolist())
        
        if search_all != "Odaberi...":
            kid = m[m['ime_prezime'] == search_all]['kadrovski_broj'].values[0]
            
            # 1. Povijest grafa (Snail Trail)
            h_graph = pd.read_sql_query("SELECT period, avg_performance, avg_potential FROM evaluations WHERE kadrovski_broj=? ORDER BY period", conn, params=(kid,))
            if not h_graph.empty:
                fig = px.line(h_graph, x='avg_performance', y='avg_potential', markers=True, text='period', title="Kretanje kroz 9-Box matricu", range_x=[0.5,5.5], range_y=[0.5,5.5])
                fig.add_hline(y=3.0, line_dash="dot"); fig.add_vline(x=3.0, line_dash="dot"); fig.add_hline(y=4.0, line_dash="dot"); fig.add_vline(x=4.0, line_dash="dot")
                st.plotly_chart(fig, use_container_width=True)

            # 2. Povijest IDP-ova
            st.markdown("#### 📜 Povijest Razvojnih Planova")
            hist_idp_full = pd.read_sql_query("SELECT * FROM development_plans WHERE kadrovski_broj=? ORDER BY period DESC", conn, params=(kid,))
            
            if not hist_idp_full.empty:
                for _, row_idp in hist_idp_full.iterrows():
                    with st.expander(f"📅 {row_idp['period']} | Voditelj: {row_idp['manager_id']}"):
                        st.markdown(f"**Cilj:** {row_idp['career_goal']}")
                        st.markdown(f"**Snage:** {row_idp['strengths']}")
                        st.markdown(f"**Razvoj:** {row_idp['areas_improve']}")
                        st.markdown("---")
                        st.caption("Plan 70-20-10:")
                        st.table(get_df_from_json(row_idp['json_70'], ["Aktivnost", "Rok", "Dokaz"]))
                        st.table(get_df_from_json(row_idp['json_20'], ["Aktivnost", "Rok"]))
                        st.table(get_df_from_json(row_idp['json_10'], ["Edukacija", "Trošak"]))
                        st.markdown(f"**Podrška:** {row_idp['support_needed']}")
            else:
                st.info("Nema povijesti IDP-a.")
        
        st.markdown("---")
        
        # FILTERI
        c1, c2 = st.columns(2)
        dept = c1.selectbox("Odjel:", ["Svi"] + sorted(m['department'].dropna().unique().tolist()))
        if dept != "Svi": df = df[df['department'] == dept]

        t1, t2, t3 = st.tabs(["Pregled", "Status po Managerima", "Grafovi"])
        
        with t1:
            if not df.empty:
                c1, c2, c3 = st.columns(3)
                c1.metric("Ukupno", len(df)); c2.metric("Prosjek", f"{df['avg_performance'].mean():.2f}"); c3.metric("Top Talenti", len(df[df['category'].str.contains("1.")]))
                fig = px.scatter(df, x="avg_performance", y="avg_potential", color="category", hover_data=["ime_prezime"], range_x=[0.5,5.5], range_y=[0.5,5.5], title="9-Box Matrica")
                fig.add_hline(y=3.0, line_dash="dot"); fig.add_vline(x=3.0, line_dash="dot"); fig.add_hline(y=4.0, line_dash="dot"); fig.add_vline(x=4.0, line_dash="dot")
                st.plotly_chart(fig, use_container_width=True)
            else: st.info("Nema podataka.")
        
        with t2:
            st.subheader("Status po Managerima")
            q = """SELECT m.manager_id, COUNT(m.kadrovski_broj) as total_team, COUNT(e.id) as completed_evals 
                   FROM employees_master m LEFT JOIN evaluations e ON m.kadrovski_broj = e.kadrovski_broj AND e.period = ? 
                   GROUP BY m.manager_id"""
            s = pd.read_sql_query(q, conn, params=(current_period,))
            s['completed_evals'] = pd.to_numeric(s['completed_evals'])
            s['total_team'] = pd.to_numeric(s['total_team'])
            s['% Završeno'] = (s['completed_evals'] / s['total_team'] * 100).fillna(0).astype(float).round(1)
            st.dataframe(s, use_container_width=True)
            
        with t3:
            st.markdown("### Usporedba Odjela")
            dept_stats = df.groupby('department')[['avg_performance', 'avg_potential']].mean().reset_index()
            if not dept_stats.empty:
                fig_bar = px.bar(dept_stats, x='department', y=['avg_performance', 'avg_potential'], barmode='group')
                st.plotly_chart(fig_bar, use_container_width=True)
            st.markdown("### Kvartalni Trendovi")
            trend_data = pd.read_sql_query("SELECT period, avg(avg_performance) as perf, avg(avg_potential) as pot FROM evaluations GROUP BY period ORDER BY period", conn)
            if not trend_data.empty:
                fig_trend = px.line(trend_data, x='period', y=['perf', 'pot'], markers=True)
                st.plotly_chart(fig_trend, use_container_width=True)

    # --- 2. CILJEVI ---
    elif menu == "🎯 Upravljanje Ciljevima":
        st.header(f"🎯 Pregled Ciljeva")
        m = pd.read_sql_query("SELECT * FROM employees_master", conn)
        d = st.selectbox("Filtriraj po odjelu:", ["Svi"] + sorted(m['department'].dropna().unique().tolist()))
        q_l = "SELECT DISTINCT g.kadrovski_broj, m.ime_prezime FROM goals g JOIN employees_master m ON g.kadrovski_broj=m.kadrovski_broj WHERE g.period=?"
        params = [current_period]
        if d != "Svi": q_l += " AND m.department=?"; params.append(d)
        emps = pd.read_sql_query(q_l, conn, params=params)
        for _, r in emps.iterrows():
            eid = r['kadrovski_broj']
            goals = pd.read_sql_query("SELECT * FROM goals WHERE kadrovski_broj=? AND period=?", conn, params=(eid, current_period))
            with st.expander(f"👤 {r['ime_prezime']}"):
                for _, g in goals.iterrows():
                    st.write(f"**{g['title']}** ({g['weight']}%) - {g['status']}")

    # --- 3. IDP PREGLED (POBOLJŠANI DETALJNI PRIKAZ) ---
    elif menu == "🚀 Razvojni Planovi":
        st.header("🚀 Pregled IDP-a po Odjelima")
        m = pd.read_sql_query("SELECT * FROM employees_master", conn)
        
        # Filter odjela
        d = st.selectbox("Odaberi odjel:", ["Svi"] + sorted(m['department'].dropna().unique().tolist()))
        
        # Filtriraj zaposlenike
        filtered_emps = m if d == "Svi" else m[m['department'] == d]
        
        st.markdown(f"Prikazano: **{len(filtered_emps)}** zaposlenika")
        st.markdown("---")

        for _, emp in filtered_emps.iterrows():
            kid = emp['kadrovski_broj']
            idp = pd.read_sql_query("SELECT * FROM development_plans WHERE kadrovski_broj=? AND period=?", conn, params=(kid, current_period))
            
            # Status logika i podaci
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
            
            # GLAVNI EXPANDER
            with st.expander(f"{status_icon} {emp['ime_prezime']} | {emp['radno_mjesto']}"):
                if not idp.empty:
                    st.caption(f"Voditelj: {row_idp['manager_id']} | Kreirano: {current_period}")
                    
                    st.markdown("### 1. Dijagnoza i Cilj")
                    st.info(f"🎯 **Karijerni cilj:** {goal}")
                    
                    c1, c2 = st.columns(2)
                    with c1:
                        st.markdown("**💪 Ključne Snage:**")
                        st.write(strengths)
                    with c2:
                        st.markdown("**📈 Područja za razvoj:**")
                        st.write(areas)
                    
                    st.markdown("---")
                    st.markdown("### 2. Plan Aktivnosti (70-20-10)")
                    
                    st.markdown("**A) 70% ISKUSTVO (On-the-job)**")
                    df70 = get_df_from_json(row_idp['json_70'], ["Što razviti?", "Aktivnost", "Rok", "Dokaz"])
                    if not df70.empty: st.dataframe(df70, use_container_width=True, hide_index=True)
                    else: st.caption("Nema unosa.")

                    st.markdown("**B) 20% UČENJE OD DRUGIH (Feedback/Mentoring)**")
                    df20 = get_df_from_json(row_idp['json_20'], ["Što razviti?", "Aktivnost", "Rok"])
                    if not df20.empty: st.dataframe(df20, use_container_width=True, hide_index=True)
                    else: st.caption("Nema unosa.")

                    st.markdown("**C) 10% EDUKACIJA (Tečajevi/Literatura)**")
                    df10 = get_df_from_json(row_idp['json_10'], ["Edukacija", "Trošak", "Rok"])
                    if not df10.empty: st.dataframe(df10, use_container_width=True, hide_index=True)
                    else: st.caption("Nema unosa.")
                    
                    st.markdown("---")
                    st.markdown("### 3. Podrška")
                    st.write(f"**Potrebna podrška:** {support}")
                    st.write(f"**Napomene:** {notes}")
                    
                else:
                    st.warning(f"Zaposlenik {emp['ime_prezime']} nema definiran IDP za period {current_period}.")
                    st.caption("Kontaktirajte voditelja (" + emp['manager_id'] + ") da ispuni plan.")

    # --- 4. ŠIFARNIK ---
    elif menu == "🗂️ Šifarnik Zaposlenika":
        st.header("🗂️ Šifarnik")
        t1, t2, t3 = st.tabs(["Pregled", "Ručni Unos", "Import Excel"])
        mgrs = pd.read_sql_query("SELECT username FROM users WHERE role='Manager'", conn)['username'].tolist()
        with t1:
            df = pd.read_sql_query("SELECT * FROM employees_master", conn)
            ed = st.data_editor(df, key="sf_e", num_rows="dynamic", column_config={"kadrovski_broj": st.column_config.TextColumn(disabled=True), "manager_id": st.column_config.SelectboxColumn(options=mgrs)})
            if st.button("Spremi promjene"):
                c = conn.cursor()
                for _, r in ed.iterrows(): c.execute("UPDATE employees_master SET ime_prezime=?, radno_mjesto=?, department=?, manager_id=? WHERE kadrovski_broj=?", (r['ime_prezime'], r['radno_mjesto'], r['department'], r['manager_id'], r['kadrovski_broj']))
                conn.commit(); st.success("Spremljeno!")
        with t2:
            with st.form("hr_add"):
                i = st.text_input("ID"); n = st.text_input("Ime"); r = st.text_input("Pozicija"); d = st.text_input("Odjel"); m = st.selectbox("Manager", [""]+mgrs)
                if st.form_submit_button("Dodaj"): 
                    try: conn.cursor().execute("INSERT INTO employees_master VALUES (?,?,?,?,?)", (i,n,r,d,m)); conn.commit(); st.success("OK")
                    except: st.error("Greška")
        with t3:
            f = st.file_uploader("Excel", type="xlsx")
            if f and st.button("Import"):
                df = pd.read_excel(f)
                c = conn.cursor()
                for _, r in df.iterrows(): c.execute("INSERT OR REPLACE INTO employees_master VALUES (?,?,?,?,?)", (str(r[0]), str(r[1]), str(r[2]), str(r[3]), str(r[4]) if len(r)>4 else None))
                conn.commit(); st.success("OK")

    elif menu == "⚙️ Postavke Razdoblja":
        st.header("🗓️ Postavke Razdoblja")
        t1, t2, t3 = st.tabs(["1. KREIRAJ NOVO", "2. UPRAVLJANJE", "3. UREDI ROK"])
        with t1:
            with st.form("np"):
                n = st.text_input("Naziv"); d = st.date_input("Rok")
                if st.form_submit_button("Kreiraj"): conn.cursor().execute("INSERT INTO periods VALUES (?,?)", (n, str(d))); conn.commit(); st.success("Kreirano")
        with t2:
            ps = [x[0] for x in conn.cursor().execute("SELECT period_name FROM periods").fetchall()]
            if ps:
                s = st.selectbox("Aktiviraj:", ps, index=ps.index(current_period) if current_period in ps else 0)
                if st.button("Postavi kao AKTIVNO"): conn.cursor().execute("UPDATE app_settings SET setting_value=? WHERE setting_key='active_period'", (s,)); conn.commit(); st.rerun()
        with t3:
            if current_period:
                curr_dl = conn.cursor().execute("SELECT deadline FROM periods WHERE period_name=?", (current_period,)).fetchone()
                nd = st.date_input("Novi rok za " + current_period, value=datetime.strptime(curr_dl[0], "%Y-%m-%d").date() if curr_dl else date.today())
                if st.button("Ažuriraj Rok"): conn.cursor().execute("UPDATE periods SET deadline=? WHERE period_name=?", (str(nd), current_period)); conn.commit(); st.success("Ažurirano!")

    elif menu == "🛠️ Admin Panel":
        from modules.views_admin import render_admin_view
        render_admin_view()

    elif menu == "📥 Export Podataka":
        st.header("Export")
        if st.button("Excel"):
            import io
            o = io.BytesIO()
            with pd.ExcelWriter(o, engine='xlsxwriter') as w:
                for t in ["evaluations", "goals", "development_plans", "employees_master"]: pd.read_sql_query(f"SELECT * FROM {t}", conn).to_excel(w, sheet_name=t)
            st.download_button("Download", o.getvalue(), "export.xlsx")