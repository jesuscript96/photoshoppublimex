"""Gestión de usuarios (solo administradores).

Permite ver los perfiles registrados en Supabase y cambiar sus roles.
Vive como página propia en la barra lateral (sección Administración).
"""

import streamlit as st
from src.supabase_client import is_admin, get_all_profiles, update_user_role
from src.theme import page_header


def show_usuarios():
    page_header(
        "Gestión de Usuarios",
        "Consulta los perfiles registrados y cambia sus roles (administrador o usuario).",
        eyebrow="Administración",
    )

    user_id = st.session_state.get("user_id")
    token = st.session_state.get("user_token")

    if not is_admin(st.session_state.get("user_role")):
        st.warning("Esta sección es solo para administradores.", icon=":material/lock:")
        return

    with st.spinner("Cargando perfiles..."):
        profiles = get_all_profiles(token)

    if not profiles:
        st.warning("No se encontraron perfiles de usuario en la base de datos.")
        return

    admins = sum(1 for p in profiles if is_admin(p.get("role")))
    m1, m2 = st.columns(2)
    m1.metric("Usuarios registrados", len(profiles))
    m2.metric("Administradores", admins)
    st.write("")

    for p in sorted(profiles, key=lambda x: x.get("name", "").lower()):
        p_id = p.get("id")
        p_name = p.get("name", "Sin nombre")
        p_role = p.get("role", "vendedor")
        p_role_display = "Admin" if is_admin(p_role) else "Usuario"

        with st.container(border=True):
            col_u1, col_u2 = st.columns([3, 1])
            with col_u1:
                st.markdown(f"**{p_name}**")
                st.caption(f"ID: `{p_id}` · Rol actual: **{p_role_display}**")
            with col_u2:
                if p_id == user_id:
                    st.info("Tu perfil")
                elif is_admin(p_role):
                    if st.button("Hacer Usuario", key=f"demote_{p_id}", use_container_width=True):
                        if update_user_role(token, p_id, "vendedor"):
                            st.success(f"{p_name} cambiado a Usuario.")
                            st.rerun()
                        else:
                            st.error("Error al actualizar el perfil.")
                else:
                    if st.button("Hacer Admin", key=f"promote_{p_id}", type="primary", use_container_width=True):
                        if update_user_role(token, p_id, "administrador"):
                            st.success(f"{p_name} promovido a Admin.")
                            st.rerun()
                        else:
                            st.error("Error al actualizar el perfil.")
