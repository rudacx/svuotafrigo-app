import streamlit as st
import stripe
from groq import Groq
from supabase import create_client
from fpdf import FPDF
import re
import io

# --- 1. CONFIGURAZIONI ---
st.set_page_config(page_title="Svuotafrigo App", layout="wide")
st.markdown('<link rel="manifest" href="./manifest.json">', unsafe_allow_html=True)

# CSS per il fumetto che sparisce dopo 60 secondi
if "user_id" not in st.session_state or st.session_state.user_id is None:
    st.markdown("""
        <style>
        @keyframes fadeOut { 0% {opacity: 1;} 90% {opacity: 1;} 100% {opacity: 0; visibility: hidden;} }
        @keyframes bounce { 0%, 20%, 50%, 80%, 100% {transform: translateX(0);} 40% {transform: translateX(10px);} 60% {transform: translateX(5px);} }
        .login-hint {
            position: fixed; top: 12px; left: 60px; z-index: 999999;
            background-color: #ff4b4b; color: white; padding: 6px 15px;
            border-radius: 20px; font-weight: bold; font-size: 14px;
            animation: bounce 2s infinite, fadeOut 60s forwards;
            box-shadow: 2px 2px 10px rgba(0,0,0,0.3);
        }
        .login-hint:after {
            content: ''; position: absolute; left: -10px; top: 50%;
            margin-top: -10px; border-top: 10px solid transparent;
            border-bottom: 10px solid transparent; border-right: 10px solid #ff4b4b;
        }
        </style>
        <div class="login-hint">⬅️ Login qui!</div>
    """, unsafe_allow_html=True)

URL = "https://ixkrnsarskqgwwuudqms.supabase.co"
KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Iml4a3Juc2Fyc2txZ3d3dXVkcW1zIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzM5Mjk5NDYsImV4cCI6MjA4OTUwNTk0Nn0.2_5BIu8g6bfjki91Uk_syMC7g8OTtQIb8yYnApEz3j8"
GROQ_AD = "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"
stripe.api_key = "sk_test_51TD7vwBBE2wDwi0CS5b18fA0sd6CqNclpupLdSZHVB9INo23zKGRErg3gtQL1ObzfztxfjCZY14wPUVQDBh98XeB00IeP2wsSK".strip()
ID_GOLD, ID_DIAMOND = "price_1TD86OBBE2wDwi0CI4KlvKFJ", "price_1TD88HBBE2wDwi0CV9d2heo2"

supabase = create_client(URL, KEY)
client = Groq(api_key=GROQ_AD)

# --- 2. FUNZIONI ---
def format_pdf(text):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    clean = re.sub('<[^<]+?>', '', text).encode('latin-1', 'ignore').decode('latin-1')
    pdf.multi_cell(0, 10, txt=clean)
    return pdf.output(dest='S').encode('latin-1')

def login_message(tab_name):
    st.error(f"🔒 Accedi per usare la sezione {tab_name}")
    if st.button(f"Vai al Login 👤", key=f"go_log_{tab_name}"):
        st.info("Usa il menu in alto a sinistra (dove c'era il fumetto rosso)!")

# --- 3. SESSION STATE ---
for key in ["user_id", "is_premium", "nickname", "ultima_ricetta", "ing_input"]:
    if key not in st.session_state: st.session_state[key] = None if key != "is_premium" else False
if "count_ospite" not in st.session_state: st.session_state.count_ospite = 0

# --- 4. SIDEBAR ---
st.sidebar.title("👤 My Kitchen")
if st.session_state.user_id is None:
    scelta = st.sidebar.selectbox("Menu", ["Login", "Crea Account"])
    with st.sidebar.form("auth"):
        e, p = st.text_input("Email"), st.text_input("Password", type="password")
        nick = st.text_input("Nickname") if scelta == "Crea Account" else ""
        if st.form_submit_button("Entra"):
            try:
                if scelta == "Login":
                    res = supabase.auth.sign_in_with_password({"email": e, "password": p})
                    st.session_state.user_id = res.user.id
                    prof = supabase.table("profili").select("*").eq("id", res.user.id).execute()
                    if prof.data:
                        st.session_state.nickname, st.session_state.is_premium = prof.data[0]["nickname"], prof.data[0]["is_premium"]
                else:
                    res = supabase.auth.sign_up({"email": e, "password": p})
                    if res.user: supabase.table("profili").insert({"id": res.user.id, "nickname": nick}).execute()
                    st.success("Fatto! Ora effettua il Login.")
                st.rerun()
            except Exception as ex: st.error(f"Errore: {ex}")
else:
    st.sidebar.success(f"Ciao {st.session_state.nickname}!")
    if st.sidebar.button("Logout 🚪"): 
        st.session_state.clear()
        st.rerun()

# --- 5. TABS ---
t1, t2, t3, t4, t5 = st.tabs(["🔥 Cucina", "📦 Dispensa", "🛒 Spesa", "📖 Archivio", "💬 Feedback"])

with t1:
    st.header("Generatore Ricette AI")
    if not st.session_state.user_id: st.info("Ospite: puoi generare 2 ricette. Poi dovrai loggarti!")
    ing = st.text_area("Ingredienti:", value=st.session_state.ing_input if st.session_state.ing_input else "")
    if st.button("Genera ✨", use_container_width=True):
        if not st.session_state.user_id and st.session_state.count_ospite >= 2: st.error("Fermati! Accedi per continuare.")
        else:
            with st.spinner("Chef al lavoro..."):
                res = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=[{"role":"user","content":f"Ricetta HTML per: {ing}"}])
                st.session_state.ultima_ricetta = res.choices[0].message.content
                if not st.session_state.user_id: st.session_state.count_ospite += 1
            st.rerun()
    if st.session_state.ultima_ricetta:
        st.markdown(st.session_state.ultima_ricetta, unsafe_allow_html=True)
        st.download_button("📄 Scarica PDF", data=format_pdf(st.session_state.ultima_ricetta), file_name="ricetta.pdf", mime="application/pdf")

with t2:
    if st.session_state.user_id:
        st.header("📦 Dispensa")
        # Logica dispensa... (codice precedente)
    else: login_message("Dispensa")

with t3:
    if st.session_state.user_id:
        st.header("🛒 Lista Spesa")
        # Logica spesa... (codice precedente)
    else: login_message("Lista Spesa")

with t4:
    if st.session_state.user_id:
        st.header("📖 Archivio")
        # Logica archivio... (codice precedente)
    else: login_message("Archivio")

with t5:
    if st.session_state.user_id:
        st.header("💬 Feedback")
        # Logica feedback... (codice precedente)
    else: login_message("Feedback")
