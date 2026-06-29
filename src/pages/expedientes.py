"""Procesos de Venta (Expedientes) — Fase 1 del PRD.

Cada expediente es el contenedor de una oportunidad y sirve sobre todo al
**seguimiento** y a la **descarga de información** del cliente:

- Solicitud  : info del cliente (agencia/marca, contactos, qué pide, ciudades,
               duración, fecha de inicio estimada, fase de negociación).
- Presupuesto: importe inicial del cliente + bitácora de avances + documentos de
               propuesta (lo que se envió para vender).
- Contratación: campañas cerradas (× meses), documentos de transacción,
               conciliación de precios, checklist fiscal y reserva efectiva.
- Producción / Cierre: repositorio de archivos (prueba de montaje).
"""

from datetime import date
import streamlit as st

from src.airtable_client import (
    ETAPAS, EXP_ESTADOS, DOC_TIPOS, DOC_DIRECCIONES, DOC_ESTADOS, TIPOS_POR_ETAPA,
    RESERVA_ESTADOS, FASES_SOLICITUD, ROLES_CONTACTO, TIPO_PRODUCTO, CIUDADES,
    CAMPANA_ESTADOS, FISCAL_DOCS, is_configured,
    list_expedientes, create_expediente, update_expediente, delete_expediente,
    list_documentos, create_documento, delete_documento,
    list_clientes, list_espacios, cliente_label, espacio_label,
    create_reservacion, refresh_data,
    list_contactos, create_contacto, delete_contacto,
    list_avances, create_avance, delete_avance,
    list_campanas, create_campana, update_campana, delete_campana, list_documentos_campana,
)
from src.supabase_client import is_admin, get_all_profiles
from src.theme import page_header

# ── Colores de chips ─────────────────────────────────────────────────────────────
ESTADO_COLORS = {
    "Abierto":  ("#DBEAFE", "#1e40af"),
    "Ganado":   ("#DCFCE7", "#166534"),
    "Perdido":  ("#FEE2E2", "#991b1b"),
    "En pausa": ("#FEF9C3", "#854d0e"),
}
FASE_COLORS = {
    "Negociación":       ("#FEF9C3", "#854d0e"),
    "Inicio":            ("#DBEAFE", "#1e40af"),
    "En Pausa":          ("#EEEDEA", "#6B6B6B"),
    "Propuesta Enviada": ("#E7F4EC", "#1B7A3D"),
}
ROL_COLORS = {
    "Contacto directo": ("#E7EEF7", "#1F4E79"),
    "Director / Jefe":  ("#FDECEC", "#A50000"),
    "Operativo":        ("#EEEDEA", "#6B6B6B"),
}
CAMP_COLORS = {
    "Activa":    ("#DBEAFE", "#1e40af"),
    "Cerrada":   ("#E7F4EC", "#1B7A3D"),
    "Cancelada": ("#FEE2E2", "#991b1b"),
}


def _chip(text, bg="#FDECEC", fg="#A50000"):
    return (f'<span style="background:{bg}; color:{fg}; padding:2px 9px; '
            f'border-radius:0; font-size:0.72rem; font-weight:600; '
            f'white-space:nowrap; display:inline-block; margin:2px 4px 2px 0;">{text}</span>')


def _refresh():
    refresh_data()
    st.rerun()


def _render_stepper(current_etapa: str):
    cur = ETAPAS.index(current_etapa) if current_etapa in ETAPAS else 0
    cells = []
    for i, et in enumerate(ETAPAS):
        done, active = i < cur, i == cur
        if active:
            c_bg, c_fg, l_color, l_w = "#E60000", "#fff", "#111111", "700"
        elif done:
            c_bg, c_fg, l_color, l_w = "#F8B4B4", "#7f1d1d", "#555555", "600"
        else:
            c_bg, c_fg, l_color, l_w = "#e2e8f0", "#94a3b8", "#94a3b8", "500"
        check = "✓" if done else str(i + 1)
        if i > 0:
            line = "#F8B4B4" if i <= cur else "#e2e8f0"
            cells.append(f'<div style="flex:1; height:3px; background:{line}; margin-top:18px;"></div>')
        cells.append(
            f'<div style="display:flex; flex-direction:column; align-items:center; min-width:84px;">'
            f'<div style="width:36px; height:36px; border-radius:50%; background:{c_bg}; color:{c_fg}; '
            f'display:flex; align-items:center; justify-content:center; font-weight:700; font-size:0.95rem;">{check}</div>'
            f'<div style="margin-top:6px; font-size:0.78rem; color:{l_color}; font-weight:{l_w}; text-align:center;">{et}</div>'
            f'</div>'
        )
    st.markdown(
        f'<div style="display:flex; align-items:flex-start; justify-content:space-between; margin:6px 0 10px 0;">{"".join(cells)}</div>',
        unsafe_allow_html=True,
    )

# ── Repositorio de documentos por etapa ──────────────────────────────────────────

def _file_icon():
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="#E60000" '
            'stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="width:18px;height:18px;">'
            '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><path d="M14 2v6h6"/></svg>')


def _file_card(d):
    df = d["fields"]
    meta = f'{df.get("Direccion","—")} · {df.get("Estado","—")}'
    if df.get("Mes"):
        meta = f'{df["Mes"]} · ' + meta
    if df.get("Fecha"):
        meta += f' · {df["Fecha"]}'
    with st.container(border=True):
        st.markdown(
            f'<div style="display:flex; align-items:center; gap:8px; margin-bottom:6px;">{_file_icon()}'
            f'{_chip(df.get("Tipo", "Documento"))}</div>'
            f'<div style="font-weight:600; color:#1A1A1A; line-height:1.3;">{df.get("Nombre", "(sin nombre)")}</div>'
            f'<div style="font-size:0.78rem; color:#6B6B6B; margin-top:3px;">{meta}</div>',
            unsafe_allow_html=True,
        )
        if df.get("Notas"):
            st.caption(df["Notas"])
        bc1, bc2 = st.columns([3, 1])
        with bc1:
            if df.get("Enlace_URL"):
                st.link_button("Abrir", df["Enlace_URL"], icon=":material/open_in_new:", use_container_width=True)
            else:
                st.caption("Sin enlace")
        with bc2:
            with st.popover("", icon=":material/delete:"):
                st.write("¿Borrar este documento?")
                if st.button("Sí, borrar", key=f"del_doc_{d['id']}", type="primary"):
                    if delete_documento(d["id"]):
                        _refresh()
                    else:
                        st.error("No se pudo borrar.")


def _doc_quick_form(exp_id, etapa, user_id):
    suggested = TIPOS_POR_ETAPA.get(etapa, DOC_TIPOS)
    default_tipo = suggested[0] if suggested else DOC_TIPOS[0]
    st.markdown("**Subir documento**")
    st.caption("Rápido: tipo, nombre y enlace. El resto se rellena por defecto.")
    with st.form(f"quick_doc_{etapa}", clear_on_submit=True):
        st.file_uploader("Archivo", disabled=True, key=f"qup_{etapa}",
                         help="Próximamente: subida directa al Google Drive de la empresa.")
        tipo = st.selectbox("Tipo", DOC_TIPOS, index=DOC_TIPOS.index(default_tipo), key=f"qtipo_{etapa}")
        nombre = st.text_input("Nombre / descripción *", key=f"qnom_{etapa}")
        desc = st.text_input("Descripción (opcional)", key=f"qdesc_{etapa}",
                             placeholder="Ej. Propuesta enviada con base en un presupuesto de 1 millón")
        enlace = st.text_input("Enlace (Drive / URL)", key=f"qenl_{etapa}", placeholder="https://drive.google.com/...")
        ok = st.form_submit_button("Guardar", type="primary", use_container_width=True)
    if ok:
        if not nombre:
            st.error("Indica al menos un nombre.")
        else:
            fields = {
                "Nombre": nombre, "Expediente": [exp_id], "Etapa": etapa, "Tipo": tipo,
                "Direccion": "Recibido", "Estado": "Recibido", "Vendedor_ID": user_id,
                "Fecha": date.today().isoformat(),
            }
            if enlace:
                fields["Enlace_URL"] = enlace
            if desc:
                fields["Notas"] = desc
            if create_documento(fields):
                st.success("Documento guardado.")
                _refresh()
            else:
                st.error("Error al guardar el documento.")


def _doc_detailed_form(exp_id, etapa, user_id):
    suggested = TIPOS_POR_ETAPA.get(etapa, DOC_TIPOS)
    default_tipo = suggested[0] if suggested else DOC_TIPOS[0]
    st.markdown("**Registrar documento**")
    st.caption("Detallado: tipo, dirección, estado, fecha, enlace y descripción.")
    with st.form(f"full_doc_{etapa}", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            tipo = st.selectbox("Tipo *", DOC_TIPOS, index=DOC_TIPOS.index(default_tipo), key=f"ftipo_{etapa}")
            direccion = st.selectbox("Dirección *", DOC_DIRECCIONES, key=f"fdir_{etapa}")
        with c2:
            estado = st.selectbox("Estado", DOC_ESTADOS, key=f"fest_{etapa}")
            fecha = st.date_input("Fecha", value=date.today(), key=f"ffec_{etapa}")
        nombre = st.text_input("Nombre / descripción *", key=f"fnom_{etapa}")
        enlace = st.text_input("Enlace (Drive / URL)", key=f"fenl_{etapa}", placeholder="https://drive.google.com/...")
        notas = st.text_area("Descripción / notas", key=f"fnotas_{etapa}", height=70)
        ok = st.form_submit_button("Registrar", type="primary", use_container_width=True)
    if ok:
        if not nombre:
            st.error("El nombre/descripción es obligatorio.")
        else:
            fields = {
                "Nombre": nombre, "Expediente": [exp_id], "Etapa": etapa, "Tipo": tipo,
                "Direccion": direccion, "Estado": estado, "Vendedor_ID": user_id,
            }
            if fecha:
                fields["Fecha"] = fecha.isoformat()
            if enlace:
                fields["Enlace_URL"] = enlace
            if notas:
                fields["Notas"] = notas
            if create_documento(fields):
                st.success("Documento registrado.")
                _refresh()
            else:
                st.error("Error al registrar el documento en Airtable.")


def _render_stage_docs(exp_id, etapa, docs, user_id, intro=None):
    if intro:
        st.caption(intro)
    enviados = sum(1 for d in docs if d["fields"].get("Direccion") == "Enviado")
    recibidos = sum(1 for d in docs if d["fields"].get("Direccion") == "Recibido")
    st.markdown(
        '<div style="display:flex; gap:6px; align-items:center; flex-wrap:wrap; margin:6px 0 12px;">'
        + _chip(f"{len(docs)} documentos", "#F1F0EC", "#5A5A5A")
        + _chip(f"Enviados {enviados}", "#E7EEF7", "#1F4E79")
        + _chip(f"Recibidos {recibidos}", "#E7F4EC", "#1B7A3D")
        + '</div>',
        unsafe_allow_html=True,
    )
    cta1, cta2, _sp = st.columns([1, 1, 2])
    with cta1:
        with st.popover("Subir documento", icon=":material/upload_file:", use_container_width=True):
            _doc_quick_form(exp_id, etapa, user_id)
    with cta2:
        with st.popover("Registrar documento", icon=":material/note_add:", use_container_width=True):
            _doc_detailed_form(exp_id, etapa, user_id)
    st.write("")
    if not docs:
        st.markdown(
            "<div style='border:1px dashed #E6E4DF; padding:24px; text-align:center; color:#6B6B6B; "
            "font-size:0.9rem;'>Aún no hay archivos en esta etapa. Súbelos como prueba visible del proceso.</div>",
            unsafe_allow_html=True,
        )
        return
    docs_sorted = sorted(docs, key=lambda x: x["fields"].get("Fecha", ""), reverse=True)
    cols = st.columns(3)
    for i, d in enumerate(docs_sorted):
        with cols[i % 3]:
            _file_card(d)

# ══════════════════════════════════════════════════════════════════════════════════
# MÓDULO 1 — SOLICITUD
# ══════════════════════════════════════════════════════════════════════════════════

def _exp_form_fields(f=None):
    """Widgets compartidos por los diálogos de alta/edición. Devuelve un dict de valores."""
    f = f or {}
    nombre = st.text_input("Nombre del proceso *", value=f.get("Nombre", ""),
                           placeholder="Ej. Coca-Cola Verano 2026")
    c1, c2 = st.columns(2)
    with c1:
        agencia = st.text_input("Agencia / Medio", value=f.get("Agencia", ""), placeholder="Ej. GroupM")
    with c2:
        marca = st.text_input("Marca", value=f.get("Marca", ""), placeholder="Ej. Paramount")
    tipo = st.multiselect("¿Qué te están pidiendo? (tipo de producto)", TIPO_PRODUCTO,
                          default=[t for t in f.get("Tipo_Producto", []) if t in TIPO_PRODUCTO])
    ciudades = st.multiselect("Plaza / ciudades de interés", CIUDADES,
                              default=[c for c in f.get("Ciudades", []) if c in CIUDADES])
    c3, c4 = st.columns(2)
    with c3:
        duracion = st.text_input("Periodo de interés / duración", value=f.get("Duracion", ""),
                                 placeholder="Ej. 1 mes, 1 año")
    with c4:
        fi = st.date_input("Fecha de inicio estimada",
                           value=date.fromisoformat(f["Fecha_Inicio_Estimada"]) if f.get("Fecha_Inicio_Estimada") else None)
    fase = st.selectbox("Fase de negociación", FASES_SOLICITUD,
                        index=FASES_SOLICITUD.index(f.get("Fase_Solicitud")) if f.get("Fase_Solicitud") in FASES_SOLICITUD else 0)
    notas = st.text_area("Comentarios", value=f.get("Notas", ""),
                         placeholder="Notas rápidas del estatus...")
    return {
        "Nombre": nombre, "Agencia": agencia, "Marca": marca, "Tipo_Producto": tipo,
        "Ciudades": ciudades, "Duracion": duracion,
        "Fecha_Inicio_Estimada": fi.isoformat() if fi else "",
        "Fase_Solicitud": fase, "Notas": notas,
    }


@st.dialog("Nuevo expediente")
def _new_expediente_dialog(user_id, user_name, admin, profiles):
    vals = _exp_form_fields()
    if admin and profiles:
        prof_opts = {p["id"]: p.get("name", p["id"]) for p in profiles}
        if user_id not in prof_opts:
            prof_opts[user_id] = user_name
        vendedor_id = st.selectbox("Vendedor asignado", options=list(prof_opts.keys()),
                                   format_func=lambda k: prof_opts[k],
                                   index=list(prof_opts.keys()).index(user_id))
        vendedor_nombre = prof_opts[vendedor_id]
    else:
        vendedor_id, vendedor_nombre = user_id, user_name
    if st.button("Crear expediente", type="primary", use_container_width=True):
        if not vals["Nombre"]:
            st.error("El nombre del proceso es obligatorio.")
        else:
            fields = {k: v for k, v in vals.items() if v}
            fields.update({"Etapa": "Solicitud", "Estado": "Abierto",
                           "Vendedor_ID": vendedor_id, "Vendedor_Nombre": vendedor_nombre})
            rec = create_expediente(fields)
            if rec:
                refresh_data()
                st.session_state["exp_selected"] = rec["id"]
                st.rerun()
            else:
                st.error("Error al crear el expediente en Airtable.")


@st.dialog("Editar datos del proceso")
def _edit_expediente_dialog(exp):
    vals = _exp_form_fields(exp["fields"])
    c1, c2 = st.columns(2)
    with c1:
        etapa = st.selectbox("Etapa (pipeline)", ETAPAS,
                             index=ETAPAS.index(exp["fields"].get("Etapa", "Solicitud")) if exp["fields"].get("Etapa") in ETAPAS else 0)
    with c2:
        estado = st.selectbox("Estado", EXP_ESTADOS,
                              index=EXP_ESTADOS.index(exp["fields"].get("Estado", "Abierto")) if exp["fields"].get("Estado") in EXP_ESTADOS else 0)
    if st.button("Guardar cambios", type="primary", use_container_width=True):
        if not vals["Nombre"]:
            st.error("El nombre es obligatorio.")
        else:
            fields = dict(vals)
            fields.update({"Etapa": etapa, "Estado": estado})
            if update_expediente(exp["id"], fields):
                _refresh()
            else:
                st.error("Error al guardar en Airtable.")


@st.dialog("Añadir contacto")
def _new_contacto_dialog(exp_id, user_id):
    nombre = st.text_input("Nombre *")
    c1, c2 = st.columns(2)
    with c1:
        telefono = st.text_input("Teléfono")
    with c2:
        correo = st.text_input("Correo")
    c3, c4 = st.columns(2)
    with c3:
        puesto = st.text_input("Puesto")
    with c4:
        rol = st.selectbox("Rol", ROLES_CONTACTO)
    if st.button("Añadir contacto", type="primary", use_container_width=True):
        if not nombre:
            st.error("El nombre es obligatorio.")
        else:
            fields = {"Nombre": nombre, "Expediente": [exp_id], "Rol": rol, "Vendedor_ID": user_id}
            if telefono:
                fields["Telefono"] = telefono
            if correo:
                fields["Correo"] = correo
            if puesto:
                fields["Puesto"] = puesto
            if create_contacto(fields):
                _refresh()
            else:
                st.error("Error al guardar el contacto.")


def _render_contactos(exp_id, user_id):
    contactos = list_contactos(exp_id)
    head1, head2 = st.columns([2, 1])
    with head1:
        st.markdown("#### Contactos")
    with head2:
        if st.button("Añadir contacto", icon=":material/person_add:", use_container_width=True, key="add_contacto"):
            _new_contacto_dialog(exp_id, user_id)
    if not contactos:
        st.caption("Sin contactos registrados. Añade con quién se está tratando.")
        return
    cols = st.columns(2)
    for i, c in enumerate(contactos):
        cf = c["fields"]
        rbg, rfg = ROL_COLORS.get(cf.get("Rol", ""), ("#EEEDEA", "#6B6B6B"))
        with cols[i % 2]:
            with st.container(border=True):
                st.markdown(
                    f'<div style="display:flex; justify-content:space-between; align-items:center;">'
                    f'<span style="font-weight:600;">{cf.get("Nombre","—")}</span>'
                    f'{_chip(cf.get("Rol","—"), rbg, rfg)}</div>'
                    + (f'<div style="font-size:0.8rem; color:#6B6B6B;">{cf["Puesto"]}</div>' if cf.get("Puesto") else "")
                    + (f'<div style="font-size:0.82rem; margin-top:3px;">📞 {cf["Telefono"]}</div>' if cf.get("Telefono") else "")
                    + (f'<div style="font-size:0.82rem;">✉️ {cf["Correo"]}</div>' if cf.get("Correo") else ""),
                    unsafe_allow_html=True,
                )
                with st.popover("", icon=":material/delete:"):
                    st.write("¿Borrar contacto?")
                    if st.button("Sí, borrar", key=f"delc_{c['id']}", type="primary"):
                        if delete_contacto(c["id"]):
                            _refresh()
                        else:
                            st.error("No se pudo borrar.")


def _render_solicitud(exp, docs, user_id, admin, clientes_map):
    exp_id = exp["id"]
    f = exp["fields"]

    agencia = f.get("Agencia") or "<span class='pm-muted'>—</span>"
    marca = f.get("Marca") or "<span class='pm-muted'>—</span>"
    tipos = "".join(_chip(t) for t in f.get("Tipo_Producto", [])) or "<span class='pm-muted'>—</span>"
    ciudades = "".join(_chip(c, "#E7EEF7", "#1F4E79") for c in f.get("Ciudades", [])) or "<span class='pm-muted'>—</span>"
    duracion = f.get("Duracion") or "<span class='pm-muted'>—</span>"
    fi = f.get("Fecha_Inicio_Estimada") or "<span class='pm-muted'>Sin fecha</span>"
    fase = f.get("Fase_Solicitud", "Negociación")
    fbg, ffg = FASE_COLORS.get(fase, ("#EEEDEA", "#6B6B6B"))
    notas = f.get("Notas") or "<span class='pm-muted'>Sin comentarios</span>"

    with st.container(border=True):
        st.markdown(
            '<div class="pm-kv">'
            f'<div><div class="lbl">Agencia / Medio</div><div class="val">{agencia}</div></div>'
            f'<div><div class="lbl">Marca</div><div class="val">{marca}</div></div>'
            f'<div class="full"><div class="lbl">¿Qué pide?</div><div class="val">{tipos}</div></div>'
            f'<div class="full"><div class="lbl">Ciudades de interés</div><div class="val">{ciudades}</div></div>'
            f'<div><div class="lbl">Duración</div><div class="val">{duracion}</div></div>'
            f'<div><div class="lbl">Inicio estimado</div><div class="val">{fi}</div></div>'
            f'<div><div class="lbl">Fase de negociación</div><div class="val">{_chip(fase, fbg, ffg)}</div></div>'
            + (f'<div><div class="lbl">Vendedor</div><div class="val">{f.get("Vendedor_Nombre","—")}</div></div>' if admin else '')
            + f'<div class="full"><div class="lbl">Comentarios</div><div class="val">{notas}</div></div>'
            '</div>',
            unsafe_allow_html=True,
        )
        st.write("")
        b1, b2, _sp = st.columns([1, 1, 2])
        with b1:
            if st.button("Editar datos", icon=":material/edit:", type="primary", use_container_width=True, key="edit_exp_btn"):
                _edit_expediente_dialog(exp)
        with b2:
            with st.popover("Eliminar", icon=":material/delete:", use_container_width=True):
                st.write("Esto elimina el expediente (no borra reservas/documentos en sus tablas).")
                if st.button("Sí, borrar expediente", type="primary", key="del_exp_confirm"):
                    if delete_expediente(exp_id):
                        st.session_state.pop("exp_selected", None)
                        _refresh()
                    else:
                        st.error("No se pudo borrar.")

    st.divider()
    _render_contactos(exp_id, user_id)
    st.divider()
    _render_stage_docs(exp_id, "Solicitud", docs, user_id,
                       intro="Presentaciones de disponibilidades y material inicial de la oportunidad.")

# ══════════════════════════════════════════════════════════════════════════════════
# MÓDULO 2 — PRESUPUESTO (seguimiento)
# ══════════════════════════════════════════════════════════════════════════════════

@st.dialog("Añadir avance")
def _new_avance_dialog(exp_id, user_id):
    fecha = st.date_input("Fecha del contacto", value=date.today())
    resumen = st.text_area("Resumen de la interacción *",
                           placeholder="Ej. Seguimiento; el cliente comenta que el presupuesto no le alcanza y pide ajuste.")
    if st.button("Guardar avance", type="primary", use_container_width=True):
        if not resumen:
            st.error("Escribe el resumen.")
        else:
            fields = {"Resumen": resumen, "Expediente": [exp_id], "Vendedor_ID": user_id,
                      "Fecha": fecha.isoformat() if fecha else date.today().isoformat()}
            if create_avance(fields):
                _refresh()
            else:
                st.error("Error al guardar el avance.")


@st.dialog("Presupuesto inicial del cliente")
def _edit_importe_dialog(exp):
    val = int(exp["fields"].get("Valor_Estimado_MXN", 0) or 0)
    nuevo = st.number_input("Importe con el que arranca el cliente (MXN)", min_value=0, step=10000, value=val,
                            help="Solo señalización del presupuesto inicial. El detalle real se captura en Contratación.")
    if st.button("Guardar", type="primary", use_container_width=True):
        if update_expediente(exp["id"], {"Valor_Estimado_MXN": nuevo}):
            _refresh()
        else:
            st.error("No se pudo guardar.")


def _render_presupuesto(exp, docs, user_id):
    exp_id = exp["id"]
    val = exp["fields"].get("Valor_Estimado_MXN", 0) or 0

    # Importe inicial
    with st.container(border=True):
        ci1, ci2 = st.columns([3, 1])
        with ci1:
            st.markdown(
                '<div class="lbl" style="font-size:0.7rem; text-transform:uppercase; letter-spacing:0.06em; color:#6B6B6B;">Presupuesto inicial del cliente</div>'
                + (f'<div style="font-size:1.6rem; font-weight:700;">${val:,.0f} MXN</div>' if val
                   else '<div style="font-size:1.1rem; color:#6B6B6B;">Sin definir</div>'),
                unsafe_allow_html=True,
            )
        with ci2:
            st.write("")
            if st.button("Editar", icon=":material/edit:", use_container_width=True, key="edit_importe"):
                _edit_importe_dialog(exp)

    st.divider()

    # Bitácora de avances (seguimiento)
    avances = list_avances(exp_id)
    h1, h2 = st.columns([2, 1])
    with h1:
        st.markdown("#### Seguimiento (bitácora)")
    with h2:
        if st.button("Añadir avance", icon=":material/add_comment:", type="primary", use_container_width=True, key="add_avance"):
            _new_avance_dialog(exp_id, user_id)
    if not avances:
        st.caption("Registra cada contacto con el cliente para ver la evolución de la negociación.")
    else:
        for a in sorted(avances, key=lambda x: x["fields"].get("Fecha", ""), reverse=True):
            af = a["fields"]
            ac1, ac2 = st.columns([10, 1])
            with ac1:
                st.markdown(
                    f'<div style="border-left:2px solid #E60000; padding:2px 0 8px 12px; margin-bottom:6px;">'
                    f'<div style="font-size:0.78rem; color:#6B6B6B; font-weight:600;">{af.get("Fecha","—")}</div>'
                    f'<div style="font-size:0.92rem; color:#1A1A1A;">{af.get("Resumen","")}</div></div>',
                    unsafe_allow_html=True,
                )
            with ac2:
                with st.popover("", icon=":material/delete:"):
                    if st.button("Borrar", key=f"dela_{a['id']}", type="primary"):
                        if delete_avance(a["id"]):
                            _refresh()
                        else:
                            st.error("No se pudo borrar.")

    st.divider()
    _render_stage_docs(exp_id, "Presupuesto", docs, user_id,
                       intro="Sube lo que enviaste para vender (disponibilidad, cotización en Excel, PowerPoint). "
                             "Añade una breve descripción de qué se mandó.")

# ══════════════════════════════════════════════════════════════════════════════════
# MÓDULO 3 — CONTRATACIÓN (cierre, campañas, fiscal)
# ══════════════════════════════════════════════════════════════════════════════════

@st.dialog("Añadir campaña")
def _new_campana_dialog(exp_id, user_id, marca_default=""):
    nombre = st.text_input("Nombre de la campaña *", placeholder="Ej. Paramount Enero 2026")
    marca = st.text_input("Marca", value=marca_default)
    c1, c2, c3 = st.columns(3)
    with c1:
        fi = st.date_input("Inicio", value=None)
    with c2:
        ff = st.date_input("Fin", value=None)
    with c3:
        meses = st.number_input("Meses", min_value=0, step=1)
    c4, c5 = st.columns(2)
    with c4:
        monto = st.number_input("Monto cerrado (MXN)", min_value=0, step=10000)
    with c5:
        estado = st.selectbox("Estado", CAMPANA_ESTADOS)
    notas = st.text_area("Notas", height=70)
    if st.button("Crear campaña", type="primary", use_container_width=True):
        if not nombre:
            st.error("El nombre de la campaña es obligatorio.")
        else:
            fields = {"Nombre": nombre, "Expediente": [exp_id], "Estado": estado, "Vendedor_ID": user_id}
            if marca:
                fields["Marca"] = marca
            if fi:
                fields["Fecha_Inicio"] = fi.isoformat()
            if ff:
                fields["Fecha_Fin"] = ff.isoformat()
            if meses:
                fields["Meses"] = int(meses)
            if monto:
                fields["Monto_Cerrado_MXN"] = monto
            if notas:
                fields["Notas"] = notas
            if create_campana(fields):
                _refresh()
            else:
                st.error("Error al crear la campaña.")


def _campana_doc_form(exp_id, campana_id):
    tipos = TIPOS_POR_ETAPA["Contratación"]
    with st.form(f"campdoc_{campana_id}", clear_on_submit=True):
        tipo = st.selectbox("Tipo", tipos, key=f"cdtipo_{campana_id}")
        c1, c2 = st.columns(2)
        with c1:
            nombre = st.text_input("Nombre *", key=f"cdnom_{campana_id}")
        with c2:
            mes = st.text_input("Mes (para facturas)", key=f"cdmes_{campana_id}", placeholder="Ej. Enero 2026")
        enlace = st.text_input("Enlace (Drive / URL)", key=f"cdenl_{campana_id}")
        ok = st.form_submit_button("Guardar documento", type="primary", use_container_width=True)
    if ok:
        if not nombre:
            st.error("Indica un nombre.")
        else:
            uid = st.session_state.get("user_id")
            fields = {"Nombre": nombre, "Expediente": [exp_id], "Campana": [campana_id],
                      "Etapa": "Contratación", "Tipo": tipo, "Direccion": "Recibido",
                      "Estado": "Recibido", "Vendedor_ID": uid, "Fecha": date.today().isoformat()}
            if mes:
                fields["Mes"] = mes
            if enlace:
                fields["Enlace_URL"] = enlace
            if create_documento(fields):
                st.success("Documento guardado.")
                _refresh()
            else:
                st.error("Error al guardar el documento.")


def _campana_card(c, user_id):
    cf = c["fields"]
    estado = cf.get("Estado", "Activa")
    bg, fg = CAMP_COLORS.get(estado, ("#EEEDEA", "#6B6B6B"))
    monto = cf.get("Monto_Cerrado_MXN", 0) or 0
    meta_bits = []
    if cf.get("Marca"):
        meta_bits.append(cf["Marca"])
    if cf.get("Meses"):
        meta_bits.append(f'{cf["Meses"]} meses')
    if cf.get("Fecha_Inicio") or cf.get("Fecha_Fin"):
        meta_bits.append(f'{cf.get("Fecha_Inicio","?")} → {cf.get("Fecha_Fin","?")}')
    docs_c = list_documentos_campana(c["id"])
    exp_id = (cf.get("Expediente") or [None])[0]
    with st.container(border=True):
        st.markdown(
            f'<div style="display:flex; justify-content:space-between; align-items:center;">'
            f'<div style="font-weight:600;">{cf.get("Nombre","(sin nombre)")}</div>{_chip(estado, bg, fg)}</div>'
            + (f'<div style="font-size:1.3rem; font-weight:700; margin-top:4px;">${monto:,.0f} MXN</div>' if monto else '')
            + (f'<div style="font-size:0.8rem; color:#6B6B6B;">{" · ".join(meta_bits)}</div>' if meta_bits else ''),
            unsafe_allow_html=True,
        )
        with st.expander(f"Documentos de la campaña ({len(docs_c)})"):
            with st.popover("Subir documento", icon=":material/upload_file:", use_container_width=True):
                _campana_doc_form(exp_id, c["id"])
            if docs_c:
                dcols = st.columns(2)
                for i, d in enumerate(docs_c):
                    with dcols[i % 2]:
                        _file_card(d)
            else:
                st.caption("Sin documentos. Sube orden de compra, factura mensual, conciliación…")
        with st.popover("Borrar campaña", icon=":material/delete:"):
            st.write("¿Borrar esta campaña? (no borra sus documentos)")
            if st.button("Sí, borrar", key=f"delcamp_{c['id']}", type="primary"):
                if delete_campana(c["id"]):
                    _refresh()
                else:
                    st.error("No se pudo borrar.")


def _render_fiscal_checklist(exp_id, docs, user_id):
    st.markdown("#### Expediente fiscal del cliente")
    st.caption("Documentos para dar de alta al cliente y poder facturar.")
    by_tipo = {}
    for d in docs:
        t = d["fields"].get("Tipo")
        if t in FISCAL_DOCS:
            by_tipo.setdefault(t, []).append(d)
    completos = sum(1 for t in FISCAL_DOCS if by_tipo.get(t))
    st.markdown(_chip(f"{completos} / {len(FISCAL_DOCS)} completos",
                      "#E7F4EC" if completos == len(FISCAL_DOCS) else "#FBF0D9",
                      "#1B7A3D" if completos == len(FISCAL_DOCS) else "#8A5A00"),
                unsafe_allow_html=True)
    st.write("")
    for tipo in FISCAL_DOCS:
        existing = by_tipo.get(tipo, [])
        col_a, col_b = st.columns([3, 1])
        with col_a:
            mark = "✅" if existing else "⬜"
            st.markdown(f"{mark} **{tipo}**")
            if existing and existing[0]["fields"].get("Enlace_URL"):
                st.markdown(f'<a href="{existing[0]["fields"]["Enlace_URL"]}" target="_blank" style="font-size:0.8rem;">Abrir documento</a>', unsafe_allow_html=True)
        with col_b:
            if existing:
                with st.popover("", icon=":material/delete:"):
                    if st.button("Borrar", key=f"delfis_{existing[0]['id']}", type="primary"):
                        if delete_documento(existing[0]["id"]):
                            _refresh()
                        else:
                            st.error("No se pudo borrar.")
            else:
                with st.popover("Subir", icon=":material/upload_file:"):
                    with st.form(f"fis_{tipo}", clear_on_submit=True):
                        enlace = st.text_input("Enlace (Drive / URL)", key=f"fisenl_{tipo}")
                        nota = st.text_input("Nota (opcional)", key=f"fisnota_{tipo}")
                        ok = st.form_submit_button("Guardar", type="primary", use_container_width=True)
                    if ok:
                        fields = {"Nombre": tipo, "Expediente": [exp_id], "Etapa": "Contratación",
                                  "Tipo": tipo, "Direccion": "Recibido", "Estado": "Validado",
                                  "Vendedor_ID": user_id, "Fecha": date.today().isoformat()}
                        if enlace:
                            fields["Enlace_URL"] = enlace
                        if nota:
                            fields["Notas"] = nota
                        if create_documento(fields):
                            _refresh()
                        else:
                            st.error("Error al guardar.")
        st.divider()


def _render_reserva_efectiva(exp, clientes_map, user_id):
    exp_id = exp["id"]
    f = exp["fields"]
    reservas_vinc = f.get("Reservas_Vinculadas", [])
    with st.expander("Generar reserva efectiva" + (f" · {len(reservas_vinc)} vinculada(s)" if reservas_vinc else ""),
                     expanded=False):
        st.caption("Crea la reserva en el calendario maestro (Disponibilidades) y la vincula a este expediente. "
                   "Puedes repetir la acción para varios espacios.")
        espacios = list_espacios()
        clientes = list_clientes()
        with st.form("form_reserva_efectiva", clear_on_submit=True):
            esp_opts = {e["id"]: espacio_label(e) for e in espacios}
            sel_esp = st.selectbox("Espacio / soporte *", options=list(esp_opts.keys()),
                                   format_func=lambda x: esp_opts.get(x, x))
            cli_opts = {c["id"]: cliente_label(c) for c in clientes}
            cli_keys = list(cli_opts.keys())
            sel_cli = st.selectbox("Cliente *", options=cli_keys, format_func=lambda x: cli_opts.get(x, x))
            rc1, rc2 = st.columns(2)
            with rc1:
                fi = st.date_input("Fecha inicio *",
                                   value=date.fromisoformat(f["Fecha_Inicio_Estimada"]) if f.get("Fecha_Inicio_Estimada") else date.today())
            with rc2:
                ff = st.date_input("Fecha fin *", value=date.today())
            estado_res = st.selectbox("Estado de la reserva", RESERVA_ESTADOS, index=RESERVA_ESTADOS.index("Confirmada"))
            ok = st.form_submit_button("Generar reserva efectiva", type="primary", use_container_width=True)
        if ok:
            if not sel_esp or not sel_cli:
                st.error("Espacio y cliente son obligatorios.")
            elif ff <= fi:
                st.error("La fecha fin debe ser posterior al inicio.")
            else:
                rec = create_reservacion(sel_esp, sel_cli, fi.isoformat(), ff.isoformat(),
                                         estado=estado_res, notas=f"Generada desde expediente: {f.get('Nombre','')}")
                if rec:
                    update_expediente(exp_id, {"Reservas_Vinculadas": reservas_vinc + [rec["id"]]})
                    st.success("Reserva efectiva creada y vinculada.")
                    _refresh()
                else:
                    st.error("No se pudo crear la reserva en Airtable.")


def _render_contratacion(exp, docs, user_id, clientes_map):
    exp_id = exp["id"]
    f = exp["fields"]
    campanas = list_campanas(exp_id)

    h1, h2 = st.columns([2, 1])
    with h1:
        st.markdown("#### Campañas cerradas")
    with h2:
        if st.button("Añadir campaña", icon=":material/note_add:", type="primary", use_container_width=True, key="add_camp"):
            _new_campana_dialog(exp_id, user_id, f.get("Marca", ""))
    if not campanas:
        st.markdown(
            "<div style='border:1px dashed #E6E4DF; padding:24px; text-align:center; color:#6B6B6B; "
            "font-size:0.9rem;'>Aún no hay campañas cerradas. Crea una para registrar órdenes de compra, "
            "facturas mensuales y la conciliación de precios.</div>",
            unsafe_allow_html=True,
        )
    else:
        for c in campanas:
            _campana_card(c, user_id)

    st.divider()
    _render_fiscal_checklist(exp_id, docs, user_id)
    st.divider()
    _render_reserva_efectiva(exp, clientes_map, user_id)

# ══════════════════════════════════════════════════════════════════════════════════
# CIERRE
# ══════════════════════════════════════════════════════════════════════════════════

def _render_cierre(exp, docs, user_id):
    exp_id = exp["id"]
    st.markdown("#### Cierre")
    st.caption("Sube la prueba de buen montaje (foto o PDF) y marca el resultado del expediente.")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("Marcar como Ganado", icon=":material/emoji_events:", use_container_width=True, key="win_exp"):
            if update_expediente(exp_id, {"Estado": "Ganado", "Etapa": "Cierre"}):
                _refresh()
            else:
                st.error("No se pudo actualizar.")
    with c2:
        if st.button("Marcar como Perdido", icon=":material/cancel:", use_container_width=True, key="lose_exp"):
            if update_expediente(exp_id, {"Estado": "Perdido"}):
                _refresh()
            else:
                st.error("No se pudo actualizar.")
    st.divider()
    _render_stage_docs(exp_id, "Cierre", docs, user_id,
                       intro="Prueba de montaje del anuncio en el espacio (foto o PDF).")

# ══════════════════════════════════════════════════════════════════════════════════
# DETALLE / LISTA / MAIN
# ══════════════════════════════════════════════════════════════════════════════════

def _render_detail(exp, user_id, token, admin, clientes_map):
    exp_id = exp["id"]
    f = exp["fields"]

    if st.button("← Volver a la lista", key="back_to_list"):
        st.session_state.pop("exp_selected", None)
        st.rerun()

    titulo = f.get("Nombre", "(sin nombre)")
    cliente_disp = f.get("Marca") or f.get("Agencia") or "Sin cliente"
    estado = f.get("Estado", "Abierto")
    bg, fg = ESTADO_COLORS.get(estado, ("#F1F5F9", "#475569"))

    st.markdown(f"### {titulo}")
    st.markdown(
        f"🏢 **{cliente_disp}** &nbsp; {_chip(estado, bg, fg)}"
        + (f" &nbsp; 👤 {f.get('Vendedor_Nombre','')}" if admin and f.get("Vendedor_Nombre") else ""),
        unsafe_allow_html=True,
    )
    _render_stepper(f.get("Etapa", "Solicitud"))

    documentos = list_documentos(exp_id)

    def docs_de(etapa):
        return [d for d in documentos if d["fields"].get("Etapa") == etapa]

    tabs = st.tabs(["📋 Solicitud", "💰 Presupuesto", "📑 Contratación", "🛠️ Producción", "🏁 Cierre"])
    with tabs[0]:
        _render_solicitud(exp, docs_de("Solicitud"), user_id, admin, clientes_map)
    with tabs[1]:
        _render_presupuesto(exp, docs_de("Presupuesto"), user_id)
    with tabs[2]:
        _render_contratacion(exp, docs_de("Contratación"), user_id, clientes_map)
    with tabs[3]:
        _render_stage_docs(exp_id, "Producción", docs_de("Producción"), user_id,
                           intro="Recepción de artes/creatividades y presupuestos/órdenes de montaje.")
    with tabs[4]:
        _render_cierre(exp, docs_de("Cierre"), user_id)


def _render_list(expedientes, admin, profiles, user_id, user_name, clientes_map):
    top1, top2 = st.columns([1, 3])
    with top1:
        if st.button("Nuevo expediente", icon=":material/add:", type="primary", use_container_width=True, key="new_exp_btn"):
            _new_expediente_dialog(user_id, user_name, admin, profiles)

    fc1, fc2, fc3, fc4 = st.columns([2, 1.3, 1.3, 0.6])
    with fc1:
        q = st.text_input("Buscar", placeholder="Nombre, agencia o marca...", label_visibility="collapsed")
    with fc2:
        f_etapa = st.multiselect("Etapa", ETAPAS, placeholder="Etapa")
    with fc3:
        f_estado = st.multiselect("Estado", EXP_ESTADOS, placeholder="Estado")
    with fc4:
        if st.button("🔄", use_container_width=True, help="Actualizar"):
            _refresh()

    items = []
    for e in expedientes:
        f = e["fields"]
        if f_etapa and f.get("Etapa") not in f_etapa:
            continue
        if f_estado and f.get("Estado") not in f_estado:
            continue
        if q:
            hay = f"{f.get('Nombre','')} {f.get('Agencia','')} {f.get('Marca','')}".lower()
            if q.lower() not in hay:
                continue
        items.append(e)

    st.markdown(f"**{len(items)} expediente(s)**")
    if not items:
        st.info("No hay expedientes que coincidan. Crea uno con el botón de arriba.")
        return

    items.sort(key=lambda e: (ETAPAS.index(e["fields"].get("Etapa", "Solicitud")) if e["fields"].get("Etapa") in ETAPAS else 0,
                              e["fields"].get("Nombre", "")))

    for e in items:
        f = e["fields"]
        cliente_disp = f.get("Marca") or f.get("Agencia") or "Sin cliente"
        estado = f.get("Estado", "Abierto")
        bg, fg = ESTADO_COLORS.get(estado, ("#F1F5F9", "#475569"))
        fase = f.get("Fase_Solicitud")
        with st.container(border=True):
            col_info, col_meta, col_btn = st.columns([4, 2.5, 1.2])
            with col_info:
                st.markdown(f"**{f.get('Nombre','(sin nombre)')}**")
                vend = f" · 👤 {f.get('Vendedor_Nombre','')}" if admin and f.get("Vendedor_Nombre") else ""
                st.caption(f"🏢 {cliente_disp}{vend}")
            with col_meta:
                chips = _chip(f.get("Etapa", "Solicitud")) + _chip(estado, bg, fg)
                if fase:
                    fbg, ffg = FASE_COLORS.get(fase, ("#EEEDEA", "#6B6B6B"))
                    chips += _chip(fase, fbg, ffg)
                st.markdown(chips, unsafe_allow_html=True)
            with col_btn:
                if st.button("Abrir", key=f"open_{e['id']}", use_container_width=True, type="primary"):
                    st.session_state["exp_selected"] = e["id"]
                    st.rerun()


def show_expedientes():
    page_header(
        "Procesos de Venta",
        "Gestiona cada oportunidad de venta de principio a fin: solicitud, presupuesto, "
        "contratación, producción y cierre.",
        eyebrow="Ventas",
    )

    if not is_configured():
        st.error("⚠️ Error de conexión con Airtable. Contacta al administrador.")
        return

    user_id = st.session_state.get("user_id")
    user_name = st.session_state.get("user_name", "Usuario")
    token = st.session_state.get("user_token")
    admin = is_admin(st.session_state.get("user_role"))

    with st.spinner("Cargando..."):
        profiles = get_all_profiles(token) if admin else []
        expedientes = list_expedientes(vendedor_id=None if admin else user_id)
        clientes_map = {c["id"]: cliente_label(c) for c in list_clientes()}

    selected = st.session_state.get("exp_selected")
    if selected:
        exp = next((e for e in expedientes if e["id"] == selected), None)
        if not exp:
            from src.airtable_client import get_expediente
            exp = get_expediente(selected)
        if not exp:
            st.warning("No se encontró el expediente. Vuelve a la lista.")
            if st.button("← Volver"):
                st.session_state.pop("exp_selected", None)
                st.rerun()
            return
        _render_detail(exp, user_id, token, admin, clientes_map)
    else:
        _render_list(expedientes, admin, profiles, user_id, user_name, clientes_map)
