import sqlite3
import os
import shutil
import glob # <--- NOVO: Služi za traženje datoteka
from datetime import datetime

DB_FILE = 'talent_database.db'

def get_connection():
    """Vraća konekciju na bazu."""
    return sqlite3.connect(DB_FILE, check_same_thread=False)

def init_db():
    """Inicijalizira bazu podataka i tablice."""
    conn = get_connection()
    c = conn.cursor()
    
    # Kreiranje tablica
    c.execute('''CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT, role TEXT, department TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS employees_master (kadrovski_broj TEXT PRIMARY KEY, ime_prezime TEXT, radno_mjesto TEXT, department TEXT, manager_id TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS evaluations (id INTEGER PRIMARY KEY AUTOINCREMENT, period TEXT, kadrovski_broj TEXT, ime_prezime TEXT, radno_mjesto TEXT, department TEXT, manager_id TEXT, p1 REAL, p2 REAL, p3 REAL, p4 REAL, p5 REAL, pot1 REAL, pot2 REAL, pot3 REAL, pot4 REAL, pot5 REAL, avg_performance REAL, avg_potential REAL, category TEXT, action_plan TEXT, status TEXT, feedback_date TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS app_settings (setting_key TEXT PRIMARY KEY, setting_value TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS periods (period_name TEXT PRIMARY KEY, deadline TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS audit_log (id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp TEXT, user TEXT, action TEXT, details TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS goals (id INTEGER PRIMARY KEY AUTOINCREMENT, period TEXT, kadrovski_broj TEXT, manager_id TEXT, title TEXT, description TEXT, weight INTEGER, progress INTEGER, status TEXT, feedback TEXT, last_updated TEXT, deadline TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS goal_kpis (id INTEGER PRIMARY KEY AUTOINCREMENT, goal_id INTEGER, description TEXT, weight INTEGER, progress INTEGER, deadline TEXT, FOREIGN KEY(goal_id) REFERENCES goals(id))''')
    c.execute('''CREATE TABLE IF NOT EXISTS development_plans (id INTEGER PRIMARY KEY AUTOINCREMENT, period TEXT, kadrovski_broj TEXT, manager_id TEXT, strengths TEXT, areas_improve TEXT, career_goal TEXT, json_70 TEXT, json_20 TEXT, json_10 TEXT, support_needed TEXT, support_notes TEXT, status TEXT)''')
    
    # Migracije (sigurnosne provjere ako tablice već postoje)
    try: c.execute("ALTER TABLE goals ADD COLUMN deadline TEXT"); conn.commit()
    except: pass
    try: c.execute("ALTER TABLE goal_kpis ADD COLUMN deadline TEXT"); conn.commit()
    except: pass

    # Default admin
    c.execute("SELECT count(*) FROM users")
    if c.fetchone()[0] == 0:
        # Default hash za 'admin123'
        admin_hash = "240be518fabd2724ddb6f04eeb1da5967448d7e831c08c8fa822809f74c720a9" 
        c.execute("INSERT INTO users VALUES ('admin', ?, 'HR', 'Uprava')", (admin_hash,))
        c.execute("INSERT OR IGNORE INTO periods VALUES (?, ?)", ("2024-Q1", "2024-12-31"))
        c.execute("INSERT OR IGNORE INTO app_settings VALUES ('active_period', ?)", ("2024-Q1",))
        conn.commit()
    
    return conn

def log_action(user, action, details):
    conn = get_connection()
    conn.cursor().execute("INSERT INTO audit_log (timestamp, user, action, details) VALUES (?,?,?,?)", 
                          (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), user, action, details))
    conn.commit()

def perform_backup(auto=False):
    if not os.path.exists("backups"): os.makedirs("backups")
    ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    fn = f"backups/backup_{'AUTO' if auto else 'MANUAL'}_{ts}.db"
    try: 
        shutil.copy2(DB_FILE, fn)
        return True, fn
    except Exception as e: 
        return False, str(e)

# --- NOVE FUNKCIJE ZA RESTORE ---
def get_available_backups():
    """Vraća listu dostupnih backup datoteka sortiranu od najnovije."""
    if not os.path.exists("backups"): return []
    files = glob.glob("backups/*.db")
    files.sort(key=os.path.getmtime, reverse=True)
    return files

def restore_backup_file(backup_path):
    """Vraća bazu iz backupa. Prije toga radi safety backup trenutne."""
    try:
        # 1. Safety backup
        perform_backup(auto=True)
        # 2. Restore
        shutil.copy2(backup_path, DB_FILE)
        return True, "Uspješno vraćeno!"
    except Exception as e:
        return False, str(e)

def get_active_period_info():
    conn = get_connection()
    try:
        an = conn.cursor().execute("SELECT setting_value FROM app_settings WHERE setting_key='active_period'").fetchone()[0]
        dl = conn.cursor().execute("SELECT deadline FROM periods WHERE period_name=?", (an,)).fetchone()
        return an, dl[0] if dl else None
    except: return "2024-Q1", None