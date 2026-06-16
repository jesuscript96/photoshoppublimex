"""Procesos de Venta (Expedientes).

Representa el flujo de venta de Publimex de principio a fin:
Solicitud → Presupuesto → Contratación → Producción → Cierre.

Cada expediente es el contenedor de una oportunidad: acumula información,
presupuestos (con datos) y documentos (metadatos + enlace a Drive) por etapa.
El hito clave "Generar reserva efectiva" exige un presupuesto Aceptado y crea la
reserva en la tabla maestra (Reservaciones), que alimenta Disponibilidades.
"""

from datetime import date
import streamlit as st

from src.airtable_client import (
    ETAPAS, EXP_ESTADOS, PRESUPUESTO_ESTADOS, DOC_TIPOS, DOC_DIRECCIONES,
    DOC_ESTADOS, TIPOS_POR_ETAPA, RESERVA_ESTADOS, is_configured,
    list_expedientes, create_expediente, update_expediente, delete_expediente,
    list_presupuestos, create_presupuesto, update_presupuesto, delete_presupuesto,
    list_documentos, create_documento, delete_documento,
    list_clientes, list_espacios, cliente_label, espacio_label,
    create_reservacion, refresh_data,
)
from src.supabase_client import is_admin, get_all_profiles
from src.theme import page_header

# ── Estilos / helpers visuales ──────────────────────────────────────────────────

ESTADO_COLORS = {
    "Abierto":  ("#DBEAFE", "#1e40af"),
    "Ganado":   ("#DCFCE7", "#166534"),
    "Perdido":  ("#FEE2E2", "#991b1b"),
    "En pausa": ("#FEF9C3", "#854d0e"),
}

PRES_COLORS = {
    "Borrador":       ("#F1F5F9", "#475569"),
    "Enviado":        ("#DBEAFE", "#1e40af"),
    "En negociación": ("#FEF9C3", "#854d0e"),
    "Aceptado":       ("#DCFCE7", "#166534"),
    "Rechazado":      ("#FEE2E2", "#991b1b"),
    "Vencido":        ("#E2E8F0", "#64748b"),
}


def _chip(text, bg="#FDECEC", fg="#A50000"):
    return (f'<span style="background:{bg}; color:{fg}; padding:2px 9px; '
            f'border-radius:0; font-size:0.72rem; font-weight:600; '
            f'white-space:nowrap;">{text}</span>')


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
        f'<div style="display:flex; align-items:flex-start; justify-content:space-between; '
        f'margin:6px 0 10px 0;">{"".join(cells)}</div>',
        unsafe_allow_html=True,
    )

# ── Gestor de documentos por etapa (metadatos) ──────────────────────────────────

def _file_icon():
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="#E60000" '
            'stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="width:18px;height:18px;">'
            '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><path d="M14 2v6h6"/></svg>')


def _file_card(d):
    """Tarjeta de archivo (aspecto de repositorio)."""
    df = d["fields"]
    dirn = df.get("Direccion", "—")
    estado = df.get("Estado", "—")
    fecha = df.get("Fecha", "")
    meta = f"{dirn} · {estado}" + (f" · {fecha}" if fecha else "")
    with st.container(border=True):
        st.markdown(
            f'<div style="display:flex; align-items:center; gap:8px; margin-bottom:6px;">{_file_icon()}'
            f'{_chip(df.get("Tipo", "Documento"))}</div>'
            f'<div style="font-weight:600; color:#1A1A1A; line-height:1.3;">{df.get("Nombre", "(sin nombre)")}</div>'
            f'<div style="font-size:0.78rem; color:#6B6B6B; margin-top:3px;">{meta}</div>',
            unsafe_allow_html=True,
        )
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
    """CTA rápido: subir un documento con datos mínimos (los demás por defecto)."""
    suggested = TIPOS_POR_ETAPA.get(etapa, DOC_TIPOS)
    default_tipo = suggested[0] if suggested else DOC_TIPOS[0]
    st.markdown("**Subir documento**")
    st.caption("Rápido: adjunta el archivo o pega su enlace. El resto se rellena por defecto.")
    with st.form(f"quick_doc_{etapa}", clear_on_submit=True):
        st.file_uploader("Archivo", disabled=True, key=f"qup_{etapa}",
                         help="Próximamente: subida directa al Google Drive de la empresa.")
        tipo = st.selectbox("Tipo", DOC_TIPOS, index=DOC_TIPOS.index(default_tipo), key=f"qtipo_{etapa}")
        nombre = st.text_input("Nombre / descripción *", key=f"qnom_{etapa}")
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
            if create_documento(fields):
                st.success("Documento guardado.")
                _refresh()
            else:
                st.error("Error al guardar el documento.")


def _doc_detailed_form(exp_id, etapa, user_id):
    """CTA detallado: registrar un documento con todos sus metadatos."""
    suggested = TIPOS_POR_ETAPA.get(etapa, DOC_TIPOS)
    default_tipo = suggested[0] if suggested else DOC_TIPOS[0]
    st.markdown("**Registrar documento**")
    st.caption("Detallado: tipo, dirección, estado, fecha, enlace y notas.")
    with st.form(f"full_doc_{etapa}", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            tipo = st.selectbox("Tipo *", DOC_TIPOS, index=DOC_TIPOS.index(default_tipo), key=f"ftipo_{etapa}")
            direccion = st.selectbox("Dirección *", DOC_DIRECCIONES, key=f"fdir_{etapa}")
        with c2:
            estado = st.selectbox("Estado", DOC_ESTADOS, key=f"fest_{etapa}")
            fecha = st.date_input("Fecha", value=date.today(), key=f"ffec_{etapa}")
        nombre = st.text_input("Nombre / descripción *", key=f"fnom_{etapa}",
                               placeholder="Ej. Contrato firmado Coca-Cola")
        enlace = st.text_input("Enlace (Drive / URL)", key=f"fenl_{etapa}", placeholder="https://drive.google.com/...")
        notas = st.text_area("Notas", key=f"fnotas_{etapa}", height=70)
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
    """Panel de seguimiento de archivos de una etapa: stats + 2 CTAs + repositorio."""
    if intro:
        st.caption(intro)

    enviados = sum(1 for d in docs if d["fields"].get("Direccion") == "Enviado")
    recibidos = sum(1 for d in docs if d["fields"].get("Direccion") == "Recibido")
    validados = sum(1 for d in docs if d["fields"].get("Estado") == "Validado")
    st.markdown(
        '<div style="display:flex; gap:8px; align-items:center; flex-wrap:wrap; margin:6px 0 12px;">'
        + _chip(f"{len(docs)} documentos", "#F1F0EC", "#5A5A5A")
        + _chip(f"Enviados {enviados}", "#E7EEF7", "#1F4E79")
        + _chip(f"Recibidos {recibidos}", "#E7F4EC", "#1B7A3D")
        + _chip(f"Validados {validados}", "#FDECEC", "#A50000")
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
            "<div style='border:1px dashed #E6E4DF; padding:26px; text-align:center; "
            "color:#6B6B6B; font-size:0.9rem;'>Aún no hay archivos en esta etapa. "
            "Súbelos como prueba visible del proceso.</div>",
            unsafe_allow_html=True,
        )
        return

    docs_sorted = sorted(docs, key=lambda x: x["fields"].get("Fecha", ""), reverse=True)
    cols = st.columns(3)
    for i, d in enumerate(docs_sorted):
        with cols[i % 3]:
            _file_card(d)

# ── Presupuestos ─────────────────────────────────────────────────────────────────

@st.dialog("Registrar presupuesto")
def _new_presupuesto_dialog(exp_id, user_id, next_version):
    c1, c2, c3 = st.columns(3)
    with c1:
        folio = st.text_input("Folio *", placeholder="Ej. P-2026-014")
    with c2:
        version = st.number_input("Versión", min_value=1, step=1, value=next_version)
    with c3:
        moneda = st.selectbox("Moneda", ["MXN", "USD"])
    c4, c5 = st.columns(2)
    with c4:
        fecha = st.date_input("Fecha", value=date.today())
    with c5:
        valido = st.date_input("Válido hasta", value=None)
    c6, c7, c8 = st.columns(3)
    with c6:
        subtotal = st.number_input("Subtotal", min_value=0, step=10000)
    with c7:
        iva = st.number_input("IVA (16% sugerido)", min_value=0, step=1000)
    with c8:
        total = st.number_input("Total", min_value=0, step=10000)
    estado = st.selectbox("Estado", PRESUPUESTO_ESTADOS, index=0)
    resumen = st.text_area("Resumen de espacios / momentos / precios",
                           placeholder="Ej. Muro Insurgentes (3 meses) $X, Pantalla Periférico (1 mes) $Y ...")
    condiciones = st.text_area("Condiciones", height=70)
    enlace = st.text_input("Enlace al PDF (Drive / URL)", placeholder="https://drive.google.com/...")
    if st.button("Registrar presupuesto", type="primary", use_container_width=True):
        if not folio:
            st.error("El folio es obligatorio.")
        else:
            iva_final = iva or round(subtotal * 0.16)
            total_final = total or (subtotal + iva_final)
            fields = {
                "Folio": folio, "Expediente": [exp_id], "Version": int(version),
                "Fecha": fecha.isoformat() if fecha else None,
                "Subtotal_MXN": subtotal, "IVA_MXN": iva_final, "Total_MXN": total_final,
                "Moneda": moneda, "Estado": estado, "Resumen_Espacios": resumen,
                "Condiciones": condiciones, "Vendedor_ID": user_id,
            }
            if valido:
                fields["Valido_Hasta"] = valido.isoformat()
            if enlace:
                fields["Enlace_Archivo"] = enlace
            fields = {k: v for k, v in fields.items() if v is not None}
            if create_presupuesto(fields):
                _refresh()
            else:
                st.error("Error al registrar el presupuesto en Airtable.")


def _presupuesto_card(p):
    pf = p["fields"]
    estado = pf.get("Estado", "Borrador")
    bg, fg = PRES_COLORS.get(estado, ("#F1F5F9", "#475569"))
    total = pf.get("Total_MXN", 0) or 0
    meta = f'Subtotal ${pf.get("Subtotal_MXN",0) or 0:,.0f} · IVA ${pf.get("IVA_MXN",0) or 0:,.0f}'
    if pf.get("Fecha"):
        meta += f' · {pf["Fecha"]}'
    if pf.get("Valido_Hasta"):
        meta += f' · vence {pf["Valido_Hasta"]}'
    with st.container(border=True):
        st.markdown(
            f'<div style="display:flex; justify-content:space-between; align-items:center;">'
            f'<div style="font-weight:600;">{pf.get("Folio","(sin folio)")} · v{pf.get("Version",1)}</div>'
            f'{_chip(estado, bg, fg)}</div>'
            f'<div style="font-size:1.35rem; font-weight:700; margin-top:4px;">{pf.get("Moneda","MXN")} ${total:,.0f}</div>'
            f'<div style="font-size:0.8rem; color:#6B6B6B;">{meta}</div>',
            unsafe_allow_html=True,
        )
        if pf.get("Resumen_Espacios"):
            st.caption(pf["Resumen_Espacios"])
        a1, a2, a3 = st.columns(3)
        with a1:
            if pf.get("Enlace_Archivo"):
                st.link_button("Abrir PDF", pf["Enlace_Archivo"], icon=":material/picture_as_pdf:", use_container_width=True)
        with a2:
            with st.popover("Estado", icon=":material/flag:", use_container_width=True):
                ne = st.selectbox("Cambiar estado", PRESUPUESTO_ESTADOS,
                                  index=PRESUPUESTO_ESTADOS.index(estado) if estado in PRESUPUESTO_ESTADOS else 0,
                                  key=f"pest_{p['id']}")
                if st.button("Guardar", key=f"psave_{p['id']}", type="primary"):
                    if update_presupuesto(p["id"], {"Estado": ne}):
                        _refresh()
                    else:
                        st.error("No se pudo actualizar.")
        with a3:
            with st.popover("Borrar", icon=":material/delete:", use_container_width=True):
                st.write("¿Borrar este presupuesto?")
                if st.button("Sí, borrar", key=f"pdel_{p['id']}", type="primary"):
                    if delete_presupuesto(p["id"]):
                        _refresh()
                    else:
                        st.error("No se pudo borrar.")


def _render_presupuestos(exp, presupuestos, docs, user_id):
    exp_id = exp["id"]
    aceptado = any(p["fields"].get("Estado") == "Aceptado" for p in presupuestos)
    st.markdown(
        '<div style="display:flex; gap:8px; align-items:center; flex-wrap:wrap; margin:2px 0 12px;">'
        + _chip(f"{len(presupuestos)} presupuestos", "#F1F0EC", "#5A5A5A")
        + (_chip("Hay uno Aceptado", "#E7F4EC", "#1B7A3D") if aceptado else _chip("Ninguno aceptado", "#FBF0D9", "#8A5A00"))
        + '</div>',
        unsafe_allow_html=True,
    )

    next_version = (max([pp["fields"].get("Version", 0) for pp in presupuestos], default=0) + 1) if presupuestos else 1
    cta, _sp = st.columns([1, 3])
    with cta:
        if st.button("Registrar presupuesto", icon=":material/note_add:", type="primary",
                     use_container_width=True, key="new_pres_btn"):
            _new_presupuesto_dialog(exp_id, user_id, next_version)

    st.write("")
    if not presupuestos:
        st.markdown(
            "<div style='border:1px dashed #E6E4DF; padding:26px; text-align:center; color:#6B6B6B; "
            "font-size:0.9rem;'>Aún no hay presupuestos. Registra el primero para avanzar la negociación.</div>",
            unsafe_allow_html=True,
        )
    else:
        for p in sorted(presupuestos, key=lambda x: (x["fields"].get("Fecha", ""), x["fields"].get("Version", 0)), reverse=True):
            _presupuesto_card(p)

    st.divider()
    _render_stage_docs(exp_id, "Presupuesto", docs, user_id,
                       intro="Adjunta presentaciones o versiones del presupuesto en PDF.")

# ── Contratación (hito: generar reserva efectiva) ───────────────────────────────

def _render_contratacion(exp, presupuestos, docs, user_id, clientes_map):
    exp_id = exp["id"]
    f = exp["fields"]
    aceptado = any(p["fields"].get("Estado") == "Aceptado" for p in presupuestos)

    st.markdown("#### Contratación")
    reservas_vinc = f.get("Reservas_Vinculadas", [])
    if reservas_vinc:
        st.success(f"Este expediente tiene {len(reservas_vinc)} reserva(s) efectiva(s) vinculada(s). "
                   "Puedes verlas en **Disponibilidades**.")

    if not aceptado:
        st.warning("🔒 **Hito bloqueado.** Para generar la reserva efectiva necesitas al menos un presupuesto en estado **Aceptado** "
                   "(ve a la pestaña *Presupuestos* y marca uno como Aceptado).", icon=":material/lock:")
    else:
        with st.expander("✅ Generar reserva efectiva", expanded=not reservas_vinc):
            st.caption("Crea la reserva en el calendario maestro (Disponibilidades) y la vincula a este expediente. "
                       "Puedes repetir la acción para varios espacios.")
            espacios = list_espacios()
            clientes = list_clientes()
            with st.form("form_reserva_efectiva", clear_on_submit=True):
                esp_opts = {e["id"]: espacio_label(e) for e in espacios}
                sel_esp = st.selectbox("Espacio / soporte *", options=list(esp_opts.keys()),
                                       format_func=lambda x: esp_opts.get(x, x))
                # Cliente: por defecto el del expediente, si lo tiene
                cli_opts = {c["id"]: cliente_label(c) for c in clientes}
                exp_cli = (f.get("Cliente") or [None])[0]
                cli_keys = list(cli_opts.keys())
                cli_idx = cli_keys.index(exp_cli) if exp_cli in cli_keys else 0
                sel_cli = st.selectbox("Cliente *", options=cli_keys,
                                       format_func=lambda x: cli_opts.get(x, x),
                                       index=cli_idx if cli_keys else 0)
                rc1, rc2 = st.columns(2)
                with rc1:
                    fi = st.date_input("Fecha inicio *", value=f.get("Fecha_Inicio_Estimada") and date.fromisoformat(f["Fecha_Inicio_Estimada"]) or date.today())
                with rc2:
                    ff = st.date_input("Fecha fin *", value=f.get("Fecha_Fin_Estimada") and date.fromisoformat(f["Fecha_Fin_Estimada"]) or date.today())
                estado_res = st.selectbox("Estado de la reserva", RESERVA_ESTADOS,
                                          index=RESERVA_ESTADOS.index("Confirmada"))
                submitted = st.form_submit_button("Generar reserva efectiva", type="primary", use_container_width=True)

            if submitted:
                if not sel_esp or not sel_cli:
                    st.error("Espacio y cliente son obligatorios.")
                elif ff <= fi:
                    st.error("La fecha fin debe ser posterior al inicio.")
                else:
                    rec = create_reservacion(sel_esp, sel_cli, fi.isoformat(), ff.isoformat(),
                                             estado=estado_res,
                                             notas=f"Generada desde expediente: {f.get('Nombre','')}")
                    if rec:
                        # Vincular al expediente y avanzar etapa a Producción
                        nuevas = reservas_vinc + [rec["id"]]
                        upd = {"Reservas_Vinculadas": nuevas}
                        if ETAPAS.index(f.get("Etapa", "Solicitud")) < ETAPAS.index("Producción"):
                            upd["Etapa"] = "Producción"
                        update_expediente(exp_id, upd)
                        st.success("Reserva efectiva creada y vinculada. El expediente avanza a Producción.")
                        _refresh()
                    else:
                        st.error("No se pudo crear la reserva en Airtable.")

    st.divider()
    _render_stage_docs(exp_id, "Contratación", docs, user_id,
                       intro="Contratos, pagarés, órdenes de compra, facturas (CFDI), justificantes y documentos de pago del cliente.")

# ── Detalle del expediente ──────────────────────────────────────────────────────

def _render_detail(exp, user_id, token, admin, clientes_map):
    exp_id = exp["id"]
    f = exp["fields"]

    if st.button("← Volver a la lista", key="back_to_list"):
        st.session_state.pop("exp_selected", None)
        st.rerun()

    nombre = f.get("Nombre", "(sin nombre)")
    cli_ids = f.get("Cliente", [])
    cli_name = clientes_map.get(cli_ids[0], None) if cli_ids else None
    cliente_disp = cli_name or f.get("Cliente_Prospecto") or "Sin cliente"
    estado = f.get("Estado", "Abierto")
    bg, fg = ESTADO_COLORS.get(estado, ("#F1F5F9", "#475569"))

    st.markdown(f"### {nombre}")
    st.markdown(
        f"🏢 **{cliente_disp}** &nbsp; {_chip(estado, bg, fg)}"
        + (f" &nbsp; 👤 {f.get('Vendedor_Nombre','')}" if admin and f.get("Vendedor_Nombre") else ""),
        unsafe_allow_html=True,
    )
    _render_stepper(f.get("Etapa", "Solicitud"))

    presupuestos = list_presupuestos(exp_id)
    documentos = list_documentos(exp_id)

    def docs_de(etapa):
        return [d for d in documentos if d["fields"].get("Etapa") == etapa]

    tabs = st.tabs(["📋 Solicitud", "💰 Presupuestos", "📑 Contratación", "🛠️ Producción", "🏁 Cierre"])

    with tabs[0]:
        _render_solicitud(exp, docs_de("Solicitud"), user_id, admin, token, clientes_map)
    with tabs[1]:
        _render_presupuestos(exp, presupuestos, docs_de("Presupuesto"), user_id)
    with tabs[2]:
        _render_contratacion(exp, presupuestos, docs_de("Contratación"), user_id, clientes_map)
    with tabs[3]:
        _render_stage_docs(exp_id, "Producción", docs_de("Producción"), user_id,
                           intro="Recepción de artes/creatividades y presupuestos/órdenes de montaje.")
    with tabs[4]:
        _render_cierre(exp, docs_de("Cierre"), user_id)


@st.dialog("Editar datos del proceso")
def _edit_expediente_dialog(exp):
    exp_id = exp["id"]
    f = exp["fields"]
    nombre = st.text_input("Nombre *", value=f.get("Nombre", ""))
    clientes = list_clientes()
    cli_opts = {"__keep__": "— (mantener / prospecto) —"}
    for c in clientes:
        cli_opts[c["id"]] = cliente_label(c)
    cur_cli = (f.get("Cliente") or ["__keep__"])[0]
    cli_keys = list(cli_opts.keys())
    cli_sel = st.selectbox("Cliente (catálogo)", options=cli_keys, format_func=lambda k: cli_opts[k],
                           index=cli_keys.index(cur_cli) if cur_cli in cli_keys else 0)
    prospecto = st.text_input("Cliente prospecto (si no está en catálogo)", value=f.get("Cliente_Prospecto", ""))
    c1, c2 = st.columns(2)
    with c1:
        fi = st.date_input("Fecha inicio estimada",
                           value=date.fromisoformat(f["Fecha_Inicio_Estimada"]) if f.get("Fecha_Inicio_Estimada") else None)
    with c2:
        ff = st.date_input("Fecha fin estimada",
                           value=date.fromisoformat(f["Fecha_Fin_Estimada"]) if f.get("Fecha_Fin_Estimada") else None)
    c3, c4 = st.columns(2)
    with c3:
        etapa = st.selectbox("Etapa", ETAPAS, index=ETAPAS.index(f.get("Etapa", "Solicitud")) if f.get("Etapa") in ETAPAS else 0)
    with c4:
        estado = st.selectbox("Estado", EXP_ESTADOS, index=EXP_ESTADOS.index(f.get("Estado", "Abierto")) if f.get("Estado") in EXP_ESTADOS else 0)
    valor = st.number_input("Valor estimado (MXN)", min_value=0, step=10000, value=int(f.get("Valor_Estimado_MXN", 0) or 0))
    notas = st.text_area("Notas", value=f.get("Notas", ""))
    if st.button("Guardar cambios", type="primary", use_container_width=True):
        if not nombre:
            st.error("El nombre es obligatorio.")
        else:
            fields = {
                "Nombre": nombre, "Cliente_Prospecto": prospecto, "Etapa": etapa, "Estado": estado,
                "Valor_Estimado_MXN": valor, "Notas": notas,
                "Fecha_Inicio_Estimada": fi.isoformat() if fi else "",
                "Fecha_Fin_Estimada": ff.isoformat() if ff else "",
            }
            if cli_sel != "__keep__":
                fields["Cliente"] = [cli_sel]
            if update_expediente(exp_id, fields):
                _refresh()
            else:
                st.error("Error al guardar en Airtable.")


def _render_solicitud(exp, docs, user_id, admin, token, clientes_map):
    exp_id = exp["id"]
    f = exp["fields"]

    cli_ids = f.get("Cliente", [])
    cli_name = clientes_map.get(cli_ids[0]) if cli_ids else None
    cliente_disp = cli_name or f.get("Cliente_Prospecto") or "<span class='pm-muted'>Sin cliente</span>"
    fi, ff = f.get("Fecha_Inicio_Estimada"), f.get("Fecha_Fin_Estimada")
    periodo = f"{fi or '—'} → {ff or '—'}" if (fi or ff) else "<span class='pm-muted'>Sin fechas definidas</span>"
    valor = f.get("Valor_Estimado_MXN", 0) or 0
    valor_disp = f"${valor:,.0f} MXN" if valor else "<span class='pm-muted'>—</span>"
    notas = f.get("Notas") or "<span class='pm-muted'>Sin notas</span>"

    with st.container(border=True):
        st.markdown(
            '<div class="pm-kv">'
            f'<div><div class="lbl">Cliente</div><div class="val">{cliente_disp}</div></div>'
            f'<div><div class="lbl">Etapa actual</div><div class="val">{f.get("Etapa","Solicitud")}</div></div>'
            f'<div><div class="lbl">Estado</div><div class="val">{f.get("Estado","Abierto")}</div></div>'
            f'<div><div class="lbl">Periodo estimado</div><div class="val">{periodo}</div></div>'
            f'<div><div class="lbl">Valor estimado</div><div class="val">{valor_disp}</div></div>'
            + (f'<div><div class="lbl">Vendedor</div><div class="val">{f.get("Vendedor_Nombre","—")}</div></div>' if admin else '')
            + f'<div class="full"><div class="lbl">Notas</div><div class="val">{notas}</div></div>'
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
                st.write("Esto elimina el expediente (no borra reservas ni documentos en sus tablas).")
                if st.button("Sí, borrar expediente", type="primary", key="del_exp_confirm"):
                    if delete_expediente(exp_id):
                        st.session_state.pop("exp_selected", None)
                        _refresh()
                    else:
                        st.error("No se pudo borrar.")

    st.divider()
    _render_stage_docs(exp_id, "Solicitud", docs, user_id,
                       intro="Presentaciones de disponibilidades y material inicial de la oportunidad.")


def _render_cierre(exp, docs, user_id):
    exp_id = exp["id"]
    f = exp["fields"]
    st.markdown("#### Cierre")
    st.caption("Sube la **prueba de buen montaje** (foto o PDF) y marca el resultado del expediente.")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("🏆 Marcar como Ganado", use_container_width=True, key="win_exp"):
            if update_expediente(exp_id, {"Estado": "Ganado", "Etapa": "Cierre"}):
                st.success("Expediente marcado como Ganado.")
                _refresh()
            else:
                st.error("No se pudo actualizar.")
    with c2:
        if st.button("❌ Marcar como Perdido", use_container_width=True, key="lose_exp"):
            if update_expediente(exp_id, {"Estado": "Perdido"}):
                st.warning("Expediente marcado como Perdido.")
                _refresh()
            else:
                st.error("No se pudo actualizar.")
    st.divider()
    _render_stage_docs(exp_id, "Cierre", docs, user_id,
                       intro="Prueba de montaje del anuncio en el espacio (foto o PDF).")

# ── Lista de expedientes ────────────────────────────────────────────────────────

def _render_new_expediente(user_id, user_name, admin, profiles):
    with st.expander("➕ Nuevo expediente / solicitud de reserva"):
        with st.form("form_new_exp", clear_on_submit=True):
            nombre = st.text_input("Nombre del proceso *", placeholder="Ej. Coca-Cola Verano 2026")
            clientes = list_clientes()
            cli_opts = {"__prospecto__": "— Prospecto (no está en catálogo) —"}
            for c in clientes:
                cli_opts[c["id"]] = cliente_label(c)
            cli_sel = st.selectbox("Cliente", options=list(cli_opts.keys()),
                                   format_func=lambda k: cli_opts[k])
            prospecto = st.text_input("Nombre del prospecto",
                                      help="Rellena solo si elegiste 'Prospecto' arriba.")
            c1, c2 = st.columns(2)
            with c1:
                fi = st.date_input("Fecha inicio estimada (opcional)", value=None)
            with c2:
                ff = st.date_input("Fecha fin estimada (opcional)", value=None)
            valor = st.number_input("Valor estimado (MXN)", min_value=0, step=10000)
            notas = st.text_area("Notas")

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

            submitted = st.form_submit_button("Crear expediente", type="primary", use_container_width=True)

        if submitted:
            if not nombre:
                st.error("El nombre del proceso es obligatorio.")
            else:
                fields = {
                    "Nombre": nombre,
                    "Etapa": "Solicitud",
                    "Estado": "Abierto",
                    "Vendedor_ID": vendedor_id,
                    "Vendedor_Nombre": vendedor_nombre,
                }
                if cli_sel != "__prospecto__":
                    fields["Cliente"] = [cli_sel]
                elif prospecto:
                    fields["Cliente_Prospecto"] = prospecto
                if fi:
                    fields["Fecha_Inicio_Estimada"] = fi.isoformat()
                if ff:
                    fields["Fecha_Fin_Estimada"] = ff.isoformat()
                if valor:
                    fields["Valor_Estimado_MXN"] = valor
                if notas:
                    fields["Notas"] = notas
                rec = create_expediente(fields)
                if rec:
                    st.success("Expediente creado.")
                    refresh_data()
                    st.session_state["exp_selected"] = rec["id"]
                    st.rerun()
                else:
                    st.error("Error al crear el expediente en Airtable.")


def _render_list(expedientes, admin, profiles, user_id, user_name, clientes_map):
    _render_new_expediente(user_id, user_name, admin, profiles)

    # Filtros
    fc1, fc2, fc3, fc4 = st.columns([2, 1.3, 1.3, 0.8])
    with fc1:
        q = st.text_input("Buscar", placeholder="Nombre o cliente...", label_visibility="collapsed")
    with fc2:
        f_etapa = st.multiselect("Etapa", ETAPAS, placeholder="Etapa")
    with fc3:
        f_estado = st.multiselect("Estado", EXP_ESTADOS, placeholder="Estado")
    with fc4:
        if st.button("🔄", use_container_width=True, help="Actualizar"):
            _refresh()

    # Aplicar filtros
    items = []
    for e in expedientes:
        f = e["fields"]
        if f_etapa and f.get("Etapa") not in f_etapa:
            continue
        if f_estado and f.get("Estado") not in f_estado:
            continue
        if q:
            cli_ids = f.get("Cliente", [])
            cli_name = clientes_map.get(cli_ids[0], "") if cli_ids else ""
            hay = f"{f.get('Nombre','')} {cli_name} {f.get('Cliente_Prospecto','')}".lower()
            if q.lower() not in hay:
                continue
        items.append(e)

    st.markdown(f"**{len(items)} expediente(s)**")
    if not items:
        st.info("No hay expedientes que coincidan. Crea uno con el botón de arriba.")
        return

    # Orden: por etapa del pipeline y luego por nombre
    items.sort(key=lambda e: (ETAPAS.index(e["fields"].get("Etapa", "Solicitud")) if e["fields"].get("Etapa") in ETAPAS else 0,
                              e["fields"].get("Nombre", "")))

    for e in items:
        f = e["fields"]
        cli_ids = f.get("Cliente", [])
        cli_name = clientes_map.get(cli_ids[0], None) if cli_ids else None
        cliente_disp = cli_name or f.get("Cliente_Prospecto") or "Sin cliente"
        estado = f.get("Estado", "Abierto")
        bg, fg = ESTADO_COLORS.get(estado, ("#F1F5F9", "#475569"))
        valor = f.get("Valor_Estimado_MXN", 0) or 0

        with st.container(border=True):
            col_info, col_meta, col_btn = st.columns([4, 2.5, 1.2])
            with col_info:
                st.markdown(f"**{f.get('Nombre','(sin nombre)')}**")
                vend = f" · 👤 {f.get('Vendedor_Nombre','')}" if admin and f.get("Vendedor_Nombre") else ""
                st.caption(f"🏢 {cliente_disp}{vend}")
            with col_meta:
                st.markdown(
                    _chip(f.get("Etapa", "Solicitud")) + " &nbsp; " + _chip(estado, bg, fg),
                    unsafe_allow_html=True,
                )
                if valor:
                    st.caption(f"≈ ${valor:,.0f} MXN")
            with col_btn:
                if st.button("Abrir", key=f"open_{e['id']}", use_container_width=True, type="primary"):
                    st.session_state["exp_selected"] = e["id"]
                    st.rerun()

# ── Vista principal ─────────────────────────────────────────────────────────────

def show_expedientes():
    page_header(
        "Procesos de Venta",
        "Gestiona cada oportunidad de venta de principio a fin: solicitud, presupuestos, "
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
            # Puede haber cambiado de dueño/etapa; recargar
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
