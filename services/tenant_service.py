import sqlite3
import random
import string
from datetime import datetime
from passlib.context import CryptContext
from database.db_manager import get_connection

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class TenantService:
    def __init__(self):
        self._ensure_tables()

    def _ensure_tables(self):
        conn = get_connection()
        try:
            conn.execute('''CREATE TABLE IF NOT EXISTS subscription_plans (
                id INTEGER PRIMARY KEY AUTOINCREMENT, plan_code TEXT UNIQUE NOT NULL, plan_name TEXT NOT NULL,
                max_members TEXT NOT NULL, price_per_year REAL NOT NULL, features TEXT, status TEXT DEFAULT 'Active')''')
            
            conn.execute('''CREATE TABLE IF NOT EXISTS mandals (
                id INTEGER PRIMARY KEY AUTOINCREMENT, mandal_code TEXT UNIQUE NOT NULL, name TEXT NOT NULL,
                reg_no TEXT, address TEXT, contact_person TEXT, mobile TEXT, email TEXT,
                max_members INTEGER DEFAULT 500, status TEXT DEFAULT 'Active', subscription_end_date TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')

            conn.execute('''CREATE TABLE IF NOT EXISTS invoices (
                id INTEGER PRIMARY KEY AUTOINCREMENT, invoice_no TEXT UNIQUE NOT NULL, invoice_date TEXT NOT NULL,
                mandal_name TEXT NOT NULL, plan_name TEXT NOT NULL, validity TEXT NOT NULL, amount REAL NOT NULL,
                payment_mode TEXT, transaction_id TEXT, status TEXT DEFAULT 'Paid', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')

            # 📢 નવું કોમ્યુનિકેશન ટેબલ
            conn.execute('''CREATE TABLE IF NOT EXISTS broadcasts (
                id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL, target_audience TEXT NOT NULL,
                channels TEXT NOT NULL, message TEXT NOT NULL, status TEXT DEFAULT 'Delivered', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')

                        # 🏢 સુપર એડમિન (મંડળ) ના પોતાના સેટિંગ્સ માટેનું ટેબલ
            conn.execute('''CREATE TABLE IF NOT EXISTS tenant_settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                mandal_id INTEGER NOT NULL,
                setting_key TEXT NOT NULL,
                setting_value TEXT NOT NULL,
                UNIQUE(mandal_id, setting_key)
            )''')

            cur = conn.execute("SELECT COUNT(*) FROM subscription_plans")
            if cur.fetchone()[0] == 0:
                year = datetime.now().year
                conn.execute("INSERT INTO subscription_plans (plan_code, plan_name, max_members, price_per_year, features) VALUES (?, 'Basic', '500', 6750, 'Loans, Basic Reports')", (f"SUB-{year}-BAS-001",))
                conn.execute("INSERT INTO subscription_plans (plan_code, plan_name, max_members, price_per_year, features) VALUES (?, 'Premium', '1000', 9600, 'Loans, Adv Reports, WhatsApp')", (f"SUB-{year}-PRE-002",))
                conn.execute("INSERT INTO subscription_plans (plan_code, plan_name, max_members, price_per_year, features) VALUES (?, 'Enterprise', 'Unlimited', 14500, 'All Features Unlocked')", (f"SUB-{year}-ENT-003",))
            conn.commit()
        except Exception as e: print("Tenant DB Error:", e)
        finally: conn.close()

    def generate_mandal_code(self, name):
        prefix = "".join([c for c in name if c.isalpha()][:3]).upper()
        if len(prefix) < 3: prefix = "MND"
        return f"{prefix}-{''.join(random.choices(string.digits, k=4))}"

    def _get_setting(self, conn, key, default_value):
        try:
            conn.row_factory = sqlite3.Row
            cur = conn.execute("SELECT setting_value FROM settings WHERE mandal_id=0 AND setting_key=?", (key,))
            row = cur.fetchone()
            return row['setting_value'] if row else default_value
        except: return default_value

    # --- મંડળ ઓનબોર્ડિંગ ---
    def create_mandal(self, name, frontend_reg_no, address, admin_name, mobile, email, max_members, end_date, admin_password, status):
        conn = get_connection()
        try:
            mandal_code = self.generate_mandal_code(name)
            format_str = self._get_setting(conn, 'mandal_reg_format', '{state}-{year}-{mandal_code}-{sequence}')
            cur = conn.execute("SELECT MAX(id) FROM mandals")
            max_id = cur.fetchone()[0] or 0
            auto_reg_no = format_str.replace('{state}', 'GUJ').replace('{year}', str(datetime.now().year)).replace('{mandal_code}', mandal_code).replace('{sequence}', f"{max_id + 1:03d}")

            cur = conn.execute("INSERT INTO mandals (mandal_code, name, reg_no, address, contact_person, mobile, email, max_members, subscription_end_date, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (mandal_code, name, auto_reg_no, address, admin_name, mobile, email, max_members, end_date, status))
            conn.execute("INSERT INTO users (mandal_id, name, mobile, password_hash, role, status) VALUES (?, ?, ?, ?, 'Super Admin', 'Active')", (cur.lastrowid, admin_name, mobile, pwd_context.hash(admin_password)))
            conn.commit()
            return True, f"🎉 મંડળ બની ગયું! રજી. નંબર: {auto_reg_no}"
        except sqlite3.IntegrityError: return False, "આ મોબાઈલ નંબર પહેલેથી નોંધાયેલો છે."
        except Exception as e: return False, str(e)
        finally: conn.close()

    def get_all_mandals(self):
        conn = get_connection(); conn.row_factory = sqlite3.Row
        try: cur = conn.execute("SELECT m.*, (SELECT COUNT(*) FROM users u WHERE u.mandal_id = m.id AND u.role != 'Super Admin') as joined_members FROM mandals m ORDER BY m.id DESC"); return [dict(r) for r in cur.fetchall()]
        finally: conn.close()

    def delete_mandal(self, mandal_id):
        conn = get_connection()
        try: conn.execute("DELETE FROM users WHERE mandal_id=?", (mandal_id,)); conn.execute("DELETE FROM mandals WHERE id=?", (mandal_id,)); conn.commit(); return True, "મંડળ ડિલીટ થઈ ગયું!"
        except Exception as e: return False, str(e)
        finally: conn.close()

    # --- પ્લેટફોર્મ સ્ટાફ ---
    def create_platform_user(self, name, mobile, password, role, status='Active'):
        conn = get_connection()
        try: conn.execute("INSERT INTO users (mandal_id, name, mobile, password_hash, role, status) VALUES (0, ?, ?, ?, ?, ?)", (name, mobile, pwd_context.hash(password), role, status)); conn.commit(); return True, "સ્ટાફ ઉમેરાઈ ગયો!"
        except: return False, "એરર"
        finally: conn.close()

    def get_platform_users(self):
        conn = get_connection(); conn.row_factory = sqlite3.Row
        try: cur = conn.execute("SELECT id, name, mobile, role, status, created_at FROM users WHERE mandal_id = 0 ORDER BY id DESC"); return [dict(r) for r in cur.fetchall()]
        finally: conn.close()

    def update_platform_user(self, user_id, name, mobile, role, status, password=None):
        conn = get_connection()
        try:
            if password: conn.execute("UPDATE users SET name=?, mobile=?, role=?, status=?, password_hash=? WHERE id=? AND mandal_id=0", (name, mobile, role, status, pwd_context.hash(password), user_id))
            else: conn.execute("UPDATE users SET name=?, mobile=?, role=?, status=? WHERE id=? AND mandal_id=0", (name, mobile, role, status, user_id))
            conn.commit(); return True, "અપડેટ થઈ ગયું!"
        except: return False, "એરર"
        finally: conn.close()

    def delete_platform_user(self, user_id):
        conn = get_connection()
        try: conn.execute("DELETE FROM users WHERE id=? AND mandal_id=0", (user_id,)); conn.commit(); return True, "ડિલીટ થઈ ગયું!"
        except: return False, "એરર"
        finally: conn.close()

    # --- લવાજમ પ્લાન ---
    def get_subscription_plans(self):
        conn = get_connection(); conn.row_factory = sqlite3.Row
        try: cur = conn.execute("SELECT * FROM subscription_plans ORDER BY id DESC"); return [dict(r) for r in cur.fetchall()]
        finally: conn.close()

    def create_subscription_plan(self, plan_name, max_members, price_per_year, features, status):
        conn = get_connection()
        try:
            cur = conn.execute("SELECT MAX(id) FROM subscription_plans")
            plan_code = f"SUB-{datetime.now().year}-{plan_name[:3].upper()}-{(cur.fetchone()[0] or 0) + 1:03d}"
            conn.execute("INSERT INTO subscription_plans (plan_code, plan_name, max_members, price_per_year, features, status) VALUES (?, ?, ?, ?, ?, ?)", (plan_code, plan_name, max_members, price_per_year, features, status))
            conn.commit(); return True, "નવો પ્લાન સફળતાપૂર્વક ઉમેરાઈ ગયો!"
        except Exception as e: return False, str(e)
        finally: conn.close()

    def delete_subscription_plan(self, plan_id):
        conn = get_connection()
        try: conn.execute("DELETE FROM subscription_plans WHERE id=?", (plan_id,)); conn.commit(); return True, "પ્લાન ડીલીટ થઈ ગયો!"
        except: return False, "એરર"
        finally: conn.close()

    # --- ઇન્વોઇસ ---
    def get_all_invoices(self):
        conn = get_connection(); conn.row_factory = sqlite3.Row
        try: cur = conn.execute("SELECT * FROM invoices ORDER BY id DESC"); return [dict(r) for r in cur.fetchall()]
        finally: conn.close()

    def create_invoice(self, invoice_no, invoice_date, mandal_name, plan_name, validity, amount, payment_mode, transaction_id, status):
        conn = get_connection()
        try:
            conn.execute("INSERT INTO invoices (invoice_no, invoice_date, mandal_name, plan_name, validity, amount, payment_mode, transaction_id, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", (invoice_no, invoice_date, mandal_name, plan_name, validity, amount, payment_mode, transaction_id, status))
            conn.commit(); return True, "ઇન્વોઇસ સેવ થઈ ગયું!"
        except: return False, "એરર"
        finally: conn.close()

    def update_invoice_status(self, invoice_id, status):
        conn = get_connection()
        try: conn.execute("UPDATE invoices SET status=? WHERE id=?", (status, invoice_id)); conn.commit(); return True, "બિલનું સ્ટેટસ બદલાઈ ગયું!"
        except: return False, "એરર"
        finally: conn.close()

    def delete_invoice(self, invoice_id):
        conn = get_connection()
        try: conn.execute("DELETE FROM invoices WHERE id=?", (invoice_id,)); conn.commit(); return True, "બિલ ડીલીટ થઈ ગયું!"
        except: return False, "એરર"
        finally: conn.close()

    # ---------------------------------------------------------
    # 📢 ગ્લોબલ કોમ્યુનિકેશન (નવા ઉમેરેલા ફંક્શન્સ)
    # ---------------------------------------------------------
    def get_communication_stats(self):
        conn = get_connection()
        try:
            # ભવિષ્યમાં આ API થી આવશે, અત્યારે ગણતરી કરીએ છીએ
            sms_credits = 24500 
            cur = conn.execute("SELECT COUNT(*) FROM broadcasts WHERE channels LIKE '%WhatsApp%'")
            wa_sent = cur.fetchone()[0] * 12 # સરેરાશ 12 મંડળ
            cur = conn.execute("SELECT COUNT(*) FROM broadcasts WHERE channels LIKE '%In-App%' AND status='Delivered'")
            in_app_active = cur.fetchone()[0]
            return {"sms_credits": sms_credits, "whatsapp_sent": wa_sent, "in_app_active": in_app_active}
        finally: conn.close()

    def get_broadcasts(self):
        conn = get_connection(); conn.row_factory = sqlite3.Row
        try: cur = conn.execute("SELECT * FROM broadcasts ORDER BY id DESC"); return [dict(r) for r in cur.fetchall()]
        finally: conn.close()

    def create_broadcast(self, title, target_audience, channels, message):
        conn = get_connection()
        try:
            conn.execute("INSERT INTO broadcasts (title, target_audience, channels, message) VALUES (?, ?, ?, ?)", (title, target_audience, channels, message))
            conn.commit(); return True, "બ્રોડકાસ્ટ સફળતાપૂર્વક ફાયર થઈ ગયો!"
        except Exception as e: return False, str(e)
        finally: conn.close()

# ---------------------------------------------------------
    # 📊 માસ્ટર એનાલિટિક્સ અને રિપોર્ટ્સ (Master Reports)
    # ---------------------------------------------------------
    def get_master_kpi(self):
        """ઉપરના 3 મોટા કાર્ડ્સ માટે રિયલ-ટાઇમ ડેટા ગણવા"""
        conn = get_connection()
        try:
            # 1. સરેરાશ મેમ્બર્સ (Avg Members)
            cur = conn.execute("SELECT COUNT(id) FROM mandals")
            total_mandals = cur.fetchone()[0] or 0
            
            cur = conn.execute("SELECT COUNT(id) FROM users WHERE role != 'Super Admin' AND mandal_id != 0")
            total_members = cur.fetchone()[0] or 0
            avg_members = (total_members / total_mandals) if total_mandals > 0 else 0
            
            # 2. ગ્લોબલ આવક (Total Revenue from Paid Invoices)
            cur = conn.execute("SELECT SUM(amount) FROM invoices WHERE status='Paid'")
            total_revenue = cur.fetchone()[0] or 0
            
            return {
                "avg_members": round(avg_members),
                "total_revenue": total_revenue,
                "npa_dummy": "0.0%" # લોન મોડ્યુલ બનશે ત્યારે આને લાઈવ કરીશું
            }
        finally:
            conn.close()

    def get_mandal_performance(self):
        """ત્રણેય ટેબ્સના ટેબલ માટે ઓલ-ઇન-વન ડેટા"""
        conn = get_connection()
        conn.row_factory = sqlite3.Row
        try:
            # આ ક્વેરી મંડળ, તેના મેમ્બર્સ અને તેનાથી થયેલી આવક બધું જ એકસાથે લાવશે
            cur = conn.execute("""
                SELECT m.id, m.name as mandal, m.mandal_code, m.created_at, m.status as mandal_status,
                (SELECT COUNT(*) FROM users u WHERE u.mandal_id = m.id AND u.role != 'Super Admin') as members,
                (SELECT SUM(amount) FROM invoices i WHERE i.mandal_name = m.name AND i.status='Paid') as revenue
                FROM mandals m ORDER BY m.id DESC
            """)
            
            rows = cur.fetchall()
            result = []
            for r in rows:
                d = dict(r)
                d['revenue'] = d['revenue'] or 0
                # ભવિષ્યના ફાઇનાન્સ મોડ્યુલ માટે ડમી ડેટા (જેથી UI ન તૂટે)
                d['totalSavings'] = "₹ 0.0 L" 
                d['totalLoans'] = "₹ 0.0 L"
                d['recovery'] = 100
                d['health'] = 'Excellent' if d['mandal_status'] == 'Active' else 'Attention Needed'
                result.append(d)
            return result
        finally:
            conn.close()

# ---------------------------------------------------------
    # 🎛️ માસ્ટર ડેશબોર્ડ (Live Engine)
    # ---------------------------------------------------------
    def get_dashboard_stats(self):
        conn = get_connection()
        conn.row_factory = sqlite3.Row
        try:
            # 1. લાઈવ આંકડા
            cur = conn.execute("SELECT COUNT(*) FROM mandals WHERE status='Active'")
            active_mandals = cur.fetchone()[0] or 0
            
            cur = conn.execute("SELECT COUNT(*) FROM users WHERE role != 'Super Admin' AND mandal_id != 0")
            total_members = cur.fetchone()[0] or 0
            
            cur = conn.execute("SELECT SUM(amount) FROM invoices WHERE status='Paid'")
            total_revenue = cur.fetchone()[0] or 0

            # 2. લાઈવ એક્ટિવિટી લોગ (તાજેતરના મંડળો અને પેમેન્ટ્સ)
            cur = conn.execute("SELECT 'New Mandal' as type, name as title, 'System Auto' as by_user, created_at FROM mandals ORDER BY id DESC LIMIT 2")
            activities = [dict(r) for r in cur.fetchall()]
            
            cur = conn.execute("SELECT 'Payment' as type, mandal_name as title, amount, created_at FROM invoices WHERE status='Paid' ORDER BY id DESC LIMIT 2")
            for r in cur.fetchall():
                activities.append({"type": "Payment", "title": f"{r['title']} paid ₹{r['amount']}", "by_user": "System Auto", "created_at": r['created_at']})
                
            return {
                "active_mandals": active_mandals,
                "total_members": total_members,
                "total_revenue": total_revenue,
                "activities": activities
            }
        finally:
            conn.close()

    # ---------------------------------------------------------
    # 🎧 હેલ્પડેસ્ક અને સપોર્ટ ટિકિટ્સ (Tickets & Chat)
    # ---------------------------------------------------------
    def _ensure_ticket_tables(self):
        # ટિકિટ માટેના ટેબલ્સ (જો ન હોય તો બનાવશે)
        conn = get_connection()
        try:
            conn.execute('''CREATE TABLE IF NOT EXISTS tickets (
                id INTEGER PRIMARY KEY AUTOINCREMENT, ticket_no TEXT UNIQUE NOT NULL, mandal_name TEXT NOT NULL,
                subject TEXT NOT NULL, category TEXT NOT NULL, priority TEXT NOT NULL, status TEXT DEFAULT 'Open', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
            
            conn.execute('''CREATE TABLE IF NOT EXISTS ticket_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT, ticket_id INTEGER NOT NULL, sender TEXT NOT NULL, sender_name TEXT NOT NULL,
                message TEXT NOT NULL, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
            conn.commit()
        except Exception as e: print("Ticket DB Error:", e)
        finally: conn.close()

    def get_all_tickets(self):
        self._ensure_ticket_tables()
        conn = get_connection(); conn.row_factory = sqlite3.Row
        try: cur = conn.execute("SELECT * FROM tickets ORDER BY id DESC"); return [dict(r) for r in cur.fetchall()]
        finally: conn.close()

    def update_ticket_status(self, ticket_id, status):
        conn = get_connection()
        try: conn.execute("UPDATE tickets SET status=? WHERE id=?", (status, ticket_id)); conn.commit(); return True, "સ્ટેટસ અપડેટ થઈ ગયું!"
        except Exception as e: return False, str(e)
        finally: conn.close()

    def get_ticket_messages(self, ticket_id):
        conn = get_connection(); conn.row_factory = sqlite3.Row
        try: cur = conn.execute("SELECT * FROM ticket_messages WHERE ticket_id=? ORDER BY id ASC", (ticket_id,)); return [dict(r) for r in cur.fetchall()]
        finally: conn.close()

    def add_ticket_message(self, ticket_id, sender, sender_name, message):
        conn = get_connection()
        try:
            conn.execute("INSERT INTO ticket_messages (ticket_id, sender, sender_name, message) VALUES (?, ?, ?, ?)", (ticket_id, sender, sender_name, message))
            conn.commit(); return True, "રિપ્લાય મોકલાઈ ગયો!"
        except Exception as e: return False, str(e)
        finally: conn.close()

# ---------------------------------------------------------
    # ⚙️ સુપર એડમિન (Tenant) સેટિંગ્સ
    # ---------------------------------------------------------
    def get_tenant_settings(self, mandal_id):
        conn = get_connection()
        try:
            cur = conn.execute("SELECT setting_key, setting_value FROM tenant_settings WHERE mandal_id=?", (mandal_id,))
            return {row[0]: row[1] for row in cur.fetchall()}
        finally: conn.close()

    def update_tenant_settings(self, mandal_id, settings_dict):
        conn = get_connection()
        try:
            for key, value in settings_dict.items():
                conn.execute("""
                    INSERT INTO tenant_settings (mandal_id, setting_key, setting_value)
                    VALUES (?, ?, ?)
                    ON CONFLICT(mandal_id, setting_key) DO UPDATE SET setting_value=excluded.setting_value
                """, (mandal_id, key, str(value)))
            conn.commit()
            return True, "તમારા મંડળના સેટિંગ્સ સફળતાપૂર્વક સેવ થઈ ગયા!"
        except Exception as e: return False, str(e)
        finally: conn.close()

