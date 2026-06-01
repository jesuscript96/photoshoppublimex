import os
import requests
import streamlit as st
import pandas as pd
from src.supabase_client import (
    get_user_contacts,
    create_user_contact,
    update_user_contact,
    delete_user_contact,
    is_admin,
    get_all_contacts,
    get_all_profiles
)

# ── Airtable client loader ────────────────────────────────────────────────────

def get_secret(key):
    try:
        return st.secrets[key]
    except Exception:
        return os.environ.get(key, "")

AIRTABLE_TOKEN = get_secret("AIRTABLE_TOKEN")
BASE_ID = "appW4QjUOV9nXQkx9"
T_CLIENTES = "tblkKHa9CNt285uv1"

@st.cache_data(ttl=60, show_spinner=False)
def fetch_client_companies():
    if not AIRTABLE_TOKEN:
        return []
    url = f"https://api.airtable.com/v0/{BASE_ID}/{T_CLIENTES}"
    headers = {"Authorization": f"Bearer {AIRTABLE_TOKEN}"}
    companies = []
    try:
        r = requests.get(url, headers=headers, params={"fields[]": "Empresa"}, timeout=10)
        if r.status_code == 200:
            records = r.json().get("records", [])
            for rec in records:
                empresa = rec["fields"].get("Empresa")
                if empresa and empresa not in companies:
                    companies.append(empresa)
            companies.sort()
    except Exception:
        pass
    return companies

def refresh():
    st.rerun()

# ── Main view function ────────────────────────────────────────────────────────

def show_contactos():
    st.markdown("""
        <style>
        .contacts-header {
            font-size: 2rem;
            font-weight: 800;
            color: #111111;
            margin-bottom: 5px;
        }
        .contacts-header span {
            color: #E60000;
        }
        </style>
    """, unsafe_allow_html=True)

    st.markdown('<div class="contacts-header"><svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="#E60000" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="width: 22px; height: 22px; display: inline-block; vertical-align: -4px; margin-right: 8px;"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>Contactos <span>Privados / Globales</span></div>', unsafe_allow_html=True)

    user_id = st.session_state.get("user_id")
    token = st.session_state.get("user_token")
    user_role = st.session_state.get("user_role")
    user_role_is_admin = is_admin(user_role)

    if user_role_is_admin:
        st.markdown("Administra la base de datos global de contactos de clientes en Supabase. Al ser Administrador, puedes ver, editar y borrar los contactos de todos los usuarios.")
    else:
        st.markdown("Administra tu base de datos de contactos de clientes en Supabase. Esta información es privada y solo tú puedes verla.")

    # Load data
    with st.spinner("Cargando contactos de Supabase..."):
        if user_role_is_admin:
            contacts = get_all_contacts(token)
            profiles = get_all_profiles(token)
            profile_map = {p["id"]: p.get("name", p["id"]) for p in profiles}
        else:
            contacts = get_user_contacts(user_id, token)
            profiles = []
            profile_map = {user_id: st.session_state.get("user_name", "Tú")}
        existing_companies = fetch_client_companies()

    tab_list, tab_new = st.tabs(["Lista de Contactos", "Agregar Contacto"])

    with tab_list:
        # Search bar
        search_query = st.text_input("Buscar contacto por nombre, empresa o correo", placeholder="Escribe el nombre del contacto...")
        
        # Filter contacts
        filtered_contacts = contacts
        if search_query:
            q = search_query.lower()
            filtered_contacts = [
                c for c in contacts
                if q in c.get("nombre", "").lower() 
                or q in c.get("empresa", "").lower() 
                or q in c.get("email", "").lower()
            ]

        st.markdown(f"**Tienes {len(filtered_contacts)} contactos**")

        if not filtered_contacts:
            if search_query:
                st.info("Ningún contacto coincide con la búsqueda.")
            else:
                st.info("Aún no tienes contactos guardados. Ve a la pestaña 'Agregar Contacto' para crear uno nuevo.")
        else:
            # Table view using dataframes for readability
            df_data = []
            for c in filtered_contacts:
                owner_name = profile_map.get(c.get("user_id"), "Desconocido")
                row_data = {
                    "Nombre": c.get("nombre"),
                    "Empresa / Cliente": c.get("empresa"),
                    "Email": c.get("email") or "—",
                    "Teléfono": c.get("telefono") or "—",
                    "Notas": c.get("notas") or "—"
                }
                if user_role_is_admin:
                    row_data["Gestor"] = owner_name
                df_data.append(row_data)
            
            st.dataframe(pd.DataFrame(df_data), use_container_width=True)
            st.divider()

            # Detailed list with Edit/Delete buttons
            st.markdown("### Gestionar Contactos")
            for c in sorted(filtered_contacts, key=lambda x: x.get("nombre", "")):
                c_id = c.get("id")
                owner_name = profile_map.get(c.get("user_id"), "Desconocido")
                owner_suffix = f" · [Gestor: {owner_name}]" if user_role_is_admin else ""
                label = f"**{c.get('nombre')}** · {c.get('empresa')}{owner_suffix}"
                
                with st.expander(label):
                    col_det, col_act = st.columns([3, 1])
                    
                    with col_det:
                        if user_role_is_admin:
                            st.write(f"👤 **Gestor del Contacto:** {owner_name}")
                        st.write(f"**Email:** {c.get('email') or '—'}")
                        st.write(f"**Teléfono:** {c.get('telefono') or '—'}")
                        st.write(f"**Notas:** {c.get('notas') or '—'}")
                        
                    with col_act:
                        if st.button("Editar", icon=":material/edit:", key=f"edit_c_{c_id}"):
                            st.session_state[f"edit_contact_{c_id}"] = True
                            st.session_state.pop(f"confirm_del_c_{c_id}", None)
                        if st.button("Borrar", icon=":material/delete:", key=f"del_c_{c_id}"):
                            st.session_state[f"confirm_del_c_{c_id}"] = True
                            st.session_state.pop(f"edit_contact_{c_id}", None)

                    # ── Edit form ─────────────────────────────────────────────────
                    if st.session_state.get(f"edit_contact_{c_id}", False):
                        st.markdown("---")
                        st.markdown("**Editar Contacto**")
                        with st.form(f"form_edit_c_{c_id}"):
                            e_nombre = st.text_input("Nombre completo", value=c.get("nombre"))
                            
                            # Suggested companies + option to enter custom
                            if existing_companies:
                                try:
                                    curr_idx = existing_companies.index(c.get("empresa"))
                                except ValueError:
                                    curr_idx = 0
                                e_empresa_sel = st.selectbox("Empresa / Cliente (Catálogo Airtable)", ["Ingresar manual..."] + existing_companies, index=curr_idx + 1 if c.get("empresa") in existing_companies else 0)
                            else:
                                e_empresa_sel = "Ingresar manual..."

                            if e_empresa_sel == "Ingresar manual...":
                                e_empresa_manual = st.text_input("Nombre de la Empresa (manual)", value=c.get("empresa"))
                                e_empresa = e_empresa_manual
                            else:
                                e_empresa = e_empresa_sel

                            if user_role_is_admin and profiles:
                                profile_options = {p["id"]: p.get("name", p["id"]) for p in profiles}
                                curr_owner_id = c.get("user_id")
                                if curr_owner_id not in profile_options:
                                    profile_options[curr_owner_id] = owner_name
                                e_owner = st.selectbox(
                                    "Propietario / Gestor (Admin)",
                                    options=list(profile_options.keys()),
                                    format_func=lambda x: profile_options[x],
                                    index=list(profile_options.keys()).index(curr_owner_id)
                                )
                            else:
                                e_owner = c.get("user_id")

                            e_email = st.text_input("Correo electrónico", value=c.get("email") or "")
                            e_telefono = st.text_input("Teléfono", value=c.get("telefono") or "")
                            e_notas = st.text_area("Notas / Comentarios", value=c.get("notas") or "")

                            s_col, c_col = st.columns(2)
                            with s_col:
                                save_c = st.form_submit_button("Guardar Cambios", icon=":material/save:", type="primary", use_container_width=True)
                            with c_col:
                                cancel_c = st.form_submit_button("Cancelar", use_container_width=True)

                        if save_c:
                            if not e_nombre or not e_empresa:
                                st.error("El nombre y la empresa son obligatorios.")
                            else:
                                update_data = {
                                    "nombre": e_nombre,
                                    "empresa": e_empresa,
                                    "email": e_email,
                                    "telefono": e_telefono,
                                    "notas": e_notas,
                                    "user_id": e_owner
                                }
                                success = update_user_contact(token, c_id, update_data)
                                if success:
                                    st.success("Contacto actualizado.")
                                    st.session_state.pop(f"edit_contact_{c_id}", None)
                                    refresh()
                                else:
                                    st.error("Error al actualizar en Supabase.")

                        if cancel_c:
                            st.session_state.pop(f"edit_contact_{c_id}", None)
                            st.rerun()

                    # ── Delete confirmation ───────────────────────────────────────
                    if st.session_state.get(f"confirm_del_c_{c_id}", False):
                        st.markdown("---")
                        st.warning(f"¿Confirmas el borrado permanente del contacto '{c.get('nombre')}'?", icon=":material/warning:")
                        d_col1, d_col2 = st.columns(2)
                        with d_col1:
                            if st.button("Sí, borrar permanentemente", icon=":material/delete_forever:", key=f"yes_del_c_{c_id}", type="primary", use_container_width=True):
                                success = delete_user_contact(token, c_id)
                                if success:
                                    st.session_state.pop(f"confirm_del_c_{c_id}", None)
                                    refresh()
                                else:
                                    st.error("Error al borrar el contacto de Supabase.")
                        with d_col2:
                            if st.button("Cancelar", key=f"no_del_c_{c_id}", use_container_width=True):
                                st.session_state.pop(f"confirm_del_c_{c_id}", None)
                                st.rerun()

    with tab_new:
        st.markdown("### Agregar Nuevo Contacto")
        with st.form("form_new_contact", clear_on_submit=True):
            nombre = st.text_input("Nombre completo *", placeholder="Ej. Ana Martínez")
            
            # Select company
            if existing_companies:
                empresa_sel = st.selectbox("Empresa / Cliente (Catálogo Airtable)", ["Ingresar manual..."] + existing_companies)
            else:
                empresa_sel = "Ingresar manual..."

            empresa_manual = st.text_input("Nombre de la Empresa (manual) *", placeholder="Ej. Coca-Cola", help="Usa este campo si no encuentras la empresa en el catálogo de Airtable.")
            
            # If admin, let them choose the owner of the new contact
            if user_role_is_admin and profiles:
                profile_options = {p["id"]: p.get("name", p["id"]) for p in profiles}
                new_owner = st.selectbox(
                    "Asignar Propietario / Gestor (Admin)",
                    options=list(profile_options.keys()),
                    format_func=lambda x: profile_options[x],
                    index=list(profile_options.keys()).index(user_id) if user_id in profile_options else 0
                )
            else:
                new_owner = user_id

            email = st.text_input("Correo electrónico", placeholder="ejemplo@correo.com")
            telefono = st.text_input("Teléfono", placeholder="+52 55 1234 5678")
            notas = st.text_area("Notas o especificaciones del contacto")

            submit_contact = st.form_submit_button("Crear Contacto", type="primary", use_container_width=True)

        if submit_contact:
            final_empresa = empresa_manual if empresa_sel == "Ingresar manual..." else empresa_sel
            
            if not nombre:
                st.error("El nombre completo es obligatorio.")
            elif not final_empresa:
                st.error("Debes seleccionar o ingresar una Empresa / Cliente.")
            else:
                contact_data = {
                    "nombre": nombre,
                    "empresa": final_empresa,
                    "email": email,
                    "telefono": telefono,
                    "notas": notas
                }
                success = create_user_contact(new_owner, token, contact_data)
                if success:
                    st.success("Contacto guardado privadamente en Supabase exitosamente.", icon=":material/check_circle:")
                    refresh()
                else:
                    st.error("Error de comunicación con Supabase. Contacto no guardado.")
