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

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
    html, body, [class*="st-"] { font-family: 'Inter', sans-serif; }
    .recipe-card {
        background: #1E1E1E; padding: 30px; border-radius: 15px;
        border-left: 6px solid #ff4b4b; color: #F0F0F0; line-height: 1.7;
        box-shadow: 0 10px 30px rgba(0,0,0,0.5); margin-bottom: 25px;
    }
    .recipe-card h1, .recipe-card h2 { color: #ff4b4b !important; font-weight: 700; margin-top: 15px; }
    .stButton>button { border-radius: 8px; font-weight: 600; }
    </style>
""", unsafe_allow_html=True)

# API KEYS
URL = "https://ixkrnsarskqgwwuudqms.supabase.co"
KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Iml4a3Juc2Fyc2txZ3d3dXVkcW1zIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzM5Mjk5NDYsImV4cCI6MjA4OTUwNTk0Nn0.2_5BIu8g6bfjki91Uk_syMC7g8OTtQIb8yYnApEz3j8"
GROQ_AD = "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"

supabase = create_client(URL, KEY)
client = Groq(api_key=GROQ_AD)

# --- FUNZIONI ---
def clean_recipe(text):
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
    mapping = {"uov": "🥚", "pata": "🥔", "carn": "🍗", "past": "🍝", "pomo": "🍅", "form": "🧀", "pesc": "🐟", "lat": "🥛", "olio": "🫗", "pane": "🥖"}
    for k, v in mapping.items():
        if k in str(n).lower(): return v
    return "🟢"

# --- SESSION STATE ---
if "user_id" not in st.session_state: st.session_state.user_id = None
if "ultima_ricetta" not in st.session_state: st.session_state.ultima_ricetta = ""
if "is_premium" not in st.session_state: st.session_state.is_premium = False
if "ing_input" not in st.session_state: st.session_state.ing_input = ""

# --- SIDEBAR ---
with st.sidebar:
    st.title("👤 Account")
    if st.session_state.user_id is None:
        with st.form("auth"):
            e = st.text_input("Email")
            p = st.text_input("Password", type="password")
            if st.form_submit_button("Entra"):
                res = supabase.auth.sign_in_with_password({"email": e, "password": p})
                st.session_state.user_id = res.user.id
                st.rerun()
    else:
        st.success(f"Loggato")
        if st.button("Logout"):
            st.session_state.clear()
            st.rerun()

# --- TABS ---
t1, t2, t3, t4, t5 = st.tabs(["🔥 Cucina AI", "📦 Dispensa", "🛒 Spesa", "📖 Archivio", "💬 Feedback"])

with t1:
    st.header("Generatore di Ricette")
    if st.session_state.user_id:
        if st.button("Carica dalla Dispensa 📦"):
            items = supabase.table("dispensa").select("ingrediente").eq("user_id", st.session_state.user_id).execute()
            st.session_state.ing_input = ", ".join([i['ingrediente'] for i in items.data])
            st.rerun()

    ing = st.text_area("Cosa hai in frigo?", value=st.session_state.ing_input)
    
    if st.button("Genera Ricetta ✨", use_container_width=True):
        with st.spinner("Lo Chef sta cucinando..."):
            prompt = f"Crea una ricetta HTML (h1, h2, ul, li) per: {ing}. Non aggiungere altro testo."
            res = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=[{"role": "user", "content": prompt}])
            st.session_state.ultima_ricetta = clean_recipe(res.choices[0].message.content)
            st.rerun()

    if st.session_state.ultima_ricetta:
        # Visualizzazione Ricetta
        st.markdown(f'<div class="recipe-card">{st.session_state.ultima_ricetta}</div>', unsafe_allow_html=True)
        
        # Righe dei comandi
        c1, c2 = st.columns(2)
        with c1:
            st.download_button("📄 Scarica PDF", data=format_pdf(st.session_state.ultima_ricetta), file_name="ricetta.pdf", use_container_width=True)
        with c2:
            if st.session_state.user_id:
                if st.button("💾 SALVA IN ARCHIVIO", use_container_width=True, type="primary"):
                    supabase.table("ricette").insert({"user_id": st.session_state.user_id, "contenuto": st.session_state.ultima_ricetta}).execute()
                    st.success("Salvata nel Tab 4!")
            else:
                st.warning("Accedi per salvare")

with t2:
    st.header("📦 Dispensa")
    if st.session_state.user_id:
        n_i = st.text_input("Nuovo ingrediente:")
        if st.button("Aggiungi ➕"):
            supabase.table("dispensa").insert({"user_id": st.session_state.user_id, "ingrediente": n_i}).execute()
            st.rerun()
        data = supabase.table("dispensa").select("*").eq("user_id", st.session_state.user_id).execute().data
        for i in data:
            col1, col2 = st.columns([4,1])
            col1.write(f"{get_emoji(i['ingrediente'])} {i['ingrediente']}")
            if col2.button("🗑️", key=f"d_{i['id']}"):
                supabase.table("dispensa").delete().eq("id", i['id']).execute()
                st.rerun()

with t3:
    st.header("🛒 Lista Spesa")
    if st.session_state.user_id:
        n_s = st.text_input("Cosa comprare?")
        if st.button("Aggiungi 🛒"):
            supabase.table("lista_spesa").insert({"user_id": st.session_state.user_id, "item": n_s}).execute()
            st.rerun()
        data = supabase.table("lista_spesa").select("*").eq("user_id", st.session_state.user_id).execute().data
        for s in data:
            col1, col2 = st.columns([4,1])
            col1.write(f"⬜ {s['item']}")
            if col2.button("✔️", key=f"s_{s['id']}"):
                supabase.table("lista_spesa").delete().eq("id", s['id']).execute()
                st.rerun()

with t4:
    st.header("📖 Archivio Ricette")
    if st.session_state.user_id:
        mie = supabase.table("ricette").select("*").eq("user_id", st.session_state.user_id).order("created_at", desc=True).execute().data
        for r in mie:
            with st.expander(f"🍴 Ricetta del {r['created_at'][:10]}"):
                st.markdown(r['contenuto'], unsafe_allow_html=True)
                if st.button("Elimina 🗑️", key=f"del_{r['id']}"):
                    supabase.table("ricette").delete().eq("id", r['id']).execute()
                    st.rerun()

with t5:
    st.header("Feedback 📣")
    if st.session_state.user_id:
        msg = st.text_area("Suggerimenti?")
        if st.button("Invia"):
            supabase.table("feedback").insert({"user_id": st.session_state.user_id, "messaggio": msg}).execute()
            st.success("Ricevuto!")
