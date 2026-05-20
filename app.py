import os
import streamlit as st
import requests
import time
from PIL import Image
from google import genai

st.set_page_config(page_title="Editor IA - Publimex", page_icon="🎨", layout="centered", initial_sidebar_state="collapsed")

# CSS responsivo para móvil
st.markdown("""
<style>
/* Botones más grandes en móvil */
@media (max-width: 768px) {
    .stButton > button {
        width: 100% !important;
        min-height: 3rem !important;
        font-size: 1.1rem !important;
    }
    .stDownloadButton > button {
        width: 100% !important;
        min-height: 3rem !important;
        font-size: 1.1rem !important;
    }
    /* Columnas apiladas en móvil */
    [data-testid="column"] {
        min-width: 100% !important;
    }
    /* Área de texto más alta */
    .stTextArea textarea {
        min-height: 100px !important;
    }
    /* Subir archivos más visible */
    [data-testid="stFileUploader"] {
        padding: 1rem 0 !important;
    }
    /* Título más pequeño en móvil */
    h1 {
        font-size: 1.5rem !important;
    }
}
/* Spinner centrado */
.stSpinner {
    text-align: center;
}
</style>
""", unsafe_allow_html=True)

# Cargar API Keys desde Streamlit Secrets (producción) o variables de entorno (local)
def get_secret(key):
    try:
        return st.secrets[key]
    except Exception:
        return os.environ.get(key, "")

DEFAULT_KREA_KEY = get_secret("KREA_API_KEY")
DEFAULT_GEMINI_KEY = get_secret("GEMINI_API_KEY")

if "krea_api_key" not in st.session_state:
    st.session_state.krea_api_key = DEFAULT_KREA_KEY
if "gemini_api_key" not in st.session_state:
    st.session_state.gemini_api_key = DEFAULT_GEMINI_KEY

st.title("🎨 Editor de Anuncios IA - Publimex")
st.markdown("Sube una foto del muro o espectacular, el logo de tu cliente y un prompt de lo que deseas.")

# Sidebar para la configuración
with st.sidebar:
    st.subheader("🍌 Modelo de Imagen")
    selected_model = st.selectbox(
        "Elige la versión de Nano Banana:",
        options=[
            "nano-banana",
            "nano-banana-2",
            "nano-banana-pro"
        ],
        format_func=lambda x: {
            "nano-banana": "Nano Banana (Rápido)",
            "nano-banana-2": "Nano Banana 2 (Calidad)",
            "nano-banana-pro": "Nano Banana Pro (Alta Fidelidad)"
        }.get(x, x),
        index=1
    )

    st.divider()
    st.markdown("""
    **💡 KREA AI:**
    Estamos utilizando los modelos de Google (Nano Banana) a través de la infraestructura de KREA para una integración perfecta.
    """)

col1, col2 = st.columns(2)

with col1:
    st.subheader("1. Imagen del Soporte")
    muro_file = st.file_uploader("Sube la foto del muro/espectacular", type=["jpg", "jpeg", "png"])
    if muro_file:
        muro_img = Image.open(muro_file)
        st.image(muro_img, caption="Muro / Espectacular", use_container_width=True)

with col2:
    st.subheader("2. Creatividad / Logo")
    logo_file = st.file_uploader("Sube el logo o creatividad", type=["jpg", "jpeg", "png"])
    if logo_file:
        logo_img = Image.open(logo_file)
        st.image(logo_img, caption="Logo", use_container_width=True)

st.subheader("3. Instrucciones de Edición")
user_prompt = st.text_area("¿Cómo quieres que se integre el anuncio?", placeholder="Ej. Pon el logo en el centro de la valla, con efecto de luz natural de tarde...", height=100)


def upload_asset(file_bytes, api_key):
    headers = {'Authorization': f'Bearer {api_key}'}
    files = {'file': ('image.jpg', file_bytes, 'image/jpeg')}
    res = requests.post('https://api.krea.ai/assets', headers=headers, files=files)
    if res.status_code != 200:
        raise Exception(f"Error al subir imagen a KREA: {res.text}")
    return res.json()['image_url']


if st.button("✨ Generar Imagen / Refinar", type="primary", use_container_width=True):
    if not st.session_state.krea_api_key:
        st.error("⚠️ Error de conexión con el servicio de generación de imágenes. Contacta al administrador.")
    elif not muro_file or not logo_file:
        st.error("⚠️ Debes subir ambas imágenes (el soporte y el logo).")
    elif not user_prompt:
        st.error("⚠️ Debes ingresar un prompt o instrucción.")
    else:
        with st.spinner(f"Procesando las imágenes y enviando a KREA con {selected_model}..."):
            try:
                # Paso 1: Refinamiento del Prompt (si hay llave de Gemini)
                refined_prompt = user_prompt
                if st.session_state.gemini_api_key:
                    st.info("🧠 Refinando el prompt con Gemini...")
                    client = genai.Client(api_key=st.session_state.gemini_api_key)
                    system_prompt = f"""Actúa como un diseñador gráfico experto y un Prompt Engineer de primer nivel.
El usuario quiere crear una imagen donde se integre un logo sobre un muro o valla publicitaria.
El usuario dio esta instrucción básica: "{user_prompt}"

Tu trabajo es expandir y mejorar esta instrucción para que sea un prompt de generación de imagen perfecto para un modelo difusor.
REGLA CRÍTICA ABSOLUTA 1: Debes intuir siempre que cuando se hable de un edificio, valla, o muro, la edición se hará EXCLUSIVAMENTE sobre el espacio publicitario vacío o reemplazando un anuncio existente. EN NINGÚN CASO se trata de cubrir un edificio entero de publicidad.
REGLA CRÍTICA ABSOLUTA 2: Debes ser ESTRICTAMENTE FIEL a la creatividad o logotipo proporcionado. ESTÁ PROHIBIDO inventar elementos, cambiar colores, tipografías o añadir textos creativos al anuncio original. Limítate a adaptar la perspectiva, luces y sombras, respetando la imagen original al 100%.

El prompt debe describir cómo integrar el logo de forma realista sobre el espacio asignado en el muro, ajustando la perspectiva, las sombras, y la iluminación para que parezca una integración real, no un pegado. No incluyas texto de relleno, solo devuelve el prompt mejorado en un solo párrafo."""

                    try:
                        response_prompt = client.models.generate_content(
                            model="gemini-2.5-flash",
                            contents=system_prompt
                        )
                    except Exception:
                        response_prompt = client.models.generate_content(
                            model="gemini-1.5-flash",
                            contents=system_prompt
                        )
                    refined_prompt = response_prompt.text.strip()
                    st.success("✨ Prompt Refinado Exitosamente")
                    st.info(f"**Prompt Mejorado:** {refined_prompt}")
                else:
                    st.info("ℹ️ El prompt se enviará a KREA sin refinamiento previo.")

                # Paso 2: Subir las imágenes a KREA
                st.info("Subiendo imágenes a KREA...")
                muro_file.seek(0)
                logo_file.seek(0)
                muro_url = upload_asset(muro_file.getvalue(), st.session_state.krea_api_key)
                logo_url = upload_asset(logo_file.getvalue(), st.session_state.krea_api_key)

                # Paso 3: Construir el Prompt Final
                prompt_vision = f"""Actúa como un diseñador gráfico experto.
La primera imagen que recibes es el muro/espectacular de referencia. La segunda imagen es el logo/creatividad a integrar.

REGLA CRÍTICA ABSOLUTA 1: La publicidad DEBE colocarse ÚNICAMENTE en el espacio publicitario vacío de la valla, cartel o marco disponible. ESTÁ PROHIBIDO cubrir todo el edificio o arquitectura con la publicidad.
REGLA CRÍTICA ABSOLUTA 2: Sé ESTRICTAMENTE FIEL a la creatividad original. NO inventes textos, gráficos ni cambies el diseño del logotipo o arte proporcionado.

Integra el logo de forma realista sobre el espacio publicitario del muro, ajustando la perspectiva, las sombras, y la iluminación para que parezca una integración real, no un pegado.
Instrucción a seguir: {refined_prompt}"""

                st.success("✨ Imágenes subidas. Iniciando generación...")

                # Paso 4: Llamar al endpoint de generación de KREA
                headers = {
                    'Authorization': f'Bearer {st.session_state.krea_api_key}',
                    'Content-Type': 'application/json'
                }
                data = {
                    'prompt': prompt_vision,
                    'imageUrls': [muro_url, logo_url]
                }

                endpoint = f"https://api.krea.ai/generate/image/google/{selected_model}"
                res = requests.post(endpoint, headers=headers, json=data)

                if res.status_code != 200:
                    raise Exception(f"Error al iniciar generación: {res.text}")

                job_id = res.json().get('job_id')
                if not job_id:
                    raise Exception("No se recibió un job_id válido.")

                # Paso 5: Polling del estado
                job_url = f"https://api.krea.ai/jobs/{job_id}"
                st.info("Generando imagen... (esto puede tomar unos segundos)")

                progress_bar = st.progress(0)
                status_text = st.empty()

                completed = False
                for i in range(60):
                    job_res = requests.get(job_url, headers=headers)
                    if job_res.status_code != 200:
                        raise Exception(f"Error al consultar estado: {job_res.text}")

                    job_data = job_res.json()
                    status = job_data.get('status')

                    if status == 'completed':
                        result_urls = job_data.get('result', {}).get('urls', [])
                        if result_urls:
                            st.success("✨ ¡Generación completada!")
                            st.image(result_urls[0], caption=f"Imagen generada por {selected_model}", use_container_width=True)

                            try:
                                img_response = requests.get(result_urls[0])
                                if img_response.status_code == 200:
                                    st.download_button(
                                        label="⬇️ Descargar Imagen",
                                        data=img_response.content,
                                        file_name="anuncio_publimex.png",
                                        mime="image/png",
                                        type="primary",
                                        use_container_width=True
                                    )
                            except Exception:
                                st.warning("No se pudo crear el botón de descarga. Puedes guardar la imagen con click derecho.")
                        else:
                            st.warning("El modelo completó el trabajo pero no devolvió ninguna URL.")
                        completed = True
                        break
                    elif status in ['failed', 'cancelled']:
                        st.error(f"❌ La generación falló o fue cancelada por KREA. Estado: {status}")
                        completed = True
                        break

                    status_text.text(f"Estado: {status}...")
                    progress_bar.progress(min((i + 1) * 2, 99))
                    time.sleep(2)

                if not completed:
                    st.warning("⚠️ Tiempo de espera agotado consultando a KREA.")

            except Exception as e:
                st.error(f"⚠️ **Ocurrió un error:** {e}")

st.divider()
st.markdown("### ✨ Mejorar con un clic")
st.markdown("¿El resultado no es perfecto? Pide ajustes a la IA:")
col_adj1, col_adj2 = st.columns([3, 1])
with col_adj1:
    adjustment = st.text_input("Ajuste adicional:", placeholder="Ej. Mantén la posición pero ajusta mejor las sombras", label_visibility="collapsed")
with col_adj2:
    if st.button("Ajustar Resultado", use_container_width=True):
        st.info("🔧 Esta función tomará la imagen anterior y el nuevo prompt para perfeccionar el resultado.")
