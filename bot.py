import streamlit as st
import stripe
from groq import Groq
from supabase import create_client
from fpdf import FPDF
import re
import io

# --- 1. CONFIGURAZIONE E CSS ---
st.set_page_config(page_title="Svuotafrigo Full PRO", layout="wide")

st.markdown("""
    <style>
    @keyframes bounce { 0%, 20%, 50%, 80%, 100% {transform: translateY(0);} 40% {transform: translateY(-10px);} 60% {transform: translateY(-5px);} }
    .login-hint {
        position: fixed; top: 70px; left: 20px; z-index: 9999;
        background-color: #ff4b4b; color: white; padding: 10px;
        border-radius: 10px; font-weight: bold; animation: bounce 2s infinite;
    }
    .stButton>button {
        width: 100%;
        border-radius: 15px;
        height: 3.5em;
        font-weight: bold;
    }
    .big-login-button>div>button {
        background-color: #ff4b4b !important;
        color: white !important;
        height: 5em !important;
        font-size: 20px !important;
        border: 3px solid white !important;
    }
    </style>
""", unsafe_allow_html=True)

# API KEYS
URL = "https://ixkrnsarskqgwwuudqms.supabase.co"
KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Iml4a3Juc2Fyc2txZ3d3dXVkcW1zIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzM5Mjk5NDYsImV4cCI6MjA4OTUwNTk0Nn0.2_5BIu8g6bfjki91Uk_syMC7g8OTtQIb8yYnApEz3j8"
GROQ_AD = "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"

supabase = create_client(URL, KEY)
client = Groq(api_key=GROQ_AD)

# --- 2. FUNZIONI CORE ---
def format_pdf(text):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    clean = re.sub('<[^<]+?>', '', text).encode('latin-1', 'ignore').decode('latin-1')
    pdf.multi_cell(0, 10, txt=clean)
    return pdf.output(dest='S').encode('latin-1')

def get_emoji(n):
    n = str(n).lower()
    m = {"uov":"🥚","pata":"🥔","carn":"🍗","past":"🍝","pomo":"🍅","form":"🧀","pesc":"🐟","lat":"🥛","olio":"🫗","pane":"🥖"}
    for k, v in m.items():
        if k in n: return v
    return "🍴"

def mostra_blocco(nome_tab):
    st.error(f"🔒 Accedi per sbloccare la sezione {nome_tab}")
    st.markdown('<div class="big-login-button">', unsafe_allow_html=True)
    if st.button(f"FAI IL LOGIN PER USARE {nome_tab.upper()}", key=f"btn_lock_{nome_tab}"):
        st.info("Apri la sidebar a sinistra (le freccette >>) e usa il modulo di accesso!")
    st.markdown('</div>', unsafe_allow_html=True)

# --- 3. SESSION STATE ---
if "user_id" not in st.session_state: st.session_state.user_id = None
if "nickname" not in st.session_state: st.session_state.nickname = ""
if "ultima_ricetta" not in st.session_state: st.session_state.ultima_ricetta = ""
if "ing_temp" not in st.session_state: st.session_state.ing_temp = ""

# --- 4. SIDEBAR ---
with st.sidebar:
    st.title("👨‍🍳 Il Tuo Profilo")
    if st.session_state.user_id is None:
        st.markdown("### 🔐 Accesso")
        modo = st.radio("Cosa vuoi fare?", ["Accedi", "Registrati"])
        with st.form("auth_form"):
            email = st.text_input("Email")
            pwd = st.text_input("Password", type="password")
            nick = st.text_input("Nickname (solo registrazione)") if modo == "Registrati" else ""
            if st.form_submit_button("CONFERMA"):
                try:
                    if modo == "Accedi":
                        res = supabase.auth.sign_in_with_password({"email": email, "password": pwd})
                        st.session_state.user_id = res.user.id
                        p = supabase.table("profili").select("nickname").eq("id", res.user.id).execute()
                        if p.data: st.session_state.nickname = p.data[0]["nickname"]
                    else:
                        res = supabase.auth.sign_up({"email": email, "password": pwd})
                        if res.user:
                            supabase.table("profili").insert({"id": res.user.id, "nickname": nick}).execute()
                            st.success("Registrato! Ora fai il login.")
                    st.rerun()
                except Exception as e: st.error(f"Errore: {e}")
    else:
        st.success(f"Ciao {st.session_state.nickname}!")
        if st.button("LOGOUT 🚪"):
            st.session_state.clear()
            st.rerun()

# --- 5. TABS ---
t1, t2, t3, t4, t5 = st.tabs(["🥘 CUCINA", "📦 DISPENSA", "🛒 SPESA", "📖 ARCHIVIO", "💬 FEEDBACK"])

with t1:
    st.header("Chef AI")
    if st.session_state.user_id:
        if st.button("📥 Importa Ingredienti dalla Dispensa"):
            res = supabase.table("dispensa").select("ingrediente").eq("user_id", st.session_state.user_id).execute()
            if res.data:
                st.session_state.ing_temp = ", ".join([i['ingrediente'] for i in res.data])
                st.rerun()
    
    ing = st.text_area("Cosa vuoi cucinare?", value=st.session_state.ing_temp)
    if st.button("CREA RICETTA ✨"):
        with st.spinner("Lo Chef sta pensando..."):
            r = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=[{"role":"user","content":f"Crea ricetta HTML per: {ing}"}])
            st.session_state.ultima_ricetta = r.choices[0].message.content
        st.rerun()
    
    if st.session_state.ultima_ricetta:
        st.markdown(st.session_state.ultima_ricetta, unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        col1.download_button("📄 Scarica PDF", data=format_pdf(st.session_state.ultima_ricetta), file_name="ricetta.pdf")
        if st.session_state.user_id:
            if col2.button("⭐ Salva in Archivio"):
                supabase.table("ricette").insert({"user_id":st.session_state.user_id, "contenuto":st.session_state.ultima_ricetta}).execute()
                st.toast("Salvata con successo!")

with t2:
    st.header("📦 Gestione Dispensa")
    if st.session_state.user_id:
        with st.form("dispensa_form", clear_on_submit=True):
            n = st.text_input("Nuovo ingrediente:")
            if st.form_submit_button("AGGIUNGI"):
                if n:
                    supabase.table("dispensa").insert({"user_id":st.session_state.user_id, "ingrediente":n}).execute()
                    st.rerun()
        # Mostra Lista
        data = supabase.table("dispensa").select("*").eq("user_id", st.session_state.user_id).execute()
        for i in data.data:
            c1, c2 = st.columns([5,1])
            c1.write(f"{get_emoji(i['ingrediente'])} {i['ingrediente']}")
            if c2.button("🗑️", key=f"del_i_{i['id']}"):
                supabase.table("dispensa").delete().eq("id", i['id']).execute()
                st.rerun()
    else:
        mostra_blocco("Dispensa")

with t3:
    st.header("🛒 Lista Spesa")
    if st.session_state.user_id:
        with st.form("spesa_form", clear_on_submit=True):
            s = st.text_input("Cosa manca?")
            if st.form_submit_button("METTI IN LISTA"):
                if s:
                    supabase.table("lista_spesa").insert({"user_id":st.session_state.user_id, "item":s}).execute()
                    st.rerun()
        # Mostra Lista
        items = supabase.table("lista_spesa").select("*").eq("user_id", st.session_state.user_id).execute()
        for it in items.data:
            c1, c2 = st.columns([5,1])
            c1.write(f"⬜ {it['item']}")
            if c2.button("✔️", key=f"del_s_{it['id']}"):
                supabase.table("lista_spesa").delete().eq("id", it['id']).execute()
                st.rerun()
    else:
        mostra_blocco("Spesa")

with t4:
    st.header("📖 Le Tue Ricette")
    if st.session_state.user_id:
        mie = supabase.table("ricette").select("*").eq("user_id", st.session_state.user_id).execute()
        if not mie.data: st.info("Nessuna ricetta salvata.")
        for r in mie.data:
            with st.expander(f"Ricetta del {r['created_at'][:10]}"):
                st.markdown(r['contenuto'], unsafe_allow_html=True)
                if st.button("Elimina Permanente", key=f"del_r_{r['id']}"):
                    supabase.table("ricette").delete().eq("id", r['id']).execute()
                    st.rerun()
    else:
        mostra_blocco("Archivio")

with t5:
    st.header("💬 Feedback App")
    if st.session_state.user_id:
        f_text = st.text_area("Cosa ne pensi?")
        voto = st.slider("Voto", 1, 5, 5)
        if st.button("INVIA"):
            supabase.table("feedback").insert({"user_id":st.session_state.user_id, "messaggio":f_text, "voto":voto}).execute()
            st.success("Ricevuto, grazie!")
    else:
        mostra_blocco("Feedback")
