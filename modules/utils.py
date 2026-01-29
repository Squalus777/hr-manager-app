import hashlib
import pandas as pd
import json
import streamlit as st

# --- KONSTANTE (VRAĆENI BOGATI OPISI) ---
METRICS = {
    "p": [
        {"id": "P1", "title": "KPI i Ciljevi", "def": "Ispunjenje brojčanih ciljeva i rokova definiranih na početku razdoblja.", "crit": "Za 5: Značajno premašuje ciljeve, ne traži izgovore, proaktivan u rješavanju prepreka."},
        {"id": "P2", "title": "Kvaliteta rada", "def": "Točnost, temeljitost i pouzdanost u izvršavanju zadataka.", "crit": "Za 5: Rad je bez grešaka, povjerenje je 100%, kolege se oslanjaju na njegov output."},
        {"id": "P3", "title": "Stručnost", "def": "Tehničko znanje i vještine potrebne za samostalan rad.", "crit": "Za 5: Ekspert u svom području, prenosi znanje drugima, rješava najkompleksnije probleme."},
        {"id": "P4", "title": "Odgovornost", "def": "Osjećaj vlasništva nad konačnim uspjehom zadatka ili projekta.", "crit": "Za 5: Ponaša se kao vlasnik, brine o široj slici, ne čeka da mu se kaže što treba napraviti."},
        {"id": "P5", "title": "Suradnja", "def": "Timski rad, komunikacija i kolegijalnost.", "crit": "Za 5: Gradi mostove među odjelima, nesebično dijeli znanje, podiže moral tima."}
    ],
    "pot": [
        {"id": "POT1", "title": "Agilnost učenja", "def": "Brzina usvajanja novih vještina i prilagodba promjenama.", "crit": "Za 5: Uči iznimno brzo, traži nove izazove, u promjenama vidi priliku a ne prijetnju."},
        {"id": "POT2", "title": "Prirodni autoritet", "def": "Utjecaj na kolege neovisno o formalnoj tituli.", "crit": "Za 5: Drugi ga prirodno slijede i slušaju, lider bez titule, inspirira okolinu."},
        {"id": "POT3", "title": "Šira slika", "def": "Razumijevanje poslovanja izvan svog uskog dijela (Strategic Mindset).", "crit": "Za 5: Razumije kako njegov rad utječe na profitabilnost tvrtke, predlaže strateška poboljšanja."},
        {"id": "POT4", "title": "Ambicija", "def": "Želja za napredovanjem i preuzimanjem veće odgovornosti.", "crit": "Za 5: Jasno pokazuje želju za rastom, proaktivan u traženju feedbacka, 'gladan' uspjeha."},
        {"id": "POT5", "title": "Stabilnost", "def": "Upravljanje stresom i emocijama u teškim situacijama.", "crit": "Za 5: Ostaje smiren i fokusiran kad je najteže, djeluje umirujuće na tim, 'stijena'."}
    ]
}

# --- AUTH HELPERI ---
def make_hashes(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def check_hashes(password, hashed_text):
    return make_hashes(password) == hashed_text

# --- LOGIKA PROCJENE ---
def calculate_category(p, pot):
    if p>=4 and pot>=4: return "1. Vrhunski talent (Top Talent)"
    elif p>=4 and pot>=3: return "2. Visoki učinak (High Performer)"
    elif p>=4 and pot<3: return "3. Stručnjak (Expert)"
    elif p>=3 and pot>=4: return "4. Rastući potencijal"
    elif p>=3 and pot>=3: return "5. Pouzdan suradnik"
    elif p>=3 and pot<3: return "6. Solidan izvođač"
    elif p<3 and pot>=4: return "7. Talent u razvoju"
    elif p<3 and pot>=3: return "8. Nekonzistentan"
    else: return "9. Ispod očekivanja"

# --- UI KOMPONENTE ---
def render_metric_input(m, key_prefix, val=3, type="perf"):
    css_class = "metric-card-perf" if type == "perf" else "metric-card-pot"
    try: val = int(val)
    except: val = 3
    
    st.markdown(f"""
    <div class="{css_class}">
        <div style="font-weight:bold; color:#333;">{m['id']}: {m['title']}</div>
        <div style="font-size:13px; color:#666; margin-bottom:3px;">{m['def']}</div>
        <div style="font-size:11px; color:#999; font-style:italic;">{m['crit']}</div>
    </div>
    """, unsafe_allow_html=True)
    return st.slider(f"Ocjena ({m['id']})", 1, 5, val, key=f"{key_prefix}_{m['id']}")

# --- KLJUČNE FUNKCIJE ZA SPREMANJE PODATAKA ---
def table_to_json_string(df):
    if df is None or df.empty: return "[]"
    try:
        df_str = df.astype(str)
        records = df_str.to_dict(orient='records')
        clean_records = []
        for row in records:
            is_empty = True
            clean_row = {}
            for k, v in row.items():
                if v and v.lower() not in ['nan', 'none', ''] and v.strip() != "":
                    is_empty = False
                    clean_row[k] = v
                else:
                    clean_row[k] = ""
            if not is_empty: clean_records.append(clean_row)
        return json.dumps(clean_records, ensure_ascii=False)
    except: return "[]"

def get_df_from_json(json_str, columns):
    try:
        data = json.loads(json_str) if json_str else []
        return pd.DataFrame(data, columns=columns)
    except:
        return pd.DataFrame(columns=columns)