import streamlit as st
import pandas as pd
import time
import sqlite3

# Importamo module
from modules.database import get_connection, perform_backup, get_active_period_info, DB_FILE
from modules.utils import make_hashes

def render_admin_view():
    st.header("🛠️ Admin Panel (Tehničko održavanje)")
    
    conn = get_connection()
    current_period, _ = get_active_period_info()
    
    t_hr, t_users, t_audit, t_backup, t_transfer, t_pass = st.tabs([
        "👥 Baza Zaposlenika", 
        "🔐 Login Računi", 
        "📜 Audit", 
        "💾 Backup", 
        "⇄ Transfer", 
        "🔑 Reset Lozinke"
    ])
    
    # ------------------------------------------------------------------
    # 1. ZAPOSLENICI
    # ------------------------------------------------------------------
    with t_hr:
        st.subheader("Upravljanje Matičnim Podacima Zaposlenika")
        
        emps = pd.read_sql_query("SELECT * FROM employees_master", conn)
        st.dataframe(emps, use_container_width=True)

        c1, c2 = st.columns(2)

        # A) DODAVANJE
        with c1:
            with st.expander("➕ Dodaj Novog Zaposlenika"):
                with st.form("add_emp_master"):
                    ni = st.text_input("Kadrovski Broj (ID)")
                    nn = st.text_input("Ime i Prezime")
                    nr = st.text_input("Pozicija")
                    nd = st.text_input("Odjel")
                    nm = st.text_input("Manager ID (Username voditelja)")
                    
                    if st.form_submit_button("Spremi u bazu"):
                        if ni and nn:
                            try:
                                with sqlite3.connect(DB_FILE) as c_conn:
                                    c_conn.execute("INSERT INTO employees_master VALUES (?,?,?,?,?)", (str(ni).strip(), nn, nr, nd, nm))
                                    c_conn.commit()
                                st.success(f"Zaposlenik {nn} dodan!")
                                time.sleep(1); st.rerun()
                            except Exception as e:
                                st.error(f"Greška (ID vjerojatno postoji): {e}")

        # B) BRISANJE (STANDARDNO)
        with c2:
            with st.expander("🗑️ Obriši Zaposlenika", expanded=False):
                st.warning("⚠️ PAŽNJA: Ovo briše Zaposlenika i SVE njegove podatke!")
                
                if not emps.empty:
                    del_choice = st.selectbox("Koga obrisati?", emps.apply(lambda x: f"{x['ime_prezime']} ({x['kadrovski_broj']})", axis=1))
                    
                    if del_choice:
                        # Čišćenje ID-a (uzimamo zadnji dio u zagradi)
                        raw_id = del_choice.split("(")[-1].replace(")", "")
                        del_id = str(raw_id).strip()
                        
                        confirm_del = st.checkbox(f"Potvrđujem brisanje ID: {del_id}")
                        
                        if st.button("❌ IZVRŠI BRISANJE", disabled=not confirm_del, type="primary"):
                            try:
                                with sqlite3.connect(DB_FILE) as d_conn:
                                    d_conn.execute("DELETE FROM evaluations WHERE kadrovski_broj=?", (del_id,))
                                    d_conn.execute("DELETE FROM goals WHERE kadrovski_broj=?", (del_id,))
                                    d_conn.execute("DELETE FROM development_plans WHERE kadrovski_broj=?", (del_id,))
                                    d_conn.execute("DELETE FROM employees_master WHERE kadrovski_broj=?", (del_id,))
                                    d_conn.commit()
                                st.toast("Obrisano!", icon="🗑️")
                                time.sleep(1); st.rerun()
                            except Exception as e:
                                st.error(f"Greška: {e}")

        # --- C) HITNI POPRAVAK (OVO TI TREBA) ---
        st.markdown("---")
        with st.expander("🚨 ALAT ZA POPRAVAK IMPORTA (Fix Bad ID)", expanded=True):
            st.error("Koristi ovaj gumb ako u tablici vidiš redove gdje ID nije broj nego tekst (npr. 'Kadrovski broj' ili 'ID').")
            
            if st.button("🧹 Očisti 'Zaglavlja' iz Baze (Force Delete)"):
                try:
                    with sqlite3.connect(DB_FILE) as fix_conn:
                        # Ovo briše sve gdje u ID-u piše "Kadrovski" ili "ID" ili "Broj"
                        # To su ostaci zaglavlja iz Excela
                        fix_conn.execute("DELETE FROM employees_master WHERE kadrovski_broj LIKE '%Kadrovski%' OR kadrovski_broj LIKE '%ID%' OR kadrovski_broj LIKE '%Broj%'")
                        fix_conn.commit()
                    
                    st.success("Baza očišćena! Svi redovi koji su izgledali kao zaglavlja su obrisani.")
                    time.sleep(2)
                    st.rerun()
                except Exception as e:
                    st.error(f"Greška pri čišćenju: {e}")

    # ------------------------------------------------------------------
    # 2. LOGIN RAČUNI
    # ------------------------------------------------------------------
    with t_users:
        st.subheader("Upravljanje Login Pristupima (System Users)")
        users_df = pd.read_sql_query("SELECT * FROM users", conn)
        edited_users = st.data_editor(users_df, key="adm_u", disabled=["username", "password"])
        
        if st.button("Spremi promjene uloga"):
            with sqlite3.connect(DB_FILE) as u_conn:
                for _, r in edited_users.iterrows():
                    u_conn.execute("UPDATE users SET role=?, department=? WHERE username=?", 
                                  (r['role'], r['department'], r['username']))
                u_conn.commit()
            st.success("Spremljeno!")
            time.sleep(1); st.rerun()
        
        st.markdown("---")
        with st.form("nu"):
            st.write("Kreiraj novi Login:")
            un = st.text_input("Username")
            up = st.text_input("Password", type="password")
            ur = st.selectbox("Role", ["Manager","HR"])
            ud = st.text_input("Department")
            if st.form_submit_button("Kreiraj Login"):
                try:
                    with sqlite3.connect(DB_FILE) as n_conn:
                        n_conn.execute("INSERT INTO users VALUES (?,?,?,?)", (un, make_hashes(up), ur, ud))
                        n_conn.commit()
                    st.success("Korisnik kreiran")
                except: st.error("Username već postoji.")

    # ------------------------------------------------------------------
    # 3. OSTALI TABOVI
    # ------------------------------------------------------------------
    with t_audit:
        st.dataframe(pd.read_sql_query("SELECT * FROM audit_log ORDER BY id DESC LIMIT 200", conn))

    with t_backup:
        if st.button("Napravi Backup Baze"):
            s, m = perform_backup()
            if s: st.success(f"Backup kreiran: {m}")
            else: st.error(f"Greška: {m}")

    with t_transfer:
        st.subheader("Transfer Zaposlenika")
        emps = pd.read_sql_query("SELECT * FROM employees_master", conn)
        mgrs = pd.read_sql_query("SELECT username FROM users WHERE role='Manager'", conn)
        c1, c2 = st.columns(2)
        te_sel = c1.selectbox("Zaposlenik:", emps.apply(lambda x: f"{x['ime_prezime']} ({x['kadrovski_broj']})", axis=1))
        nm = c2.selectbox("Novi Manager:", mgrs['username'])
        if st.button("Izvrši Transfer"):
            eid = te_sel.split("(")[1].replace(")", "")
            with sqlite3.connect(DB_FILE) as t_conn:
                t_conn.execute("UPDATE employees_master SET manager_id=? WHERE kadrovski_broj=?", (nm, eid))
                t_conn.commit()
            st.success(f"Transfer izvršen!")

    with t_pass:
        users_list = pd.read_sql_query("SELECT username FROM users", conn)['username'].tolist()
        user_to_reset = st.selectbox("Korisnik:", users_list)
        new_pass = st.text_input("Nova lozinka:", type="password", key="new_p_reset")
        if st.button("Promijeni lozinku"):
            if new_pass:
                with sqlite3.connect(DB_FILE) as p_conn:
                    p_conn.execute("UPDATE users SET password=? WHERE username=?", (make_hashes(new_pass), user_to_reset))
                    p_conn.commit()
                st.success(f"Lozinka za {user_to_reset} promijenjena.")