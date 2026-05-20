import io
import os
import calendar
from datetime import date, datetime

import pandas as pd
import requests
import streamlit as st
from PIL import Image

st.set_page_config(
    page_title="Disponibilidades - Publimex",
    page_icon="📅",
    layout="wide",
    initial_sidebar_state="expanded",
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
    "Propuesta":  "🟡 Propuesta",
    "Pendiente":  "🟠 Pendiente",
    "Confirmada": "🔵 Confirmada",
    "Activa":     "🟢 Activa",
    "Finalizada": "⬜ Finalizada",
    "Cancelada":  "❌ Cancelada",
}

ZONAS       = ["Polanco", "Periférico Norte", "Del Valle"]
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


@st.cache_data(ttl=30, show_spinner=False)
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
    id_num = f.get("﻿ID", "")
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
    """Returns (badge_text, color_class) based on reservations in month."""
    if not res_mes:
        return "🟢 LIBRE", "libre"
    estados = [r["fields"].get("Estado", "") for r in res_mes]
    if any(e in ("Confirmada", "Activa") for e in estados):
        return "🔴 OCUPADO", "ocupado"
    return "🟡 PROPUESTA", "propuesta"

# ── Presentation / PDF helpers ───────────────────────────────────────────────

_CATS_ORDER = ["Muro", "Muro + Espectacular", "Pantalla Digital", "Valla"]

_CAT_TO_SECCION = {
    "Muro":               "Sección - Muros",
    "Muro + Espectacular":"Sección - Muros",
    "Valla":              "Sección - Vallas",
    "Pantalla Digital":   "Sección - Pantallas Digitales",
}


def build_presentation_slides(espacios_filtrados: list, materiales: list) -> list:
    """Returns ordered list of full-size image URLs: Portada → sections+spaces → Cierre."""
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


# ── Page ──────────────────────────────────────────────────────────────────────

st.title("📅 Gestión de Disponibilidades")

if not TOKEN:
    st.error("⚠️ Error de conexión con la base de datos. Contacta al administrador.")
    st.stop()

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
        if st.button("🔄 Actualizar", use_container_width=True):
            refresh()

# ── Load ──────────────────────────────────────────────────────────────────────

with st.spinner("Cargando datos de Airtable..."):
    try:
        espacios_raw, reservaciones_raw, clientes_raw, materiales_raw = load_data()
    except requests.HTTPError as e:
        st.error(f"Error al conectar con Airtable: {e}")
        st.stop()

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
m2.metric("🟢 Libres", libres)
m3.metric("🔴 Ocupados", ocupados)
m4.metric("🟡 Propuestas / Pendientes", propuestas)

st.divider()

# ── Presentation download ─────────────────────────────────────────────────────

pres_c1, pres_c2 = st.columns([1, 1])
with pres_c1:
    gen_pdf = st.button(
        "📊 Generar presentación PDF",
        use_container_width=True,
        disabled=not espacios_filtered,
    )
with pres_c2:
    if st.session_state.get("pres_pdf"):
        st.download_button(
            "⬇️ Descargar PDF",
            data=st.session_state["pres_pdf"],
            file_name=st.session_state.get("pres_name", "presentacion.pdf"),
            mime="application/pdf",
            use_container_width=True,
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
    f"📊 Disponibilidad — {MESES_ES[sel_month - 1]} {sel_year}",
    "📋 Reservaciones",
])

with tab_grid:
    if not espacios_filtered:
        st.info("Ningún espacio coincide con los filtros aplicados.")
    else:
        for esp in sorted(espacios_filtered, key=lambda e: e["fields"].get("﻿ID", 0)):
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
                    precio = f.get("Precio_MXN", 0)
                    st.markdown(f"**Precio base:** ${precio:,.0f} MXN / mes")
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
                            cli_ids = rf.get("Cliente", [])
                            cli_name = (
                                clientes_map[cli_ids[0]]["fields"].get("Empresa", "—")
                                if cli_ids and cli_ids[0] in clientes_map else "—"
                            )
                            estado_badge = ESTADO_BADGE.get(rf.get("Estado", ""), rf.get("Estado", ""))
                            st.markdown(
                                f"- **{cli_name}**  \n"
                                f"  {rf.get('Fecha_Inicio','?')} → {rf.get('Fecha_Fin','?')}  \n"
                                f"  {estado_badge}  ·  ${rf.get('Precio_Acordado_MXN',0):,.0f} MXN"
                            )
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
                        cli_ids = rf.get("Cliente", [])
                        cli_name = (
                            clientes_map[cli_ids[0]]["fields"].get("Empresa", "—")
                            if cli_ids and cli_ids[0] in clientes_map else "—"
                        )
                        rows.append({
                            "#": rf.get("ID_Reservacion", ""),
                            "Cliente": cli_name,
                            "Inicio": rf.get("Fecha_Inicio", ""),
                            "Fin": rf.get("Fecha_Fin", ""),
                            "Días": rf.get("Duración_Días", ""),
                            "Estado": rf.get("Estado", ""),
                            "Precio MXN": rf.get("Precio_Acordado_MXN", 0),
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
                new_precio = st.number_input("Precio acordado (MXN)", min_value=0, step=5000)

            new_notas = st.text_area("Notas", height=80)

            submitted = st.form_submit_button(
                "Crear reservación", type="primary", use_container_width=True
            )

        if submitted:
            if new_ff <= new_fi:
                st.error("La fecha fin debe ser posterior al inicio.")
            else:
                payload = {
                    "Espacio (Nuevo)": [sel_esp],
                    "Cliente":         [sel_cli],
                    "Fecha_Inicio":    new_fi.isoformat(),
                    "Fecha_Fin":       new_ff.isoformat(),
                    "Estado":          new_estado,
                    "Precio_Acordado_MXN": float(new_precio),
                    "Notas":           new_notas,
                }
                resp = airtable_post(T_RESERVACIONES, payload)
                if resp.status_code == 200:
                    st.success("✅ Reservación creada correctamente.")
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
            res_display.append({
                "_id":    r["id"],
                "_raw":   r,
                "#":      rf.get("ID_Reservacion", ""),
                "Espacio":  esp_name,
                "Cliente":  cli_name,
                "Inicio":   rf.get("Fecha_Inicio", ""),
                "Fin":      rf.get("Fecha_Fin", ""),
                "Días":     rf.get("Duración_Días", ""),
                "Estado":   estado,
                "Precio MXN": rf.get("Precio_Acordado_MXN", 0),
                "Notas":    rf.get("Notas", ""),
            })

        res_display.sort(key=lambda x: x["Inicio"] or "", reverse=True)
        st.markdown(f"**{len(res_display)} reservaciones**")

        if not res_display:
            st.info("No hay reservaciones que coincidan con los filtros.")

        for row in res_display:
            rid = row["_id"]
            estado_b = ESTADO_BADGE.get(row["Estado"], row["Estado"])
            label = (
                f"#{row['#']} · {row['Espacio']} · **{row['Cliente']}** · "
                f"{row['Inicio']} → {row['Fin']} · {estado_b}"
            )

            with st.expander(label):
                detail_col, action_col = st.columns([3, 1])

                with detail_col:
                    st.markdown(
                        f"**Precio:** ${row['Precio MXN']:,.0f} MXN  |  "
                        f"**Duración:** {row['Días']} días"
                    )
                    if row["Notas"]:
                        st.caption(f"Notas: {row['Notas']}")

                with action_col:
                    if st.button("✏️ Editar", key=f"btn_edit_{rid}"):
                        st.session_state[f"editing_{rid}"] = True
                        st.session_state.pop(f"confirming_del_{rid}", None)
                    if st.button("🗑️ Borrar", key=f"btn_del_{rid}"):
                        st.session_state[f"confirming_del_{rid}"] = True
                        st.session_state.pop(f"editing_{rid}", None)

                # ── Edit form ─────────────────────────────────────────────────
                if st.session_state.get(f"editing_{rid}", False):
                    rf = row["_raw"]["fields"]
                    st.markdown("---")
                    with st.form(f"form_edit_{rid}"):
                        ec1, ec2 = st.columns(2)
                        with ec1:
                            fi_val = date.fromisoformat(rf["Fecha_Inicio"]) if rf.get("Fecha_Inicio") else date.today()
                            edit_fi = st.date_input("Fecha inicio", value=fi_val, key=f"efi_{rid}")
                        with ec2:
                            ff_val = date.fromisoformat(rf["Fecha_Fin"]) if rf.get("Fecha_Fin") else date.today()
                            edit_ff = st.date_input("Fecha fin", value=ff_val, key=f"eff_{rid}")

                        ec3, ec4 = st.columns(2)
                        with ec3:
                            curr_idx = ESTADOS.index(rf.get("Estado", "Propuesta")) if rf.get("Estado") in ESTADOS else 0
                            edit_estado = st.selectbox("Estado", ESTADOS, index=curr_idx, key=f"eest_{rid}")
                        with ec4:
                            edit_precio = st.number_input(
                                "Precio MXN",
                                value=float(rf.get("Precio_Acordado_MXN", 0)),
                                step=1000.0,
                                key=f"epr_{rid}",
                            )

                        edit_notas = st.text_area("Notas", value=rf.get("Notas", ""), key=f"ent_{rid}")

                        sb1, sb2 = st.columns(2)
                        with sb1:
                            save_btn = st.form_submit_button("💾 Guardar", type="primary", use_container_width=True)
                        with sb2:
                            cancel_btn = st.form_submit_button("Cancelar", use_container_width=True)

                    if save_btn:
                        patch = {
                            "Fecha_Inicio":          edit_fi.isoformat(),
                            "Fecha_Fin":             edit_ff.isoformat(),
                            "Estado":                edit_estado,
                            "Precio_Acordado_MXN":   edit_precio,
                            "Notas":                 edit_notas,
                        }
                        resp = airtable_patch(T_RESERVACIONES, rid, patch)
                        if resp.status_code == 200:
                            st.success("Guardado.")
                            st.session_state.pop(f"editing_{rid}", None)
                            refresh()
                        else:
                            st.error(f"Error: {resp.text}")

                    if cancel_btn:
                        st.session_state.pop(f"editing_{rid}", None)
                        st.rerun()

                # ── Delete confirmation ───────────────────────────────────────
                if st.session_state.get(f"confirming_del_{rid}", False):
                    st.warning(f"¿Confirmar borrado de reservación #{row['#']}? Esta acción no se puede deshacer.")
                    dc1, dc2 = st.columns(2)
                    with dc1:
                        if st.button("Sí, borrar", key=f"yes_del_{rid}", type="primary"):
                            resp = airtable_delete(T_RESERVACIONES, rid)
                            if resp.status_code == 200:
                                st.session_state.pop(f"confirming_del_{rid}", None)
                                refresh()
                            else:
                                st.error(f"Error: {resp.text}")
                    with dc2:
                        if st.button("Cancelar", key=f"no_del_{rid}"):
                            st.session_state.pop(f"confirming_del_{rid}", None)
                            st.rerun()
