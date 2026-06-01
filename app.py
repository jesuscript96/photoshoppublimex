import streamlit as st
import os

# Configure global page parameters (ONLY once at the very start of app.py execution)
st.set_page_config(
    page_title="Publimex Hub - Suite",
    page_icon="logo.png" if os.path.exists("logo.png") else "🔴",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Global styles for the entire suite
st.markdown("""
    <style>
    /* Force main background to remain clean white */
    .stApp {
        background-color: #ffffff !important;
    }
    /* Styling Streamlit sidebar and main components to match Crimson Red branding */
    div[data-testid="stSidebarNav"] {
        padding-top: 20px;
    }
    div[data-testid="stSidebarNav"] ul {
        padding-bottom: 20px;
    }
    /* Style all sidebar navigation icons to be crimson red */
    [data-testid="stSidebarNav"] span[data-testid="stPageLinkIcon"] {
        color: #E60000 !important;
    }
    /* Set custom active sidebar link coloring */
    [data-testid="stSidebarNav"] li a[aria-current="page"] {
        color: #E60000 !important;
        font-weight: 700;
    }
    /* Buttons typography and hover */
    .stButton > button {
        border-radius: 6px !important;
    }
    .stDownloadButton > button {
        border-radius: 6px !important;
    }
    /* Responsive layout padding */
    .block-container {
        padding-top: 2rem !important;
        padding-bottom: 3rem !important;
    }
    </style>
""", unsafe_allow_html=True)

# Import page rendering functions (reload triggered)
from src.pages.login import show_login
from src.pages.home import show_home
from src.pages.editor import show_editor
from src.pages.disponibilidades import show_disponibilidades
from src.pages.contactos import show_contactos
from src.pages.reservas import show_reservas
from src.supabase_client import is_admin

# Initialize session state variables
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "user_token" not in st.session_state:
    st.session_state.user_token = None
if "user_id" not in st.session_state:
    st.session_state.user_id = None
if "user_email" not in st.session_state:
    st.session_state.user_email = None
if "user_name" not in st.session_state:
    st.session_state.user_name = None
if "user_role" not in st.session_state:
    st.session_state.user_role = None

# Fail-safe superuser check
if st.session_state.user_email and st.session_state.user_email.lower() == "jvalenzuela.chulia@gmail.com":
    st.session_state.user_role = "administrador"

# Routing and Navigation based on auth state
if not st.session_state.authenticated:
    # If not authenticated, the ONLY available page is Login
    pages = [
        st.Page(show_login, title="Iniciar Sesión", icon=":material/login:")
    ]
else:
    # Construct authenticated page suite
    page_home = st.Page(show_home, title="Panel Inicio", icon=":material/dashboard:")
    page_editor = st.Page(show_editor, title="Editor IA", icon=":material/palette:")
    page_disponibilidades = st.Page(show_disponibilidades, title="Disponibilidades", icon=":material/calendar_month:")
    page_contacts = st.Page(show_contactos, title="Mis Contactos", icon=":material/contacts:")
    page_reservas = st.Page(show_reservas, title="Mis Reservas", icon=":material/book_online:")

    # Save to session state so show_home or other pages can call st.switch_page
    st.session_state.page_home = page_home
    st.session_state.page_editor = page_editor
    st.session_state.page_disponibilidades = page_disponibilidades
    st.session_state.page_contacts = page_contacts
    st.session_state.page_reservas = page_reservas

    pages = [
        page_home,
        page_editor,
        page_disponibilidades,
        page_contacts,
        page_reservas
    ]

# Setup and run dynamic navigation
pg = st.navigation(pages)

# Display corporate logo at the top of the sidebar if authenticated
if st.session_state.authenticated:
    with st.sidebar:
        if os.path.exists("logo.png"):
            st.image("logo.png", use_container_width=True)
        st.write("")

# Execute the active page
pg.run()

# Display sidebar user details and logout button if authenticated
if st.session_state.authenticated:
    with st.sidebar:
        st.write("")
        st.write("")
        st.divider()
        st.markdown(f"**Sesión Activa:**")
        st.markdown(f'<div style="display: flex; align-items: center; gap: 8px; margin-bottom: 6px;"><svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="#E60000" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="width: 16px; height: 16px;"><path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg><span style="font-weight: 500;">{st.session_state.user_name}</span></div>', unsafe_allow_html=True)
        role_label = "Admin" if is_admin(st.session_state.user_role) else "Usuario"
        st.markdown(f'<div style="display: flex; align-items: center; gap: 8px;"><svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="#E60000" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="width: 16px; height: 16px;"><rect x="2" y="7" width="20" height="14" rx="2" ry="2"/><path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16"/></svg><span style="color: #64748b;">{role_label}</span></div>', unsafe_allow_html=True)
        st.write("")
        if st.button("Cerrar Sesión", icon=":material/logout:", type="primary", use_container_width=True, key="sidebar_logout_btn"):
            st.session_state.clear()
            st.rerun()
