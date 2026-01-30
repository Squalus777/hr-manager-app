import streamlit as st
from modules.database import init_db
from modules.auth import login_screen
from modules.views_mgr import render_manager_view
from modules.views_hr import render_hr_view
from modules.views_employee import render_employee_view

# Inicijalizacija baze
init_db()

st.set_page_config(page_title="Tommy Talent", page_icon="🔴", layout="wide")

# Provjera prijave
if 'logged_in' not in st.session_state or not st.session_state['logged_in']:
    login_screen()
else:
    # Sidebar: Info i Odjava
    with st.sidebar:
        st.write(f"👤 **{st.session_state.get('username', 'Korisnik')}**")
        role = st.session_state.get('role', 'Employee')
        st.caption(f"Rola: {role}")
        
        # --- LOGIKA ZA PREBACIVANJE POGLEDA (Samo za Managere) ---
        view_mode = "Zaposlenik" # Default za obične radnike
        
        if role == 'Manager':
            st.markdown("---")
            st.write("👀 **Način pregleda:**")
            # Manager može birati
            view_choice = st.radio("Odaberi pogled:", ["👔 Voditelj (Moj Tim)", "👤 Zaposlenik (Moj Profil)"], label_visibility="collapsed")
            
            if view_choice == "👔 Voditelj (Moj Tim)":
                view_mode = "Manager"
            else:
                view_mode = "Employee"
        
        elif role == 'HR':
            view_mode = "HR"
            
        st.markdown("---")
        if st.button("🚪 Odjava"):
            st.session_state['logged_in'] = False
            st.session_state['username'] = None
            st.session_state['role'] = None
            st.rerun()

    # RUTER - Odlučujemo koji ekran prikazati na temelju ODABIRA, a ne samo role
    if view_mode == 'HR':
        render_hr_view()
    elif view_mode == 'Manager':
        render_manager_view()
    else:
        # Prikazuje se Employee view za obične radnike I za Managere koji su odabrali "Moj Profil"
        render_employee_view()