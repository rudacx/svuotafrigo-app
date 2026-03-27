import streamlit as st
import stripe
from groq import Groq
from supabase import create_client
from fpdf import FPDF
import re
import io

# --- 1. CONFIGURAZIONE E DESIGN "ULTIMATE DARK" ---
st.set_page_config(page_title="Svuotafrigo AI PRO", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;600;800&display=swap');
    
    * { font-family: 'Plus Jakarta Sans', sans-serif; }
    .stApp { background-color: #08090b; }

    /* Card Ricetta */
    .recipe-card {
        background: linear-gradient(145deg, #111318, #161920);
        border: 1px solid #2d3139;
        border-radius: 28px;
        padding: 45px;
        margin: 25px 0;
        box-shadow: 0 25px 50px rgba(0,0,0,0.5);
        color: #e6edf3;
    }
    
    .recipe-card h2 { 
        color: #ff4b4b; 
        font-size: 2.2rem; 
        font-weight: 800; 
        letter-spacing: -1.5px;
        margin-bottom: 25px;
    }

    /* Input e Textarea */
    .stTextArea textarea, .stTextInput input {
        background: #111318 !important;
        border: 1px solid #2d3139 !important;
        border-radius: 15px !important;
        color: white !important;
    }

    /* Bottoni */
    div.stButton > button {
        background: #ff4b4b !important;
        color: white !important;
        border: none !important;
        padding: 15px !important;
        border-radius: 15px !important;
        font-weight: 800 !important;
        width: 100% !important;
        transition: 0.3s;
    }
    div.stButton > button:hover { transform: scale(1.02); }

    /* Box Errore/Login */
    .lock-box {
        background: #111318;
        border: 2px dashed #2d3139;
        border-radius: 20px;
        padding: 40px;
        text-align: center;
    }
    </style>
""", unsafe_allow_html=True)

# API SETUP
URL = "https://ixkrnsarskqgwwuudqms.supabase.co"
KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Iml4a3Juc2Fyc2txZ3d3dXVkcW1zIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzM5Mjk5NDYsImV4cCI6MjA4OTUwNTk0Nn0.2_5BIu8g6bfjki91Uk_syMC7g8OTtQIb8yYnApEz3j8"
GROQ_AD = "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"
stripe.api_key = "sk_test_51TD7vwBBE2wDwi0CS5b18fA0sd6CqNclpupLdSZHVB9INo23zKGRErg3gtQL1ObzfztxfjCZY14wPUVQDBh98XeB00IeP2wsSK"

supabase = create_client(URL, KEY)
client = Groq(api_key=GROQ_AD)

# --- 2. FUNZIONI TECNICHE ---
def pulisci_testo(t):
    return t.replace("```html", "").replace("```", "").strip()

def format_pdf(text):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    clean = re.sub('<[^<]+?>', '', text).encode('latin-1', 'ignore').decode('latin-1')
    pdf.multi_cell(0, 10, txt=clean)
    return pdf.output(dest='S').encode('latin-1')

def crea_stripe_session(price_id):
    try:
        s = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{'price': price_id, 'quantity': 1}],
            mode='subscription',
            success_url="https://svuotafrigo-app-4cvkjntg8gklzrkp5sjbuh.streamlit.app/",
            cancel_url="https://svuotafrigo-app-4cvkjntg8gklzrkp5sjbuh.streamlit.app/",
        )
        return s.url
    except: return None

# --- 3. SESSION STATE ---
if "user_id" not in st.session_state: st.session_state.user_id = None
if "is_premium" not in st.session_state: st.session_state.is_premium = False
if "ultima_ricetta" not in st.session_state: st.session_state.ultima_ricetta = ""

# --- 4. UI PRINCIPALE ---
st.title("👨‍🍳 Svuotafrigo AI")

t1, t2, t3, t4 = st.tabs(["✨ CUCINA", "📦 DISPENSA", "🛒 SPESA", "👤 ACCOUNT"])

with t1:
    ing = st.text_area("Cosa hai in frigo?", height=100)
    if st.button("GENERA RICETTA ✨"):
        if ing:
            with st.spinner("Lo Chef sta scrivendo..."):
                res = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[{"role":"user","content":f"Crea ricetta HTML (h2, li) per: {ing}. Sii breve."}]
                )
                st.session_state.ultima_ricetta = pulisci_testo(res.choices[0].message.content)
                st.rerun()

    if st.session_state.ultima_ricetta:
        st.markdown(f'<div class="recipe-card">{st.session_state.ultima_ricetta}</div>', unsafe_allow_html=True)
        
        # PLAYER VOCALE PROFESSIONALE
        clean_audio = re.sub('<[^<]+?>', '', st.session_state.ultima_ricetta).replace("'", "\\'").replace("\n", " ")
        st.components.v1.html(f"""
            <div style="background:#1a1d24; padding:20px; border-radius:20px; border:1px solid #30363d; color:white;">
                <p style="font-weight:800; color:#ff4b4b; margin-bottom:10px;">ASSISTENTE VOCALE</p>
                <div style="display:flex; gap:10px;">
                    <button id="p" style="flex:2; padding:12px; background:#ff4b4b; border:none; border-radius:10px; color:white; font-weight:bold; cursor:pointer;">RIPRODUCI</button>
                    <button id="s" style="flex:1; padding:12px; background:#30363d; border:none; border-radius:10px; color:white; font-weight:bold; cursor:pointer;">STOP</button>
                </div>
            </div>
            <script>
                const synth = window.speechSynthesis;
                document.getElementById('p').onclick = () => {{
                    synth.cancel();
                    const u = new SpeechSynthesisUtterance('{clean_audio}');
                    u.lang = 'it-IT';
                    synth.speak(u);
                }};
                document.getElementById('s').onclick = () => synth.cancel();
            </script>
        """, height=130)
        
        pdf = format_pdf(st.session_state.ultima_ricetta)
        st.download_button("📄 SCARICA PDF", data=pdf, file_name="ricetta.pdf")

with t2:
    if not st.session_state.user_id:
        st.markdown('<div class="lock-box">🔒 Accedi per la Dispensa</div>', unsafe_allow_html=True)
    else:
        st.header("📦 Dispensa")
        n_i = st.text_input("Nuovo ingrediente:")
        if st.button("Aggiungi"):
            supabase.table("dispensa").insert({"user_id": st.session_state.user_id, "ingrediente": n_i}).execute()
            st.rerun()
        for i in supabase.table("dispensa").select("*").eq("user_id", st.session_state.user_id).execute().data:
            st.write(f"🟢 {i['ingrediente']}")

with t3:
    if not st.session_state.user_id:
        st.markdown('<div class="lock-box">🔒 Accedi per la Spesa</div>', unsafe_allow_html=True)
    else:
        st.header("🛒 Lista Spesa")
        # Logica Spesa (Simile a Dispensa)

with t4:
    if not st.session_state.user_id:
        st.subheader("Login / Registrazione")
        e = st.text_input("Email")
        p = st.text_input("Password", type="password")
        if st.button("ENTRA"):
            res = supabase.auth.sign_in_with_password({"email":e, "password":p})
            st.session_state.user_id = res.user.id
            st.rerun()
    else:
        st.write(f"Account: {st.session_state.user_id}")
        if not st.session_state.is_premium:
            if st.button("ATTIVA PREMIUM (Stripe)"):
                url = crea_stripe_session("price_1TD86OBBE2wDwi0CI4KlvKFJ")
                if url: st.link_button("Vai al pagamento", url)
        if st.button("LOGOUT"):
            st.session_state.clear()
            st.rerun()
