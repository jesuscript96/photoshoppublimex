# PRD — Módulo de Proceso de Ventas (Fase 1)

**Producto:** Publimex Hub · **Versión:** 1.0 · **Fecha:** 2026-06-16
**Fuentes:** borrador de PRD interno + transcripción de sesión de descubrimiento con Sandra (vendedora) y dirección.

---

## 0. Contexto: de dónde venimos y a dónde vamos

**Estado actual de la app.** Ya existe un esqueleto del proceso de venta (módulo *Procesos de Venta*):
una entidad **Expediente** con etapas `Solicitud → Presupuesto → Contratación → Producción → Cierre`,
tablas en Airtable (`Expedientes`, `Presupuestos`, `Documentos`), un repositorio de documentos por etapa
(metadatos + enlace, subida real a Drive pendiente), un hito "Generar reserva efectiva" y vistas tipo
dashboard. Sirve como **repositorio de archivos que sigue el proceso de venta por fases**.

**Hacia dónde debe ir (insight central del video).** El valor real no es "orden general", sino
**seguimiento**:

> "creo que tiene más que ver con seguimiento tanto de vosotros hacia los vendedores como de los
> vendedores en los propios procesos."

Dos motores concretos:
1. **Dirección → vendedores:** que el hermano/dirección pueda entrar y ver el seguimiento de cualquier
   cliente sin perseguir al vendedor ("¿qué pasó con ese cliente? ¿lo ibas a contactar hace dos semanas?").
2. **Institucionalización / descarga de información:** cuando un vendedor se va, hoy se pierde todo
   ("luego se van los vendedores y es como ¿y con quién chingado trataba?"). Hay que **descargar** en la
   plataforma: con quién se trata, qué se pidió, qué se propuso, cómo evolucionó.

**Criterio de éxito que condiciona todo el diseño — adopción voluntaria:**

> "la app tiene que ser bastante guay como para que la usen por su cuenta. […] si luego es un Cristo ir
> detrás de los vendedores para que utilicen la app, ya sería el colmo, no se gana nada."

---

## 1. Objetivos del sistema

1. **Seguimiento comercial activo.** Que dirección e interesados consulten el avance exacto de cada
   negociación sin preguntar al vendedor.
2. **Institucionalización de datos.** Que contactos, marcas y agencias queden registrados de forma
   estructurada y persistan aunque rote el equipo.
3. **Onboarding fiscal eficiente.** Facilitar la recopilación de documentos para facturación y alta del
   cliente en la etapa de cierre.
4. **Adopción del vendedor.** Interfaces intuitivas, de baja fricción, que el equipo use por iniciativa
   propia. Evitar sensación de "doble trabajo administrativo".

---

## 2. Principios de diseño (transversales, extraídos del video)

- **Cada etapa = descarga de información, no formulario.** La sensación de "rellenar un formulario" frena
  la adopción. Vista base de resumen/seguimiento; capturar datos de forma progresiva.
- **Separar "qué pide el cliente" de "qué le propongo".** Solicitud y Presupuesto deben ir **separados**
  (decisión explícita de Sandra), aunque se barajó unirlos.
- **Las cantidades reales viven en Contratación, no en Presupuesto.** En presupuesto "uno manda su carta a
  Santa Claus"; en contratación "a ver qué te cerraron". No pedir IVA ni desglose fino en la propuesta.
- **Los nombres/etiquetas importan.** Evitar nombres genéricos ("subir documentos"); usar subtítulos
  claros ("sube la propuesta que enviaste para vender") entendibles por cualquiera que consulte.
- **No sobre-modelar todavía.** Por ahora cada paso es un repositorio de archivos que sigue el proceso;
  los subpasos finos llegan después.
- **Drive solo para lo contratado.** Evitar saturar el Drive compartido con propuestas preliminares.

---

## 3. Personas

| Persona | Necesidad principal |
|---|---|
| **Vendedor/a** (Sandra) | Registrar rápido cliente, contactos, propuestas y avances; sin fricción. |
| **Dirección** (hermano) | Entrar y ver el estado/seguimiento de cualquier cliente sin preguntar. |
| **Administración/Finanzas** | Recopilar expediente fiscal y datos de cierre para facturar y dar de alta. |

---

## 4. Módulo 1 — Solicitud (información inicial del cliente)

**Propósito:** recabar la información del cliente, sus necesidades y los contactos clave **antes** de emitir
propuesta formal. Es una **descarga de información del cliente**, sin importes.

### 4.1 Identificación del cliente
- **Agencia / Medio** (input + catálogo): el intermediario con el que se trata (ej. *GroupM*).
  *Insight:* muchas veces no se trata con la marca sino con la agencia de medios.
- **Marca** (input + catálogo): la marca final que se anunciará (ej. *Paramount*).

> "a veces Paramount no lo llevamos con Paramount, lo llevamos con la agencia de medios que se llama GroupM
> […] señalizar cuál es el cliente, pero abajo ponerle la marca."

### 4.2 Contactos (soporte multi-contacto)
- Permitir **añadir varios contactos** bajo una misma solicitud (botón "añadir contacto").
- Campos por contacto: **Nombre, Teléfono, Correo, Puesto**.
- **Rol del contacto** (dropdown): *Contacto directo*, *Director / Jefe*, *Operativo*.
  *Insight:* saber a quién escalar cuando se discuten precios/costos ("ya sé quién es su jefe y le digo a
  Gibrán o a mi hermano: ayúdenme a hablar con tal").

### 4.3 Detalle del requerimiento
- **Tipo de producto solicitado** (multi-select / checkbox): *Muro, Espectacular, Autobús, Pantalla, Valla…*
  ("¿qué te están pidiendo? un muro, espectaculares, autobuses…").
- **Plaza / Ciudades de interés** (multi-select): *CDMX, Guadalajara, Monterrey, Toluca…* (varias a la vez).
- **Periodo de interés / Duración** (estimada): ej. *1 mes, 1 año*.
- **Fecha de inicio estimada:** cuándo quiere arrancar el cliente, **independiente** de cuándo empieza la
  negociación. *Insight:* "le interesa en agosto, lo platicamos desde junio".

### 4.4 Estado de la solicitud (progreso de negociación)
- **Fase** (dropdown): *Negociación, Inicio, En Pausa, Propuesta Enviada*.
  *Nota:* es la fase **de negociación**, distinta del "estado" ganado/perdido del expediente.
- **Comentarios abiertos** (texto libre): notas rápidas de estatus ("se le pasó la propuesta", "a dos de
  cerrar").

> Solicitud debe quedar como "literalmente la información que te pidió, la info del cliente, mail, todo eso,
> qué te está pidiendo, para cuándo, para dónde y qué le interesa".

---

## 5. Módulo 2 — Presupuesto (propuestas y avance comercial)

**Propósito:** el proceso **activo** de venta y el **registro histórico** de los intentos de cierre.
**Separado** de Solicitud. Aquí NO van importes detallados ni IVA.

### 5.1 Carga de documentos de venta
- Subir los archivos que sirvieron como **propuesta comercial**: PDFs de disponibilidad (fichas técnicas de
  sitios), **Excels de cotizaciones**, **PowerPoints**, etc.
- **Descripción del documento** (texto breve): qué se envió y por qué.
  Ej.: *"Propuesta enviada con base en un presupuesto de 1 millón de pesos."*
- **Etiqueta clara** (no "subir documentos"): p. ej. *"Sube la propuesta / lo que enviaste para vender."*

### 5.2 Historial de seguimiento (log de avances) — **núcleo del seguimiento**
- Bitácora **secuencial** de interacciones con el cliente. Por entrada: **Fecha** + **Resumen**.
- Ejemplos reales:
  - "5 de enero: primer contacto."
  - "7 de febrero: seguimiento; el cliente comenta que el presupuesto no le alcanza y pide ajuste."
  - "Tercer acercamiento: medio convencido, pide que me ajuste." … "se logró la contratación en abril."
- Permite ver **la evolución del cliente y del esfuerzo del vendedor** (los cierres no son rápidos).

### 5.3 Presupuesto estimado inicial
- Un **monto orientativo** con el que el cliente inicia ("traen 1 millón" / "traen 5 pesos").
- **Solo señalización**, sin desglose ni IVA. *Insight:* el detalle/real se captura en Contratación.

> Implicación sobre la app actual: la tabla `Presupuestos` hoy pide Subtotal/IVA/Total; según este insight
> el desglose fino **se mueve a Contratación** y aquí basta un importe inicial + documentos + log.

---

## 6. Módulo 3 — Contratación (cierre, documentación y onboarding fiscal)

**Propósito:** formalizar la venta y recopilar la documentación legal/fiscal. Aquí sí van **las cantidades
reales cerradas** ("me cerraron 3 y medio de los 5").

### 6.1 Estructura por campañas y temporalidad
- Asociar **múltiples campañas** a un mismo cliente/agencia (una agencia lleva muchas marcas).
- Estructurar por **Campaña** (ej. *Campaña Paramount*) y **subdividir por meses** contratados.
  Ej.: "esta agencia me cerró para enero, Paramount; me cerró 3 meses".

### 6.2 Documentación de la transacción
- **Orden de compra inicial** y **orden de compra final** (documentos que formalizan el cierre).
- **Constancia** adicional que ellos suelen enviar (a confirmar el nombre exacto con Sandra).
- **Factura mensual:** carga de la factura correspondiente a **cada mes** de campaña.

### 6.3 Conciliación de inventario y precios
- Carga de un **Excel/PDF** con el desglose **final** de los sitios contratados y los **precios reales
  acordados**, contemplando **descuentos** sobre la tarifa del inventario general (no el precio de catálogo).

### 6.4 Expediente legal del cliente (checklist de alta fiscal)
Carga (obligatoria/sugerida) de documentos para facturación y alta:
- Acta Constitutiva
- Constancia de Situación Fiscal (CSF)
- Datos bancarios (estado de cuenta para validar CLABE)
- Poder Notarial
- Comprobante de domicilio
- Identificación oficial (INE) del apoderado legal

> Presentar como **checklist** (qué falta / qué está) para el onboarding fiscal.

---

## 7. Producción (fuera de alcance — Fase 1)

El último paso es "más interno"; se diseñará **en paralelo/después**. Out of scope de esta fase. Se
abordará tras cerrar Solicitud/Presupuesto/Contratación.

---

## 8. Requerimientos técnicos y de integración

### 8.1 Integración con Google Drive (regla de negocio)
- **Solo los documentos finales de Contratación** (contrato firmado, orden de compra, expediente fiscal) se
  **sincronizan automáticamente** a las carpetas compartidas de Google Drive.
- **Solicitud y Presupuesto** mantienen sus documentos **internos/temporales** en la app (evitar saturar el
  Drive con propuestas preliminares o versiones descartadas).

> "en el Drive ya nada más cierra lo que se contrató; no todo este proceso."

### 8.2 Almacenamiento
- Etapas tempranas: metadatos + archivo en almacenamiento interno de la app (hoy: enlace; a futuro subida
  directa).
- Etapa de Contratación (finales): subida + sincronización a Drive.

### 8.3 UX / UI
- Captura de datos numéricos limpia y fácil.
- **Disclosure progresivo** de campos requeridos para evitar sensación de doble trabajo.
- Etiquetas y subtítulos claros (renombrar el repositorio de documentos; "disponibilidad junio" > nombre
  genérico).

---

## 9. Impacto en el modelo de datos actual (deltas)

> Decisión vigente: las entidades del proceso viven en **Airtable** (base `appW4QjUOV9nXQkx9`). Multi-contacto
> y multi-campaña requieren **tablas hijas** enlazadas.

| Área | Hoy | Cambio requerido |
|---|---|---|
| **Cliente** | `Expedientes.Cliente` + `Cliente_Prospecto` | Separar en **Agencia/Medio** y **Marca** (ambos input+catálogo). |
| **Contactos** | No hay contactos en el expediente | Nueva tabla **Contactos de expediente** (multi): Nombre, Teléfono, Correo, Puesto, **Rol**. |
| **Requerimiento** | — | **Tipo de producto** (multi), **Ciudades de interés** (multi), **Duración/Periodo de interés**. |
| **Fase negociación** | `Etapa` + `Estado` (Abierto/Ganado/…) | Añadir **Fase de Solicitud** (Negociación/Inicio/En Pausa/Propuesta Enviada) + **comentarios**. |
| **Presupuesto** | `Subtotal/IVA/Total`, `Folio`, `Version`… | Simplificar a **importe inicial** + documentos + **descripción**; mover desglose/real a Contratación. |
| **Log de seguimiento** | No existe | Nueva tabla **Avances/Bitácora** (multi): Fecha + Resumen, ligada al expediente. |
| **Campañas** | No existe | Nueva tabla **Campañas** (por cliente/agencia) → subdividida por **Meses** contratados. |
| **Docs transacción** | `Documentos` por etapa (genérico) | Tipos específicos en Contratación: OC inicial/final, **factura mensual**, conciliación. |
| **Expediente fiscal** | Tipos sueltos | **Checklist** estructurado (6 documentos de alta). |
| **Drive** | Pendiente (enlace manual) | Sync automática **solo** de finales de Contratación. |

---

## 10. Fases de entrega sugeridas

1. **Solicitud (rediseño):** Agencia/Marca, multi-contacto con rol, tipo de producto, ciudades, duración,
   fecha inicio estimada, fase de negociación, comentarios. (Mayor impacto en "descarga de información".)
2. **Presupuesto:** documentos con descripción + **log de avances** + importe inicial. (Mayor impacto en
   "seguimiento".)
3. **Contratación:** campañas × meses, docs de transacción, conciliación de precios, checklist fiscal,
   sync a Drive de finales.
4. **Producción:** fase posterior (a definir).

> La implementación puede empezar de forma incremental tras feedback; producción va en paralelo después.

---

## 11. Decisiones tomadas y preguntas abiertas

**Decisiones (del video):**
- Solicitud y Presupuesto **separados** (no se fusionan).
- Importes detallados/IVA **no** en Presupuesto; sí en Contratación.
- Drive **solo** para finales de Contratación.
- Producción fuera de alcance de esta fase.

**Preguntas abiertas a confirmar con Sandra:**
- Nombre exacto de la "constancia" adicional que el cliente envía en Contratación.
- Catálogos de **Tipo de producto** y **Ciudades/Plazas** definitivos.
- ¿Agencia y Marca son catálogos gestionados (con alta) o texto libre + sugerencias?
- ¿El "importe inicial" del presupuesto es único o puede haber varios por iteración de propuesta?
- ¿Qué documentos del expediente fiscal son **obligatorios** vs **sugeridos** para poder cerrar?

---

## Anexo — Insights clave del video (trazabilidad)

- **Propósito real = seguimiento + descarga de información**, no orden general.
- **Adopción voluntaria** como criterio de éxito ("que la usen por su cuenta").
- **Agencia vs Marca**: se trata con la agencia de medios, registrar ambas.
- **Multi-contacto con rol** (directo/jefe/operativo) para saber a quién escalar.
- **Qué pide + ciudades + duración + fecha de inicio estimada** en Solicitud.
- **Fase de negociación** con comentarios abiertos.
- **Presupuesto separado**: documentos de propuesta + **descripción** + **log de avances** + importe inicial;
  sin IVA/desglose.
- **Contratación**: cantidades reales cerradas, **campañas × meses**, OC inicial/final, factura mensual,
  **conciliación de precios reales con descuentos**, **expediente fiscal** (acta, CSF, datos bancarios,
  poder notarial, comprobante de domicilio, INE del apoderado).
- **Drive solo para lo contratado**; etapas previas internas.
- **Etiquetas claras**; no sobre-modelar; repositorio por fases de momento.
