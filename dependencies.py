from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
import jwt
from services.auth_service import SECRET_KEY, ALGORITHM

# આ કહે છે કે ટોકન ક્યાંથી મળશે
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/login")

def get_current_user(token: str = Depends(oauth2_scheme)):
    """આ ફંક્શન દર વખતે યુઝરનો પાસપોર્ટ (ટોકન) ચેક કરશે"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        mobile: str = payload.get("sub")
        role: str = payload.get("role")
        name: str = payload.get("name")
        
        if mobile is None:
            raise HTTPException(status_code=401, detail="અમાન્ય પાસપોર્ટ.")
            
        return {"mobile": mobile, "role": role, "name": name}
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="તમારું સેશન પૂરું થઈ ગયું છે, ફરીથી લૉગિન કરો.")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="સુરક્ષા કારણોસર ઍક્સેસ નકારવામાં આવ્યો છે.")