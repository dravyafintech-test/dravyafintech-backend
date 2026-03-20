from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import os

from services.auth_service import AuthService
from dependencies import get_current_user
from services.settings_service import SettingsService
from services.tenant_service import TenantService

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

auth_service = AuthService()
settings_service = SettingsService()
tenant_service = TenantService() # 🚀 આપણું નવું પાવરફુલ એન્જિન

# ---------------------------------------------------------
# 🚪 લૉગિન API
# ---------------------------------------------------------
class LoginRequest(BaseModel):
    mobile: str
    password: str

@app.post("/api/login")
def login(request: LoginRequest):
    result, message = auth_service.authenticate_user(request.mobile, request.password)
    if not result:
        raise HTTPException(status_code=401, detail=message)
    return result

# ---------------------------------------------------------
# 🏢 મંડળ અને ટેનન્ટ API (Master Admin Only)
# ---------------------------------------------------------
class MandalCreateRequest(BaseModel):
    name: str
    reg_no: str
    address: str
    admin_name: str
    mobile: str
    email: str
    password: str
    max_members: int
    subscription_end_date: str
    status: str

@app.post("/api/master/mandals")
def create_new_mandal(request: MandalCreateRequest, current_user: dict = Depends(get_current_user)):
    if current_user['role'] != "Master Admin":
        raise HTTPException(status_code=403, detail="માત્ર માસ્ટર એડમિન નવું મંડળ બનાવી શકે છે.")
    
    success, msg = tenant_service.create_mandal(
        request.name, request.reg_no, request.address, request.admin_name, 
        request.mobile, request.email, request.max_members, 
        request.subscription_end_date, request.password, request.status
    )
    if not success:
        raise HTTPException(status_code=400, detail=msg)
    return {"message": msg}

@app.get("/api/master/mandals")
def get_all_mandals(current_user: dict = Depends(get_current_user)):
    if current_user['role'] != "Master Admin":
        raise HTTPException(status_code=403, detail="Access Denied.")
    return tenant_service.get_all_mandals()

@app.delete("/api/master/mandals/{mandal_id}")
def delete_mandal(mandal_id: int, current_user: dict = Depends(get_current_user)):
    """મંડળ ડિલીટ કરવાની API"""
    if current_user['role'] != "Master Admin":
        raise HTTPException(status_code=403, detail="માત્ર માસ્ટર એડમિન જ મંડળ ડિલીટ કરી શકે છે.")
    
    success, msg = tenant_service.delete_mandal(mandal_id)
    if not success:
        raise HTTPException(status_code=400, detail=msg)
    return {"message": msg}

@app.post("/api/master/mandals")
def create_new_mandal(request: MandalCreateRequest, current_user: dict = Depends(get_current_user)):
    """નવું મંડળ ઓનબોર્ડ કરવાની API"""
    if current_user['role'] != "Master Admin":
        raise HTTPException(status_code=403, detail="માત્ર માસ્ટર એડમિન નવું મંડળ બનાવી શકે છે.")
    
    success, msg = tenant_service.create_mandal(
        request.mandal_code, request.name, request.contact_person, 
        request.mobile, request.subscription_end_date, request.admin_password
    )
    if not success:
        raise HTTPException(status_code=400, detail=msg)
    return {"message": msg}

# ---------------------------------------------------------
# 🛡️ પ્લેટફોર્મ સ્ટાફ API (mandal_id = 0)
# ---------------------------------------------------------
class PlatformUserCreate(BaseModel):
    name: str
    mobile: str
    password: str
    role: str
    status: str = "Active"

@app.post("/api/master/users")
def create_platform_user(request: PlatformUserCreate, current_user: dict = Depends(get_current_user)):
    """નવો પ્લેટફોર્મ સ્ટાફ ઉમેરવાની API"""
    if current_user['role'] != "Master Admin":
        raise HTTPException(status_code=403, detail="માત્ર માસ્ટર એડમિન જ નવો સ્ટાફ ઉમેરી શકે છે.")
    
    success, msg = tenant_service.create_platform_user(
        request.name, request.mobile, request.password, request.role, request.status
    )
    if not success:
        raise HTTPException(status_code=400, detail=msg)
    return {"message": msg}

@app.get("/api/master/users")
def get_platform_users(current_user: dict = Depends(get_current_user)):
    """પ્લેટફોર્મ સ્ટાફનું લિસ્ટ લાવવાની API"""
    if current_user['role'] != "Master Admin":
        raise HTTPException(status_code=403, detail="Access Denied.")
    return tenant_service.get_platform_users()

class PlatformUserUpdate(BaseModel):
    name: str
    mobile: str
    role: str
    status: str
    password: Optional[str] = None # એડિટ વખતે પાસવર્ડ ફરજિયાત નથી

@app.put("/api/master/users/{user_id}")
def update_platform_user(user_id: int, request: PlatformUserUpdate, current_user: dict = Depends(get_current_user)):
    """સ્ટાફને એડિટ કરવાની API"""
    if current_user['role'] != "Master Admin":
        raise HTTPException(status_code=403, detail="Access Denied.")
    
    success, msg = tenant_service.update_platform_user(
        user_id, request.name, request.mobile, request.role, request.status, request.password
    )
    if not success:
        raise HTTPException(status_code=400, detail=msg)
    return {"message": msg}

@app.delete("/api/master/users/{user_id}")
def delete_platform_user(user_id: int, current_user: dict = Depends(get_current_user)):
    """સ્ટાફને ડિલીટ કરવાની API"""
    if current_user['role'] != "Master Admin":
        raise HTTPException(status_code=403, detail="Access Denied.")
    
    success, msg = tenant_service.delete_platform_user(user_id)
    if not success:
        raise HTTPException(status_code=400, detail=msg)
    return {"message": msg}

@app.get("/api/master/mandals")
def get_all_mandals(current_user: dict = Depends(get_current_user)):
    """બધા મંડળોનું લિસ્ટ લાવવાની API"""
    if current_user['role'] != "Master Admin":
        raise HTTPException(status_code=403, detail="Access Denied.")
    return tenant_service.get_all_mandals()


# ---------------------------------------------------------
# 🧠 ડાયનેમિક સેટિંગ્સ API (EAV Engine)
# ---------------------------------------------------------
class DynamicFieldRequest(BaseModel):
    module: str
    label: str
    key: str
    type: str
    options: Optional[str] = ""

@app.post("/api/settings/dynamic-fields")
def create_dynamic_field(request: DynamicFieldRequest, current_user: dict = Depends(get_current_user)):
    if current_user['role'] != "Master Admin":
        raise HTTPException(status_code=403, detail="માત્ર માસ્ટર એડમિન જ સિસ્ટમમાં નવા ફિલ્ડ બનાવી શકે છે.")
    
    success, msg = settings_service.add_dynamic_field(
        request.module, request.label, request.key, request.type, request.options
    )
    if not success:
        raise HTTPException(status_code=400, detail=msg)
    return {"message": msg}

@app.get("/api/settings/dynamic-fields")
def fetch_dynamic_fields(current_user: dict = Depends(get_current_user)):
    return settings_service.get_dynamic_fields()

@app.delete("/api/settings/dynamic-fields/{key}")
def delete_dynamic_field(key: str, current_user: dict = Depends(get_current_user)):
    if current_user['role'] != "Master Admin":
        raise HTTPException(status_code=403, detail="માત્ર માસ્ટર એડમિન જ ફિલ્ડ ડિલીટ કરી શકે છે.")
    
    success, msg = settings_service.delete_dynamic_field(key)
    if not success:
        raise HTTPException(status_code=400, detail=msg)
    return {"message": msg}

# ---------------------------------------------------------
# ⚙️ સેટિંગ્સ વેલ્યૂ API
# ---------------------------------------------------------
@app.get("/api/settings")
def get_settings(current_user: dict = Depends(get_current_user)):
    mandal_id = 0 if current_user['role'] == "Master Admin" else 1
    return settings_service.load(mandal_id)

@app.post("/api/settings/bulk-update")
def update_settings(payload: dict, current_user: dict = Depends(get_current_user)):
    if current_user['role'] not in ["Master Admin", "Super Admin"]:
        raise HTTPException(status_code=403, detail="તમને સેટિંગ્સ બદલવાનો અધિકાર નથી.")
    
    mandal_id = 0 if current_user['role'] == "Master Admin" else 1
    for key, value in payload.items():
        settings_service.update(mandal_id, key, value)
    return {"message": "તમામ સેટિંગ્સ સફળતાપૂર્વક અપડેટ થઈ ગયા છે!"}


# ---------------------------------------------------------
# 💳 લવાજમ પ્લાન મેનેજમેન્ટ (Subscription Plans APIs)
# ---------------------------------------------------------
class PlanCreate(BaseModel):
    plan_name: str
    max_members: str
    price_per_year: float
    features: str
    status: str = "Active"

@app.get("/api/master/subscription-plans")
def get_subscription_plans(current_user: dict = Depends(get_current_user)):
    return tenant_service.get_subscription_plans()

@app.post("/api/master/subscription-plans")
def create_subscription_plan(request: PlanCreate, current_user: dict = Depends(get_current_user)):
    success, msg = tenant_service.create_subscription_plan(request.plan_name, request.max_members, request.price_per_year, request.features, request.status)
    if not success: raise HTTPException(status_code=400, detail=msg)
    return {"message": msg}

@app.delete("/api/master/subscription-plans/{plan_id}")
def delete_subscription_plan(plan_id: int, current_user: dict = Depends(get_current_user)):
    success, msg = tenant_service.delete_subscription_plan(plan_id)
    if not success: raise HTTPException(status_code=400, detail=msg)
    return {"message": msg}

# ---------------------------------------------------------
# 🧾 એડવાન્સ બિલિંગ અને ઇન્વોઇસ APIs
# ---------------------------------------------------------
class InvoiceCreate(BaseModel):
    invoice_no: str
    invoice_date: str
    mandal_name: str
    plan_name: str
    validity: str
    amount: float
    payment_mode: str
    transaction_id: str
    status: str

@app.post("/api/master/invoices")
def create_invoice(request: InvoiceCreate, current_user: dict = Depends(get_current_user)):
    success, msg = tenant_service.create_invoice(
        request.invoice_no, request.invoice_date, request.mandal_name, request.plan_name, 
        request.validity, request.amount, request.payment_mode, request.transaction_id, request.status
    )
    if not success: raise HTTPException(status_code=400, detail=msg)
    return {"message": msg}

@app.get("/api/master/invoices")
def get_invoices(current_user: dict = Depends(get_current_user)):
    return tenant_service.get_all_invoices()

@app.put("/api/master/invoices/{invoice_id}/status")
def update_invoice_status(invoice_id: int, status: dict, current_user: dict = Depends(get_current_user)):
    success, msg = tenant_service.update_invoice_status(invoice_id, status.get('status'))
    if not success: raise HTTPException(status_code=400, detail=msg)
    return {"message": msg}

@app.delete("/api/master/invoices/{invoice_id}")
def delete_invoice(invoice_id: int, current_user: dict = Depends(get_current_user)):
    success, msg = tenant_service.delete_invoice(invoice_id)
    if not success: raise HTTPException(status_code=400, detail=msg)
    return {"message": msg}

# ---------------------------------------------------------
# 📢 ગ્લોબલ કોમ્યુનિકેશન APIs
# ---------------------------------------------------------
class BroadcastCreate(BaseModel):
    title: str
    target_audience: str
    channels: str
    message: str

@app.get("/api/master/communications/stats")
def get_comm_stats(current_user: dict = Depends(get_current_user)):
    return tenant_service.get_communication_stats()

@app.get("/api/master/communications")
def get_broadcasts(current_user: dict = Depends(get_current_user)):
    return tenant_service.get_broadcasts()

@app.post("/api/master/communications")
def create_broadcast(request: BroadcastCreate, current_user: dict = Depends(get_current_user)):
    success, msg = tenant_service.create_broadcast(request.title, request.target_audience, request.channels, request.message)
    if not success: raise HTTPException(status_code=400, detail=msg)
    return {"message": msg}

# ---------------------------------------------------------
# 📊 માસ્ટર એનાલિટિક્સ અને રિપોર્ટ્સ APIs
# ---------------------------------------------------------
@app.get("/api/master/reports/kpi")
def get_master_kpi(current_user: dict = Depends(get_current_user)):
    if current_user['role'] != "Master Admin": raise HTTPException(status_code=403, detail="Access Denied.")
    return tenant_service.get_master_kpi()

@app.get("/api/master/reports/mandals")
def get_mandal_performance(current_user: dict = Depends(get_current_user)):
    if current_user['role'] != "Master Admin": raise HTTPException(status_code=403, detail="Access Denied.")
    return tenant_service.get_mandal_performance()

# ---------------------------------------------------------
# 🎛️ ડેશબોર્ડ અને હેલ્પડેસ્ક APIs
# ---------------------------------------------------------
class MessageCreate(BaseModel):
    message: str

@app.get("/api/master/dashboard/stats")
def get_dashboard_stats(current_user: dict = Depends(get_current_user)):
    return tenant_service.get_dashboard_stats()

@app.get("/api/master/tickets")
def get_tickets(current_user: dict = Depends(get_current_user)):
    return tenant_service.get_all_tickets()

@app.put("/api/master/tickets/{ticket_id}/status")
def update_ticket_status(ticket_id: int, status_data: dict, current_user: dict = Depends(get_current_user)):
    success, msg = tenant_service.update_ticket_status(ticket_id, status_data.get('status'))
    if not success: raise HTTPException(status_code=400, detail=msg)
    return {"message": msg}

@app.get("/api/master/tickets/{ticket_id}/messages")
def get_ticket_messages(ticket_id: int, current_user: dict = Depends(get_current_user)):
    return tenant_service.get_ticket_messages(ticket_id)

@app.post("/api/master/tickets/{ticket_id}/messages")
def add_ticket_message(ticket_id: int, request: MessageCreate, current_user: dict = Depends(get_current_user)):
    success, msg = tenant_service.add_ticket_message(ticket_id, 'admin', current_user['name'] or 'Master Admin', request.message)
    if not success: raise HTTPException(status_code=400, detail=msg)
    return {"message": msg}

# ---------------------------------------------------------
# ⚙️ સુપર એડમિન સેટિંગ્સ APIs
# ---------------------------------------------------------
@app.get("/api/tenant/settings")
def get_tenant_settings(current_user: dict = Depends(get_current_user)):
    return tenant_service.get_tenant_settings(current_user['mandal_id'])

@app.post("/api/tenant/settings")
def update_tenant_settings(settings: dict, current_user: dict = Depends(get_current_user)):
    success, msg = tenant_service.update_tenant_settings(current_user['mandal_id'], settings)
    if not success: raise HTTPException(status_code=400, detail=msg)
    return {"message": msg}

# ---------------------------------------------------------
# 🌐 ફ્રન્ટએન્ડ (ડેશબોર્ડ) અને સ્ટેટિક ફાઈલો (JS/CSS) સર્વ કરવાનો રૂટ
# ---------------------------------------------------------

# ૧. JS અને CSS ફાઈલો (assets ફોલ્ડર) ને સર્વ કરવા માટેનું સેટિંગ
if os.path.exists("assets"):
    app.mount("/assets", StaticFiles(directory="assets"), name="assets")

# ૨. મેઈન પેજ (index.html) બતાવવાનો રૂટ
@app.get("/")
def serve_dashboard():
    # ⚠️ Render માટેનો સાચો રસ્તો (Absolute ની જગ્યાએ Relative path)
    index_path = "index.html" 
    if os.path.exists(index_path):
        with open(index_path, 'r', encoding='utf-8') as f:
            return HTMLResponse(content=f.read())
    return {"message": "Dravya FinTech Backend is Live! (Upload your frontend files)"}
