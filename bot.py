import streamlit as st
import stripe
from groq import Groq
from supabase import create_client
from fpdf import FPDF
import re
import io

# --- 1. CONFIGURAZIONI E DESIGN "RADICAL DARK" ---
st.set_page_config(page_title="Svuotafrigo App", layout="wide")

# CSS: Fumetto Login + Design Ricetta + Player Vocale Custom
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;700;800&display=swap');
    * { font-family: 'Plus Jakarta Sans', sans-serif; }
    
    /* Animazione Fumetto Login */
    @keyframes fadeOut { 0% {opacity: 1;} 90% {opacity: 1;} 100% {opacity: 0; visibility: hidden;} }
    @keyframes bounce { 0%, 20%, 50%, 80%, 100% {transform: translateX(0);} 40% {transform: translateX(10px);} 60% {transform: translateX(5px);} }
    .login-hint {
        position: fixed; top: 12px; left: 60px; z-index: 9999;
        background-color: #ff4b4b; color: white; padding: 8px 15px;
        border-radius: 20px; font-weight: bold; font-size: 14px;
        animation: bounce 2s infinite, fadeOut 60s forwards;
        box-shadow: 2px 2px 10px rgba(0,0,0,0.3);
    }
    .login-hint:after {
        content: ''; position: absolute; left: -10px; top: 50%;
        margin-top: -10px; border-top: 10px solid transparent;
        border-bottom: 10px solid transparent; border-right: 10px solid #ff4b4b;
    }

    /* Card Ricetta Professionale */
    .recipe-card {
        background: #1e1e1e;
        padding: 30px;
        border-radius: 20px;
        border-left: 5px solid #ff4b4b;
        color: white;
        margin: 20px 0;
    }
    .recipe-card h2 { color: #ff4b4b !important; font-weight: 800; }

    /* Player Vocale Custom */
    .voice-box {
        background: #262626;
        padding: 15px;
        border-radius: 12px;
        border: 1px solid #444;
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-top: 10px;
    }
    </style>
""", unsafe_allow_html=True)

# Mostra fumetto se non loggato
if "user_id" not in st.session_state or st.session_state.user_id is None:
    st.markdown('<div class="login-hint">⬅️ Login qui!</div>', unsafe_allow_html=True)

# API SETUP
URL = "https://ixkrnsarskqgwwuudqms.supabase.co"
KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Iml4a3Juc2Fyc2txZ3d3dXVkcW1zIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzM5Mjk5NDYsImV4cCI6MjA4OTUwNTk0Nn0.2_5BIu8g6bfjki91Uk_syMC7g8OTtQIb8yYnApEz3j8"
GROQ_AD = "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"
stripe.api_key = "sk_test_51TD7vwBBE2wDwi0CS5b18fA0sd6CqNclpupLdSZHVB9INo23zKGRErg3gtQL1ObzfztxfjCZY14wPUVQDBh98XeB00IeP2wsSK"

supabase = create_client(URL, KEY)
client = Groq(api_key=GROQ_AD)

# --- 2. FUNZIONI DI SUPPORTO ---
def format_pdf(text):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    clean = re.sub('<[^<]+?>', '', text).encode('latin-1', 'ignore').decode('latin-1')
    pdf.multi_cell(0, 10, txt=clean)
    return pdf.output(dest='S').encode('latin-1')

def get_emoji(n):
    n = str(n).lower()
    mapping = {"uov": "🥚", "pata": "🥔", "carn": "🍗", "past": "🍝", "pomo": "🍅", "form": "🧀", "lat": "🥛"}
    for k, v in mapping.items():
        if k in n: return v
    return "🟢"

def login_message(tab_name):
    st.error(f"🔒 Accedi per usare la sezione {tab_name}")
    if st.button(f"Vai al Login 👤", key=f"go_log_{tab_name}"):
        st.info("Apri la sidebar a sinistra per accedere!")

# --- 3. SESSION STATE ---
states = {"user_id": None, "is_premium": False, "nickname": "", "ultima_ricetta": "", "ing_input": "", "count_ospite": 0}
for k, v in states.items():
    if k not in st.session_state: st.session_state[k] = v

# --- 4. SIDEBAR (LOGIC COMPLETA) ---
st.sidebar.title("👤 My Kitchen")
if st.session_state.user_id is None:
    scelta = st.sidebar.selectbox("Cosa vuoi fare?", ["Login", "Crea Account", "Recupero Password"])
    with st.sidebar.form("auth_form"):
        email = st.text_input("Email")
        pwd = st.text_input("Password", type="password") if scelta != "Recupero Password" else ""
        nick = st.text_input("Nickname") if scelta == "Crea Account" else ""
        if st.form_submit_button("Conferma"):
            try:
                if scelta == "Login":
                    res = supabase.auth.sign_in_with_password({"email": email, "password": pwd})
                    st.session_state.user_id = res.user.id
                    p = supabase.table("profili").select("*").eq("id", res.user.id).execute()
                    if p.data:
                        st.session_state.nickname = p.data[0]["nickname"]
                        st.session_state.is_premium = p.data[0]["is_premium"]
                elif scelta == "Crea Account":
                    res = supabase.auth.sign_up({"email": email, "password": pwd})
                    if res.user:
                        supabase.table("profili").insert({"id": res.user.id, "nickname": nick}).execute()
                        st.success("Account creato! Fai il login.")
                st.rerun()
            except Exception as e: st.error("Errore Autenticazione")
else:
    st.sidebar.success(f"Ciao, {st.session_state.nickname}!")
    st.sidebar.write(f"Piano: {'💎 DIAMOND' if st.session_state.is_premium else '👨‍🍳 STANDARD'}")
    if st.sidebar.button("Logout 🚪"):
        st.session_state.clear()
        st.rerun()

# --- 5. TABS ---
t1, t2, t3, t4, t5 = st.tabs(["🔥 Cucina AI", "📦 Dispensa", "🛒 Spesa", "📖 Archivio", "💬 Feedback"])

with t1:
    st.header("Generatore di Ricette")
    if st.session_state.user_id:
        if st.button("Carica dalla Dispensa 📦"):
            items = supabase.table("dispensa").select("ingrediente").eq("user_id", st.session_state.user_id).execute()
            if items.data:
                st.session_state.ing_input = ", ".join([i['ingrediente'] for i in items.data])
                st.rerun()
    
    ing = st.text_area("Cosa hai in frigo?", value=st.session_state.ing_input)
    c1, c2 = st.columns(2)
    tmp = c1.selectbox("Tempo", ["15 min", "30 min", "60 min"])
    mod = c2.selectbox("Chef", ["Simpatico", "Professionale", "Cattivissimo"])

    if st.button("Genera Ricetta ✨", use_container_width=True):
        if not st.session_state.user_id and st.session_state.count_ospite >= 2:
            st.error("Accedi per generare altre ricette! (Limite 2 per ospiti)")
        else:
            with st.spinner("Lo Chef sta scrivendo..."):
                macros = " Aggiungi Macro e Kcal." if st.session_state.is_premium else ""
                prompt = f"Sei uno chef {mod}. Crea ricetta HTML per: {ing}. Tempo: {tmp}.{macros}"
                res = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=[{"role": "user", "content": prompt}])
                st.session_state.ultima_ricetta = res.choices[0].message.content
                if not st.session_state.user_id: st.session_state.count_ospite += 1
                st.rerun()

    if st.session_state.ultima_ricetta:
        st.markdown(f'<div class="recipe-card">{st.session_state.ultima_ricetta}</div>', unsafe_allow_html=True)
        
        # --- PLAYER VOCALE CUSTOM ---
        col_v, col_p = st.columns(2)
        with col_v:
            if st.session_state.is_premium:
                txt = re.sub('<[^<]+?>', '', st.session_state.ultima_ricetta).replace("'", " ").replace("\n", " ")
                st.components.v1.html(f"""
                    <div style="background:#262626; padding:10px; border-radius:10px; display:flex; gap:10px;">
                        <button id='p' style='flex:1; background:#ff4b4b; color:white; border:none; padding:10px; border-radius:5px; font-weight:bold; cursor:pointer;'>🔊 PLAY</button>
                        <button id='s' style='flex:1; background:#444; color:white; border:none; padding:10px; border-radius:5px; font-weight:bold; cursor:pointer;'>STOP</button>
                    </div>
                    <script>
                        const synth = window.speechSynthesis;
                        document.getElementById('p').onclick = () => {{
                            synth.cancel();
                            const u = new SpeechSynthesisUtterance('{txt}');
                            u.lang = 'it-IT';
                            synth.speak(u);
                        }};
                        document.getElementById('s').onclick = () => synth.cancel();
                    </script>
                """, height=70)
            else:
                if st.button("🔊 Sblocca Voce (Premium)"): st.warning("Passa a Diamond!")

        pdf_data = format_pdf(st.session_state.ultima_ricetta)
        col_p.download_button("📄 Scarica PDF", data=pdf_data, file_name="ricetta.pdf", use_container_width=True)

with t2:
    if st.session_state.user_id:
        st.header("📦 La tua Dispensa")
        n_i = st.text_input("Aggiungi ingrediente:")
        if st.button("Salva ➕"):
            if n_i:
                supabase.table("dispensa").insert({"user_id": st.session_state.user_id, "ingrediente": n_i}).execute()
                st.rerun()
        res_disp = supabase.table("dispensa").select("*").eq("user_id", st.session_state.user_id).execute()
        for i in res_disp.data:
            c1, c2 = st.columns([4,1])
            c1.write(f"{get_emoji(i['ingrediente'])} {i['ingrediente']}")
            if c2.button("🗑️", key=f"d_{i['id']}"):
                supabase.table("dispensa").delete().eq("id", i['id']).execute()
                st.rerun()
    else: login_message("Dispensa")

with t3:
    if st.session_state.user_id:
        st.header("🛒 Lista della Spesa")
        m = st.text_input("Cosa comprare?")
        if st.button("Aggiungi 🛒"):
            if m:
                supabase.table("lista_spesa").insert({"user_id": st.session_state.user_id, "item": m}).execute()
                st.rerun()
        res_spesa = supabase.table("lista_spesa").select("*").eq("user_id", st.session_state.user_id).execute()
        for s in res_spesa.data:
            c1, c2 = st.columns([4,1])
            c1.write(f"⬜ {s['item']}")
            if c2.button("✔️", key=f"s_{s['id']}"):
                supabase.table("lista_spesa").delete().eq("id", s['id']).execute()
                st.rerun()
    else: login_message("Lista Spesa")

with t5:
    if st.session_state.user_id:
        st.header("Feedback 📣")
        msg = st.text_area("Suggerimenti?")
        if st.button("Invia 🚀"):
            supabase.table("feedback").insert({"user_id": st.session_state.user_id, "messaggio": msg}).execute()
            st.success("Grazie!")
    else: login_message("Feedback")
