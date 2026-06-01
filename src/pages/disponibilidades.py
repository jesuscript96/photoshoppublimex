import io
import os
import calendar
from datetime import date, datetime

import pandas as pd
import requests
import streamlit as st
from PIL import Image

from src.supabase_client import (
    get_user_reservations,
    assign_reservation_to_user,
    update_user_reservation,
    unassign_reservation_from_user,
    is_admin,
    get_all_reservations,
    get_all_profiles
)

# ── Credentials & constants ───────────────────────────────────────────────────

def get_secret(key):
    try:
        return st.secrets[key]
    except Exception:
        return os.environ.get(key, "")

TOKEN = get_secret("AIRTABLE_TOKEN")
BASE = "appW4QjUOV9nXQkx9"
HEADERS = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}

T_ESPACIOS       = "tblQ9Z0KW0XheaHRc"
T_RESERVACIONES  = "tbluUAzNFSuaqMrYX"
T_CLIENTES       = "tblkKHa9CNt285uv1"
T_MATERIALES     = "tblxP9eGeHVbeBV6r"

MESES_ES = [
    "Enero","Febrero","Marzo","Abril","Mayo","Junio",
    "Julio","Agosto","Septiembre","Octubre","Noviembre","Diciembre",
]

ESTADOS = ["Propuesta", "Confirmada", "Activa", "Finalizada", "Cancelada", "Pendiente"]

ESTADO_BADGE = {
    "Propuesta":  "Propuesta",
    "Pendiente":  "Pendiente",
    "Confirmada": "Confirmada",
    "Activa":     "Activa",
    "Finalizada": "Finalizada",
    "Cancelada":  "Cancelada",
}

ZONAS       = ["CDMX", "EDOMX", "ACA"]
CATEGORIAS  = ["Muro", "Muro + Espectacular", "Pantalla Digital", "Valla"]

# ── Airtable helpers ──────────────────────────────────────────────────────────

def fetch_table(table_id: str) -> list:
    records, params = [], {}
    url = f"https://api.airtable.com/v0/{BASE}/{table_id}"
    while True:
        r = requests.get(url, headers=HEADERS, params=params, timeout=15)
        r.raise_for_status()
        data = r.json()
        records.extend(data.get("records", []))
        offset = data.get("offset")
        if not offset:
            break
        params = {"offset": offset}
    return records


@st.cache_data(ttl=15, show_spinner=False)
def load_data():
    espacios      = fetch_table(T_ESPACIOS)
    reservaciones = fetch_table(T_RESERVACIONES)
    clientes      = fetch_table(T_CLIENTES)
    materiales    = fetch_table(T_MATERIALES)
    return espacios, reservaciones, clientes, materiales


def refresh():
    load_data.clear()
    st.rerun()


def airtable_post(table_id: str, fields: dict):
    r = requests.post(
        f"https://api.airtable.com/v0/{BASE}/{table_id}",
        headers=HEADERS, json={"fields": fields}, timeout=15,
    )
    return r


def airtable_patch(table_id: str, record_id: str, fields: dict):
    r = requests.patch(
        f"https://api.airtable.com/v0/{BASE}/{table_id}/{record_id}",
        headers=HEADERS, json={"fields": fields}, timeout=15,
    )
    return r


def airtable_delete(table_id: str, record_id: str):
    r = requests.delete(
        f"https://api.airtable.com/v0/{BASE}/{table_id}/{record_id}",
        headers={"Authorization": f"Bearer {TOKEN}"}, timeout=15,
    )
    return r

# ── Domain helpers ────────────────────────────────────────────────────────────

def overlaps_month(fi_str: str, ff_str: str, year: int, month: int) -> bool:
    if not fi_str or not ff_str:
        return False
    try:
        fi = date.fromisoformat(fi_str)
        ff = date.fromisoformat(ff_str)
        month_start = date(year, month, 1)
        month_end   = date(year, month, calendar.monthrange(year, month)[1])
        return fi <= month_end and ff >= month_start
    except ValueError:
        return False


def espacio_option_label(esp: dict) -> str:
    f = esp["fields"]
    id_num = f.get("﻿ID", f.get("ID", ""))
    return f"ID {id_num} · {f.get('Direccion','')[:45]} · {f.get('Categoria','')}"


def cliente_option_label(cli: dict) -> str:
    f = cli["fields"]
    return f.get("Empresa") or f.get("Contacto") or cli["id"]


def reservaciones_for_space(esp_id: str, reservaciones: list) -> list:
    return [
        r for r in reservaciones
        if esp_id in r["fields"].get("Espacio (Nuevo)", [])
    ]


def active_reservaciones_in_month(esp_id: str, reservaciones: list, year: int, month: int) -> list:
    return [
        r for r in reservaciones_for_space(esp_id, reservaciones)
        if r["fields"].get("Estado") != "Cancelada"
        and overlaps_month(r["fields"].get("Fecha_Inicio"), r["fields"].get("Fecha_Fin"), year, month)
    ]


def availability_status(res_mes: list) -> tuple[str, str]:
    if not res_mes:
        return "LIBRE", "libre"
    estados = [r["fields"].get("Estado", "") for r in res_mes]
    if any(e in ("Confirmada", "Activa") for e in estados):
        return "OCUPADO", "ocupado"
    return "PROPUESTA", "propuesta"

# ── Presentation / PDF helpers ───────────────────────────────────────────────

_CATS_ORDER = ["Muro", "Muro + Espectacular", "Pantalla Digital", "Valla"]

_CAT_TO_SECCION = {
    "Muro":               "Sección - Muros",
    "Muro + Espectacular":"Sección - Muros",
    "Valla":              "Sección - Vallas",
    "Pantalla Digital":   "Sección - Pantallas Digitales",
}


def build_presentation_slides(espacios_filtrados: list, materiales: list) -> list:
    mat_by_nombre: dict = {}
    mat_by_tipo: dict = {}
    for m in materiales:
        f = m["fields"]
        mat_by_nombre[f.get("Nombre", "")] = f
        mat_by_tipo.setdefault(f.get("Tipo", ""), []).append(f)

    urls = []

    for mat in mat_by_tipo.get("Portada", []):
        for img in mat.get("Imagen", []):
            if img.get("url"):
                urls.append(img["url"])

    by_cat: dict = {}
    for esp in espacios_filtrados:
        cat = esp["fields"].get("Categoria", "")
        by_cat.setdefault(cat, []).append(esp)

    added_sections: set = set()
    for cat in _CATS_ORDER:
        if cat not in by_cat:
            continue
        sec = _CAT_TO_SECCION.get(cat, "")
        if sec and sec not in added_sections and sec in mat_by_nombre:
            for img in mat_by_nombre[sec].get("Imagen", []):
                if img.get("url"):
                    urls.append(img["url"])
            added_sections.add(sec)
        for esp in by_cat[cat]:
            for img in esp["fields"].get("Imagenes", []):
                if img.get("url"):
                    urls.append(img["url"])

    for cat, esps in by_cat.items():
        if cat in _CATS_ORDER:
            continue
        for esp in esps:
            for img in esp["fields"].get("Imagenes", []):
                if img.get("url"):
                    urls.append(img["url"])

    for mat in mat_by_tipo.get("Cierre", []):
        for img in mat.get("Imagen", []):
            if img.get("url"):
                urls.append(img["url"])

    return urls


def _fit_to_slide(img: Image.Image, w: int = 1920, h: int = 1080) -> Image.Image:
    r = img.width / img.height
    if r > w / h:
        nw, nh = w, int(w / r)
    else:
        nw, nh = int(h * r), h
    slide = Image.new("RGB", (w, h), (255, 255, 255))
    slide.paste(img.resize((nw, nh), Image.LANCZOS), ((w - nw) // 2, (h - nh) // 2))
    return slide


def generate_pdf_bytes(image_urls: list, status_placeholder=None) -> bytes | None:
    pil_imgs = []
    total = len(image_urls)
    for i, url in enumerate(image_urls):
        if status_placeholder:
            status_placeholder.caption(f"Descargando imagen {i + 1} / {total}…")
        try:
            resp = requests.get(url, timeout=20)
            resp.raise_for_status()
            img = Image.open(io.BytesIO(resp.content)).convert("RGB")
            pil_imgs.append(_fit_to_slide(img))
        except Exception:
            pass

    if not pil_imgs:
        return None

    buf = io.BytesIO()
    pil_imgs[0].save(
        buf, format="PDF", save_all=True,
        append_images=pil_imgs[1:], resolution=144,
    )
    return buf.getvalue()

# ── Main view function ────────────────────────────────────────────────────────

def show_disponibilidades():
    st.markdown("""
        <style>
        .disp-header {
            font-size: 2rem;
            font-weight: 800;
            color: #111111;
            margin-bottom: 5px;
        }
        .disp-header span {
            color: #E60000;
        }
        </style>
    """, unsafe_allow_html=True)

    st.markdown('<div class="disp-header">📅 Gestión de <span>Disponibilidades</span></div>', unsafe_allow_html=True)

    if not TOKEN:
        st.error("⚠️ Error de conexión con la base de datos de Airtable. Contacta al administrador.")
        return

    user_id = st.session_state.get("user_id")
    token = st.session_state.get("user_token")
    user_role = st.session_state.get("user_role")
    user_role_is_admin = is_admin(user_role)

    # ── Filter bar ────────────────────────────────────────────────────────────────
    with st.container():
        col1, col2, col3, col4, col5 = st.columns([1, 1, 2, 2, 1])
        with col1:
            sel_year = st.selectbox("Año", list(range(2024, 2029)),
                                    index=datetime.now().year - 2024)
        with col2:
            sel_month = st.selectbox("Mes", list(range(1, 13)),
                                     format_func=lambda m: MESES_ES[m - 1],
                                     index=datetime.now().month - 1)
        with col3:
            sel_zona = st.multiselect("Zona", ZONAS)
        with col4:
            sel_cat = st.multiselect("Categoría", CATEGORIAS)
        with col5:
            st.write("")
            st.write("")
            if st.button("🔄 Actualizar", use_container_width=True, key="btn_refresh"):
                refresh()

    # ── Load data (Airtable + Supabase) ──────────────────────────────────────────
    with st.spinner("Cargando datos de Airtable y Supabase..."):
        try:
            espacios_raw, reservaciones_raw, clientes_raw, materiales_raw = load_data()
            # Fetch private user reservations based on role
            if user_role_is_admin:
                supabase_res = get_all_reservations(token)
                profiles = get_all_profiles(token)
                profile_map = {p["id"]: p.get("name", p["id"]) for p in profiles}
            else:
                supabase_res = get_user_reservations(user_id, token)
                profiles = []
                profile_map = {user_id: st.session_state.get("user_name", "Tú")}
            # Create a dictionary mapping Airtable reservation_id to Supabase record
            supabase_res_map = {r["reservation_id"]: r for r in supabase_res}
        except requests.HTTPError as e:
            st.error(f"Error al conectar con Airtable: {e}")
            return
        except Exception as e:
            st.error(f"Error al cargar datos de Supabase: {e}")
            supabase_res_map = {}

    clientes_map = {c["id"]: c for c in clientes_raw}
    espacios_map = {e["id"]: e for e in espacios_raw}

    # ── Apply space filters ───────────────────────────────────────────────────────
    def passes_filters(esp: dict) -> bool:
        f = esp["fields"]
        if sel_zona and f.get("Zona") not in sel_zona:
            return False
        if sel_cat and f.get("Categoria") not in sel_cat:
            return False
        return True

    espacios_filtered = [e for e in espacios_raw if passes_filters(e)]

    # ── Summary metrics ───────────────────────────────────────────────────────────
    libres = propuestas = ocupados = 0
    for esp in espacios_filtered:
        res_mes = active_reservaciones_in_month(esp["id"], reservaciones_raw, sel_year, sel_month)
        badge, _ = availability_status(res_mes)
        if "LIBRE" in badge:
            libres += 1
        elif "PROPUESTA" in badge:
            propuestas += 1
        else:
            ocupados += 1

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total espacios", len(espacios_filtered))
    m2.metric("Libres", libres)
    m3.metric("Ocupados", ocupados)
    m4.metric("Propuestas / Pendientes", propuestas)

    st.divider()

    # ── Presentation download ─────────────────────────────────────────────────────
    pres_c1, pres_c2 = st.columns([1, 1])
    with pres_c1:
        gen_pdf = st.button(
            "Generar presentación PDF",
            icon=":material/analytics:",
            use_container_width=True,
            disabled=not espacios_filtered,
            key="btn_gen_pdf"
        )
    with pres_c2:
        if st.session_state.get("pres_pdf"):
            st.download_button(
                "Descargar PDF",
                icon=":material/download:",
                data=st.session_state["pres_pdf"],
                file_name=st.session_state.get("pres_name", "presentacion.pdf"),
                mime="application/pdf",
                use_container_width=True,
                key="btn_download_pdf"
            )

    if gen_pdf:
        slide_urls = build_presentation_slides(espacios_filtered, materiales_raw)
        _prog = st.empty()
        with st.spinner(f"Generando presentación ({len(slide_urls)} imágenes)…"):
            pdf_bytes = generate_pdf_bytes(slide_urls, status_placeholder=_prog)
        _prog.empty()
        if pdf_bytes:
            st.session_state["pres_pdf"] = pdf_bytes
            st.session_state["pres_name"] = (
                f"Disponibilidades_{MESES_ES[sel_month - 1]}_{sel_year}.pdf"
            )
            st.rerun()
        else:
            st.warning("No se encontraron imágenes para generar la presentación.")

    st.divider()

    # ── Availability grid ─────────────────────────────────────────────────────────
    tab_grid, tab_crud = st.tabs([
        f"Disponibilidad — {MESES_ES[sel_month - 1]} {sel_year}",
        "Reservaciones",
    ])

    with tab_grid:
        if not espacios_filtered:
            st.info("Ningún espacio coincide con los filtros aplicados.")
        else:
            for esp in sorted(espacios_filtered, key=lambda e: e["fields"].get("﻿ID", e["fields"].get("ID", 0))):
                f = esp["fields"]
                esp_id = esp["id"]
                res_mes = active_reservaciones_in_month(esp_id, reservaciones_raw, sel_year, sel_month)
                badge, status_key = availability_status(res_mes)

                header = (
                    f"**ID {f.get(chr(65279)+'ID', f.get('ID','?'))}** · "
                    f"{f.get('Direccion','—')} · "
                    f"{f.get('Categoria','—')} · "
                    f"Zona: {f.get('Zona','—')} &nbsp;&nbsp; {badge}"
                )

                with st.expander(header, expanded=(status_key == "libre")):
                    left, right = st.columns([3, 2])

                    with left:
                        st.markdown(
                            f"**Medida:** {f.get('Medida','—')}  "
                            f"({f.get('M2','—')} m²)  |  "
                            f"**Vista:** {f.get('Vista','—')}"
                        )
                        # Nota: El catálogo de base sigue mostrando el precio base de catálogo
                        precio = f.get("Precio_MXN", 0)
                        st.markdown(f"**Precio base catálogo:** ${precio:,.0f} MXN / mes")
                        if f.get("Referencia"):
                            st.caption(f.get("Referencia"))
                        if f.get("URL_Maps"):
                            st.markdown(f"[Ver en Maps]({f.get('URL_Maps')})")

                        imagenes = f.get("Imagenes", [])
                        if imagenes:
                            thumb_urls = []
                            for img in imagenes[:5]:
                                url = (
                                    img.get("thumbnails", {}).get("large", {}).get("url")
                                    or img.get("url")
                                )
                                if url:
                                    thumb_urls.append((url, img.get("filename", "")))
                            if thumb_urls:
                                st.markdown("**Fotos:**")
                                thumb_cols = st.columns(len(thumb_urls))
                                for col, (url, fname) in zip(thumb_cols, thumb_urls):
                                    col.image(url, use_container_width=True)

                    with right:
                        if res_mes:
                            st.markdown(f"**Reservaciones en {MESES_ES[sel_month - 1]}:**")
                            for r in res_mes:
                                rf = r["fields"]
                                r_id = r["id"]
                                cli_ids = rf.get("Cliente", [])
                                cli_name = (
                                    clientes_map[cli_ids[0]]["fields"].get("Empresa", "—")
                                    if cli_ids and cli_ids[0] in clientes_map else "—"
                                )
                                estado_badge = ESTADO_BADGE.get(rf.get("Estado", ""), rf.get("Estado", ""))
                                
                                # Comprobar si esta reserva está asignada en Supabase al usuario actual (o a cualquiera si es admin)
                                if r_id in supabase_res_map:
                                    sp_res = supabase_res_map[r_id]
                                    owner_name = profile_map.get(sp_res.get("user_id"), "Desconocido")
                                    owner_lbl = f"👤 **Gestor:** {owner_name}  \n" if user_role_is_admin else ""
                                    price_text = f"💰 **Precio acordado (Privado):** ${sp_res['precio_acordado']:,.0f} MXN"
                                    notes_text = f"📝 *Notas de gestión:* {sp_res['notas_gestion'] or 'Ninguna'}"
                                    
                                    st.markdown(
                                        f"- **{cli_name}**  \n"
                                        f"  {rf.get('Fecha_Inicio','?')} → {rf.get('Fecha_Fin','?')}  \n"
                                        f"  {estado_badge}  \n"
                                        f"  {owner_lbl}"
                                        f"  {price_text}  \n"
                                        f"  {notes_text}"
                                    )
                                else:
                                    # Ocultar precios acordados de otros usuarios o no asignados
                                    st.markdown(
                                        f"- **{cli_name}**  \n"
                                        f"  {rf.get('Fecha_Inicio','?')} → {rf.get('Fecha_Fin','?')}  \n"
                                        f"  {estado_badge}  ·  Precio: *[Privado]*"
                                    )
                                    
                                    # Botón para asignar a la gestión del usuario logueado o elegir gestor si es Admin
                                    if user_role_is_admin and profiles:
                                        with st.popover("Asignar a gestión...", icon=":material/assignment:"):
                                            profile_options = {p["id"]: p.get("name", p["id"]) for p in profiles}
                                            selected_assign_user = st.selectbox(
                                                "Seleccionar gestor",
                                                options=list(profile_options.keys()),
                                                format_func=lambda x: profile_options[x],
                                                key=f"assign_grid_select_{r_id}_{esp_id}"
                                            )
                                            assign_price = st.number_input("Precio Privado (MXN)", min_value=0, key=f"assign_grid_price_{r_id}_{esp_id}")
                                            assign_notes = st.text_input("Notas", key=f"assign_grid_notes_{r_id}_{esp_id}")
                                            if st.button("Confirmar Asignación", key=f"assign_grid_confirm_{r_id}_{esp_id}", type="primary"):
                                                success = assign_reservation_to_user(selected_assign_user, token, r_id, assign_price, assign_notes)
                                                if success:
                                                    st.success("Reserva asignada correctamente.")
                                                    refresh()
                                                else:
                                                    st.error("Error al asignar la reserva.")
                                    else:
                                        if st.button("Asignar a mi gestión", icon=":material/assignment:", key=f"assign_grid_{r_id}_{esp_id}"):
                                            success = assign_reservation_to_user(user_id, token, r_id, 0, "Asignado desde panel de disponibilidad")
                                            if success:
                                                st.success("Reserva asignada a tu gestión.")
                                                refresh()
                                            else:
                                                st.error("Error al asignar la reserva.")
                        else:
                            st.success("Disponible todo el mes")

                    # History for this space
                    hist = sorted(
                        reservaciones_for_space(esp_id, reservaciones_raw),
                        key=lambda r: r["fields"].get("Fecha_Inicio", ""),
                        reverse=True,
                    )
                    if hist:
                        st.markdown("---")
                        st.markdown("**Historial completo de reservaciones:**")
                        rows = []
                        for r in hist:
                            rf = r["fields"]
                            r_id = r["id"]
                            cli_ids = rf.get("Cliente", [])
                            cli_name = (
                                clientes_map[cli_ids[0]]["fields"].get("Empresa", "—")
                                if cli_ids and cli_ids[0] in clientes_map else "—"
                            )
                            
                            # Mostrar precio privado si corresponde, si no, "Privado"
                            if r_id in supabase_res_map:
                                p_val = f"${supabase_res_map[r_id]['precio_acordado']:,.0f}"
                            else:
                                p_val = "[Privado]"
                                
                            rows.append({
                                "#": rf.get("ID_Reservacion", ""),
                                "Cliente": cli_name,
                                "Inicio": rf.get("Fecha_Inicio", ""),
                                "Fin": rf.get("Fecha_Fin", ""),
                                "Días": rf.get("Duración_Días", ""),
                                "Estado": rf.get("Estado", ""),
                                "Precio Privado": p_val,
                            })
                        st.dataframe(
                            pd.DataFrame(rows),
                            use_container_width=True,
                            hide_index=True,
                        )

    # ── CRUD tab ──────────────────────────────────────────────────────────────────
    with tab_crud:
        sub_nueva, sub_lista = st.tabs(["➕ Nueva reservación", "✏️ Ver / Editar / Borrar"])

        # ── Nueva reservación ─────────────────────────────────────────────────────
        with sub_nueva:
            with st.form("form_nueva", clear_on_submit=True):
                st.markdown("### Nueva reservación")

                r1c1, r1c2 = st.columns(2)
                with r1c1:
                    esp_opts = {e["id"]: espacio_option_label(e) for e in espacios_raw}
                    sel_esp = st.selectbox(
                        "Espacio *",
                        options=list(esp_opts.keys()),
                        format_func=lambda x: esp_opts[x],
                    )
                with r1c2:
                    cli_opts = {c["id"]: cliente_option_label(c) for c in clientes_raw}
                    sel_cli = st.selectbox(
                        "Cliente *",
                        options=list(cli_opts.keys()),
                        format_func=lambda x: cli_opts[x],
                    )

                r2c1, r2c2 = st.columns(2)
                with r2c1:
                    new_fi = st.date_input(
                        "Fecha inicio *",
                        value=date(sel_year, sel_month, 1),
                    )
                with r2c2:
                    new_ff = st.date_input(
                        "Fecha fin *",
                        value=date(sel_year, sel_month, calendar.monthrange(sel_year, sel_month)[1]),
                    )

                r3c1, r3c2 = st.columns(2)
                with r3c1:
                    new_estado = st.selectbox("Estado *", ESTADOS)
                with r3c2:
                    # El precio acordado se ingresa aquí pero se guardará PRIVADAMENTE en Supabase
                    new_precio = st.number_input("Precio acordado privado (MXN)", min_value=0, step=5000)

                if user_role_is_admin and profiles:
                    profile_options = {p["id"]: p.get("name", p["id"]) for p in profiles}
                    sel_manager = st.selectbox(
                        "Asignar Gestor (Admin)",
                        options=list(profile_options.keys()),
                        format_func=lambda x: profile_options[x],
                        index=list(profile_options.keys()).index(user_id) if user_id in profile_options else 0
                    )
                else:
                    sel_manager = user_id

                new_notas = st.text_area("Notas internas (Supabase)", height=80)

                submitted = st.form_submit_button(
                    "Crear reservación", type="primary", use_container_width=True
                )

            if submitted:
                if new_ff <= new_fi:
                    st.error("La fecha fin debe ser posterior al inicio.")
                else:
                        # Registramos la reserva en Airtable (sin mandar el precio, para mantenerlo privado)
                    payload = {
                        "Espacio (Nuevo)": [sel_esp],
                        "Cliente":         [sel_cli],
                        "Fecha_Inicio":    new_fi.isoformat(),
                        "Fecha_Fin":       new_ff.isoformat(),
                        "Estado":          new_estado,
                    }
                    resp = airtable_post(T_RESERVACIONES, payload)
                    if resp.status_code == 200:
                        new_airtable_id = resp.json().get("id")
                        # Guardamos el precio de forma privada en Supabase
                        success_sp = assign_reservation_to_user(
                            sel_manager, token, new_airtable_id, new_precio, new_notas
                        )
                        if success_sp:
                            st.success("Reservación creada e información financiera privada guardada en Supabase.", icon=":material/check_circle:")
                        else:
                            st.warning("Reservación creada en Airtable, pero falló el registro del precio en Supabase.", icon=":material/warning:")
                        refresh()
                    else:
                        st.error(f"Error Airtable: {resp.text}")

        # ── Ver / Editar / Borrar ─────────────────────────────────────────────────
        with sub_lista:
            col_check, col_info = st.columns([2, 3])
            with col_check:
                solo_mes = st.checkbox("Solo reservaciones del mes seleccionado", value=True)
            with col_info:
                filtro_estado = st.multiselect(
                    "Filtrar por estado", ESTADOS,
                    default=[e for e in ESTADOS if e != "Cancelada"],
                    key="multiselect_status"
                )

            # Build display list
            res_display = []
            for r in reservaciones_raw:
                rf = r["fields"]
                estado = rf.get("Estado", "")

                if filtro_estado and estado not in filtro_estado:
                    continue
                if solo_mes and not overlaps_month(
                    rf.get("Fecha_Inicio"), rf.get("Fecha_Fin"), sel_year, sel_month
                ):
                    continue

                esp_ids = rf.get("Espacio (Nuevo)", [])
                esp_name = (
                    espacios_map[esp_ids[0]]["fields"].get("Direccion", "—")[:40]
                    if esp_ids and esp_ids[0] in espacios_map else "—"
                )
                cli_ids = rf.get("Cliente", [])
                cli_name = (
                    clientes_map[cli_ids[0]]["fields"].get("Empresa", "—")
                    if cli_ids and cli_ids[0] in clientes_map else "—"
                )
                
                r_id = r["id"]
                is_assigned = r_id in supabase_res_map
                p_acordado = supabase_res_map[r_id]["precio_acordado"] if is_assigned else 0.0
                n_gestion = supabase_res_map[r_id]["notas_gestion"] if is_assigned else ""
                
                res_display.append({
                    "_id":          r_id,
                    "_raw":         r,
                    "#":            rf.get("ID_Reservacion", ""),
                    "Espacio":      esp_name,
                    "Cliente":      cli_name,
                    "Inicio":       rf.get("Fecha_Inicio", ""),
                    "Fin":          rf.get("Fecha_Fin", ""),
                    "Días":         rf.get("Duración_Días", ""),
                    "Estado":       estado,
                    "Precio MXN":   p_acordado if is_assigned else 0.0,
                    "is_assigned":  is_assigned,
                    "Notas":        n_gestion if is_assigned else "",
                })

            res_display.sort(key=lambda x: x["Inicio"] or "", reverse=True)
            st.markdown(f"**{len(res_display)} reservaciones**")

            if not res_display:
                st.info("No hay reservaciones que coincidan con los filtros.")

            for row in res_display:
                rid = row["_id"]
                estado_b = ESTADO_BADGE.get(row["Estado"], row["Estado"])
                p_label = f"${row['Precio MXN']:,.0f} MXN (Privado)" if row["is_assigned"] else "*[Precio Privado]*"
                
                owner_lbl = ""
                if user_role_is_admin and row["is_assigned"]:
                    owner_lbl = f" · Gestor: {profile_map.get(supabase_res_map[rid].get('user_id'), 'Desconocido')}"

                label = (
                    f"#{row['#']} · {row['Espacio']} · **{row['Cliente']}** · "
                    f"{row['Inicio']} → {row['Fin']} · {estado_b} · {p_label}{owner_lbl}"
                )

                with st.expander(label):
                    detail_col, action_col = st.columns([3, 1])

                    with detail_col:
                        if row["is_assigned"]:
                            owner_name = profile_map.get(supabase_res_map[rid].get("user_id"), "Desconocido")
                            owner_prefix = f"👤 **Gestor:** {owner_name}  |  " if user_role_is_admin else ""
                            st.markdown(
                                f"{owner_prefix}💰 **Precio acordado privado:** ${row['Precio MXN']:,.0f} MXN  |  "
                                f"📅 **Duración:** {row['Días']} días"
                            )
                            if row["Notas"]:
                                st.caption(f"Notas de gestión: {row['Notas']}")
                        else:
                            st.warning("⚠️ Esta reserva no está asignada a tu gestión.")
                            st.markdown(f"📅 **Duración:** {row['Días']} días")
                            if user_role_is_admin and profiles:
                                with st.popover("Asignar a gestión (Admin)...", use_container_width=True):
                                    profile_options = {p["id"]: p.get("name", p["id"]) for p in profiles}
                                    selected_assign_user = st.selectbox(
                                        "Seleccionar gestor",
                                        options=list(profile_options.keys()),
                                        format_func=lambda x: profile_options[x],
                                        key=f"assign_list_select_{rid}"
                                    )
                                    assign_price = st.number_input("Precio Privado (MXN)", min_value=0, key=f"assign_list_price_{rid}")
                                    assign_notes = st.text_input("Notas", key=f"assign_list_notes_{rid}")
                                    if st.button("Confirmar Asignación", key=f"assign_list_confirm_{rid}", type="primary"):
                                        success = assign_reservation_to_user(selected_assign_user, token, rid, assign_price, assign_notes)
                                        if success:
                                            st.success("Reserva asignada correctamente.")
                                            refresh()
                                        else:
                                            st.error("Error al asignar.")
                            else:
                                if st.button("Asignar a mi gestión", key=f"assign_list_{rid}"):
                                    success = assign_reservation_to_user(user_id, token, rid, 0, "Asignado desde lista")
                                    if success:
                                        st.success("Reserva asignada correctamente.")
                                        refresh()
                                    else:
                                        st.error("Error al asignar.")

                    with action_col:
                        # Permitir editar/borrar si está asignada a alguien
                        if row["is_assigned"]:
                            if st.button("✏️ Editar", key=f"btn_edit_{rid}"):
                                st.session_state[f"editing_{rid}"] = True
                                st.session_state.pop(f"confirming_del_{rid}", None)
                            if st.button("🗑️ Desasignar / Cancelar", key=f"btn_del_{rid}"):
                                st.session_state[f"confirming_del_{rid}"] = True
                                st.session_state.pop(f"editing_{rid}", None)

                    # ── Edit form ─────────────────────────────────────────────────
                    if row["is_assigned"] and st.session_state.get(f"editing_{rid}", False):
                        rf = row["_raw"]["fields"]
                        st.markdown("---")
                        with st.form(f"form_edit_{rid}"):
                            ec1, ec2 = st.columns(2)
                            with ec1:
                                fi_val = date.fromisoformat(rf["Fecha_Inicio"]) if rf.get("Fecha_Inicio") else date.today()
                                edit_fi = st.date_input("Fecha inicio (Airtable)", value=fi_val, key=f"efi_{rid}")
                            with ec2:
                                ff_val = date.fromisoformat(rf["Fecha_Fin"]) if rf.get("Fecha_Fin") else date.today()
                                edit_ff = st.date_input("Fecha fin (Airtable)", value=ff_val, key=f"eff_{rid}")

                            ec3, ec4 = st.columns(2)
                            with ec3:
                                curr_idx = ESTADOS.index(rf.get("Estado", "Propuesta")) if rf.get("Estado") in ESTADOS else 0
                                edit_estado = st.selectbox("Estado (Airtable)", ESTADOS, index=curr_idx, key=f"eest_{rid}")
                            with ec4:
                                edit_precio = st.number_input(
                                    "Precio Privado (Supabase)",
                                    value=float(row["Precio MXN"]),
                                    step=1000.0,
                                    key=f"epr_{rid}",
                                )

                            if user_role_is_admin and profiles:
                                profile_options = {p["id"]: p.get("name", p["id"]) for p in profiles}
                                curr_gestor_id = supabase_res_map[rid]["user_id"]
                                if curr_gestor_id not in profile_options:
                                    profile_options[curr_gestor_id] = profile_map.get(curr_gestor_id, "Desconocido")
                                edit_gestor = st.selectbox(
                                    "Reasignar Gestor (Admin)",
                                    options=list(profile_options.keys()),
                                    format_func=lambda x: profile_options[x],
                                    index=list(profile_options.keys()).index(curr_gestor_id),
                                    key=f"eges_{rid}"
                                )
                            else:
                                edit_gestor = None

                            edit_notas = st.text_area("Notas gestión (Supabase)", value=row["Notas"], key=f"ent_{rid}")

                            sb1, sb2 = st.columns(2)
                            with sb1:
                                save_btn = st.form_submit_button("Guardar", icon=":material/save:", type="primary", use_container_width=True)
                            with sb2:
                                cancel_btn = st.form_submit_button("Cancelar", use_container_width=True)

                        if save_btn:
                            # 1. Patch en Airtable
                            patch = {
                                "Fecha_Inicio":          edit_fi.isoformat(),
                                "Fecha_Fin":             edit_ff.isoformat(),
                                "Estado":                edit_estado,
                            }
                            resp = airtable_patch(T_RESERVACIONES, rid, patch)
                            
                            # 2. Patch en Supabase
                            sp_res_id = supabase_res_map[rid]["id"]
                            success_sp = update_user_reservation(token, sp_res_id, edit_precio, edit_notas, user_id=edit_gestor)
                            
                            if resp.status_code == 200 and success_sp:
                                st.success("Cambios guardados correctamente.")
                                st.session_state.pop(f"editing_{rid}", None)
                                refresh()
                            else:
                                st.error(f"Error al guardar. Airtable: {resp.status_code}. Supabase: {success_sp}")

                        if cancel_btn:
                            st.session_state.pop(f"editing_{rid}", None)
                            st.rerun()

                    # ── Delete confirmation ───────────────────────────────────────
                    if row["is_assigned"] and st.session_state.get(f"confirming_del_{rid}", False):
                        st.warning(f"¿Qué deseas hacer con la reservación #{row['#']}? Puedes desasignarla (eliminar tu precio y notas privadas) o borrarla por completo.", icon=":material/warning:")
                        dc1, dc2, dc3 = st.columns(3)
                        with dc1:
                            if st.button("Desasignar de mi gestión", icon=":material/remove_circle:", key=f"yes_unassign_{rid}", type="primary", use_container_width=True):
                                sp_res_id = supabase_res_map[rid]["id"]
                                success = unassign_reservation_from_user(token, sp_res_id)
                                if success:
                                    st.session_state.pop(f"confirming_del_{rid}", None)
                                    refresh()
                                else:
                                    st.error("Error al desasignar.")
                        with dc2:
                            if st.button("Borrar por completo", icon=":material/delete_forever:", key=f"yes_del_{rid}", use_container_width=True):
                                # 1. Borrar de Airtable
                                resp = airtable_delete(T_RESERVACIONES, rid)
                                # 2. Borrar de Supabase
                                sp_res_id = supabase_res_map[rid]["id"]
                                success = unassign_reservation_from_user(token, sp_res_id)
                                
                                if resp.status_code == 200:
                                    st.session_state.pop(f"confirming_del_{rid}", None)
                                    refresh()
                                else:
                                    st.error(f"Error Airtable: {resp.text}")
                        with dc3:
                            if st.button("Cancelar", key=f"no_del_{rid}", use_container_width=True):
                                st.session_state.pop(f"confirming_del_{rid}", None)
                                st.rerun()
