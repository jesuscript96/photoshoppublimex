import streamlit as st
import os

# Configure global page parameters (ONLY once at the very start of app.py execution)
st.set_page_config(
    page_title="Publimex Hub - Suite",
    page_icon="logo.png" if os.path.exists("logo.png") else "🔴",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Sistema de diseño central (tipografía Outfit, líneas rectas, rojo/blanco)
from src.theme import inject_theme
inject_theme()

# Import page rendering functions
from src.pages.login import show_login
from src.pages.home import show_home
from src.pages.editor import show_editor
from src.pages.disponibilidades import show_disponibilidades
from src.pages.contactos import show_contactos
from src.pages.reservas import show_reservas
from src.pages.expedientes import show_expedientes
from src.pages.usuarios import show_usuarios
from src.supabase_client import is_admin

# Initialize session state variables
for _k in ("user_token", "user_id", "user_email", "user_name", "user_role"):
    if _k not in st.session_state:
        st.session_state[_k] = None
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

# Fail-safe superuser check
if st.session_state.user_email and st.session_state.user_email.lower() == "jvalenzuela.chulia@gmail.com":
    st.session_state.user_role = "administrador"

# Routing and Navigation based on auth state
if not st.session_state.authenticated:
    # If not authenticated, the ONLY available page is Login
    nav = [st.Page(show_login, title="Iniciar Sesión", icon=":material/login:")]
else:
    # Construct authenticated page suite
    page_home = st.Page(show_home, title="Panel Inicio", icon=":material/dashboard:")
    page_expedientes = st.Page(show_expedientes, title="Procesos de Venta", icon=":material/account_tree:")
    page_editor = st.Page(show_editor, title="Editor IA", icon=":material/palette:")
    page_disponibilidades = st.Page(show_disponibilidades, title="Disponibilidades", icon=":material/calendar_month:")
    page_contacts = st.Page(show_contactos, title="Mis Contactos", icon=":material/contacts:")
    page_reservas = st.Page(show_reservas, title="Mis Reservas", icon=":material/book_online:")
    page_usuarios = st.Page(show_usuarios, title="Gestión de Usuarios", icon=":material/group:")

    # Save to session state so other pages can call st.switch_page
    st.session_state.page_home = page_home
    st.session_state.page_expedientes = page_expedientes
    st.session_state.page_editor = page_editor
    st.session_state.page_disponibilidades = page_disponibilidades
    st.session_state.page_contacts = page_contacts
    st.session_state.page_reservas = page_reservas
    st.session_state.page_usuarios = page_usuarios

    # Navegación agrupada por secciones (jerarquía)
    nav = {
        "Inicio": [page_home],
        "Ventas": [page_expedientes, page_disponibilidades, page_reservas],
        "Herramientas": [page_editor],
        "Datos": [page_contacts],
    }
    # Administración: solo administradores
    if is_admin(st.session_state.user_role):
        nav["Administración"] = [page_usuarios]

# Setup and run dynamic navigation
pg = st.navigation(nav)

# Execute the active page
pg.run()

# Sidebar: datos de sesión + cerrar sesión + logo pequeño al fondo
if st.session_state.authenticated:
    with st.sidebar:
        st.divider()
        role_label = "Administrador" if is_admin(st.session_state.user_role) else "Usuario"
        st.markdown(
            f'<div style="line-height:1.35;">'
            f'<div style="font-size:0.7rem; text-transform:uppercase; letter-spacing:0.08em; color:#6B6B6B;">Sesión activa</div>'
            f'<div style="font-weight:600; color:#1A1A1A;">{st.session_state.user_name or "—"}</div>'
            f'<div style="font-size:0.8rem; color:#6B6B6B;">{role_label}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
        st.write("")
        if st.button("Cerrar sesión", icon=":material/logout:", use_container_width=True, key="sidebar_logout_btn"):
            st.session_state.clear()
            st.rerun()
        # Logo pequeño al fondo
        if os.path.exists("logo.png"):
            st.write("")
            lc1, lc2, lc3 = st.columns([1, 2, 1])
            with lc2:
                st.image("logo.png", use_container_width=True)
