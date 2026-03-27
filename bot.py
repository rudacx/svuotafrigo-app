import streamlit as st
import stripe
from groq import Groq
from supabase import create_client
from fpdf import FPDF
import re

# --- 1. CONFIGURAZIONI E CSS ---
st.set_page_config(page_title="Svuotafrigo App", layout="wide")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
    html, body, [class*="st-"] { font-family: 'Inter', sans-serif; }
    
    .recipe-card {
        background: #1E1E1E; padding: 25px; border-radius: 15px;
        border-left: 6px solid #ff4b4b; color: #F0F0F0; line-height: 1.6;
        box-shadow: 0 10px 30px rgba(0,0,0,0.5); margin-bottom: 20px;
    }
    .recipe-card h1, .recipe-card h2 { color: #ff4b4b !important; font-weight: 700; margin-bottom: 10px; }
    .recipe-card p, .recipe-card li { font-size: 16px; }
    </style>
""", unsafe_allow_html=True)

# API KEYS
URL = "https://ixkrnsarskqgwwuudqms.supabase.co"
KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Iml4a3Juc2Fyc2txZ3d3dXVkcW1zIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzM5Mjk5NDYsImV4cCI6MjA4OTUwNTk0Nn0.2_5BIu8g6bfjki91Uk_syMC7g8OTtQIb8yYnApEz3j8"
GROQ_AD = "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"

supabase = create_client(URL, KEY)
client = Groq(api_key=GROQ_AD)

# --- FUNZIONE DI PULIZIA ---
def super_clean(text):
    # Rimuove i blocchi di codice markdown
    text = re.sub(r"```html|```", "", text)
    # Cerca l'inizio effettivo dell'HTML (h1 o h2) per tagliare i testi strani iniziali
    match = re.search(r"<h[12].*", text, re.DOTALL | re.IGNORECASE)
    if match:
        text = match.group(0)
    # Rimuove le frasi finali di cortesia dell'AI
    text = re.sub(r"(Spero che ti piaccia|Buon appetito|Se hai altre richieste).*", "", text, flags=re.DOTALL | re.IGNORECASE)
    return text.strip()

# --- SESSION STATE ---
if "user_id" not in st.session_state: st.session_state.user_id = None
if "ultima_ricetta" not in st.session_state: st.session_state.ultima_ricetta = ""

# --- SIDEBAR LOGIN ---
with st.sidebar:
    st.title("👤 Account")
    if not st.session_state.user_id:
        e = st.text_input("Email")
        p = st.text_input("Password", type="password")
        if st.button("Accedi"):
            try:
                res = supabase.auth.sign_in_with_password({"email": e, "password": p})
                st.session_state.user_id = res.user.id
                st.rerun()
            except: st.error("Errore login")
    else:
        st.success("Connesso")
        if st.button("Esci"):
            st.session_state.clear()
            st.rerun()

# --- TABS ---
t1, t2, t3, t4 = st.tabs(["🔥 Genera", "📦 Dispensa", "🛒 Spesa", "📖 Archivio"])

with t1:
    ing = st.text_area("Cosa hai in frigo?", placeholder="Esempio: uova, pancetta...")
    
    if st.button("Genera Ricetta ✨", use_container_width=True):
        with st.spinner("Cucinando..."):
            res = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": f"Dammi SOLO il codice HTML per una ricetta con: {ing}. Inizia direttamente con il tag <h1>"}]
            )
            st.session_state.ultima_ricetta = super_clean(res.choices[0].message.content)
            st.rerun()

    if st.session_state.ultima_ricetta:
        st.markdown(f'<div class="recipe-card">{st.session_state.ultima_ricetta}</div>', unsafe_allow_html=True)
        
        st.divider()
        # PULSANTE SALVA - Visibile solo se loggato
        if st.session_state.user_id:
            if st.button("💾 SALVA NELL'ARCHIVIO", use_container_width=True, type="primary"):
                try:
                    supabase.table("ricette").insert({
                        "user_id": st.session_state.user_id, 
                        "contenuto": st.session_state.ultima_ricetta
                    }).execute()
                    st.success("Ricetta salvata con successo! La trovi nel tab Archivio.")
                except Exception as ex:
                    st.error(f"Errore durante il salvataggio: {ex}")
        else:
            st.warning("⚠️ Esegui il login dal menu laterale per poter salvare questa ricetta.")

with t4:
    st.header("📖 Archivio Personale")
    if st.session_state.user_id:
        try:
            items = supabase.table("ricette").select("*").eq("user_id", st.session_state.user_id).order("created_at", desc=True).execute().data
            if not items:
                st.info("Non hai ancora salvato nessuna ricetta.")
            for r in items:
                with st.expander(f"🍴 Ricetta del {r['created_at'][:10]}"):
                    st.markdown(r['contenuto'], unsafe_allow_html=True)
                    if st.button("Elimina Ricetta", key=f"del_{r['id']}"):
                        supabase.table("ricette").delete().eq("id", r['id']).execute()
                        st.rerun()
        except:
            st.error("Errore nel caricamento dell'archivio.")
    else:
        st.info("Accedi per consultare le tue ricette salvate.")
