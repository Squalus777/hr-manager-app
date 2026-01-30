import streamlit as st
import pandas as pd
import time
import sqlite3

# Importamo module
from modules.database import get_connection, perform_backup, get_active_period_info, DB_FILE, get_available_backups, restore_backup_file
from modules.utils import make_hashes

def render_admin_view():
    st.header("🛠️ Admin Panel (Tehničko održavanje)")
    
    conn = get_connection()
    current_period, _ = get_active_period_info()
    
    t_hr, t_users, t_audit, t_backup, t_transfer, t_pass = st.tabs([
        "👥 Baza Zaposlenika", 
        "🔐 Login Računi", 
        "📜 Audit", 
        "💾 Backup & Restore", 
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

        # A) DODAVANJE (SADA S ODABIROM ROLE!)
        with c1:
            with st.expander("➕ Dodaj Novog Zaposlenika"):
                with st.form("add_emp_master"):
                    ni = st.text_input("Kadrovski Broj (ID)")
                    nn = st.text_input("Ime i Prezime")
                    nr = st.text_input("Pozicija")
                    nd = st.text_input("Odjel")
                    nm = st.text_input("Manager ID (Username voditelja)")
                    # --- NOVO: ODABIR ROLE ---
                    n_role = st.selectbox("Razina pristupa (Rola)", ["Employee", "Manager", "HR"], index=0)
                    
                    if st.form_submit_button("Spremi u bazu"):
                        if ni and nn:
                            try:
                                with sqlite3.connect(DB_FILE) as c_conn:
                                    clean_id = str(ni).strip()
                                    # 1. Insert u Master (Zaposlenik)
                                    c_conn.execute("INSERT INTO employees_master VALUES (?,?,?,?,?)", (clean_id, nn, nr, nd, nm))
                                    
                                    # 2. Insert u Users (Login s odabranom rolom)
                                    # Lozinka je default: user123
                                    c_conn.execute("INSERT OR IGNORE INTO users (username, password, role, department) VALUES (?,?,?,?)", 
                                                  (clean_id, make_hashes("user123"), n_role, nd))
                                    
                                    c_conn.commit()
                                st.success(f"Zaposlenik {nn} dodan kao {n_role}!")
                                time.sleep(1); st.rerun()
                            except Exception as e:
                                st.error(f"Greška (ID vjerojatno postoji): {e}")
                        else:
                            st.warning("ID i Ime su obavezni.")

        # B) BRISANJE
        with c2:
            with st.expander("🗑️ Obriši Zaposlenika", expanded=False):
                st.warning("⚠️ PAŽNJA: Ovo briše Zaposlenika i SVE njegove podatke!")
                
                if not emps.empty:
                    del_choice = st.selectbox("Koga obrisati?", emps.apply(lambda x: f"{x['ime_prezime']} ({x['kadrovski_broj']})", axis=1))
                    
                    if del_choice:
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
                                    # Brišemo i login da ne ostane 'siroče'
                                    d_conn.execute("DELETE FROM users WHERE username=?", (del_id,)) 
                                    d_conn.commit()
                                st.toast("Obrisano!", icon="🗑️")
                                time.sleep(1); st.rerun()
                            except Exception as e:
                                st.error(f"Greška: {e}")

        # C) HITNI POPRAVAK
        st.markdown("---")
        with st.expander("🚨 ALAT ZA POPRAVAK IMPORTA (Fix Bad ID)", expanded=True):
            st.error("Koristi ovaj gumb ako u tablici vidiš redove gdje ID nije broj nego tekst.")
            if st.button("🧹 Očisti 'Zaglavlja' iz Baze (Force Delete)"):
                try:
                    with sqlite3.connect(DB_FILE) as fix_conn:
                        fix_conn.execute("DELETE FROM employees_master WHERE kadrovski_broj LIKE '%Kadrovski%' OR kadrovski_broj LIKE '%ID%' OR kadrovski_broj LIKE '%Broj%'")
                        fix_conn.commit()
                    st.success("Baza očišćena!")
                    time.sleep(2); st.rerun()
                except Exception as e:
                    st.error(f"Greška pri čišćenju: {e}")

    # ------------------------------------------------------------------
    # 2. LOGIN RAČUNI
    # ------------------------------------------------------------------
    with t_users:
        st.subheader("Upravljanje Login Pristupima (System Users)")
        
        # --- MASOVNI GENERATOR ---
        with st.expander("⚡ Masovno kreiranje korisnika (za one koji fale)", expanded=True):
            st.info("Ovaj alat će proći kroz sve zaposlenike u 'employees_master' i ako nemaju login, kreirat će ga (Pass: user123).")
            
            if st.button("🚀 Generiraj Logine za SVE propuštene"):
                try:
                    with sqlite3.connect(DB_FILE) as bulk_conn:
                        missing = bulk_conn.execute("""
                            SELECT m.kadrovski_broj, m.department 
                            FROM employees_master m 
                            LEFT JOIN users u ON m.kadrovski_broj = u.username 
                            WHERE u.username IS NULL
                        """).fetchall()
                        
                        if not missing:
                            st.success("Svi zaposlenici već imaju login račun! Nema posla.")
                        else:
                            count = 0
                            def_pass = make_hashes("user123")
                            for row in missing:
                                kid, dept = row[0], row[1]
                                bulk_conn.execute("INSERT INTO users (username, password, role, department) VALUES (?,?,?,?)", 
                                                 (str(kid), def_pass, 'Employee', dept))
                                count += 1
                            bulk_conn.commit()
                            st.success(f"✅ Uspješno kreirano {count} novih korisničkih računa!")
                            time.sleep(2); st.rerun()
                except Exception as e:
                    st.error(f"Greška: {e}")

        st.markdown("---")
        
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
            st.write("Kreiraj novi Login (samo User, bez zaposlenika):")
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
        col_b1, col_b2 = st.columns(2)
        with col_b1:
            st.subheader("Kreiraj Backup")
            if st.button("💾 Napravi Backup Sada"):
                s, m = perform_backup()
                if s: st.success(f"Backup kreiran: {m}")
                else: st.error(f"Greška: {m}")
        with col_b2:
            st.subheader("Učitaj Backup (Restore)")
            backups = get_available_backups()
            if backups:
                selected_backup = st.selectbox("Odaberi točku povratka:", backups)
                confirm_restore = st.checkbox("Razumijem da ću izgubiti podatke unesene nakon ovog backupa.")
                if st.button("♻️ RESTORE BAZU", disabled=not confirm_restore, type="primary"):
                    success, msg = restore_backup_file(selected_backup)
                    if success:
                        st.toast("Baza uspješno vraćena! Osvježavam...", icon="✅")
                        time.sleep(2); st.rerun()
                    else: st.error(f"Greška pri vraćanju: {msg}")
            else: st.info("Nema dostupnih backup datoteka.")

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