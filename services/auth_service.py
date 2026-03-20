import sqlite3
from datetime import datetime, timedelta
from passlib.context import CryptContext
from jose import jwt
from database.db_manager import get_connection

SECRET_KEY = "mandal_super_secret_key_change_this"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7 

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class AuthService:
    def __init__(self):
        self._ensure_tables()

    def _ensure_tables(self):
        conn = get_connection()
        try:
            # 1. યુઝર્સ ટેબલ બનાવો
            conn.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    mandal_id INTEGER NOT NULL DEFAULT 0,
                    name TEXT,
                    mobile TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    role TEXT NOT NULL,
                    status TEXT DEFAULT 'Active',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # 🪄 2. જો ટેબલ ખાલી હોય, તો માસ્ટર એડમિન ઓટોમેટિક બનાવો! (આ જ ખૂટતું હતું)
            cur = conn.execute("SELECT COUNT(*) FROM users")
            if cur.fetchone()[0] == 0:
                hashed_pwd = pwd_context.hash("admin123")
                conn.execute("""
                    INSERT INTO users (mandal_id, name, mobile, password_hash, role)
                    VALUES (0, 'Master Admin', '9722278384', ?, 'Master Admin')
                """, (hashed_pwd,))
                
            conn.commit()
        except Exception as e:
            print("Auth DB Error:", e)
        finally:
            conn.close()

    def create_access_token(self, data: dict):
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt

    def authenticate_user(self, mobile: str, password: str):
        conn = get_connection()
        conn.row_factory = sqlite3.Row
        try:
            cur = conn.execute("SELECT * FROM users WHERE mobile=?", (mobile,))
            user = cur.fetchone()
            
            if not user:
                return False, "આ મોબાઈલ નંબર નોંધાયેલો નથી."
            
            if user['status'] != 'Active':
                return False, "તમારું એકાઉન્ટ બ્લોક કરવામાં આવ્યું છે."
                
            if pwd_context.verify(password, user['password_hash']):
                user_dict = dict(user)
                del user_dict['password_hash']
                
                access_token = self.create_access_token(data={
                    "sub": user['mobile'], 
                    "role": user['role'],
                    "mandal_id": user['mandal_id']
                })
                
                return {
                    "access_token": access_token, 
                    "token_type": "bearer", 
                    "user": user_dict
                }, "Login Successful"
            else:
                return False, "પાસવર્ડ ખોટો છે."
        finally:
            conn.close()