import streamlit as st
import pandas as pd
import time
from modules.database import get_connection, perform_backup, get_active_period_info
from modules.utils import make_hashes

def render_admin_view():
    st.header("🛠️ Admin Panel")
    conn = get_connection()
    current_period, _ = get_active_period_info()
    
    t1, t2, t3, t4, t5 = st.tabs(["Korisnici", "Audit", "Backup", "Transfer", "🔐 Reset Lozinke"])
    
    # --- 1. KORISNICI ---
    with t1:
        st.info("Editiranje korisnika (osim User/Pass):")
        users_df = pd.read_sql_query("SELECT * FROM users", conn)
        # Onemogućeno uređivanje ključnih polja
        edited_users = st.data_editor(users_df, key="adm_u", disabled=["username", "password"])
        
        if st.button("Spremi promjene korisnika"):
            c = conn.cursor()
            for _, r in edited_users.iterrows():
                c.execute("UPDATE users SET role=?, department=? WHERE username=?", 
                          (r['role'], r['department'], r['username']))
            conn.commit()
            st.success("Promjene spremljene!")
            time.sleep(1)
            st.rerun()
        
        st.markdown("---")
        with st.form("nu"):
            st.write("Novi korisnik:")
            un = st.text_input("User")
            up = st.text_input("Pass", type="password")
            ur = st.selectbox("Role", ["Manager","HR"])
            ud = st.text_input("Dept")
            
            if st.form_submit_button("Kreiraj"):
                try:
                    c = conn.cursor()
                    c.execute("INSERT INTO users VALUES (?,?,?,?)", 
                              (un, make_hashes(up), ur, ud))
                    conn.commit()
                    st.success("OK")
                except:
                    st.error("Greška: Korisnik vjerojatno već postoji.")

    # --- 2. AUDIT ---
    with t2:
        st.dataframe(pd.read_sql_query("SELECT * FROM audit_log ORDER BY id DESC LIMIT 200", conn))

    # --- 3. BACKUP ---
    with t3:
        if st.button("Napravi Backup"):
            s, m = perform_backup()
            if s: st.success(f"Backup kreiran: {m}")
            else: st.error(f"Greška: {m}")

    # --- 4. TRANSFER ---
    with t4:
        st.subheader("Transfer Zaposlenika")
        st.info("Ovo prebacuje zaposlenika i sve njegove podatke (za trenutni period) novom manageru.")
        
        emps = pd.read_sql_query("SELECT * FROM employees_master", conn)
        mgrs = pd.read_sql_query("SELECT username FROM users WHERE role='Manager'", conn)
        
        c1, c2 = st.columns(2)
        te_sel = c1.selectbox("Zaposlenik:", emps.apply(lambda x: f"{x['ime_prezime']} ({x['kadrovski_broj']})", axis=1))
        nm = c2.selectbox("Novi Manager:", mgrs['username'])
        
        if st.button("Izvrši Transfer"):
            eid = te_sel.split("(")[1].replace(")", "")
            c = conn.cursor()
            
            # Update master
            c.execute("UPDATE employees_master SET manager_id=? WHERE kadrovski_broj=?", (nm, eid))
            
            # Update transakcijskih tablica za trenutni period
            for t in ["evaluations", "goals", "development_plans"]:
                c.execute(f"UPDATE {t} SET manager_id=? WHERE kadrovski_broj=? AND period=?", 
                          (nm, eid, current_period))
            
            conn.commit()
            st.success(f"Zaposlenik {eid} uspješno transferiran manageru {nm}!")

    # --- 5. RESET LOZINKE ---
    with t5:
        st.subheader("Resetiranje lozinke")
        users_list = pd.read_sql_query("SELECT username FROM users", conn)['username'].tolist()
        user_to_reset = st.selectbox("Odaberi korisnika za reset:", users_list)
        new_pass = st.text_input("Nova lozinka:", type="password")
        
        if st.button("Promijeni lozinku"):
            if new_pass:
                c = conn.cursor()
                c.execute("UPDATE users SET password=? WHERE username=?", 
                          (make_hashes(new_pass), user_to_reset))
                conn.commit()
                st.success(f"Lozinka za {user_to_reset} je promijenjena.")
            else:
                st.warning("Unesite novu lozinku.")