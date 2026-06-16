import os
import requests
import streamlit as st
from src.supabase_client import (
    get_user_contacts,
    get_user_reservations,
    is_admin,
    get_all_contacts,
)
from src.airtable_client import list_expedientes, list_espacios
from src.theme import page_header

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


# Iconos (trazo blanco para ir dentro del cuadro rojo .pm-ico)
def _ico(inner: str) -> str:
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" '
            f'stroke="#fff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" '
            f'style="width:16px;height:16px;">{inner}</svg>')

ICONS = {
    "ventas":   '<path d="M3 3v18h18"/><path d="M7 16l4-4 4 4 5-6"/>',
    "editor":   '<path d="m12 3-1.9 5.8a2 2 0 0 1-1.3 1.3L3 12l5.8 1.9a2 2 0 0 1 1.3 1.3L12 21l1.9-5.8a2 2 0 0 1 1.3-1.3L21 12l-5.8-1.9a2 2 0 0 1-1.3-1.3Z"/>',
    "calendar": '<rect x="3" y="4" width="18" height="18"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/>',
    "contacts": '<path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/>',
    "reservas": '<path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/>',
}


def _dash_card(icon_key, title, desc, stats, btn_label, btn_key, page_key):
    """Tarjeta tipo dashboard: icono + título + info + botón rojo, todo dentro del borde."""
    with st.container(border=True):
        st.markdown(
            f'<div class="pm-dash-title"><span class="pm-ico">{_ico(ICONS[icon_key])}</span>{title}</div>'
            f'<div class="pm-dash-desc">{desc}</div>',
            unsafe_allow_html=True,
        )
        if stats:
            cells = "".join(
                f'<div><div class="pm-stat-num">{n}</div><div class="pm-stat-lbl">{lbl}</div></div>'
                for n, lbl in stats
            )
            st.markdown(f'<div class="pm-stat-row">{cells}</div>', unsafe_allow_html=True)
        if st.button(btn_label, type="primary", key=btn_key, use_container_width=True):
            if page_key in st.session_state:
                st.switch_page(st.session_state[page_key])


def show_home():
    user_name = st.session_state.get("user_name", "Usuario")
    user_role = st.session_state.get("user_role", "Vendedor")
    user_id = st.session_state.get("user_id")
    token = st.session_state.get("user_token")
    user_role_is_admin = is_admin(user_role)

    # Datos para métricas y mini-estadísticas de las tarjetas
    with st.spinner("Cargando panel..."):
        if user_role_is_admin:
            contacts = get_all_contacts(token)
            num_reservations = get_airtable_reservations_count()
            exps = list_expedientes(None)
        else:
            contacts = get_user_contacts(user_id, token)
            num_reservations = len(get_user_reservations(user_id, token))
            exps = list_expedientes(user_id)
        num_contacts = len(contacts)
        n_exp = len(exps)
        n_abiertos = sum(1 for e in exps if e.get("fields", {}).get("Estado") == "Abierto")
        n_ganados = sum(1 for e in exps if e.get("fields", {}).get("Estado") == "Ganado")
        n_soportes = len(list_espacios())

    def draw_panel():
        page_header(
            f"Bienvenido, {user_name}",
            subtitle=("Gestiona todos los soportes, procesos y usuarios."
                      if user_role_is_admin else
                      "Gestiona tus procesos de venta, soportes y clientes."),
            eyebrow="Publimex Hub",
        )

        m1, m2, m3 = st.columns(3)
        m1.metric("Procesos abiertos", n_abiertos)
        m2.metric("Reservas Globales" if user_role_is_admin else "Reservas asignadas", num_reservations)
        m3.metric("Contactos Globales" if user_role_is_admin else "Contactos", num_contacts)

        st.write("")
        st.markdown("### Aplicaciones")

        # Destacado: Procesos de Venta (a todo el ancho, con varias estadísticas)
        _dash_card(
            "ventas", "Procesos de Venta",
            "Gestiona cada oportunidad de principio a fin: solicitud de reserva, presupuestos, "
            "contratación (reserva efectiva y papeleo), producción y prueba de montaje.",
            [(n_exp, "Expedientes"), (n_abiertos, "Abiertos"), (n_ganados, "Ganados")],
            "Abrir Procesos de Venta", "launch_expedientes", "page_expedientes",
        )

        st.write("")
        col_a1, col_a2 = st.columns(2)
        with col_a1:
            _dash_card(
                "calendar", "Disponibilidades",
                "Consulta los soportes libres u ocupados en tiempo real y gestiona reservaciones.",
                [(n_soportes, "Soportes")],
                "Ver Disponibilidades", "launch_disponibilidades", "page_disponibilidades",
            )
            _dash_card(
                "contacts", "Contactos Globales" if user_role_is_admin else "Mis Contactos",
                ("Administra la agenda global de contactos y clientes."
                 if user_role_is_admin else "Administra tu agenda privada de contactos y clientes."),
                [(num_contacts, "Contactos")],
                "Ver Contactos", "launch_contacts", "page_contacts",
            )
        with col_a2:
            _dash_card(
                "reservas", "Reservas Globales" if user_role_is_admin else "Mis Reservas",
                "Gestiona las reservaciones próximas, precios y notas de seguimiento.",
                [(num_reservations, "Reservas")],
                "Ver Reservas", "launch_reservas", "page_reservas",
            )
            _dash_card(
                "editor", "Editor de Anuncios IA",
                "Integra logotipos y creatividades de tus clientes en muros y espectaculares reales con IA.",
                None,
                "Abrir Editor IA", "launch_editor", "page_editor",
            )

        st.divider()
        st.caption("Publimex Hub · © 2026. Usa la barra lateral para navegar entre aplicaciones.")

    draw_panel()
