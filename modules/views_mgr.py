import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import time
import sqlite3
from datetime import datetime, date
import streamlit.components.v1 as components

# Importamo putanju do baze
from modules.database import get_connection, get_active_period_info, DB_FILE
from modules.utils import (
    METRICS, calculate_category, render_metric_input, 
    table_to_json_string, get_df_from_json
)

# ------------------------------------------------------------------
# GLAVNI RENDER VIEW
# ------------------------------------------------------------------
def render_manager_view():
    # 1. ČITANJE PODATAKA (Koristimo glavnu konekciju samo za čitanje)
    conn = sqlite3.connect(DB_FILE)
    current_period, _ = get_active_period_info()
    
    # Izbornik
    menu = st.sidebar.radio("Izbornik", ["📊 Dashboard", "🎯 Moji Ciljevi", "📝 Unos Procjena", "🚀 Razvojni Planovi (IDP)"])

    # --- AUTOMATSKO ZATVARANJE PDF-a ---
    if 'last_active_menu' not in st.session_state:
        st.session_state['last_active_menu'] = menu

    if st.session_state['last_active_menu'] != menu:
        keys_to_reset = [k for k in st.session_state.keys() if k.startswith("prt_") or k.startswith("prt_eval_")]
        for k in keys_to_reset:
            st.session_state[k] = False
        st.session_state['last_active_menu'] = menu

    # ------------------------------------------------------------------
    # 1. DASHBOARD
    # ------------------------------------------------------------------
    if menu == "📊 Dashboard":
        st.header(f"📊 Moj Dashboard - {current_period}")
        
        my_evals = pd.read_sql_query("SELECT * FROM evaluations WHERE period=? AND manager_id=?", conn, params=(current_period, st.session_state['username']))
        my_team = pd.read_sql_query("SELECT * FROM employees_master WHERE manager_id=?", conn, params=(st.session_state['username'],))
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Moj Tim", len(my_team))
        
        submitted_count = 0
        if not my_evals.empty:
            submitted_count = len(my_evals[my_evals['status'].astype(str).str.strip() == 'Submitted'])
            
        c2.metric("Završene Procjene", f"{submitted_count} / {len(my_team)}")
        c3.metric("Prosjek Tima", f"{my_evals['avg_performance'].mean():.2f}" if not my_evals.empty else "0.0")
        
        t1, t2 = st.tabs(["9-Box Matrica", "Povijest Zaposlenika"])
        
        with t1:
            if not my_evals.empty:
                fig = px.scatter(my_evals, x="avg_performance", y="avg_potential", color="category", hover_data=["ime_prezime"], range_x=[0.5,5.5], range_y=[0.5,5.5], title="Moj Tim: 9-Box")
                fig.add_hline(y=3.0, line_dash="dot"); fig.add_vline(x=3.0, line_dash="dot"); fig.add_hline(y=4.0, line_dash="dot"); fig.add_vline(x=4.0, line_dash="dot")
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Još nema unesenih procjena za ovaj period.")
        
        with t2:
            if not my_team.empty:
                sel_emp = st.selectbox("Odaberi zaposlenika:", my_team['ime_prezime'].tolist())
                if sel_emp:
                    kid = my_team[my_team['ime_prezime']==sel_emp]['kadrovski_broj'].values[0]
                    hist = pd.read_sql_query("SELECT period, avg_performance, avg_potential FROM evaluations WHERE kadrovski_broj=? ORDER BY period", conn, params=(kid,))
                    if not hist.empty:
                        fig_h = go.Figure()
                        fig_h.add_trace(go.Scatter(x=hist['period'], y=hist['avg_performance'], name='Učinak'))
                        fig_h.add_trace(go.Scatter(x=hist['period'], y=hist['avg_potential'], name='Potencijal'))
                        st.plotly_chart(fig_h, use_container_width=True)
                    else: st.warning("Nema povijesti za ovog zaposlenika.")

    # ------------------------------------------------------------------
    # 2. CILJEVI
    # ------------------------------------------------------------------
    elif menu == "🎯 Moji Ciljevi":
        st.header(f"🎯 Moji Ciljevi - {current_period}")
        m = pd.read_sql_query("SELECT * FROM employees_master", conn)
        
        with st.expander("➕ Novi Cilj"):
            q = st.text_input("Traži:", placeholder="Ime...")
            if q:
                res = m[m['ime_prezime'].str.contains(q, case=False)]
                s = st.selectbox("Odaberi:", res.apply(lambda x: f"{x['ime_prezime']} ({x['kadrovski_broj']})", axis=1)) if not res.empty else None
                if s:
                    kid = s.split("(")[1].replace(")", "")
                    with st.form("ng"):
                        t = st.text_input("Naziv"); w = st.number_input("Težina", 1, 100, 25); ds = st.text_area("Opis"); dl = st.date_input("Rok")
                        if st.form_submit_button("Kreiraj"):
                            with sqlite3.connect(DB_FILE) as c_conn:
                                mgr = st.session_state['username']
                                try: mgr = m[m['kadrovski_broj']==kid]['manager_id'].values[0]
                                except: pass
                                c_conn.execute("INSERT INTO goals (period, kadrovski_broj, manager_id, title, description, weight, progress, status, feedback, last_updated, deadline) VALUES (?,?,?,?,?,?,0,'On Track',?, ?, ?)", (current_period, kid, mgr, t, ds, w, "", datetime.now().strftime("%Y-%m-%d"), str(dl)))
                                c_conn.commit()
                            st.success("OK"); st.rerun()

        st.markdown("---")
        q_l = "SELECT DISTINCT g.kadrovski_broj, m.ime_prezime FROM goals g JOIN employees_master m ON g.kadrovski_broj=m.kadrovski_broj WHERE g.period=? AND g.manager_id=?"
        emps = pd.read_sql_query(q_l, conn, params=(current_period, st.session_state['username']))
        
        if emps.empty: st.info("Nema ciljeva.")
        
        for _, r in emps.iterrows():
            eid = r['kadrovski_broj']
            goals = pd.read_sql_query("SELECT * FROM goals WHERE kadrovski_broj=? AND period=?", conn, params=(eid, current_period))
            
            total_w = goals['weight'].sum()
            if total_w != 100:
                msg = f"⚠️ PAŽNJA: Ukupna težina je {total_w}% (Mora biti 100%)"
                msg_color = "red"
            else:
                msg = "✅ Ciljevi ispravno postavljeni (100%)"
                msg_color = "green"

            total_p = (goals['progress']*goals['weight']).sum()/goals['weight'].sum() if goals['weight'].sum()>0 else 0
            
            with st.expander(f"👤 {r['ime_prezime']} | Napredak: {total_p:.1f}%"):
                st.markdown(f"<div style='color:{msg_color}; font-weight:bold; margin-bottom:10px; border:1px solid {msg_color}; padding:5px; border-radius:5px;'>{msg}</div>", unsafe_allow_html=True)
                
                for _, g in goals.iterrows():
                    gid = g['id']
                    st.markdown(f"**{g['title']} ({g['weight']}%)** - {g['deadline']}")
                    kpis = pd.read_sql_query("SELECT * FROM goal_kpis WHERE goal_id=?", conn, params=(gid,))
                    df_k = kpis[['description','weight','progress','deadline']].rename(columns={'description':'KPI','weight':'Težina','progress':'%','deadline':'Rok'}) if not kpis.empty else pd.DataFrame(columns=['KPI','Težina','%','Rok'])
                    
                    ed = st.data_editor(df_k, key=f"k_{gid}", num_rows="dynamic", use_container_width=True)
                    
                    if st.button("💾 Spremi KPI", key=f"s_{gid}"):
                        calc = 0
                        if not ed.empty:
                            temp = ed.copy()
                            temp['Težina'] = pd.to_numeric(temp['Težina'], errors='coerce').fillna(0)
                            temp['%'] = pd.to_numeric(temp['%'], errors='coerce').fillna(0)
                            if temp['Težina'].sum() > 0: calc = (temp['Težina'] * temp['%']).sum() / temp['Težina'].sum()
                        
                        with sqlite3.connect(DB_FILE) as k_conn:
                            k_conn.execute("UPDATE goals SET progress=?, last_updated=? WHERE id=?", (calc, datetime.now().strftime("%Y-%m-%d"), gid))
                            k_conn.execute("DELETE FROM goal_kpis WHERE goal_id=?", (gid,))
                            for _, kr in ed.iterrows():
                                if str(kr['KPI']).strip(): k_conn.execute("INSERT INTO goal_kpis (goal_id, description, weight, progress, deadline) VALUES (?,?,?,?,?)", (gid, str(kr['KPI']), str(kr['Težina']), str(kr['%']), str(kr['Rok'])))
                            k_conn.commit()
                        st.toast("KPI Spremljeni!", icon="✅"); st.rerun()
                    
                    with st.expander("🛠️ Uredi"):
                        with st.form(f"fg_{gid}"):
                            nt = st.text_input("Naziv", g['title']); nw = st.number_input("Težina", 0, 100, int(g['weight'])); nds = st.text_area("Opis", g['description']); ndl = st.date_input("Rok", datetime.strptime(g['deadline'], '%Y-%m-%d').date() if g['deadline'] else date.today()); ns = st.selectbox("Status", ["On Track", "At Risk", "Off Track", "Done"], index=["On Track", "At Risk", "Off Track", "Done"].index(g['status']))
                            if st.form_submit_button("Ažuriraj"):
                                with sqlite3.connect(DB_FILE) as u_conn:
                                    u_conn.execute("UPDATE goals SET title=?, weight=?, description=?, deadline=?, status=? WHERE id=?", (nt, nw, nds, str(ndl), ns, gid))
                                    u_conn.commit()
                                st.success("Ažurirano"); st.rerun()
                            if st.form_submit_button("Obriši"):
                                with sqlite3.connect(DB_FILE) as d_conn:
                                    d_conn.execute("DELETE FROM goal_kpis WHERE goal_id=?", (gid,))
                                    d_conn.execute("DELETE FROM goals WHERE id=?", (gid,))
                                    d_conn.commit()
                                st.rerun()

    # ------------------------------------------------------------------
    # 3. PROCJENE
    # ------------------------------------------------------------------
    elif menu == "📝 Unos Procjena":
        st.header("📝 Procjena Zaposlenika")
        
        with st.expander("➕ Nije na listi? Dodaj novog zaposlenika"):
            with st.form("quick_add"):
                ni = st.text_input("ID"); nn = st.text_input("Ime i Prezime"); nr = st.text_input("Pozicija"); nd = st.text_input("Odjel")
                if st.form_submit_button("Dodaj u sustav"):
                    try:
                        with sqlite3.connect(DB_FILE) as i_conn:
                            i_conn.execute("INSERT INTO employees_master VALUES (?,?,?,?,?)", (ni, nn, nr, nd, st.session_state['username']))
                            i_conn.commit()
                        st.success("Dodan!"); time.sleep(1); st.rerun()
                    except: st.error("ID već postoji.")

        st.markdown("---")
        st.subheader("👨‍💼 Moj Tim")

        my_team = pd.read_sql_query("SELECT * FROM employees_master WHERE manager_id=?", conn, params=(st.session_state['username'],))
        
        if my_team.empty: st.info("Nemate dodijeljenih zaposlenika.")
        
        for _, emp in my_team.iterrows():
            kid = emp['kadrovski_broj']
            # Dohvaćamo zadnji zapis
            exist = pd.read_sql_query("SELECT * FROM evaluations WHERE kadrovski_broj=? AND period=? ORDER BY id DESC LIMIT 1", conn, params=(kid, current_period))
            
            is_locked = False
            r = None
            
            if not exist.empty:
                r = exist.iloc[0]
                status_val = str(r['status']).strip() if r['status'] is not None else "Draft"
                
                # --- PROVJERA STATUSA ---
                if status_val == 'Submitted':
                    is_locked = True
                    status_icon = "🔒"
                    status_text = f"Završeno ({r['category']})"
                else:
                    status_icon = "✏️"
                    status_text = f"U tijeku ({r['category']})"
            else:
                status_icon = "⚠️"
                status_text = "Nije započeto"

            with st.expander(f"{status_icon} {emp['ime_prezime']} ({status_text})"):
                
                # A) ZAKLJUČANO (Submitted) - SAMO READ-ONLY
                if is_locked and r is not None:
                    st.success(f"🔒 Ova procjena je trajno zaključana.")
                    
                    c1, c2 = st.columns(2)
                    with c1: 
                        st.write("### Učinak")
                        st.write(f"**KPI:** {r['p1']}"); st.write(f"**Kvaliteta:** {r['p2']}"); st.write(f"**Stručnost:** {r['p3']}"); st.write(f"**Odgovornost:** {r['p4']}"); st.write(f"**Suradnja:** {r['p5']}")
                        st.markdown(f"**PROSJEK:** {r['avg_performance']}")
                    with c2:
                        st.write("### Potencijal")
                        st.write(f"**Agilnost:** {r['pot1']}"); st.write(f"**Autoritet:** {r['pot2']}"); st.write(f"**Šira slika:** {r['pot3']}"); st.write(f"**Ambicija:** {r['pot4']}"); st.write(f"**Stabilnost:** {r['pot5']}")
                        st.markdown(f"**PROSJEK:** {r['avg_potential']}")
                    
                    st.markdown("---")
                    st.write("### Komentar"); st.write(r['action_plan'])
                    
                    if f"prt_eval_{r['id']}" not in st.session_state: st.session_state[f"prt_eval_{r['id']}"] = False
                    if st.button("🖨️ PDF Procjene", key=f"btn_prt_l_{r['id']}"):
                        st.session_state[f"prt_eval_{r['id']}"] = True; st.rerun()

                # B) OTVORENO (Draft) - FORMA ZA UREĐIVANJE
                elif not exist.empty and not is_locked:
                    with st.form(f"edit_eval_{kid}"):
                        st.caption("Izmjena postojeće procjene")
                        nps = [render_metric_input(METRICS["p"][i], f"ep_{kid}", r[f'p{i+1}']) for i in range(5)]
                        npots = [render_metric_input(METRICS["pot"][i], f"ep_{kid}", r[f'pot{i+1}'], "pot") for i in range(5)]
                        npl = st.text_area("Plan / Komentar", r['action_plan'])
                        
                        if st.form_submit_button("💾 Spremi kao nacrt"):
                            with sqlite3.connect(DB_FILE) as s_conn:
                                # Pretvaramo ID u int za svaki slučaj
                                eval_id_int = int(r['id'])
                                ap, at = sum(nps)/5, sum(npots)/5
                                s_conn.execute("UPDATE evaluations SET p1=?,p2=?,p3=?,p4=?,p5=?, pot1=?,pot2=?,pot3=?,pot4=?,pot5=?, avg_performance=?, avg_potential=?, category=?, action_plan=?, status='Draft' WHERE id=?", 
                                          (*nps, *npots, ap, at, calculate_category(ap, at), npl, eval_id_int))
                                s_conn.commit()
                            st.success("Spremljeno!"); st.rerun()
                    
                    st.markdown("---")
                    col_pdf, col_submit = st.columns([1, 2])
                    
                    with col_pdf:
                         if f"prt_eval_{r['id']}" not in st.session_state: st.session_state[f"prt_eval_{r['id']}"] = False
                         if st.button("🖨️ PDF (Pregled)", key=f"btn_prt_{r['id']}"):
                            st.session_state[f"prt_eval_{r['id']}"] = True; st.rerun()

                    with col_submit:
                        st.write("### Zaključavanje")
                        locked_check = st.checkbox(f"Potvrđujem da je ovo konačno za {emp['ime_prezime']}", key=f"lock_{r['id']}")
                        
                        # --- GUMB ZA ZAKLJUČAVANJE (ROBUSTNA VERZIJA) ---
                        if st.button("🔒 ZAKLJUČAJ I POŠALJI", key=f"btn_send_{r['id']}", disabled=not locked_check, type="primary"):
                             try:
                                 with sqlite3.connect(DB_FILE) as lock_conn:
                                     cursor = lock_conn.cursor()
                                     
                                     # 1. ČIŠĆENJE ID-a (KLJUČNO!)
                                     # Pandas koristi numpy.int64 što SQLite ponekad ne prepoznaje u WHERE klauzuli
                                     clean_id = int(r['id'])
                                     print(f"DEBUG: Pokušavam ažurirati ID: {clean_id} (tip: {type(clean_id)})")
                                     
                                     # 2. UPDATE
                                     cursor.execute("UPDATE evaluations SET status='Submitted' WHERE id=?", (clean_id,))
                                     lock_conn.commit()
                                     
                                     # 3. PROVJERA JE LI USPJELO (Affected rows)
                                     if cursor.rowcount == 0:
                                         print("DEBUG: Rowcount je 0! Nije pronađen redak.")
                                         st.error(f"GREŠKA BAZE: Nije pronađen zapis s ID={clean_id}. Pokušaj ponovno.")
                                     else:
                                         print(f"DEBUG: Uspjeh! Ažurirano {cursor.rowcount} redova.")
                                         
                                         # 4. DODATNA PROVJERA ČITANJEM
                                         check_cur = lock_conn.execute("SELECT status FROM evaluations WHERE id=?", (clean_id,))
                                         new_status = check_cur.fetchone()[0]
                                         print(f"DEBUG: Status u bazi nakon updatea: {new_status}")
                                         
                                         st.toast("✅ Zaključano!", icon="🔒")
                                         time.sleep(1)
                                         st.rerun()
                                         
                             except Exception as e:
                                 print(f"DEBUG EXCEPTION: {e}")
                                 st.error(f"Greška: {e}")

                # C) NE POSTOJI -> KREIRAJ
                else:
                    with st.form(f"new_eval_{kid}"):
                        st.caption("Nova procjena")
                        c1, c2 = st.columns(2)
                        with c1:
                            st.subheader("Učinak")
                            ps = [st.slider("Ciljevi", 1, 5, 3, key=f"n_p0_{kid}")] + [render_metric_input(x, f"n_{kid}") for x in METRICS["p"][1:]]
                        with c2:
                            st.subheader("Potencijal")
                            pots = [render_metric_input(x, f"n_{kid}", 3, "pot") for x in METRICS["pot"]]
                        pl = st.text_area("Kratki komentar / Plan", key=f"n_pl_{kid}")
                        
                        if st.form_submit_button("Spremi Nacrt"):
                            with sqlite3.connect(DB_FILE) as n_conn:
                                ap, at = sum(ps)/5, sum(pots)/5
                                n_conn.execute("INSERT INTO evaluations (period, kadrovski_broj, ime_prezime, radno_mjesto, department, manager_id, p1,p2,p3,p4,p5, pot1,pot2,pot3,pot4,pot5, avg_performance, avg_potential, category, action_plan, status) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                                                     (current_period, kid, emp['ime_prezime'], emp['radno_mjesto'], emp['department'], st.session_state['username'], *ps, *pots, ap, at, calculate_category(ap, at), pl, 'Draft'))
                                n_conn.commit()
                            st.success("Kreirano"); st.rerun()
                
                # --- PDF GENERATOR ---
                if r is not None:
                    if f"prt_eval_{r['id']}" in st.session_state and st.session_state[f"prt_eval_{r['id']}"]:
                            html_content = f"""
                            <html><head><style>
                                @media print {{ body {{ font-family: Arial, sans-serif; }} .no-print {{ display: none; }} }}
                                body {{ font-family: Arial, sans-serif; padding: 20px; }}
                                .header {{ border-bottom: 2px solid #E2001A; padding-bottom: 10px; margin-bottom: 20px; }}
                                .title {{ color: #E2001A; font-size: 24px; font-weight: bold; }}
                                .meta {{ font-size: 12px; color: #666; }}
                                table {{ width: 100%; border-collapse: collapse; margin-bottom: 20px; }}
                                td, th {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                                .box-title {{ background-color: #f0f0f0; padding: 10px; font-weight: bold; margin-top: 15px; border-left: 5px solid #E2001A; }}
                                .print-btn {{ background-color: #E2001A; color: white; border: none; padding: 10px 20px; font-weight: bold; cursor: pointer; border-radius: 4px; margin-top: 20px; }}
                            </style><script>window.onload = function() {{ window.print(); }}</script></head>
                            <body>
                                <div class="no-print" style="text-align:center;"><button class="print-btn" onclick="window.print()">🖨️ PRINT / SPREMI PDF</button></div>
                                <div class="header"><div class="title">OBRAZAC PROCJENE UČINKA</div><div class="meta">Period: {current_period} | Datum: {date.today()}</div></div>
                                <table><tr><td><b>Zaposlenik:</b> {r['ime_prezime']}</td><td><b>Pozicija:</b> {r['radno_mjesto']}</td></tr><tr><td><b>Odjel:</b> {r['department']}</td><td><b>Voditelj:</b> {r['manager_id']}</td></tr></table>
                                <div class="box-title">1. UČINAK</div>
                                <table><tr><th>Kompetencija</th><th>Ocjena</th></tr><tr><td>1. KPI</td><td>{r['p1']}</td></tr><tr><td>2. Kvaliteta</td><td>{r['p2']}</td></tr><tr><td>3. Stručnost</td><td>{r['p3']}</td></tr><tr><td>4. Odgovornost</td><td>{r['p4']}</td></tr><tr><td>5. Suradnja</td><td>{r['p5']}</td></tr><tr style="background:#f9f9f9"><td><b>PROSJEK:</b></td><td><b>{r['avg_performance']}</b></td></tr></table>
                                <div class="box-title">2. POTENCIJAL</div>
                                <table><tr><th>Kompetencija</th><th>Ocjena</th></tr><tr><td>1. Agilnost</td><td>{r['pot1']}</td></tr><tr><td>2. Autoritet</td><td>{r['pot2']}</td></tr><tr><td>3. Šira slika</td><td>{r['pot3']}</td></tr><tr><td>4. Ambicija</td><td>{r['pot4']}</td></tr><tr><td>5. Stabilnost</td><td>{r['pot5']}</td></tr><tr style="background:#f9f9f9"><td><b>PROSJEK:</b></td><td><b>{r['avg_potential']}</b></td></tr></table>
                                <div class="box-title">3. 9-BOX STATUS</div><div style="padding:15px; border:1px solid #ddd; text-align:center; font-size:18px; font-weight:bold;">{r['category']}</div>
                                <div class="box-title">4. KOMENTAR</div><div style="padding:15px; border:1px solid #ddd;">{r['action_plan'] if r['action_plan'] else "Nema komentara."}</div>
                                <br><br><table style="border:none"><tr><td style="border:none; border-top:1px solid #000;">Potpis zaposlenika</td><td style="border:none;"></td><td style="border:none; border-top:1px solid #000; text-align:right;">Potpis voditelja</td></tr></table>
                            </body></html>
                            """
                            components.html(html_content, height=800, scrolling=True)
                            if st.button("Zatvori pregled", key=f"close_{r['id']}"):
                                st.session_state[f"prt_eval_{r['id']}"] = False
                                st.rerun()

    # ------------------------------------------------------------------
    # 4. IDP
    # ------------------------------------------------------------------
    elif menu == "🚀 Razvojni Planovi (IDP)":
        st.header("🚀 Individualni Razvojni Planovi (IDP)")
        master = pd.read_sql_query("SELECT * FROM employees_master", conn)
        q = st.text_input("Traži zaposlenika:", key="idp_s")
        current_team_df = master[master['manager_id'] == st.session_state['username']]
        my_plans_df = pd.read_sql_query("SELECT m.ime_prezime, m.kadrovski_broj FROM development_plans d JOIN employees_master m ON d.kadrovski_broj = m.kadrovski_broj WHERE d.manager_id = ? AND d.period = ?", conn, params=(st.session_state['username'], current_period))
        combined = pd.concat([current_team_df[['ime_prezime', 'kadrovski_broj']], my_plans_df]).drop_duplicates().sort_values('ime_prezime')
        if q: combined = combined[combined['ime_prezime'].str.contains(q, case=False)]
        sel = st.selectbox("Rezultat:", combined.apply(lambda x: f"{x['ime_prezime']} ({x['kadrovski_broj']})", axis=1)) if not combined.empty else None
        
        if sel:
            eid = sel.split("(")[1].replace(")", "")
            emp_name = sel.split(" (")[0]
            emp_role = master[master['kadrovski_broj']==eid]['radno_mjesto'].values[0] if not master[master['kadrovski_broj']==eid].empty else "N/A"
            emp_dept = master[master['kadrovski_broj']==eid]['department'].values[0] if not master[master['kadrovski_broj']==eid].empty else "N/A"
            
            ev = conn.cursor().execute("SELECT category FROM evaluations WHERE kadrovski_broj=? AND period=?", (eid, current_period)).fetchone()
            cat = ev[0] if ev else "Nije procijenjen"
            idp = pd.read_sql_query("SELECT * FROM development_plans WHERE kadrovski_broj=? AND period=?", conn, params=(eid, current_period))
            
            with st.expander(f"📄 {emp_name} ({cat})", expanded=True):
                hist_idp = pd.read_sql_query("SELECT period, manager_id FROM development_plans WHERE kadrovski_broj=?", conn, params=(eid,))
                if len(hist_idp) > 1:
                    with st.popover("📜 Pregledaj stare planove"):
                        st.dataframe(hist_idp, hide_index=True)

                if f"prt_{eid}" not in st.session_state: st.session_state[f"prt_{eid}"] = False
                
                if st.session_state[f"prt_{eid}"]:
                    d = idp.iloc[0] if not idp.empty else {}
                    def html_table(df):
                        html = "<table style='width:100%; border-collapse: collapse; border: 1px solid #000; font-family: Arial; font-size: 11px; margin-bottom: 10px;'><tr style='background-color: #f2f2f2;'>" + "".join([f"<th style='border: 1px solid #000; padding: 5px; text-align: left;'>{col}</th>" for col in df.columns]) + "</tr>"
                        for _, row_data in df.iterrows(): html += "<tr>" + "".join([f"<td style='border: 1px solid #000; padding: 5px;'>{cell}</td>" for cell in row_data]) + "</tr>"
                        return html + "</table>"
                    t70 = html_table(get_df_from_json(d.get('json_70',''), ["Što razviti?", "Aktivnost", "Rok", "Dokaz"]))
                    t20 = html_table(get_df_from_json(d.get('json_20',''), ["Što razviti?", "Aktivnost", "Rok"]))
                    t10 = html_table(get_df_from_json(d.get('json_10',''), ["Edukacija", "Trošak", "Rok"]))
                    html_content = f"""<html><head><style>@media print {{ @page {{ margin: 1cm; }} body {{ font-family: Arial, sans-serif; }} button {{ display: none; }} }} .section-title {{ background-color: #eee; padding: 5px; font-weight: bold; border-bottom: 2px solid #E2001A; margin-top: 15px; margin-bottom: 5px; font-size: 12px; }} .info-box {{ border: 1px solid #ccc; padding: 10px; margin-bottom: 10px; font-size: 12px; }} .print-btn {{ background-color: #E2001A; color: white; border: none; padding: 10px 20px; font-weight: bold; cursor: pointer; border-radius: 4px; }}</style><script>window.onload = function() {{ window.print(); }}</script></head><body><div style="text-align:center; padding-bottom:20px;"><button class="print-btn" onclick="window.print()">🖨️ ISPRINTAJ / SPREMI KAO PDF</button></div><div style="display:flex; justify-content:space-between; align-items:center; border-bottom: 2px solid #E2001A; padding-bottom:10px;"><h2 style="margin:0; color: #E2001A;">INDIVIDUALNI RAZVOJNI PLAN</h2><div style="text-align:right; font-size:10px;">Period: {current_period}<br>Datum: {date.today()}</div></div><table style="width:100%; margin-top:10px; font-size:12px;"><tr><td><b>Ime i prezime:</b> {emp_name}</td><td><b>Pozicija:</b> {emp_role}</td></tr><tr><td><b>Odjel:</b> {emp_dept}</td><td><b>Voditelj:</b> {d.get('manager_id', st.session_state['username'])}</td></tr></table><div class="section-title">1. DIJAGNOZA STANJA</div><div class="info-box"><b>Ključne snage:</b><br>{d.get('strengths','-')}<br><br><b>Područja za razvoj:</b><br>{d.get('areas_improve','-')}<br><br><b>Karijerni cilj:</b> {d.get('career_goal','-')}</div><div class="section-title">2. PLAN AKTIVNOSTI</div><b style="font-size:11px;">A) 70% ISKUSTVO I PRAKSA</b>{t70}<b style="font-size:11px;">B) 20% UČENJE OD DRUGIH</b>{t20}<b style="font-size:11px;">C) 10% FORMALNA EDUKACIJA</b>{t10}<div class="section-title">3. PODRŠKA I RESURSI</div><div class="info-box"><b>Potrebna podrška:</b> {d.get('support_needed','-')}<br><b>Napomene:</b> {d.get('support_notes','-')}</div><br><br><br><table style="width:100%; margin-top:30px; font-size:12px;"><tr><td style="border-top:1px solid #000; width:40%; padding-top:5px;">Potpis zaposlenika</td><td style="width:20%;"></td><td style="border-top:1px solid #000; width:40%; padding-top:5px; text-align:right;">Potpis voditelja</td></tr></table><br><div style="text-align:center; padding-top:20px;"><button class="print-btn" onclick="window.print()">🖨️ ISPRINTAJ / SPREMI KAO PDF</button></div></body></html>"""
                    components.html(html_content, height=1000, scrolling=True)
                    if st.button("🔙 Natrag na uređivanje"): st.session_state[f"prt_{eid}"] = False; st.rerun()
                
                else:
                    d = idp.iloc[0] if not idp.empty else {}
                    st.markdown("### 1. DIJAGNOZA")
                    s = st.text_area("Ključne snage (Što zadržati?)", d.get('strengths',''), key=f"s_{eid}")
                    w = st.text_area("Područja za razvoj (Što popraviti?)", d.get('areas_improve',''), key=f"w_{eid}")
                    g = st.text_input("Karijerni cilj (1-2 godine)", d.get('career_goal',''), key=f"g_{eid}")
                    
                    st.markdown("### 2. PLAN AKTIVNOSTI (70-20-10)")
                    st.markdown('<div class="idp-instruction"><b>A) 70% ISKUSTVO I PRAKSA</b><br>Učenje kroz rad – novi zadaci, projekti, rotacije poslova.<div class="idp-example">Primjer: "Preuzeti potpunu organizaciju jednog internog događaja od plana do realizacije."</div></div>', unsafe_allow_html=True)
                    df70 = get_df_from_json(d.get('json_70',''), ["Što razviti?", "Aktivnost", "Rok", "Dokaz"])
                    d70 = st.data_editor(df70, key=f"d70_{eid}", num_rows="dynamic", use_container_width=True)
                    
                    st.markdown('<div class="idp-instruction"><b>B) 20% UČENJE OD DRUGIH</b><br>Mentoring, feedback, shadowing.<div class="idp-example">Primjer: "Kratki 1-na-1 sastanak s Voditeljem projekata jednom mjesečno radi feedbacka na vođenje sastanaka."</div></div>', unsafe_allow_html=True)
                    df20 = get_df_from_json(d.get('json_20',''), ["Što razviti?", "Aktivnost", "Rok"])
                    d20 = st.data_editor(df20, key=f"d20_{eid}", num_rows="dynamic", use_container_width=True)
                    
                    st.markdown('<div class="idp-instruction"><b>C) 10% FORMALNA EDUKACIJA</b><br>Tečajevi, knjige, seminari.<div class="idp-example">Primjer: "Završiti Excel Advanced tečaj na Udemy platformi."</div></div>', unsafe_allow_html=True)
                    df10 = get_df_from_json(d.get('json_10',''), ["Edukacija", "Trošak", "Rok"])
                    d10 = st.data_editor(df10, key=f"d10_{eid}", num_rows="dynamic", use_container_width=True)
                    
                    st.markdown("### 3. PODRŠKA")
                    sup_opts = ["Budžet za edukaciju", "Vrijeme za učenje", "Mentorstvo", "Alati/Softver"]
                    sup_val = d.get('support_needed','')
                    sup = st.multiselect("Potrebno:", sup_opts, default=[x.strip() for x in sup_val.split(',') if x.strip() in sup_opts], key=f"sup_{eid}")
                    sup_n = st.text_input("Napomene:", d.get('support_notes',''), key=f"sn_{eid}")
                    
                    c_save, c_print = st.columns(2)
                    if c_save.button("💾 SPREMI IDP", key=f"btn_{eid}"):
                        try:
                            j70s = table_to_json_string(d70)
                            j20s = table_to_json_string(d20)
                            j10s = table_to_json_string(d10)
                            sups = ",".join(sup)
                            with sqlite3.connect(DB_FILE) as idp_conn:
                                idp_conn.execute("DELETE FROM development_plans WHERE kadrovski_broj=? AND period=?", (eid, current_period))
                                idp_conn.execute("INSERT INTO development_plans (period, kadrovski_broj, manager_id, strengths, areas_improve, career_goal, json_70, json_20, json_10, support_needed, support_notes, status) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", (current_period, eid, st.session_state['username'], s, w, g, j70s, j20s, j10s, sups, sup_n, "Active"))
                                idp_conn.commit()
                            st.toast("IDP Spremljen!", icon="✅"); time.sleep(1); st.rerun()
                        except Exception as e: st.error(f"Greška: {e}")
                    if c_print.button("🖨️ PDF", key=f"pp_{eid}"): st.session_state[f"prt_{eid}"] = True; st.rerun()
    
    # 3. ZATVARAMO GLAVNU KONEKCIJU
    conn.close()