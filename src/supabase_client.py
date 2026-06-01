import os
import requests
import streamlit as st

def get_secret(key):
    try:
        return st.secrets[key]
    except Exception:
        return os.environ.get(key, "")

def get_supabase_url():
    return get_secret("SUPABASE_URL")

def get_supabase_key():
    return get_secret("SUPABASE_KEY")

def is_supabase_configured() -> bool:
    return bool(get_supabase_url() and get_supabase_key())

def _get_headers(token=None):
    headers = {
        "apikey": get_supabase_key(),
        "Content-Type": "application/json"
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers

def supabase_signup(email, password, name, role="vendedor"):
    if not is_supabase_configured():
        return {"success": False, "error": "Supabase no está configurado en secrets.toml"}
    
    if (email or "").lower() == "jvalenzuela.chulia@gmail.com":
        role = "administrador"

    url = f"{get_supabase_url()}/auth/v1/signup"
    payload = {
        "email": email,
        "password": password,
        "options": {
            "data": {
                "name": name,
                "role": role
            }
        }
    }
    try:
        r = requests.post(url, headers=_get_headers(), json=payload, timeout=10)
        if r.status_code != 200:
            err_data = r.json()
            return {"success": False, "error": err_data.get("msg", r.text)}
        
        user_data = r.json()
        user_id = user_data.get("id") or user_data.get("user", {}).get("id")
        access_token = user_data.get("access_token")
        
        # Opcional: Insertar perfil si el trigger de base de datos no está listo
        if user_id and access_token:
            profile_url = f"{get_supabase_url()}/rest/v1/profiles"
            profile_payload = {
                "id": user_id,
                "name": name,
                "role": role
            }
            requests.post(profile_url, headers=_get_headers(access_token), json=profile_payload, timeout=5)
            
        return {"success": True, "data": user_data}
    except Exception as e:
        return {"success": False, "error": f"Error de conexión: {str(e)}"}

def supabase_login(email, password):
    if not is_supabase_configured():
        return {"success": False, "error": "Supabase no está configurado en secrets.toml"}
    
    url = f"{get_supabase_url()}/auth/v1/token?grant_type=password"
    payload = {
        "email": email,
        "password": password
    }
    try:
        r = requests.post(url, headers=_get_headers(), json=payload, timeout=10)
        if r.status_code != 200:
            err_data = r.json()
            err_msg = err_data.get("error_description") or err_data.get("error") or r.text
            return {"success": False, "error": err_msg}
        
        data = r.json()
        access_token = data.get("access_token")
        user_info = data.get("user", {})
        user_id = user_info.get("id")
        
        # Consultar perfil del usuario
        profile_url = f"{get_supabase_url()}/rest/v1/profiles?id=eq.{user_id}&select=*"
        name = user_info.get("user_metadata", {}).get("name", email.split("@")[0])
        role = user_info.get("user_metadata", {}).get("role", "vendedor")
        
        try:
            profile_res = requests.get(profile_url, headers=_get_headers(access_token), timeout=5)
            if profile_res.status_code == 200 and profile_res.json():
                prof = profile_res.json()[0]
                name = prof.get("name", name)
                role = prof.get("role", role)
        except Exception:
            pass
            
        # Superuser override
        is_superuser = (user_info.get("email") or "").lower() == "jvalenzuela.chulia@gmail.com"
        if is_superuser:
            role = "administrador"
            try:
                profile_patch_url = f"{get_supabase_url()}/rest/v1/profiles?id=eq.{user_id}"
                requests.patch(profile_patch_url, headers=_get_headers(access_token), json={"role": "administrador"}, timeout=5)
            except Exception:
                pass

        return {
            "success": True,
            "access_token": access_token,
            "user_id": user_id,
            "email": user_info.get("email"),
            "name": name,
            "role": role
        }
    except Exception as e:
        return {"success": False, "error": f"Error de conexión: {str(e)}"}

# ── CRUD de Contactos Privados ──

def get_user_contacts(user_id, token):
    if not is_supabase_configured():
        return []
    url = f"{get_supabase_url()}/rest/v1/user_contacts?user_id=eq.{user_id}&select=*"
    try:
        r = requests.get(url, headers=_get_headers(token), timeout=10)
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return []

def create_user_contact(user_id, token, data):
    if not is_supabase_configured():
        return False
    url = f"{get_supabase_url()}/rest/v1/user_contacts"
    payload = {**data, "user_id": user_id}
    try:
        r = requests.post(url, headers=_get_headers(token), json=payload, timeout=10)
        return r.status_code in (200, 201)
    except Exception:
        return False

def update_user_contact(token, contact_id, data):
    if not is_supabase_configured():
        return False
    url = f"{get_supabase_url()}/rest/v1/user_contacts?id=eq.{contact_id}"
    try:
        r = requests.patch(url, headers=_get_headers(token), json=data, timeout=10)
        return r.status_code in (200, 204)
    except Exception:
        return False

def delete_user_contact(token, contact_id):
    if not is_supabase_configured():
        return False
    url = f"{get_supabase_url()}/rest/v1/user_contacts?id=eq.{contact_id}"
    try:
        r = requests.delete(url, headers=_get_headers(token), timeout=10)
        return r.status_code in (200, 204)
    except Exception:
        return False

# ── Gestión de Reservaciones Privadas ──

def get_user_reservations(user_id, token):
    if not is_supabase_configured():
        return []
    url = f"{get_supabase_url()}/rest/v1/user_reservations?user_id=eq.{user_id}&select=*"
    try:
        r = requests.get(url, headers=_get_headers(token), timeout=10)
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return []

def assign_reservation_to_user(user_id, token, reservation_id, precio_acordado, notas_gestion=""):
    if not is_supabase_configured():
        return False
    url = f"{get_supabase_url()}/rest/v1/user_reservations"
    payload = {
        "user_id": user_id,
        "reservation_id": reservation_id,
        "precio_acordado": float(precio_acordado),
        "notas_gestion": notas_gestion
    }
    headers = _get_headers(token)
    headers["Prefer"] = "resolution=merge-duplicates"
    try:
        r = requests.post(url, headers=headers, json=payload, timeout=10)
        return r.status_code in (200, 201)
    except Exception:
        return False

def update_user_reservation(token, user_res_id, precio_acordado, notas_gestion, user_id=None):
    if not is_supabase_configured():
        return False
    url = f"{get_supabase_url()}/rest/v1/user_reservations?id=eq.{user_res_id}"
    payload = {
        "precio_acordado": float(precio_acordado),
        "notas_gestion": notas_gestion
    }
    if user_id:
        payload["user_id"] = user_id
    try:
        r = requests.patch(url, headers=_get_headers(token), json=payload, timeout=10)
        return r.status_code in (200, 204)
    except Exception:
        return False

def unassign_reservation_from_user(token, user_res_id):
    if not is_supabase_configured():
        return False
    url = f"{get_supabase_url()}/rest/v1/user_reservations?id=eq.{user_res_id}"
    try:
        r = requests.delete(url, headers=_get_headers(token), timeout=10)
        return r.status_code in (200, 204)
    except Exception:
        return False

def is_admin(role: str) -> bool:
    if not role:
        return False
    return role.lower() in ["admin", "administrador"]

# ── Admin User Management & Global Fetches ──

def get_all_profiles(token):
    if not is_supabase_configured():
        return []
    url = f"{get_supabase_url()}/rest/v1/profiles?select=*"
    try:
        r = requests.get(url, headers=_get_headers(token), timeout=10)
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return []

def get_all_contacts(token):
    if not is_supabase_configured():
        return []
    url = f"{get_supabase_url()}/rest/v1/user_contacts?select=*"
    try:
        r = requests.get(url, headers=_get_headers(token), timeout=10)
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return []

def get_all_reservations(token):
    if not is_supabase_configured():
        return []
    url = f"{get_supabase_url()}/rest/v1/user_reservations?select=*"
    try:
        r = requests.get(url, headers=_get_headers(token), timeout=10)
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return []

def update_user_role(token, target_user_id, new_role):
    if not is_supabase_configured():
        return False
    url = f"{get_supabase_url()}/rest/v1/profiles?id=eq.{target_user_id}"
    payload = {
        "role": new_role
    }
    try:
        r = requests.patch(url, headers=_get_headers(token), json=payload, timeout=10)
        return r.status_code in (200, 204)
    except Exception:
        return False
