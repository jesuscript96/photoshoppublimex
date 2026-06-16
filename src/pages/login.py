import streamlit as st
import base64
import os
from src.supabase_client import supabase_login, supabase_signup, is_supabase_configured

def show_login():
    # Custom CSS to style the login page and merge components into a 3D billboard
    st.markdown("""
        <style>
        /* Centered column styling override */
        div[data-testid="column"] {
            overflow: visible !important;
        }

        /* Ensure page background remains clean white */
        .stApp {
            background-color: #ffffff !important;
        }

        /* Tab container styling inside outer frame (no border) */
        div[data-testid="stTabs"] {
            background-color: transparent !important;
            border: none !important;
            padding: 10px 15px 0 15px !important;
            margin: 0 !important;
            box-shadow: none !important;
            position: relative;
            z-index: 5;
            overflow: visible !important;
        }

        /* Disable stTabs before pseudo-element (moved spotlights to outer wrapper) */
        div[data-testid="stTabs"]::before {
            display: none !important;
        }

        /* Tab buttons styling for light white background readability */
        button[data-baseweb="tab"] {
            color: #64748b !important;
            font-weight: 700 !important;
            background: transparent !important;
            border: none !important;
            padding: 8px 16px !important;
            font-size: 0.98rem !important;
            transition: all 0.2s ease !important;
        }

        button[data-baseweb="tab"]:hover {
            color: #0f172a !important;
        }

        button[data-baseweb="tab"][aria-selected="true"] {
            color: #E60000 !important;
            border-bottom: 3px solid #E60000 !important;
        }

        /* Inject red icon into first tab (Login) */
        button[data-baseweb="tab"]:nth-of-type(1)::before {
            content: '';
            display: inline-block;
            width: 15px;
            height: 15px;
            margin-right: 6px;
            background-image: url('data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="%23E60000" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M15 3h4a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-4"/><polyline points="10 17 15 12 10 7"/><line x1="15" y1="12" x2="3" y2="12"/></svg>');
            background-size: contain;
            background-repeat: no-repeat;
            vertical-align: -2px;
        }

        /* Inject red icon into second tab (Register) */
        button[data-baseweb="tab"]:nth-of-type(2)::before {
            content: '';
            display: inline-block;
            width: 15px;
            height: 15px;
            margin-right: 6px;
            background-image: url('data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="%23E60000" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><line x1="19" y1="8" x2="19" y2="14"/><line x1="22" y1="11" x2="16" y2="11"/></svg>');
            background-size: contain;
            background-repeat: no-repeat;
            vertical-align: -2px;
        }

        /* Form container inside outer frame (no border) */
        div[data-testid="stForm"] {
            background-color: transparent !important;
            background-image: none !important;
            border: none !important;
            box-shadow: none !important;
            padding: 15px 25px 25px 25px !important;
            margin: 0 !important;
            position: relative;
            z-index: 4;
        }

        /* Disable form catwalk to avoid duplication */
        div[data-testid="stForm"]::after {
            display: none !important;
        }

        /* Outer container styled as billboard frame */
        div[data-testid="stVerticalBlockBorderWrapper"] {
            max-width: 364px !important;
            margin: 0 auto !important;
            /* 3D metallic/charcoal billboard border effect */
            border-top: 12px solid #3b444b !important;
            border-left: 12px solid #2c3539 !important;
            border-right: 12px solid #2c3539 !important;
            border-bottom: 12px solid #1c2429 !important;
            border-radius: 14px !important;
            background-color: #ffffff !important;
            /* Combine multiple radial gradients to simulate illuminated canvas at the top of the outer block (scaled positions) */
            background-image: 
                radial-gradient(circle at 54px 0px, rgba(245, 158, 11, 0.12) 0%, rgba(255, 255, 255, 0) 154px),
                radial-gradient(circle at 182px 0px, rgba(245, 158, 11, 0.12) 0%, rgba(255, 255, 255, 0) 154px),
                radial-gradient(circle at 310px 0px, rgba(245, 158, 11, 0.12) 0%, rgba(255, 255, 255, 0) 154px) !important;
            background-repeat: no-repeat !important;
            /* Strong multi-layered shadow to pop on white background */
            box-shadow: 
                0 0 0 1px #444444, /* outer bevel highlight */
                0 25px 50px -12px rgba(0, 0, 0, 0.18),
                0 10px 20px -5px rgba(0, 0, 0, 0.08),
                inset 0 0 0 2px #333333, /* inner bevel shadow */
                inset 0 2px 10px rgba(0, 0, 0, 0.03) !important;
            position: relative;
            z-index: 4;
            padding: 0px !important;
            overflow: visible !important;
        }

        /* Eliminate vertical gap between tabs and forms inside the border wrapper */
        div[data-testid="stVerticalBlockBorderWrapper"] > div[data-testid="stVerticalBlock"] {
            gap: 0px !important;
        }

        /* Billboard spotlights on the outer container border wrapper (scaled to 70% width) */
        div[data-testid="stVerticalBlockBorderWrapper"]::before {
            content: '';
            position: absolute;
            top: -24px;
            left: 54px;
            width: 14px;
            height: 14px;
            background: #222222;
            border-radius: 50% 50% 0 0;
            border: 2px solid #444444;
            box-shadow: 
                /* Lamp 1 glow on white canvas below */
                0 12px 35px 10px rgba(245, 158, 11, 0.22),
                /* Lamp 2 (middle) fixture + beam */
                128px 0 0 -2px #222222,
                128px 0 0 0 #444444,
                128px 12px 35px 10px rgba(245, 158, 11, 0.22),
                /* Lamp 3 (right) fixture + beam */
                256px 0 0 -2px #222222,
                256px 0 0 0 #444444,
                256px 12px 35px 10px rgba(245, 158, 11, 0.22);
            z-index: 10;
        }

        /* Billboard bottom catwalk platform (attaches to the outer frame) */
        div[data-testid="stVerticalBlockBorderWrapper"]::after {
            content: '';
            position: absolute;
            bottom: -6px;
            left: -12px;
            right: -12px;
            height: 8px;
            background: linear-gradient(180deg, #334155 0%, #0f172a 100%);
            border-radius: 2px;
            box-shadow: 
                0 4px 8px rgba(0, 0, 0, 0.35),
                inset 0 1px 2px rgba(255, 255, 255, 0.25);
            z-index: 6;
        }

        /* Form input fields */
        div[data-testid="stForm"] input {
            background-color: #fcfcfc !important;
            border: 1px solid #e2e8f0 !important;
            border-radius: 6px !important;
            color: #0f172a !important;
            padding: 10px 14px !important;
            font-size: 0.95rem !important;
        }

        div[data-testid="stForm"] input:focus {
            border-color: #E60000 !important;
            box-shadow: 0 0 0 3px rgba(230, 0, 0, 0.15) !important;
        }

        /* Select box styles inside form */
        div[data-testid="stForm"] div[data-baseweb="select"] {
            border-radius: 6px !important;
        }

        /* Billboard structural legs and ground base (scaled for 364px width) */
        .billboard-structure {
            max-width: 364px;
            margin: -5px auto 40px auto; /* slight overlap with outer container bottom border */
            position: relative;
            height: 140px;
            text-align: center;
            overflow: visible;
        }

        .billboard-legs-container {
            position: relative;
            width: 100%;
            height: 100px;
        }

        .billboard-leg {
            position: absolute;
            top: 0;
            width: 26px;
            height: 90px;
            /* Textured metal steel look with vertical reflection */
            background: linear-gradient(90deg, #1e293b 0%, #475569 35%, #64748b 50%, #334155 65%, #0f172a 100%);
            box-shadow: 
                inset 0 0 8px rgba(0,0,0,0.6),
                5px 10px 20px rgba(0, 0, 0, 0.12);
        }

        .billboard-leg.left {
            left: 77px;
        }

        .billboard-leg.right {
            right: 77px;
        }

        /* Crossbeam support structure (realigned for 364px) */
        .billboard-legs-container::before {
            content: '';
            position: absolute;
            top: 25px;
            left: 80px;
            right: 80px;
            height: 6px;
            background: linear-gradient(180deg, #334155 0%, #1e293b 100%);
            box-shadow: 0 4px 8px rgba(0,0,0,0.08);
        }

        .billboard-legs-container::after {
            content: '';
            position: absolute;
            top: 55px;
            left: 80px;
            right: 80px;
            height: 6px;
            background: linear-gradient(180deg, #334155 0%, #1e293b 100%);
            box-shadow: 0 4px 8px rgba(0,0,0,0.08);
        }

        .billboard-base-stand {
            position: absolute;
            bottom: 6px;
            left: 63px;
            right: 63px;
            height: 12px;
            background: linear-gradient(180deg, #475569 0%, #1e293b 100%);
            border-radius: 3px;
            box-shadow: 0 4px 10px rgba(0, 0, 0, 0.1);
            z-index: 2;
        }

        .billboard-concrete {
            position: absolute;
            bottom: -6px;
            left: 49px;
            right: 49px;
            height: 14px;
            background: linear-gradient(180deg, #cbd5e1 0%, #94a3b8 100%);
            border-radius: 4px;
            border-bottom: 3px solid #64748b;
            box-shadow: 0 8px 16px rgba(0, 0, 0, 0.05);
            z-index: 3;
        }

        .billboard-tagline {
            margin-top: 15px;
            font-size: 0.8rem;
            letter-spacing: 2px;
            font-weight: 700;
            color: #64748b;
            text-transform: uppercase;
        }
        </style>
    """, unsafe_allow_html=True)

    # Load corporate logo
    logo_base64 = ""
    if os.path.exists("logo.png"):
        try:
            with open("logo.png", "rb") as f:
                logo_base64 = base64.b64encode(f.read()).decode("utf-8")
        except Exception:
            pass

    # Centered structure for billboard
    col_l, col_c, col_r = st.columns([1, 4, 1])
    
    with col_c:
        if logo_base64:
            st.markdown(f"""
                <div style="text-align: center; margin-top: 20px; margin-bottom: 25px;">
                    <img src="data:image/png;base64,{logo_base64}" style="max-width: 280px; height: auto;" />
                    <div style="font-size: 1.05rem; color: #475569; margin-top: 12px; font-weight: 600; letter-spacing: 0.5px;">
                        Suite de Herramientas de Publicidad Exterior
                    </div>
                </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("""
                <div style="text-align: center; margin-top: 20px; margin-bottom: 25px;">
                    <div style="font-size: 2.2rem; font-weight: 800; letter-spacing: -1px; color: #111111; margin-bottom: 5px;">
                        PUBLIMEX<span style="color: #E60000;">HUB</span>
                    </div>
                    <div style="font-size: 0.95rem; color: #666666; margin-bottom: 30px;">
                        Suite de Herramientas de Publicidad Exterior
                    </div>
                </div>
            """, unsafe_allow_html=True)

        
        if not is_supabase_configured():
            st.warning("**Configuración Pendiente:** Asegúrate de agregar las credenciales `SUPABASE_URL` y `SUPABASE_KEY` en tu archivo `.streamlit/secrets.toml` para poder iniciar sesión.", icon=":material/warning:")
            return

        # Wrapper container for the entire billboard panel
        with st.container(border=True):
            # Toggle tabs for login or signup
            tab_login, tab_signup = st.tabs(["Iniciar Sesión", "Registrarse"])
            
            with tab_login:
                with st.form("login_form"):
                    email = st.text_input("Correo electrónico", placeholder="correo@publimex.com")
                    password = st.text_input("Contraseña", type="password", placeholder="••••••••")
                    
                    st.write("")
                    submit_btn = st.form_submit_button("Entrar", type="primary", use_container_width=True)
                    
                    if submit_btn:
                        if not email or not password:
                            st.error("Por favor completa todos los campos.")
                        else:
                            with st.spinner("Autenticando..."):
                                res = supabase_login(email, password)
                                if res["success"]:
                                    if email.lower() == "jvalenzuela.chulia@gmail.com":
                                        res["role"] = "administrador"
                                    st.session_state.authenticated = True
                                    st.session_state.user_token = res["access_token"]
                                    st.session_state.user_id = res["user_id"]
                                    st.session_state.user_email = res["email"]
                                    st.session_state.user_name = res["name"]
                                    st.session_state.user_role = res["role"]
                                    st.success("¡Inicio de sesión exitoso!")
                                    st.rerun()
                                elif res.get("conn_error"):
                                    st.warning(res["error"], icon=":material/cloud_off:")
                                else:
                                    st.error(f"Error de inicio de sesión: {res['error']}")
                                    
            with tab_signup:
                with st.form("signup_form"):
                    new_name = st.text_input("Nombre completo", placeholder="Juan Pérez")
                    new_email = st.text_input("Correo electrónico", placeholder="correo@publimex.com")
                    new_password = st.text_input("Nueva contraseña", type="password", placeholder="Mínimo 6 caracteres")
                    
                    new_role_display = st.selectbox("Rol / Puesto", ["Usuario", "Admin"], index=0)
                    new_role = "vendedor" if new_role_display == "Usuario" else "administrador"
                    
                    st.write("")
                    signup_btn = st.form_submit_button("Crear Cuenta", type="primary", use_container_width=True)
                    
                    if signup_btn:
                        if not new_name or not new_email or not new_password:
                            st.error("Por favor completa todos los campos obligatorios.")
                        elif len(new_password) < 6:
                            st.error("La contraseña debe tener al menos 6 caracteres.")
                        else:
                            with st.spinner("Registrando usuario..."):
                                res = supabase_signup(new_email, new_password, new_name, new_role)
                                if res["success"]:
                                    st.success("¡Registro completado! Ya puedes iniciar sesión con tus credenciales.")
                                elif res.get("conn_error"):
                                    st.warning(res["error"], icon=":material/cloud_off:")
                                else:
                                    st.error(f"Error al registrar: {res['error']}")

        # Render the billboard legs, crossbeams, base, and concrete foundation below the active form
        st.markdown("""
            <div class="billboard-structure">
                <div class="billboard-legs-container">
                    <div class="billboard-leg left"></div>
                    <div class="billboard-leg right"></div>
                    <div class="billboard-base-stand"></div>
                    <div class="billboard-concrete"></div>
                </div>
                <div class="billboard-tagline">PUBLIMEX • PUBLICIDAD EXTERIOR</div>
            </div>
        """, unsafe_allow_html=True)

