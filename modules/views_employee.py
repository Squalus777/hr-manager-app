import streamlit as st
import pandas as pd
import plotly.express as px
import sqlite3
from modules.database import get_connection, get_active_period_info, DB_FILE
from modules.utils import get_df_from_json, METRICS, check_hashes, make_hashes

def render_employee_view():
    conn = get_connection()
    current_period, _ = get_active_period_info()
    
    # ID je username ulogiranog korisnika
    my_id = st.session_state['username']
    
    # Dohvat osnovnih podataka o zaposleniku
    my_info = pd.read_sql_query("SELECT * FROM employees_master WHERE kadrovski_broj=?", conn, params=(my_id,))
    
    if my_info.empty:
        st.error(f"Nisu pronađeni podaci za broj: {my_id}. Obratite se HR-u.")
        return

    me = my_info.iloc[0]
    
    # Sidebar
    st.sidebar.title(f"👋 Bok, {me['ime_prezime'].split()[0]}")
    menu = st.sidebar.radio("Izbornik", ["🏠 Moj Profil", "🎯 Moji Ciljevi", "📝 Moja Procjena", "🚀 Moj Razvoj (IDP)"])

    # ------------------------------------------------------------------
    # 1. MOJ PROFIL (S PROMJENOM LOZINKE)
    # ------------------------------------------------------------------
    if menu == "🏠 Moj Profil":
        st.header(f"🏠 Profil: {me['ime_prezime']}")
        
        # Kartica s podacima
        with st.container():
            c1, c2 = st.columns(2)
            with c1:
                st.info(f"**Pozicija:** {me['radno_mjesto']}")
                st.write(f"**Odjel:** {me['department']}")
                st.caption(f"ID: {my_id}")
            with c2:
                st.success(f"**Voditelj:** {me['manager_id']}")
                st.write(f"**Trenutni ciklus:** {current_period}")
        
        st.markdown("---")
        
        # SEKCIJA ZA PROMJENU LOZINKE
        with st.expander("🔐 Promjena Lozinke"):
            with st.form("change_pass_form"):
                st.write("Ovdje možete promijeniti svoju lozinku.")
                old_pass = st.text_input("Trenutna lozinka", type="password")
                new_pass = st.text_input("Nova lozinka", type="password")
                confirm_pass = st.text_input("Potvrdi novu lozinku", type="password")
                
                if st.form_submit_button("Promijeni lozinku"):
                    # Provjera stare lozinke
                    user_row = conn.execute("SELECT password FROM users WHERE username=?", (my_id,)).fetchone()
                    
                    if user_row and check_hashes(old_pass, user_row[0]):
                        if new_pass == confirm_pass:
                            if len(new_pass) >= 4:
                                new_hash = make_hashes(new_pass)
                                with sqlite3.connect(DB_FILE) as u_conn:
                                    u_conn.execute("UPDATE users SET password=? WHERE username=?", (new_hash, my_id))
                                    u_conn.commit()
                                st.success("✅ Lozinka uspješno promijenjena! Odjavite se i prijavite ponovno.")
                            else:
                                st.warning("Lozinka mora imati barem 4 znaka.")
                        else:
                            st.error("Nove lozinke se ne podudaraju.")
                    else:
                        st.error("Pogrešna trenutna lozinka.")

        st.markdown("---")
        st.subheader("📊 Tvoj razvoj kroz vrijeme")
        
        # Graf povijesti (Snail Trail) - SAMO ZAKLJUČANE
        hist = pd.read_sql_query("SELECT period, avg_performance, avg_potential FROM evaluations WHERE kadrovski_broj=? AND status='Submitted' ORDER BY period", conn, params=(my_id,))
        
        if not hist.empty:
            fig = px.line(hist, x='avg_performance', y='avg_potential', markers=True, text='period', 
                          range_x=[0.5, 5.5], range_y=[0.5, 5.5], title="Kretanje kroz 9-Box matricu")
            # Dodajemo linije matrice
            fig.add_hline(y=3.0, line_dash="dot", line_color="grey"); fig.add_vline(x=3.0, line_dash="dot", line_color="grey")
            fig.add_hline(y=4.0, line_dash="dot", line_color="grey"); fig.add_vline(x=4.0, line_dash="dot", line_color="grey")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Još nemaš zaključenih povijesnih podataka o procjenama.")

    # ------------------------------------------------------------------
    # 2. MOJI CILJEVI
    # ------------------------------------------------------------------
    elif menu == "🎯 Moji Ciljevi":
        # Filter perioda
        periods_list = [x[0] for x in conn.execute("SELECT DISTINCT period FROM goals WHERE kadrovski_broj=? ORDER BY period DESC", (my_id,)).fetchall()]
        
        if not periods_list: 
            selected_period = current_period
        else:
            idx = periods_list.index(current_period) if current_period in periods_list else 0
            selected_period = st.selectbox("📅 Odaberi razdoblje:", periods_list, index=idx)

        st.header(f"🎯 Ciljevi za: {selected_period}")
        
        goals = pd.read_sql_query("SELECT * FROM goals WHERE kadrovski_broj=? AND period=?", conn, params=(my_id, selected_period))
        
        if goals.empty:
            st.warning(f"Nema postavljenih ciljeva za razdoblje {selected_period}.")
        else:
            # Progress bar
            total_w = goals['weight'].sum()
            tp = (goals['progress'] * goals['weight']).sum() / total_w if total_w > 0 else 0
            st.metric("Ukupno ostvarenje ciljeva", f"{tp:.1f}%")
            st.progress(tp / 100)
            
            st.markdown("---")
            
            for _, g in goals.iterrows():
                # Status boja
                status_color = "green" if g['status'] == 'Done' else "orange" if g['status'] == 'On Track' else "red"
                
                with st.expander(f"🚩 {g['title']} ({g['weight']}%) - :{status_color}[{g['status']}]"):
                    st.markdown(f"**Opis cilja:** {g['description']}")
                    st.caption(f"📅 Rok: {g['deadline']}")
                    
                    # KPI Tablica
                    kpis = pd.read_sql_query("SELECT description as 'KPI / Mjera', weight as 'Težina', progress as 'Ostvarenje' FROM goal_kpis WHERE goal_id=?", conn, params=(g['id'],))
                    if not kpis.empty:
                        st.dataframe(kpis, hide_index=True, use_container_width=True)
                    else:
                        st.info("Nema definiranih pod-mjera (KPI).")

    # ------------------------------------------------------------------
    # 3. MOJA PROCJENA (SKRIVENA DOK NIJE SUBMITTED)
    # ------------------------------------------------------------------
    elif menu == "📝 Moja Procjena":
        # Filter perioda
        periods_list = [x[0] for x in conn.execute("SELECT DISTINCT period FROM evaluations WHERE kadrovski_broj=? ORDER BY period DESC", (my_id,)).fetchall()]
        
        if not periods_list: 
            selected_period = current_period
        else:
            idx = periods_list.index(current_period) if current_period in periods_list else 0
            selected_period = st.selectbox("📅 Odaberi razdoblje procjene:", periods_list, index=idx)

        st.header(f"📝 Procjena Učinka: {selected_period}")
        
        ev = pd.read_sql_query("SELECT * FROM evaluations WHERE kadrovski_broj=? AND period=?", conn, params=(my_id, selected_period))
        
        if ev.empty:
            st.info(f"Procjena za {selected_period} još nije započela.")
        else:
            r = ev.iloc[0]
            
            # --- LOGIKA SKRIVANJA ---
            if r['status'] != 'Submitted':
                # NIJE ZAKLJUČANO -> SKRIJ DETALJE
                st.warning("⚠️ Vaš voditelj trenutno radi na vašoj procjeni.")
                st.info("Detaljni rezultati i ocjene bit će vidljivi tek nakon što voditelj finalizira i zaključa procjenu.")
                st.caption(f"Status: {r['status']} (U tijeku)")
            
            else:
                # ZAKLJUČANO -> PRIKAŽI SVE
                st.success(f"🔒 Procjena je zaključana i konačna. (Kategorija: {r['category']})")
                st.markdown("---")
                
                c1, c2 = st.columns(2)
                
                with c1:
                    st.subheader("1. Učinak (Performance)")
                    for i, m in enumerate(METRICS['p']):
                        score = r[f'p{i+1}']
                        st.markdown(f"**{m['title']}**: {score}/5")
                        st.caption(f"{m['def']}")
                        st.progress(score/5)
                    st.markdown(f"#### 🏆 Prosjek Učinka: {r['avg_performance']}")

                with c2:
                    st.subheader("2. Potencijal (Potential)")
                    for i, m in enumerate(METRICS['pot']):
                        score = r[f'pot{i+1}']
                        st.markdown(f"**{m['title']}**: {score}/5")
                        st.caption(f"{m['def']}")
                        st.progress(score/5)
                    st.markdown(f"#### 🚀 Prosjek Potencijala: {r['avg_potential']}")
                
                st.markdown("---")
                st.subheader("💬 Komentar voditelja i Akcijski plan")
                if r['action_plan']:
                    st.info(r['action_plan'])
                else:
                    st.write("Nema unesenog komentara.")

    # ------------------------------------------------------------------
    # 4. MOJ RAZVOJ (IDP) - SVE NA JEDNOM MJESTU
    # ------------------------------------------------------------------
    elif menu == "🚀 Moj Razvoj (IDP)":
        st.header("🚀 Moji Razvojni Planovi (IDP)")
        
        # Dohvaćamo SVE planove, sortirane od najnovijeg
        idps = pd.read_sql_query("SELECT * FROM development_plans WHERE kadrovski_broj=? ORDER BY id DESC", conn, params=(my_id,))
        
        if idps.empty:
            st.warning("Nemate definiranih razvojnih planova.")
        else:
            st.write("Ovdje se nalaze svi vaši razvojni planovi. Kliknite na period za detalje.")
            
            for _, d in idps.iterrows():
                period_title = d['period']
                if period_title == current_period:
                    period_title += " (AKTUALNO)"
                
                # Aktualni je defaultno otvoren, stari zatvoreni
                with st.expander(f"📄 Plan za razdoblje: **{period_title}**", expanded=(d['period']==current_period)):
                    st.caption(f"Kreirao voditelj: {d['manager_id']}")
                    
                    st.info(f"🎯 **Karijerni cilj:** {d['career_goal']}")
                    
                    c1, c2 = st.columns(2)
                    c1.write(f"**💪 Moje Snage:**\n{d['strengths']}")
                    c2.write(f"**📈 Područja za razvoj:**\n{d['areas_improve']}")
                    
                    st.markdown("---")
                    st.markdown("### Plan Aktivnosti (70-20-10)")
                    
                    st.write("**A) 70% Učenje kroz rad (Iskustvo)**")
                    st.dataframe(get_df_from_json(d['json_70'], ["Aktivnost", "Rok", "Dokaz"]), hide_index=True, use_container_width=True)
                    
                    st.write("**B) 20% Učenje od drugih (Feedback/Mentoring)**")
                    st.dataframe(get_df_from_json(d['json_20'], ["Aktivnost", "Rok"]), hide_index=True, use_container_width=True)
                    
                    st.write("**C) 10% Formalna edukacija**")
                    st.dataframe(get_df_from_json(d['json_10'], ["Edukacija", "Trošak", "Rok"]), hide_index=True, use_container_width=True)
                    
                    st.markdown("---")
                    st.write(f"**🛠️ Dogovorena podrška:** {d['support_needed']}")
                    if d['support_notes']:
                        st.caption(f"Napomene: {d['support_notes']}")

    conn.close()