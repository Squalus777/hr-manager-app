import hashlib
import pandas as pd
import json
import streamlit as st

# --- KONSTANTE I DEFINICIJE OCJENA ---
METRICS = {
    "p": [
        {"id": "P1", "title": "KPI i Ciljevi", "def": "Ispunjenje brojčanih ciljeva i rokova definiranih na početku razdoblja.", "crit": "Za 5: Značajno premašuje ciljeve, ne traži izgovore, proaktivan u rješavanju prepreka."},
        {"id": "P2", "title": "Kvaliteta rada", "def": "Točnost, temeljitost i pouzdanost u izvršavanju zadataka.", "crit": "Za 5: Rad je bez grešaka, povjerenje je 100%, kolege se oslanjaju na njegov output."},
        {"id": "P3", "title": "Stručnost", "def": "Tehničko znanje i vještine potrebne za samostalan rad.", "crit": "Za 5: Ekspert u svom području, prenosi znanje drugima, rješava najkompleksnije probleme."},
        {"id": "P4", "title": "Odgovornost", "def": "Osjećaj vlasništva nad konačnim uspjehom zadatka ili projekta.", "crit": "Za 5: Ponaša se kao vlasnik, brine o široj slici, ne čeka da mu se kaže što treba napraviti."},
        {"id": "P5", "title": "Suradnja", "def": "Timski rad, komunikacija i dijeljenje informacija.", "crit": "Za 5: Osoba s kojom svi žele raditi, gradi mostove između odjela, smiruje konflikte."}
    ],
    "pot": [
        {"id": "POT1", "title": "Agilnost učenja", "def": "Brzina usvajanja novih znanja i prilagodba promjenama.", "crit": "Za 5: Uči izuzetno brzo, traži nove izazove, samostalno se educira izvan radnog vremena."},
        {"id": "POT2", "title": "Autoritet / Utjecaj", "def": "Sposobnost utjecaja na druge bez formalne moći.", "crit": "Za 5: Prirodni lider, ljudi ga slušaju i poštuju njegovo mišljenje čak i ako im nije šef."},
        {"id": "POT3", "title": "Šira slika", "def": "Razumijevanje kako vlastiti rad utječe na ciljeve tvrtke.", "crit": "Za 5: Razmišlja strateški, predlaže rješenja koja koriste cijeloj firmi, a ne samo njemu."},
        {"id": "POT4", "title": "Ambicija / Drive", "def": "Unutarnja motivacija za napredovanjem i postizanjem više.", "crit": "Za 5: Ne zadovoljava se prosjekom, uvijek traži 'što je iduće', gura granice."},
        {"id": "POT5", "title": "Emocionalna stabilnost", "def": "Zadržavanje fokusa i smirenosti pod pritiskom.", "crit": "Za 5: Stijena u oluji, smiruje druge kad je kriza, donosi racionalne odluke pod stresom."}
    ]
}

# --- FUNKCIJE ZA LOZINKE (KRITIČNO BITNO!) ---
def make_hashes(password):
    """Kreira SHA256 hash od lozinke."""
    return hashlib.sha256(str.encode(password)).hexdigest()

def check_hashes(password, hashed_text):
    """Provjerava odgovara li lozinka hashu."""
    if make_hashes(password) == hashed_text:
        return True
    return False

# --- POMOĆNE FUNKCIJE ZA TABLICE I JSON ---
def calculate_category(perf, pot):
    """Računa 9-Box kategoriju (1-5 skala)."""
    # Performance (X os)
    if perf <= 2.5: p_cat = "Low"
    elif perf <= 3.8: p_cat = "Moderate"
    else: p_cat = "High"
    
    # Potential (Y os)
    if pot <= 2.5: pot_cat = "Low"
    elif pot <= 3.8: pot_cat = "Moderate"
    else: pot_cat = "High"
    
    matrix = {
        ("Low", "Low"): "9. Risk / Underperformer",
        ("Moderate", "Low"): "8. Effective / Solid",
        ("High", "Low"): "7. Trusted Professional",
        ("Low", "Moderate"): "6. Inconsistent Player",
        ("Moderate", "Moderate"): "5. Core Performer",
        ("High", "Moderate"): "4. High Impact",
        ("Low", "High"): "3. Potential Gem",
        ("Moderate", "High"): "2. Rising Star",
        ("High", "High"): "1. Top Talent / Star"
    }
    return matrix.get((p_cat, pot_cat), "Unclassified")

def table_to_json_string(df):
    """Pretvara pandas DataFrame u JSON string za bazu."""
    if df is None or df.empty: return "[]"
    try:
        # Konvertiramo sve u string da izbjegnemo probleme s tipovima
        df_str = df.astype(str)
        records = df_str.to_dict(orient='records')
        # Čistimo prazne redove
        clean_records = []
        for row in records:
            # Provjera je li red prazan (sve vrijednosti su None, '' ili 'nan')
            is_empty = True
            clean_row = {}
            for k, v in row.items():
                if v and v.lower() not in ['nan', 'none', ''] and v.strip() != "":
                    is_empty = False
                    clean_row[k] = v
                else:
                    clean_row[k] = ""
            if not is_empty:
                clean_records.append(clean_row)
        
        return json.dumps(clean_records, ensure_ascii=False)
    except Exception:
        return "[]"

def get_df_from_json(json_str, columns):
    """Vraća DataFrame iz JSON stringa."""
    if not json_str: return pd.DataFrame(columns=columns)
    try:
        data = json.loads(json_str)
        if not data: return pd.DataFrame(columns=columns)
        df = pd.DataFrame(data)
        # Osiguraj da imamo sve potrebne kolone čak i ako fale u JSON-u
        for col in columns:
            if col not in df.columns:
                df[col] = ""
        return df[columns] # Vrati samo tražene kolone u pravom redoslijedu
    except:
        return pd.DataFrame(columns=columns)

def render_metric_input(m, key_prefix, default_val=3.0, type="perf"):
    """Prikazuje karticu s opisom kompetencije i sliderom."""
    css_class = "metric-card-perf" if type == "perf" else "metric-card-pot"
    try: val = int(float(default_val))
    except: val = 3
    
    st.markdown(f"""
    <div style="background-color: {'#e6f3ff' if type == 'perf' else '#fff0e6'}; padding: 10px; border-radius: 5px; margin-bottom: 10px; border-left: 5px solid {'#2196F3' if type == 'perf' else '#FF9800'};">
        <div style="font-weight:bold; color:#333;">{m['id']}: {m['title']}</div>
        <div style="font-size:13px; color:#666; margin-bottom:3px;">{m['def']}</div>
        <div style="font-size:11px; color:#999; font-style:italic;">{m['crit']}</div>
    </div>
    """, unsafe_allow_html=True)
    return st.slider(f"Ocjena ({m['id']})", 1, 5, val, key=f"{key_prefix}_{m['id']}")