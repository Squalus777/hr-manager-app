import streamlit as st
import pandas as pd
# OVDJE JE BILA GREŠKA - dodao sam get_active_period_info u ovaj import red:
from modules.database import get_connection, perform_backup, log_action, get_active_period_info
# A maknuo ga iz ovog reda:
from modules.utils import check_hashes

def login_screen():
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        st.title("🔴 Tommy Talent")
        
        # Prikaz aktivnog perioda
        current_period, _ = get_active_period_info()
        st.info(f"Period: **{current_period}**")
        
        u = st.text_input("Korisničko ime")
        p = st.text_input("Lozinka", type="password")
        
        if st.button("Prijavi se"):
            conn = get_connection()
            c = conn.cursor()
            data = c.execute("SELECT password, role, department FROM users WHERE username=?", (u,)).fetchone()
            
            if data and check_hashes(p, data[0]):
                # Postavljanje sesije
                st.session_state.update({
                    'logged_in': True, 
                    'username': u, 
                    'role': data[1], 
                    'department': data[2]
                })
                
                log_action(u, "LOGIN", "Prijava u sustav")
                
                # Auto-backup za HR-a
                if data[1] == 'HR':
                    perform_backup(auto=True)
                
                st.rerun()
            else:
                st.error("Pogrešni podaci.")
        
        st.caption("Admin: admin / admin123")