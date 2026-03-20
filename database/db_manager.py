import sqlite3
import os

# 🪄 આ આપણી ડેટાબેઝ ફાઈલનું નામ છે (જે backend ફોલ્ડરમાં જ બનશે)
DB_FILE = "mandal_erp.db"

def get_connection():
    """ડેટાબેઝ સાથે સુરક્ષિત જોડાણ (Connection) બનાવવા માટેનું માસ્ટર ફંક્શન"""
    
    # backend ફોલ્ડરનો સાચો રસ્તો (Path) શોધવા માટે
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    db_path = os.path.join(base_dir, DB_FILE)
    
    # ડેટાબેઝ સાથે કનેક્શન ચાલુ કરો
    conn = sqlite3.connect(db_path)
    
    # આ સેટિંગથી ડેટા આપણને Dictionary ફોર્મેટમાં મળશે, જે React માટે બેસ્ટ છે
    conn.row_factory = sqlite3.Row 
    
    return conn