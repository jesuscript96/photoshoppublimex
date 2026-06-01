import os
import requests
import streamlit as st
from src.supabase_client import (
    get_user_contacts,
    get_user_reservations,
    is_admin,
    get_all_contacts,
    get_all_reservations,
    get_all_profiles,
    update_user_role
)

def get_secret(key):
    try:
        return st.secrets[key]
    except Exception:
        return os.environ.get(key, "")

AIRTABLE_TOKEN = get_secret("AIRTABLE_TOKEN")
BASE_ID = "appW4QjUOV9nXQkx9"
T_RESERVACIONES  = "tbluUAzNFSuaqMrYX"

@st.cache_data(ttl=15, show_spinner=False)
def get_airtable_reservations_count():
    if not AIRTABLE_TOKEN:
        return 0
    headers = {"Authorization": f"Bearer {AIRTABLE_TOKEN}"}
    url = f"https://api.airtable.com/v0/{BASE_ID}/{T_RESERVACIONES}"
    params = {"fields[]": ["ID_Reservacion"], "maxRecords": 1000}
    count = 0
    try:
        while True:
            r = requests.get(url, headers=headers, params=params, timeout=10)
            if r.status_code != 200:
                break
            data = r.json()
            count += len(data.get("records", []))
            offset = data.get("offset")
            if not offset:
                break
            params["offset"] = offset
        return count
    except Exception:
        return 0

def show_home():
    st.markdown("""
        <style>
        .welcome-header {
            font-size: 2.2rem;
            font-weight: 800;
            color: #111111;
            margin-bottom: 5px;
        }
        .welcome-header span {
            color: #E60000;
        }
        .welcome-subtitle {
            font-size: 1.1rem;
            color: #666666;
            margin-bottom: 30px;
        }
        .metric-card {
            background: #ffffff;
            padding: 20px;
            border-radius: 8px;
            border-left: 4px solid #E60000;
            box-shadow: 0 4px 15px rgba(0,0,0,0.03);
            text-align: center;
        }
        .metric-value {
            font-size: 1.8rem;
            font-weight: 700;
            color: #111111;
        }
        .metric-label {
            font-size: 0.9rem;
            color: #666666;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        .app-card {
            background: #ffffff;
            border: 1px solid #eaeaea;
            border-radius: 10px;
            padding: 24px;
            margin-bottom: 20px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.02);
            transition: all 0.3s ease;
        }
        .app-card:hover {
            box-shadow: 0 6px 20px rgba(230,0,0,0.06);
            border-color: #ffcccc;
        }
        .app-title {
            font-size: 1.25rem;
            font-weight: 700;
            color: #111111;
            margin-bottom: 8px;
        }
        .app-desc {
            font-size: 0.95rem;
            color: #555555;
            min-height: 50px;
            margin-bottom: 20px;
        }
        </style>
    """, unsafe_allow_html=True)

    user_name = st.session_state.get("user_name", "Usuario")
    user_role = st.session_state.get("user_role", "Vendedor")
    user_id = st.session_state.get("user_id")
    token = st.session_state.get("user_token")

    user_role_is_admin = is_admin(user_role)

    # Fetch counts from Supabase
    with st.spinner("Cargando métricas..."):
        if user_role_is_admin:
            contacts = get_all_contacts(token)
            num_reservations = get_airtable_reservations_count()
        else:
            contacts = get_user_contacts(user_id, token)
            reservations = get_user_reservations(user_id, token)
            num_reservations = len(reservations)
        num_contacts = len(contacts)

    def draw_panel():
        st.markdown(f"""
            <div class="welcome-header">Bienvenido a la Suite, <span>{user_name}</span></div>
            <div class="welcome-subtitle">Rol: {"Admin" if user_role_is_admin else "Usuario"} &nbsp;|&nbsp; {"Gestiona todos los soportes y usuarios." if user_role_is_admin else "Gestiona tus soportes publicitarios y clientes."}</div>
        """, unsafe_allow_html=True)

        # Metric Row
        col_m1, col_m2, col_m3 = st.columns(3)
        
        contacts_label = "Contactos Globales" if user_role_is_admin else "Contactos Privados"
        reservations_label = "Reservas Globales" if user_role_is_admin else "Reservas Asignadas"

        with col_m1:
            st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-value">{num_contacts}</div>
                    <div class="metric-label"><svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="#E60000" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="width: 16px; height: 16px; display: inline-block; vertical-align: -2px; margin-right: 6px;"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>{contacts_label}</div>
                </div>
            """, unsafe_allow_html=True)
            
        with col_m2:
            st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-value">{num_reservations}</div>
                    <div class="metric-label"><svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="#E60000" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="width: 16px; height: 16px; display: inline-block; vertical-align: -2px; margin-right: 6px;"><rect x="3" y="4" width="18" height="18" rx="2" ry="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>{reservations_label}</div>
                </div>
            """, unsafe_allow_html=True)
            
        with col_m3:
            st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-value">Activo</div>
                    <div class="metric-label"><span style="display: inline-block; width: 8px; height: 8px; border-radius: 50%; background-color: #E60000; box-shadow: 0 0 6px #E60000; margin-right: 6px; vertical-align: 1px;"></span>Estado de la Cuenta</div>
                </div>
            """, unsafe_allow_html=True)

        st.write("")
        st.write("")
        st.markdown('<div style="font-size: 1.4rem; font-weight: 700; color: #111111; margin-top: 10px; margin-bottom: 20px;"><svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="#E60000" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="width: 22px; height: 22px; display: inline-block; vertical-align: -4px; margin-right: 8px;"><rect x="3" y="3" width="7" height="9"/><rect x="14" y="3" width="7" height="5"/><rect x="14" y="12" width="7" height="9"/><rect x="3" y="16" width="7" height="5"/></svg>Aplicaciones Disponibles</div>', unsafe_allow_html=True)

        # Apps Grid
        col_a1, col_a2 = st.columns(2)

        with col_a1:
            st.markdown("""
                <div class="app-card">
                    <div class="app-title"><svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="#E60000" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="width: 18px; height: 18px; display: inline-block; vertical-align: -2px; margin-right: 8px;"><path d="M12 22C17.52 22 22 17.52 22 12S17.52 2 12 2 2 6.52 2 12c0 1.5.5 3 1.5 4.14.3.36.75.56 1.23.56h1.4c.78 0 1.4.62 1.4 1.4v1.4c0 .48.2.93.56 1.23C9 21.5 10.5 22 12 22z"/></svg>Editor de Anuncios IA</div>
                    <div class="app-desc">Integra logotipos y creatividades de tus clientes en muros y espectaculares reales utilizando Inteligencia Artificial.</div>
                </div>
            """, unsafe_allow_html=True)
            if st.button("Abrir Editor IA", type="primary", use_container_width=True, key="launch_editor"):
                if "page_editor" in st.session_state:
                    st.switch_page(st.session_state.page_editor)

            st.markdown(f"""
                <div class="app-card">
                    <div class="app-title"><svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="#E60000" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="width: 18px; height: 18px; display: inline-block; vertical-align: -2px; margin-right: 8px;"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>{"Contactos Globales" if user_role_is_admin else "Mis Contactos Privados"}</div>
                    <div class="app-desc">{"Administra la agenda global de contactos y clientes en Supabase de forma segura y confidencial." if user_role_is_admin else "Administra tu agenda privada de contactos y clientes en Supabase de forma segura y confidencial."}</div>
                </div>
            """, unsafe_allow_html=True)
            if st.button("Ver Contactos", type="primary", use_container_width=True, key="launch_contacts"):
                if "page_contacts" in st.session_state:
                    st.switch_page(st.session_state.page_contacts)

        with col_a2:
            st.markdown("""
                <div class="app-card">
                    <div class="app-title"><svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="#E60000" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="width: 18px; height: 18px; display: inline-block; vertical-align: -2px; margin-right: 8px;"><rect x="3" y="4" width="18" height="18" rx="2" ry="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>Control de Disponibilidades</div>
                    <div class="app-desc">Consulta los espectaculares libres u ocupados en tiempo real, genera reportes y asigna reservaciones a tu gestión.</div>
                </div>
            """, unsafe_allow_html=True)
            if st.button("Ver Disponibilidades", type="primary", use_container_width=True, key="launch_disponibilidades"):
                if "page_disponibilidades" in st.session_state:
                    st.switch_page(st.session_state.page_disponibilidades)

            st.markdown(f"""
                <div class="app-card">
                    <div class="app-title"><svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="#E60000" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="width: 18px; height: 18px; display: inline-block; vertical-align: -2px; margin-right: 8px;"><path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"/><rect x="8" y="2" width="8" height="4" rx="1" ry="1"/></svg>{"Reservas Globales" if user_role_is_admin else "Mis Reservas Asignadas"}</div>
                    <div class="app-desc">{"Gestiona todas las reservaciones en los próximos meses, ajustando precios y anotaciones de seguimiento." if user_role_is_admin else "Gestiona tus reservaciones asignadas en los próximos meses, ajustando precios privados y anotaciones de seguimiento."}</div>
                </div>
            """, unsafe_allow_html=True)
            if st.button("Ver Reservas", type="primary", use_container_width=True, key="launch_reservas"):
                if "page_reservas" in st.session_state:
                    st.switch_page(st.session_state.page_reservas)

        # Divider and Logout info
        st.divider()
        st.caption("Publimex Hub - © 2026. Todos los derechos reservados. Utiliza la barra lateral para navegar de manera rápida entre aplicaciones.")

    if user_role_is_admin:
        tab_panel, tab_users = st.tabs(["Panel de Control", "👥 Gestión de Usuarios"])
        with tab_panel:
            draw_panel()
        with tab_users:
            st.markdown("### Control de Roles de Usuario")
            st.markdown("Como Administrador, puedes ver todos los perfiles de usuario registrados en Supabase y cambiar sus roles para promover a nuevos administradores o cambiarlos a usuarios estándar.")
            
            # Fetch profiles
            with st.spinner("Cargando perfiles..."):
                profiles = get_all_profiles(token)
                
            if not profiles:
                st.warning("No se encontraron perfiles de usuario en la base de datos.")
            else:
                for p in sorted(profiles, key=lambda x: x.get("name", "").lower()):
                    p_id = p.get("id")
                    p_name = p.get("name", "Sin nombre")
                    p_role = p.get("role", "vendedor")
                    p_role_display = "Admin" if is_admin(p_role) else "Usuario"
                    
                    col_u1, col_u2 = st.columns([3, 1])
                    with col_u1:
                        st.markdown(f"👤 **Nombre:** {p_name}")
                        st.caption(f"ID: `{p_id}` | Rol actual: **{p_role_display}**")
                    with col_u2:
                        if p_id == user_id:
                            st.info("Tu perfil actual")
                        else:
                            if is_admin(p_role):
                                if st.button("Hacer Usuario", key=f"demote_{p_id}", use_container_width=True):
                                    if update_user_role(token, p_id, "vendedor"):
                                        st.success(f"Usuario {p_name} cambiado a rol Usuario.")
                                        st.rerun()
                                    else:
                                        st.error("Error al actualizar el perfil.")
                            else:
                                if st.button("Hacer Admin", key=f"promote_{p_id}", type="primary", use_container_width=True):
                                    if update_user_role(token, p_id, "administrador"):
                                        st.success(f"Usuario {p_name} promovido a Admin.")
                                        st.rerun()
                                    else:
                                        st.error("Error al actualizar el perfil.")
                    st.divider()
    else:
        draw_panel()
