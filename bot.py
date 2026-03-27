import streamlit as st
import stripe
from groq import Groq
from supabase import create_client
from fpdf import FPDF
import re
import time
import io

# --- 1. CONFIGURAZIONI E CSS ---
st.set_page_config(page_title="Svuotafrigo App", layout="wide")

# CSS per Font Inter, Card Ricetta e Design Dark
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
    
    html, body, [class*="st-"] { font-family: 'Inter', sans-serif; }

    .recipe-card {
        background: #1E1E1E;
        padding: 30px;
        border-radius: 15px;
        border-left: 6px solid #ff4b4b;
        color: #F0F0F0;
        line-height: 1.7;
        box-shadow: 0 10px 30px rgba(0,0,0,0.5);
        margin-bottom: 25px;
    }
    .recipe-card h1, .recipe-card h2 { color: #ff4b4b !important; margin-top: 10px; font-weight: 700; }
    .recipe-card ul { margin-bottom: 20px; }
    .recipe-card li { margin-bottom: 8px; }
    
    @keyframes bounce {
        0%, 20%, 50%, 80%, 100% {transform: translateX(0);}
        40% {transform: translateX(10px);}
        60% {transform: translateX(5px);}
    }
    .login-hint {
        position: fixed; top: 12px; left: 60px; z-index: 9999;
        background-color: #ff4b4b; color: white; padding: 6px 15px;
        border-radius: 20px; font-weight: bold; font-size: 14px;
        animation: bounce 2s infinite; box-shadow: 2px 2px 10px rgba(0,0,0,0.3);
    }
    </style>
""", unsafe_allow_html=True)

# API KEYS
URL = "https://ixkrnsarskqgwwuudqms.supabase.co"
KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Iml4a3Juc2Fyc2txZ3d3dXVkcW1zIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzM5Mjk5NDYsImV4cCI6MjA4OTUwNTk0Nn0.2_5BIu8g6bfjki91Uk_syMC7g8OTtQIb8yYnApEz3j8"
GROQ_AD = "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"
stripe.api_key = "sk_test_51TD7vwBBE2wDwi0CS5b18fA0sd6CqNclpupLdSZHVB9INo23zKGRErg3gtQL1ObzfztxfjCZY14wPUVQDBh98XeB00IeP2wsSK".strip()

supabase = create_client(URL, KEY)
client = Groq(api_key=GROQ_AD)

# --- 2. FUNZIONI DI SUPPORTO ---
def clean_recipe_output(text):
    """Elimina i tag codice e il testo inutile dell'AI"""
    text = re.sub(r"```html|```", "", text)
    text = re.sub(r"(?i)^.*?(?=<h[12])", "", text, flags=re.DOTALL) 
    return text.strip()

def format_pdf(text):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    clean_text = re.sub('<[^<]+?>', '', text).encode('latin-1', 'ignore').decode('latin-1')
    pdf.multi_cell(0, 10, txt=clean_text)
    return pdf.output(dest='S').encode('latin-1')

def get_emoji(n):
    n = str(n).lower()
    mapping = {"uov": "🥚", "pata": "🥔", "carn": "🍗", "past": "🍝", "pomo": "🍅", "form": "🧀", "pesc": "🐟", "lat": "🥛", "olio": "🫗", "pane": "🥖"}
    for k, v in mapping.items():
        if k in n: return v
    return "🟢"

# --- 3. SESSION STATE ---
if "user_id" not in st.session_state: st.session_state.user_id = None
if "ultima_ricetta" not in st.session_state: st.session_state.ultima_ricetta = ""
if "nickname" not in st.session_state: st.session_state.nickname = ""
if "is_premium" not in st.session_state: st.session_state.is_premium = False
if "ing_input" not in st.session_state: st.session_state.ing_input = ""

if st.session_state.user_id is None:
    st.markdown('<div class="login-hint">⬅️ Login qui!</div>', unsafe_allow_html=True)

# --- 4. SIDEBAR ---
st.sidebar.title("👤 Account")
if st.session_state.user_id is None:
    scelta = st.sidebar.selectbox("Azione", ["Login", "Crea Account"])
    with st.sidebar.form("auth"):
        email = st.text_input("Email")
        pwd = st.text_input("Password", type="password")
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
                else:
                    res = supabase.auth.sign_up({"email": email, "password": pwd})
                    if res.user:
                        supabase.table("profili").insert({"id": res.user.id, "nickname": nick}).execute()
                        st.success("Account creato!")
                st.rerun()
            except: st.error("Errore Credenziali")
else:
    st.sidebar.success(f"Ciao {st.session_state.nickname}")
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
            st.session_state.ing_input = ", ".join([i['ingrediente'] for i in items.data])
            st.rerun()

    ing = st.text_area("Cosa c'è in frigo?", value=st.session_state.ing_input)
    
    if st.button("Genera Ricetta ✨", use_container_width=True):
        with st.spinner("Lo Chef sta creando..."):
            prompt = f"Sei uno chef stellato. Crea ricetta HTML per: {ing}. Usa h1 per titolo, h2 per sezioni. NO testo extra prima o dopo."
            res = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=[{"role": "user", "content": prompt}])
            st.session_state.ultima_ricetta = clean_recipe_output(res.choices[0].message.content)
            st.rerun()

    if st.session_state.ultima_ricetta:
        st.markdown(f'<div class="recipe-card">{st.session_state.ultima_ricetta}</div>', unsafe_allow_html=True)
        c1, c2, c3 = st.columns(3)
        with c1:
            if st.session_state.is_premium:
                txt = re.sub('<[^<]+?>', '', st.session_state.ultima_ricetta).replace("'", " ").replace("\n", " ")
                st.components.v1.html(f"<button id='v' style='width:100%; padding:10px; background:#ff4b4b; color:white; border:none; border-radius:5px; font-weight:bold;'>🔊 Leggi</button><script>document.getElementById('v').onclick=()=>{{const s=new SpeechSynthesisUtterance('{txt}');s.lang='it-IT';window.speechSynthesis.speak(s);}};</script>", height=50)
            else: st.button("🔊 Premium Only", disabled=True, use_container_width=True)
        with c2:
            st.download_button("📄 PDF", data=format_pdf(st.session_state.ultima_ricetta), file_name="ricetta.pdf", use_container_width=True)
        with c3:
            if st.session_state.user_id and st.button("💾 Salva", use_container_width=True):
                supabase.table("ricette").insert({"user_id": st.session_state.user_id, "contenuto": st.session_state.ultima_ricetta}).execute()
                st.success("Salvata!")

with t2:
    st.header("📦 Dispensa")
    if st.session_state.user_id:
        new_i = st.text_input("Nuovo ingrediente:")
        if st.button("Salva ➕"):
            supabase.table("dispensa").insert({"user_id": st.session_state.user_id, "ingrediente": new_i}).execute()
            st.rerun()
        for i in supabase.table("dispensa").select("*").eq("user_id", st.session_state.user_id).execute().data:
            c1, c2 = st.columns([4,1])
            c1.write(f"{get_emoji(i['ingrediente'])} {i['ingrediente']}")
            if c2.button("🗑️", key=f"d_{i['id']}"):
                supabase.table("dispensa").delete().eq("id", i['id']).execute()
                st.rerun()

with t3:
    st.header("🛒 Lista Spesa")
    if st.session_state.user_id:
        new_s = st.text_input("Cosa manca?")
        if st.button("Aggiungi 🛒"):
            supabase.table("lista_spesa").insert({"user_id": st.session_state.user_id, "item": new_s}).execute()
            st.rerun()
        for s in supabase.table("lista_spesa").select("*").eq("user_id", st.session_state.user_id).execute().data:
            c1, c2 = st.columns([4,1])
            c1.write(f"⬜ {s['item']}")
            if c2.button("✔️", key=f"s_{s['id']}"):
                supabase.table("lista_spesa").delete().eq("id", s['id']).execute()
                st.rerun()

with t4:
    st.header("📖 Archivio")
    if st.session_state.user_id:
        mie = supabase.table("ricette").select("*").eq("user_id", st.session_state.user_id).order("created_at", desc=True).execute()
        for r in mie.data:
            with st.expander(f"🍴 Ricetta del {r['created_at'][:10]}"):
                st.markdown(r['contenuto'], unsafe_allow_html=True)
                if st.button("Elimina", key=f"del_{r['id']}"):
                    supabase.table("ricette").delete().eq("id", r['id']).execute()
                    st.rerun()

with t5:
    st.header("Feedback 📣")
    if st.session_state.user_id:
        msg = st.text_area("Dicci la tua:")
        if st.button("Invia 🚀"):
            supabase.table("feedback").insert({"user_id": st.session_state.user_id, "messaggio": msg}).execute()
            st.success("Grazie!")
