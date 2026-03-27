import streamlit as st
from groq import Groq
from supabase import create_client
from fpdf import FPDF
import re

# --- 1. CONFIGURAZIONE E STILE (FONT INTER) ---
st.set_page_config(page_title="Svuotafrigo AI", layout="wide")

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
    .recipe-card h1, .recipe-card h2 { color: #ff4b4b !important; font-weight: 700; margin-top: 10px; }
    .stButton>button { border-radius: 8px; font-weight: 600; }
    </style>
""", unsafe_allow_html=True)

# --- 2. CONNESSIONI API ---
URL = "https://ixkrnsarskqgwwuudqms.supabase.co"
KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Iml4a3Juc2Fyc2txZ3d3dXVkcW1zIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzM5Mjk5NDYsImV4cCI6MjA4OTUwNTk0Nn0.2_5BIu8g6bfjki91Uk_syMC7g8OTtQIb8yYnApEz3j8"
GROQ_KEY = "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"

supabase = create_client(URL, KEY)
client = Groq(api_key=GROQ_KEY)

# --- 3. FUNZIONI DI SUPPORTO ---
def super_clean(text):
    """Pulisce la risposta dell'AI dai tag visualizzati e dalle chiacchiere"""
    text = re.sub(r"```html|```", "", text)
    # Cerca l'inizio del primo tag h1 o h2 e taglia tutto quello che c'è prima
    match = re.search(r"<h[1-2].*", text, re.DOTALL | re.IGNORECASE)
    if match:
        text = match.group(0)
    # Rimuove i saluti finali dell'AI
    text = re.sub(r"(Spero che|Buon appetito|Se hai altre|Spero di esserti).*", "", text, flags=re.DOTALL | re.IGNORECASE)
    return text.strip()

def format_pdf(text):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    clean_text = re.sub('<[^<]+?>', '', text).encode('latin-1', 'ignore').decode('latin-1')
    pdf.multi_cell(0, 10, txt=clean_text)
    return pdf.output(dest='S').encode('latin-1')

# --- 4. GESTIONE SESSIONE ---
if "user_id" not in st.session_state: st.session_state.user_id = None
if "ultima_ricetta" not in st.session_state: st.session_state.ultima_ricetta = ""

# --- 5. SIDEBAR LOGIN ---
with st.sidebar:
    st.title("👤 Account")
    if not st.session_state.user_id:
        with st.form("login_form"):
            email = st.text_input("Email")
            pwd = st.text_input("Password", type="password")
            if st.form_submit_button("Accedi"):
                try:
                    res = supabase.auth.sign_in_with_password({"email": email, "password": pwd})
                    st.session_state.user_id = res.user.id
                    st.rerun()
                except: st.error("Credenziali errate")
    else:
        st.success("Sei loggato!")
        if st.button("Logout 🚪"):
            st.session_state.clear()
            st.rerun()

# --- 6. TAB INTERFACCIA ---
t1, t2, t3, t4 = st.tabs(["🔥 Genera Ricetta", "📦 Dispensa", "🛒 Lista Spesa", "📖 Archivio"])

with t1:
    ing = st.text_area("Cosa hai in frigo?", placeholder="Esempio: 2 uova, farina, latte...")
    
    if st.button("Genera Ricetta ✨", use_container_width=True):
        with st.spinner("Lo Chef AI sta scrivendo..."):
            res = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": f"Rispondi SOLO con codice HTML (h1, h2, ul, li). Crea una ricetta con: {ing}. Inizia subito con <h1>"}]
            )
            st.session_state.ultima_ricetta = super_clean(res.choices[0].message.content)
            st.rerun()

    if st.session_state.ultima_ricetta:
        # Visualizzazione pulita della ricetta
        st.markdown(f'<div class="recipe-card">{st.session_state.ultima_ricetta}</div>', unsafe_allow_html=True)
        
        st.divider()
        
        # Pulsanti Azione
        col_a, col_b = st.columns(2)
        with col_a:
            st.download_button("📄 Scarica PDF", data=format_pdf(st.session_state.ultima_ricetta), file_name="ricetta.pdf", use_container_width=True)
        with col_b:
            if st.session_state.user_id:
                if st.button("💾 SALVA IN ARCHIVIO", use_container_width=True, type="primary"):
                    supabase.table("ricette").insert({
                        "user_id": st.session_state.user_id, 
                        "contenuto": st.session_state.ultima_ricetta
                    }).execute()
                    st.success("Salvata correttamente nel Tab Archivio!")
            else:
                st.warning("Accedi per salvare la ricetta")

with t4:
    st.header("📖 Le tue Ricette Salvate")
    if st.session_state.user_id:
        ricette = supabase.table("ricette").select("*").eq("user_id", st.session_state.user_id).order("created_at", desc=True).execute().data
        if not ricette:
            st.info("Non hai ancora ricette salvate.")
        for r in ricette:
            with st.expander(f"🍴 Ricetta del {r['created_at'][:10]}"):
                st.markdown(r['contenuto'], unsafe_allow_html=True)
                if st.button("Elimina 🗑️", key=f"del_{r['id']}"):
                    supabase.table("ricette").delete().eq("id", r['id']).execute()
                    st.rerun()
    else:
        st.info("Esegui il login per vedere il tuo archivio personale.")
