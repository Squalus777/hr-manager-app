import streamlit as st
from modules.database import init_db
from modules.auth import login_screen
from modules.views_mgr import render_manager_view
from modules.views_hr import render_hr_view

# Inicijalizacija baze
init_db()

# Provjera prijave
if 'logged_in' not in st.session_state or not st.session_state['logged_in']:
    login_screen()
else:
    # --- NOVO: GUMB ZA ODJAVU U SIDEBARU ---
    with st.sidebar:
        st.write(f"👤 **{st.session_state.get('username', 'Korisnik')}**")
        st.caption(f"Rola: {st.session_state.get('role', '-')}")
        if st.button("Odjava"):
            st.session_state['logged_in'] = False
            st.rerun()
        st.markdown("---") # Linija razdvajanja
    # ---------------------------------------

    # Usmjeravanje ovisno o roli
    role = st.session_state.get('role', 'Manager')
    
    if role == 'HR':
        render_hr_view()
    else:
        render_manager_view()