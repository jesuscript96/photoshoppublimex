import os
import requests
from datetime import date, datetime
import streamlit as st
import pandas as pd
from src.supabase_client import (
    get_user_reservations,
    update_user_reservation,
    unassign_reservation_from_user,
    is_admin,
    get_all_reservations,
    get_all_profiles,
    assign_reservation_to_user
)

# ── Airtable credentials & loader ─────────────────────────────────────────────

def get_secret(key):
    try:
        return st.secrets[key]
    except Exception:
        return os.environ.get(key, "")

AIRTABLE_TOKEN = get_secret("AIRTABLE_TOKEN")
BASE_ID = "appW4QjUOV9nXQkx9"
T_RESERVACIONES  = "tbluUAzNFSuaqMrYX"
T_ESPACIOS       = "tblQ9Z0KW0XheaHRc"
T_CLIENTES       = "tblkKHa9CNt285uv1"

ESTADOS = ["Propuesta", "Confirmada", "Activa", "Finalizada", "Cancelada", "Pendiente"]

ESTADO_BADGE = {
    "Propuesta":  "Propuesta",
    "Pendiente":  "Pendiente",
    "Confirmada": "Confirmada",
    "Activa":     "Activa",
    "Finalizada": "Finalizada",
    "Cancelada":  "Cancelada",
}

@st.cache_data(ttl=15, show_spinner=False)
def load_airtable_data():
    if not AIRTABLE_TOKEN:
        return [], [], []
    headers = {"Authorization": f"Bearer {AIRTABLE_TOKEN}"}
    
    def fetch_all(table_id):
        records = []
        url = f"https://api.airtable.com/v0/{BASE_ID}/{table_id}"
        params = {}
        while True:
            r = requests.get(url, headers=headers, params=params, timeout=15)
            r.raise_for_status()
            data = r.json()
            records.extend(data.get("records", []))
            offset = data.get("offset")
            if not offset:
                break
            params = {"offset": offset}
        return records

    try:
        res = fetch_all(T_RESERVACIONES)
        esp = fetch_all(T_ESPACIOS)
        cli = fetch_all(T_CLIENTES)
        return res, esp, cli
    except Exception as e:
        st.error(f"Error al conectar con Airtable: {e}")
        return [], [], []

def airtable_patch(table_id: str, record_id: str, fields: dict):
    headers = {"Authorization": f"Bearer {AIRTABLE_TOKEN}", "Content-Type": "application/json"}
    r = requests.patch(
        f"https://api.airtable.com/v0/{BASE_ID}/{table_id}/{record_id}",
        headers=headers, json={"fields": fields}, timeout=15,
    )
    return r

def refresh():
    load_airtable_data.clear()
    st.rerun()

def get_space_id(esp):
    f = esp.get("fields", {})
    val = f.get("\ufeffID")
    if val is None:
        val = f.get("ID")
    if val is not None:
        try:
            return int(val)
        except (ValueError, TypeError):
            pass
    return 9999

def get_client_color(client_name):
    colors = [
        {"bg": "#FFE2E2", "text": "#990000", "border": "#FFCCCC"},
        {"bg": "#E2F0D9", "text": "#385723", "border": "#C5E0B4"},
        {"bg": "#FFF2CC", "text": "#7F6000", "border": "#FFE699"},
        {"bg": "#DDEBF7", "text": "#1F4E79", "border": "#BDD7EE"},
        {"bg": "#E8D8F8", "text": "#602080", "border": "#D0B0F0"},
        {"bg": "#FCE4D6", "text": "#C65911", "border": "#F8CBAD"},
        {"bg": "#E2F3F5", "text": "#0E7A8A", "border": "#BCE3E8"},
    ]
    hash_val = sum(ord(c) for c in client_name)
    return colors[hash_val % len(colors)]

def render_admin_calendar(espacios_raw, reservaciones_raw, clientes_raw, supabase_res_map, profile_map):
    import calendar
    st.markdown("### Vista de Ocupación Anual")
    st.markdown("Filtra los soportes por zona, tipo y dirección para visualizar el calendario de reservas de cada mes.")
    
    col_f1, col_f2, col_f3, col_f4 = st.columns([2, 1, 1, 1])
    with col_f1:
        search_q = st.text_input("Buscar dirección soporte", key="cal_search")
    with col_f2:
        sel_zones = st.multiselect("Zona", options=["CDMX", "EDOMX", "ACA"], default=["CDMX", "EDOMX", "ACA"], key="cal_zones")
    with col_f3:
        sel_cats = st.multiselect("Categoría", options=["Muro", "Muro + Espectacular", "Pantalla Digital", "Valla"], default=["Muro", "Muro + Espectacular", "Pantalla Digital", "Valla"], key="cal_cats")
    with col_f4:
        current_year = datetime.now().year
        year_options = [current_year - 1, current_year, current_year + 1]
        if 2026 not in year_options:
            year_options.append(2026)
        year_options = sorted(list(set(year_options)))
        default_idx = year_options.index(2026) if 2026 in year_options else 0
        sel_year = st.selectbox("Año", options=year_options, index=default_idx, key="cal_year")

    # Filter spaces
    filtered_spaces = []
    for esp in espacios_raw:
        ef = esp.get("fields", {})
        dir_val = ef.get("Direccion", "").lower()
        if search_q and search_q.lower() not in dir_val:
            continue
        zone_val = ef.get("Zona", "")
        if sel_zones and zone_val not in sel_zones:
            continue
        cat_val = ef.get("Categoria", "")
        if sel_cats and cat_val not in sel_cats:
            continue
        filtered_spaces.append(esp)
        
    filtered_spaces = sorted(filtered_spaces, key=get_space_id)
    
    # Pre-process relationships
    clientes_dict = {c["id"]: c.get("fields", {}) for c in clientes_raw}
    
    space_res = {}
    for r in reservaciones_raw:
        rf = r.get("fields", {})
        esp_ids = rf.get("Espacio (Nuevo)", [])
        if esp_ids:
            esp_id = esp_ids[0]
            if esp_id not in space_res:
                space_res[esp_id] = []
            space_res[esp_id].append(r)

    if not filtered_spaces:
        st.info("No se encontraron soportes que coincidan con los filtros.")
        return

    # Build HTML table
    html = []
    html.append("""
    <div style="overflow-x: auto; width: 100%; border: 1px solid #cbd5e1; border-radius: 8px; margin-top: 15px;">
      <table class="global-calendar-table" style="width: 100%; border-collapse: collapse; font-family: sans-serif; font-size: 0.82rem; color: #334155; min-width: 1000px;">
        <style>
          .global-calendar-table th {
              padding: 10px 8px;
              background: #f1f5f9;
              border: 1px solid #cbd5e1;
              font-weight: 700;
              text-align: center;
              color: #475569;
          }
          .global-calendar-table td {
              padding: 8px;
              border: 1px solid #e2e8f0;
              vertical-align: middle;
          }
          .global-calendar-table tr:hover {
              background-color: #f8fafc;
          }
        </style>
        <thead>
          <tr>
            <th style="width: 250px; min-width: 250px; position: sticky; left: 0; background: #f1f5f9; z-index: 10; border-right: 2px solid #cbd5e1; text-align: left;">Soporte</th>
            <th>Ene</th>
            <th>Feb</th>
            <th>Mar</th>
            <th>Abr</th>
            <th>May</th>
            <th>Jun</th>
            <th>Jul</th>
            <th>Ago</th>
            <th>Sep</th>
            <th>Oct</th>
            <th>Nov</th>
            <th>Dic</th>
          </tr>
        </thead>
        <tbody>
    """)

    for esp in filtered_spaces:
        ef = esp.get("fields", {})
        esp_rec_id = esp["id"]
        esp_id_num = ef.get("\ufeffID", ef.get("ID", "?"))
        direccion = ef.get("Direccion", "Sin dirección")
        zona = ef.get("Zona", "—")
        categoria = ef.get("Categoria", "—")
        precio_base = ef.get("Precio_MXN", 0)

        # Space cell (sticky)
        html.append(f"""
          <tr>
            <td style="position: sticky; left: 0; background: #f8fafc; font-weight: 600; border-right: 2px solid #cbd5e1; z-index: 5; box-shadow: 2px 0 5px rgba(0,0,0,0.02); text-align: left;">
              <div style="font-weight: 700; color: #1e293b;">ID {esp_id_num} · {zona}</div>
              <div style="font-size: 0.72rem; color: #64748b; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 230px;" title="{direccion}">{direccion}</div>
              <div style="font-size: 0.68rem; margin-top: 3px;"><span style="background: #e2e8f0; padding: 2px 5px; border-radius: 4px; color: #475569;">{categoria}</span></div>
            </td>
        """)

        # Month cells
        for m in range(1, 13):
            month_start = date(sel_year, m, 1)
            month_end = date(sel_year, m, calendar.monthrange(sel_year, m)[1])
            
            # Find overlaps
            overlapping_res = []
            for r in space_res.get(esp_rec_id, []):
                rf = r.get("fields", {})
                if rf.get("Estado") == "Cancelada":
                    continue
                start_str = rf.get("Fecha_Inicio")
                end_str = rf.get("Fecha_Fin")
                if start_str and end_str:
                    try:
                        r_start = date.fromisoformat(start_str)
                        r_end = date.fromisoformat(end_str)
                        if r_start <= month_end and r_end >= month_start:
                            overlapping_res.append(r)
                    except ValueError:
                        pass

            if not overlapping_res:
                html.append("""
            <td style="text-align: center; background: #ffffff;">
              <span style="color: #cbd5e1; font-size: 0.65rem;">—</span>
            </td>
                """)
            else:
                html.append("""
            <td style="background: #ffffff;">
              <div style="display: flex; flex-direction: column; gap: 3px; align-items: center;">
                """)
                for r in overlapping_res:
                    rf = r.get("fields", {})
                    r_id = r["id"]
                    
                    # Resolve client brand
                    cli_ids = rf.get("Cliente", [])
                    cli_id = cli_ids[0] if cli_ids else None
                    cli_fields = clientes_dict.get(cli_id, {}) if cli_id else {}
                    client_name = cli_fields.get("Empresa", "Desconocido")
                    
                    # Tooltip construction
                    start_str = rf.get("Fecha_Inicio", "?")
                    end_str = rf.get("Fecha_Fin", "?")
                    estado = rf.get("Estado", "Confirmada")
                    
                    # Private details from Supabase if present
                    if r_id in supabase_res_map:
                        r_sp = supabase_res_map[r_id]
                        gestor = profile_map.get(r_sp.get("user_id"), "Desconocido")
                        precio_ac = f"${r_sp.get('precio_acordado', 0):,.0f} MXN"
                        notas_sp = r_sp.get("notas_gestion", "Sin notas")
                        tooltip = f"Cliente: {client_name}\nFechas: {start_str} a {end_str}\nEstado: {estado}\nGestor: {gestor}\nPrecio Acordado: {precio_ac}\nNotas: {notas_sp}"
                    else:
                        tooltip = f"Cliente: {client_name}\nFechas: {start_str} a {end_str}\nEstado: {estado}\nGestor: Sin asignar\nPrecio Base: ${precio_base:,.0f} MXN"
                    
                    color = get_client_color(client_name)
                    
                    # Double quotes escaping in HTML attribute title
                    tooltip_escaped = tooltip.replace('"', '&quot;')
                    
                    html.append(f"""
                <div style="background-color: {color['bg']}; color: {color['text']}; border: 1px solid {color['border']}; border-radius: 4px; padding: 3px 5px; font-size: 0.68rem; font-weight: 700; text-align: center; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 75px; width: 100%; cursor: help;" title="{tooltip_escaped}">
                  {client_name}
                </div>
                    """)
                html.append("""
              </div>
            </td>
                """)

        html.append("          </tr>")

    html.append("""
        </tbody>
      </table>
    </div>
    """)

    clean_html = "\n".join([line.strip() for line in "".join(html).split("\n")])
    st.markdown(clean_html, unsafe_allow_html=True)

# ── Main view function ────────────────────────────────────────────────────────

def show_reservas():
    st.markdown("""
        <style>
        .reservas-header {
            font-size: 2rem;
            font-weight: 800;
            color: #111111;
            margin-bottom: 5px;
        }
        .reservas-header span {
            color: #E60000;
        }
        </style>
    """, unsafe_allow_html=True)

    st.markdown('<div class="reservas-header"><svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="#E60000" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="width: 22px; height: 22px; display: inline-block; vertical-align: -4px; margin-right: 8px;"><path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"/><rect x="8" y="2" width="8" height="4" rx="1" ry="1"/></svg>Reservas <span>Asignadas / Globales</span></div>', unsafe_allow_html=True)
    
    user_id = st.session_state.get("user_id")
    token = st.session_state.get("user_token")
    user_role = st.session_state.get("user_role")
    user_role_is_admin = is_admin(user_role)

    if user_role_is_admin:
        st.markdown("Consulta y gestiona las reservas de publicidad exterior de todos los usuarios en Supabase.")
    else:
        st.markdown("Consulta y gestiona las reservas de publicidad exterior que tienes asignadas. El precio pactado y las notas son estrictamente privados.")

    # Load data from Airtable and Supabase
    with st.spinner("Sincronizando información de reservas..."):
        reservaciones_raw, espacios_raw, clientes_raw = load_airtable_data()
        if user_role_is_admin:
            supabase_res = get_all_reservations(token)
            profiles = get_all_profiles(token)
            profile_map = {p["id"]: p.get("name", p["id"]) for p in profiles}
        else:
            supabase_res = get_user_reservations(user_id, token)
            profiles = []
            profile_map = {user_id: st.session_state.get("user_name", "Tú")}

    if not supabase_res:
        if not user_role_is_admin:
            st.info("Aún no tienes reservaciones asignadas a tu gestión.")
            st.markdown("Puedes explorar los espacios publicitarios disponibles y asignarte reservaciones haciendo clic en el botón de abajo:")
            if st.button("Ir a Disponibilidades", type="primary"):
                if "page_disponibilidades" in st.session_state:
                    st.switch_page(st.session_state.page_disponibilidades)
            return
        else:
            st.info("Nota: Actualmente no hay reservaciones registradas en Supabase. Las listas de gestión de gestores están vacías, pero puedes consultar todas las reservas de Airtable en la pestaña 'Calendario Global (Admin)'.")

    # Map Airtable structures for fast lookup
    espacios_map = {e["id"]: e for e in espacios_raw}
    clientes_map = {c["id"]: c for c in clientes_raw}
    supabase_res_map = {r["reservation_id"]: r for r in supabase_res} if supabase_res else {}

    # Filter Airtable reservations (for admin, include ALL reservations; for vendor, only assigned ones)
    my_reservations = []
    for r in reservaciones_raw:
        r_id = r["id"]
        if user_role_is_admin:
            my_reservations.append((r, supabase_res_map.get(r_id)))
        else:
            if r_id in supabase_res_map:
                my_reservations.append((r, supabase_res_map[r_id]))

    # Filter by date: show active and future reservations (from current month onwards)
    today = date.today()
    start_of_current_month = date(today.year, today.month, 1)

    upcoming_reservations = []
    past_reservations = []

    for r_art, r_sp in my_reservations:
        rf = r_art["fields"]
        ff_str = rf.get("Fecha_Fin")
        is_upcoming = True
        if ff_str:
            try:
                ff = date.fromisoformat(ff_str)
                if ff < start_of_current_month:
                    is_upcoming = False
            except ValueError:
                pass
        
        if is_upcoming:
            upcoming_reservations.append((r_art, r_sp))
        else:
            past_reservations.append((r_art, r_sp))

    # Tabs for Active/Upcoming, History and Admin Global Calendar
    tabs_list = [
        f"Gestión Próximos Meses ({len(upcoming_reservations)})",
        f"Historial Pasadas ({len(past_reservations)})"
    ]
    if user_role_is_admin:
        tabs_list.append("Calendario Global (Admin) 📅")
        
    tabs = st.tabs(tabs_list)

    def render_reservations_list(items, is_history=False):
        if not items:
            st.info("No hay reservaciones en esta sección.")
            return

        items_sorted = sorted(
            items,
            key=lambda x: x[0]["fields"].get("Fecha_Inicio", ""),
            reverse=True
        )

        for r_art, r_sp in items_sorted:
            rf = r_art["fields"]
            rid = r_art["id"]
            # Resolve space details
            esp_ids = rf.get("Espacio (Nuevo)", [])
            esp_ref = espacios_map[esp_ids[0]] if esp_ids and esp_ids[0] in espacios_map else None
            esp_dir = esp_ref["fields"].get("Direccion", "Dirección no encontrada") if esp_ref else "—"
            esp_cat = esp_ref["fields"].get("Categoria", "Categoría no encontrada") if esp_ref else "—"
            esp_id_num = esp_ref["fields"].get("﻿ID", esp_ref["fields"].get("ID", "?")) if esp_ref else "?"
            precio_base = float(esp_ref["fields"].get("Precio_MXN", 0) if esp_ref else 0)

            # Resolve client
            cli_ids = rf.get("Cliente", [])
            cli_ref = clientes_map[cli_ids[0]] if cli_ids and cli_ids[0] in clientes_map else None
            cli_name = cli_ref["fields"].get("Empresa", "Cliente desconocido") if cli_ref else "—"

            estado_b = ESTADO_BADGE.get(rf.get("Estado", ""), rf.get("Estado", ""))
            
            # Resolve prices & managers
            sp_res_id = r_sp["id"] if r_sp else None
            precio_acordado = float(r_sp["precio_acordado"]) if r_sp else precio_base
            notas_gestion = r_sp["notas_gestion"] if r_sp else ""
            curr_gestor_id = r_sp["user_id"] if r_sp else user_id
            owner_name = profile_map.get(curr_gestor_id, "Desconocido") if r_sp else "Sin asignar"

            # Card header string
            owner_suffix = f" · [Gestor: {owner_name}]" if user_role_is_admin else ""
            card_title = f"ID {esp_id_num} · {esp_dir[:40]} · **{cli_name}**{owner_suffix}"
            card_subtitle = f"{rf.get('Fecha_Inicio','?')} ➔ {rf.get('Fecha_Fin','?')} · {estado_b} · 💰 **${precio_acordado:,.0f} MXN**"

            with st.expander(f"{card_title} ({rf.get('Fecha_Inicio','?')})"):
                st.markdown(f"### Detalles de la Reservación")
                col_i1, col_i2 = st.columns(2)
                
                with col_i1:
                    st.write(f"**Cliente/Empresa:** {cli_name}")
                    st.write(f"**Dirección Soporte:** {esp_dir} (Categoría: {esp_cat})")
                    st.write(f"**Período:** {rf.get('Fecha_Inicio','?')} al {rf.get('Fecha_Fin','?')}")
                    
                with col_i2:
                    if user_role_is_admin:
                        st.write(f"👤 **Gestor Asignado:** {owner_name}")
                    st.write(f"**Estado de Renta (Compartido):** {estado_b}")
                    st.markdown(f"**Precio Acordado (Privado):** `${precio_acordado:,.0f} MXN`" if r_sp else f"**Precio Acordado (Privado):** *No asignado (Renta base: ${precio_acordado:,.0f} MXN)*")
                    st.write(f"**Notas de Seguimiento (Privado):** {notas_gestion or 'Sin notas'}")

                # Edit & Unassign Buttons
                st.write("")
                col_btn1, col_btn2 = st.columns([1, 1])
                with col_btn1:
                    if st.button("Editar Privados y Estado", icon=":material/edit:", key=f"edit_res_{rid}"):
                        st.session_state[f"edit_mode_{rid}"] = True
                        st.session_state.pop(f"confirm_unassign_{rid}", None)
                with col_btn2:
                    if r_sp:
                        btn_label = "Quitar de mi gestión" if not user_role_is_admin else "Quitar / Desasignar"
                        if st.button(btn_label, icon=":material/remove_circle:", key=f"unassign_res_{rid}"):
                            st.session_state[f"confirm_unassign_{rid}"] = True
                            st.session_state.pop(f"edit_mode_{rid}", None)
                    else:
                        st.button("No asignado", icon=":material/info:", disabled=True, key=f"unassign_disabled_{rid}")

                # ── Edit Form ─────────────────────────────────────────────────
                if st.session_state.get(f"edit_mode_{rid}", False):
                    st.markdown("---")
                    st.markdown("**Editar Detalles Privados de Reservación**")
                    with st.form(f"form_edit_res_{rid}"):
                        st.write("Puedes modificar el precio acordado privado y tus notas internas de Supabase. También puedes cambiar el Estado general de la reserva en Airtable.")
                        
                        ec1, ec2 = st.columns(2)
                        with ec1:
                            new_price = st.number_input("Precio Privado (MXN) *", value=precio_acordado, min_value=0.0, step=1000.0)
                        with ec2:
                            curr_idx = ESTADOS.index(rf.get("Estado", "Propuesta")) if rf.get("Estado") in ESTADOS else 0
                            new_status = st.selectbox("Estado de Renta (Airtable) *", ESTADOS, index=curr_idx)

                        if user_role_is_admin and profiles:
                            profile_options = {p["id"]: p.get("name", p["id"]) for p in profiles}
                            if curr_gestor_id not in profile_options:
                                profile_options[curr_gestor_id] = owner_name
                            edit_gestor = st.selectbox(
                                "Reasignar Gestor (Admin)" if r_sp else "Asignar Gestor (Admin)",
                                options=list(profile_options.keys()),
                                format_func=lambda x: profile_options[x],
                                index=list(profile_options.keys()).index(curr_gestor_id),
                                key=f"eges_res_{rid}"
                            )
                        else:
                            edit_gestor = curr_gestor_id

                        new_notes = st.text_area("Notas internas de gestión (Supabase)", value=notas_gestion)

                        sub_col, can_col = st.columns(2)
                        with sub_col:
                            save_res = st.form_submit_button("Guardar Cambios", icon=":material/save:", type="primary", use_container_width=True)
                        with can_col:
                            cancel_res = st.form_submit_button("Cancelar", use_container_width=True)

                    if save_res:
                        # 1. Update general status in Airtable
                        art_resp = airtable_patch(T_RESERVACIONES, rid, {"Estado": new_status})
                        
                        # 2. Update/Assign in Supabase
                        if r_sp:
                            sp_success = update_user_reservation(token, sp_res_id, new_price, new_notes, user_id=edit_gestor)
                        else:
                            sp_success = assign_reservation_to_user(edit_gestor or user_id, token, rid, new_price, new_notes)

                        if art_resp.status_code == 200 and sp_success:
                            st.success("Reserva actualizada correctamente en Airtable y Supabase.")
                            st.session_state.pop(f"edit_mode_{rid}", None)
                            refresh()
                        else:
                            st.error(f"Error al guardar: Airtable={art_resp.status_code}, Supabase={sp_success}")

                    if cancel_res:
                        st.session_state.pop(f"edit_mode_{rid}", None)
                        st.rerun()

                # ── Unassign Confirmation ─────────────────────────────────────
                if st.session_state.get(f"confirm_unassign_{rid}", False) and r_sp:
                    st.markdown("---")
                    warn_lbl = (
                        "¿Seguro que deseas quitar esta reservación de tu gestión? Esto eliminará de forma permanente tu precio privado y tus notas en Supabase. La reserva general permanecerá en Airtable."
                        if not user_role_is_admin else
                        f"¿Seguro que deseas desasignar esta reservación de {owner_name}? Esto eliminará de forma permanente su precio privado y notas en Supabase. La reserva general permanecerá en Airtable."
                    )
                    st.warning(warn_lbl, icon=":material/warning:")
                    u_col1, u_col2 = st.columns(2)
                    with u_col1:
                        if st.button("Sí, desasignar", key=f"yes_unassign_{rid}", type="primary", use_container_width=True):
                            success = unassign_reservation_from_user(token, sp_res_id)
                            if success:
                                st.session_state.pop(f"confirm_unassign_{rid}", None)
                                refresh()
                            else:
                                st.error("Error al eliminar la asignación en Supabase.")
                    with u_col2:
                        if st.button("Cancelar", key=f"no_unassign_{rid}", use_container_width=True):
                            st.session_state.pop(f"confirm_unassign_{rid}", None)
                            st.rerun()

    with tabs[0]:
        render_reservations_list(upcoming_reservations, is_history=False)

    with tabs[1]:
        render_reservations_list(past_reservations, is_history=True)
        
    if user_role_is_admin:
        with tabs[2]:
            render_admin_calendar(espacios_raw, reservaciones_raw, clientes_raw, supabase_res_map, profile_map)
