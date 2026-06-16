"""Cliente central de Airtable para la base de Publimex.

Centraliza credenciales, helpers REST genéricos (fetch/post/patch/delete) y el
CRUD de las entidades del proceso de venta (Expedientes, Presupuestos, Documentos).

Las páginas antiguas (disponibilidades.py, reservas.py) siguen con sus propios
helpers; pueden migrarse a este módulo más adelante. El código nuevo usa este.
"""

import os
import requests
import streamlit as st

# ── Credenciales ──────────────────────────────────────────────────────────────

def get_secret(key):
    try:
        return st.secrets[key]
    except Exception:
        return os.environ.get(key, "")

AIRTABLE_TOKEN = get_secret("AIRTABLE_TOKEN")
BASE = "appW4QjUOV9nXQkx9"

# ── IDs de tablas ───────────────────────────────────────────────────────────────
# Catálogo / maestro (existentes)
T_ESPACIOS       = "tblQ9Z0KW0XheaHRc"
T_RESERVACIONES  = "tbluUAzNFSuaqMrYX"
T_CLIENTES       = "tblkKHa9CNt285uv1"
T_MATERIALES     = "tblxP9eGeHVbeBV6r"

# Proceso de venta (nuevas)
T_EXPEDIENTES    = "tblQS1aJLOPJUE1bP"
T_PRESUPUESTOS   = "tblX4TboVxCANUKSI"
T_DOCUMENTOS     = "tblFrBtscu4LzpS78"

# ── Catálogos de valores (deben coincidir con los singleSelect de Airtable) ─────

ETAPAS = ["Solicitud", "Presupuesto", "Contratación", "Producción", "Cierre"]

EXP_ESTADOS = ["Abierto", "Ganado", "Perdido", "En pausa"]

PRESUPUESTO_ESTADOS = [
    "Borrador", "Enviado", "En negociación", "Aceptado", "Rechazado", "Vencido",
]

DOC_TIPOS = [
    "Presentación", "Presupuesto", "Contrato", "Pagaré", "Justificante de pago",
    "Factura (CFDI)", "Complemento de pago", "Orden de compra",
    "Documento de pago del cliente", "Arte/Creatividad", "Presupuesto de montaje",
    "Orden de montaje", "Prueba de montaje", "Otro",
]

DOC_DIRECCIONES = ["Enviado", "Recibido"]
DOC_ESTADOS = ["Pendiente", "Recibido", "Validado", "Vencido"]

# Tipos de documento sugeridos por etapa (para guiar el formulario)
TIPOS_POR_ETAPA = {
    "Solicitud":    ["Presentación", "Otro"],
    "Presupuesto":  ["Presupuesto", "Otro"],
    "Contratación": [
        "Contrato", "Pagaré", "Orden de compra", "Documento de pago del cliente",
        "Justificante de pago", "Factura (CFDI)", "Complemento de pago", "Otro",
    ],
    "Producción":   ["Arte/Creatividad", "Presupuesto de montaje", "Orden de montaje", "Otro"],
    "Cierre":       ["Prueba de montaje", "Otro"],
}

# Estado de reservación efectiva (Airtable Reservaciones.Estado)
RESERVA_ESTADOS = ["Propuesta", "Confirmada", "Activa", "Finalizada", "Cancelada", "Pendiente"]

# ── Helpers REST genéricos ──────────────────────────────────────────────────────

def _headers(write=False):
    h = {"Authorization": f"Bearer {AIRTABLE_TOKEN}"}
    if write:
        h["Content-Type"] = "application/json"
    return h

def is_configured() -> bool:
    return bool(AIRTABLE_TOKEN)

def fetch_table(table_id: str, formula: str | None = None,
                sort_field: str | None = None, sort_dir: str = "asc") -> list:
    """Devuelve todos los registros de una tabla, con filtro/orden opcionales."""
    if not AIRTABLE_TOKEN:
        return []
    records: list = []
    params: dict = {}
    if formula:
        params["filterByFormula"] = formula
    if sort_field:
        params["sort[0][field]"] = sort_field
        params["sort[0][direction]"] = sort_dir
    url = f"https://api.airtable.com/v0/{BASE}/{table_id}"
    while True:
        r = requests.get(url, headers=_headers(), params=params, timeout=15)
        r.raise_for_status()
        data = r.json()
        records.extend(data.get("records", []))
        offset = data.get("offset")
        if not offset:
            break
        params = {**params, "offset": offset}
    return records

def create_record(table_id: str, fields: dict):
    """Crea un registro. Devuelve el registro creado (dict) o None."""
    r = requests.post(
        f"https://api.airtable.com/v0/{BASE}/{table_id}",
        headers=_headers(write=True), json={"fields": fields, "typecast": True}, timeout=15,
    )
    if r.status_code == 200:
        return r.json()
    return None

def update_record(table_id: str, record_id: str, fields: dict) -> bool:
    r = requests.patch(
        f"https://api.airtable.com/v0/{BASE}/{table_id}/{record_id}",
        headers=_headers(write=True), json={"fields": fields, "typecast": True}, timeout=15,
    )
    return r.status_code == 200

def delete_record(table_id: str, record_id: str) -> bool:
    r = requests.delete(
        f"https://api.airtable.com/v0/{BASE}/{table_id}/{record_id}",
        headers=_headers(), timeout=15,
    )
    return r.status_code == 200

# ── Lectura con caché ligera ────────────────────────────────────────────────────
# Streamlit re-ejecuta el script en cada interacción; cacheamos las lecturas unos
# segundos para no golpear la API de Airtable, y limpiamos tras cada escritura.

@st.cache_data(ttl=10, show_spinner=False)
def _all_records(table_id: str, formula: str | None = None) -> list:
    return fetch_table(table_id, formula=formula)

def refresh_data():
    """Invalida las cachés de lectura (llamar tras escrituras o al refrescar)."""
    _all_records.clear()

def list_clientes() -> list:
    return _all_records(T_CLIENTES)

def list_espacios() -> list:
    return _all_records(T_ESPACIOS)

def clear_cache():
    refresh_data()

def cliente_label(cli: dict) -> str:
    f = cli.get("fields", {})
    return f.get("Empresa") or f.get("Contacto") or cli.get("id", "—")

def espacio_label(esp: dict) -> str:
    f = esp.get("fields", {})
    id_num = f.get("﻿ID", f.get("ID", ""))
    return f"ID {id_num} · {f.get('Direccion', '')[:45]} · {f.get('Categoria', '')}"

# ── Expedientes ─────────────────────────────────────────────────────────────────

def list_expedientes(vendedor_id: str | None = None) -> list:
    """Lista expedientes. Si se pasa vendedor_id, filtra por dueño (no-admin)."""
    formula = None
    if vendedor_id:
        formula = f"{{Vendedor_ID}}='{vendedor_id}'"
    return _all_records(T_EXPEDIENTES, formula=formula)

def get_expediente(record_id: str) -> dict | None:
    if not AIRTABLE_TOKEN:
        return None
    r = requests.get(
        f"https://api.airtable.com/v0/{BASE}/{T_EXPEDIENTES}/{record_id}",
        headers=_headers(), timeout=15,
    )
    if r.status_code == 200:
        return r.json()
    return None

def create_expediente(fields: dict):
    return create_record(T_EXPEDIENTES, fields)

def update_expediente(record_id: str, fields: dict) -> bool:
    return update_record(T_EXPEDIENTES, record_id, fields)

def delete_expediente(record_id: str) -> bool:
    return delete_record(T_EXPEDIENTES, record_id)

# ── Presupuestos ────────────────────────────────────────────────────────────────

def list_presupuestos(expediente_id: str) -> list:
    """Presupuestos de un expediente (filtrado en cliente por enlace)."""
    todos = _all_records(T_PRESUPUESTOS)
    return [p for p in todos if expediente_id in p.get("fields", {}).get("Expediente", [])]

def create_presupuesto(fields: dict):
    return create_record(T_PRESUPUESTOS, fields)

def update_presupuesto(record_id: str, fields: dict) -> bool:
    return update_record(T_PRESUPUESTOS, record_id, fields)

def delete_presupuesto(record_id: str) -> bool:
    return delete_record(T_PRESUPUESTOS, record_id)

def tiene_presupuesto_aceptado(expediente_id: str) -> bool:
    return any(
        p.get("fields", {}).get("Estado") == "Aceptado"
        for p in list_presupuestos(expediente_id)
    )

# ── Documentos ──────────────────────────────────────────────────────────────────

def list_documentos(expediente_id: str, etapa: str | None = None) -> list:
    todos = _all_records(T_DOCUMENTOS)
    docs = [d for d in todos if expediente_id in d.get("fields", {}).get("Expediente", [])]
    if etapa:
        docs = [d for d in docs if d.get("fields", {}).get("Etapa") == etapa]
    return docs

def create_documento(fields: dict):
    return create_record(T_DOCUMENTOS, fields)

def update_documento(record_id: str, fields: dict) -> bool:
    return update_record(T_DOCUMENTOS, record_id, fields)

def delete_documento(record_id: str) -> bool:
    return delete_record(T_DOCUMENTOS, record_id)

# ── Reservación efectiva (escribe en la tabla maestra Reservaciones) ─────────────

def create_reservacion(espacio_id: str, cliente_id: str, fecha_inicio: str,
                       fecha_fin: str, estado: str = "Confirmada", notas: str = ""):
    """Crea una reserva efectiva en la tabla maestra. Devuelve el registro o None."""
    fields = {
        "Espacio (Nuevo)": [espacio_id],
        "Cliente": [cliente_id],
        "Fecha_Inicio": fecha_inicio,
        "Fecha_Fin": fecha_fin,
        "Estado": estado,
    }
    if notas:
        fields["Notas"] = notas
    return create_record(T_RESERVACIONES, fields)
