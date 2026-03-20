import sqlite3
from database.db_manager import get_connection

class SettingsService:
    def __init__(self):
        self._ensure_tables()

    def _ensure_tables(self):
        """નવું 360° ડાયનેમિક ડેટાબેઝ માળખું બનાવશે"""
        conn = get_connection()
        try:
            # ૧. સેટિંગ્સની વેલ્યૂ સેવ કરવાનું ટેબલ
            conn.execute('''
                CREATE TABLE IF NOT EXISTS settings (
                    mandal_id INTEGER,
                    setting_key TEXT,
                    setting_value TEXT,
                    PRIMARY KEY (mandal_id, setting_key)
                )
            ''')
            
            # ૨. માસ્ટર એડમીન જે નવા ફિલ્ડ બનાવશે તેનું ટેબલ (EAV Brain)
            conn.execute('''
                CREATE TABLE IF NOT EXISTS dynamic_fields (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    module TEXT NOT NULL,
                    field_label TEXT NOT NULL,
                    field_key TEXT UNIQUE NOT NULL,
                    field_type TEXT NOT NULL,
                    options TEXT
                )
            ''')
            conn.commit()
        except Exception as e:
            print("Settings DB Error:", e)
        finally:
            conn.close()

    # ---------------------------------------------------------
    # 🧠 ડાયનેમિક ફિલ્ડ મેનેજર (EAV Engine)
    # ---------------------------------------------------------
    def add_dynamic_field(self, module, label, key, f_type, options):
        """માસ્ટર એડમિન નવું ફિલ્ડ બનાવશે ત્યારે આ ફંક્શન તેને સેવ કરશે"""
        conn = get_connection()
        try:
            conn.execute("""
                INSERT INTO dynamic_fields (module, field_label, field_key, field_type, options)
                VALUES (?, ?, ?, ?, ?)
            """, (module, label, key, f_type, options))
            conn.commit()
            return True, "ફિલ્ડ સફળતાપૂર્વક ઉમેરાઈ ગયું!"
        except sqlite3.IntegrityError:
            return False, "આ નામનું ફિલ્ડ અથવા ID પહેલેથી જ સિસ્ટમમાં હાજર છે."
        finally:
            conn.close()

    def get_dynamic_fields(self):
        """સુપર એડમિન અને માસ્ટર એડમિનને જોવા માટે બધા ફિલ્ડ્સ લાવશે"""
        conn = get_connection()
        conn.row_factory = sqlite3.Row
        try:
            cur = conn.execute("SELECT * FROM dynamic_fields")
            return [dict(row) for row in cur.fetchall()]
        finally:
            conn.close()

    def delete_dynamic_field(self, field_key: str):
        """માસ્ટર એડમિન ફિલ્ડ ડિલીટ કરે ત્યારે આ ફંક્શન ડેટાબેઝમાંથી કાઢી નાખશે"""
        conn = get_connection()
        try:
            # 1. ડાયનેમિક ફિલ્ડ ટેબલમાંથી કાઢો
            conn.execute("DELETE FROM dynamic_fields WHERE field_key=?", (field_key,))
            # 2. જો કોઈ મંડળે વેલ્યૂ ભરી હોય તો settings માંથી પણ કાઢો
            conn.execute("DELETE FROM settings WHERE setting_key=?", (field_key,))
            conn.commit()
            return True, "ફિલ્ડ સફળતાપૂર્વક ડિલીટ થઈ ગયું."
        except Exception as e:
            return False, "એરર: " + str(e)
        finally:
            conn.close()
    # ---------------------------------------------------------
    # ⚙️ સેટિંગ્સ વેલ્યૂ મેનેજર
    # ---------------------------------------------------------
    def load(self, mandal_id: int):
        conn = get_connection()
        cache = {}
        try:
            cur = conn.execute("SELECT setting_key, setting_value FROM settings WHERE mandal_id=?", (mandal_id,))
            for row in cur.fetchall():
                cache[row['setting_key']] = str(row['setting_value'])
            return cache
        finally:
            conn.close()

    def update(self, mandal_id: int, key: str, value: str):
        conn = get_connection()
        try:
            cur = conn.execute("SELECT 1 FROM settings WHERE mandal_id=? AND setting_key=?", (mandal_id, key))
            exists = cur.fetchone()
            
            if exists:
                conn.execute("UPDATE settings SET setting_value=? WHERE mandal_id=? AND setting_key=?", (str(value), mandal_id, key))
            else:
                conn.execute("INSERT INTO settings (mandal_id, setting_key, setting_value) VALUES (?, ?, ?)", (mandal_id, key, str(value)))
                
            conn.commit()
        finally:
            conn.close()