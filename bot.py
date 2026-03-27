import streamlit as st
import stripe
from groq import Groq
from supabase import create_client
from fpdf import FPDF
import re
import io

# --- 1. CONFIGURAZIONE E STILE ---
st.set_page_config(page_title="Svuotafrigo PRO v3", layout="wide")

# CSS TOTALE: Gestisce fumetto, bottoni giganti e layout
st.markdown("""
    <style>
    @keyframes fadeOut { 0% {opacity: 1;} 90% {opacity: 1;} 100% {opacity: 0; visibility: hidden;} }
    .login-hint {
        position: fixed; top: 12px; left: 60px; z-index: 999999;
        background-color: #ff4b4b; color: white; padding: 6px 15px;
        border-radius: 20px; font-weight: bold; font-size: 14px;
        animation: fadeOut 60s forwards;
        box-shadow: 2px 2px 10px rgba(0,0,0,0.3);
    }
    .stButton>button {
        width: 100% !important;
        border-radius: 12px !important;
        font-weight: bold !important;
        transition: 0.3s;
    }
    .login-btn-big>div>button {
        height: 5em !important;
        background-color: #ff4b4b !important;
        color: white !important;
        font-size: 18px !important;
        border: 2px solid white !important;
    }
    </style>
""", unsafe_allow_html=True)

# API E DATABASE
URL = "https://ixkrnsarskqgwwuudqms.supabase.co"
KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Iml4a3Juc2Fyc2txZ3d3dXVkcW1zIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzM5Mjk5NDYsImV4cCI6MjA4OTUwNTk0Nn0.2_5BIu8g6bfjki91Uk_syMC7g8OTtQIb8yYnApEz3j8"
GROQ_AD = "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"

supabase = create_client(URL, KEY)
client = Groq(api_key=GROQ_AD)

# --- 2. FUNZIONI UTILI ---
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
    return "🟢"

def block_screen(nome):
    st.error(f"🔒 La sezione {nome} è riservata.")
    st.markdown('<div class="login-btn-big">', unsafe_allow_html=True)
    if st.button(f"CLICCA QUI PER ACCEDERE E USARE {nome.upper()}", key=f"lock_{nome}"):
        st.info("Apri la barra laterale a sinistra per fare il Login!")
    st.markdown('</div>', unsafe_allow_html=True)

# --- 3. SESSION STATE ---
if "user_id" not in st.session_state: st.session_state.user_id = None
if "nickname" not in st.session_state: st.session_state.nickname = ""
if "ultima_ricetta" not in st.session_state: st.session_state.ultima_ricetta = ""
if "count_ospite" not in st.session_state: st.session_state.count_ospite = 0

# --- 4. SIDEBAR ---
with st.sidebar:
    st.title("👤 Account")
    if st.session_state.user_id is None:
        st.markdown('<div class="login-hint">⬅️ Login qui!</div>', unsafe_allow_html=True)
        opz = st.radio("Scegli:", ["Login", "Registrati"])
        with st.form("auth"):
            em = st.text_input("Email")
            pw = st.text_input("Password", type="password")
            nk = st.text_input("Nickname") if opz == "Registrati" else ""
            if st.form_submit_button("CONFERMA"):
                try:
                    if opz == "Login":
                        res = supabase.auth.sign_in_with_password({"email": em, "password": pw})
                        st.session_state.user_id = res.user.id
                        p = supabase.table("profili").select("*").eq("id", res.user.id).execute()
                        if p.data: st.session_state.nickname = p.data[0]["nickname"]
                    else:
                        res = supabase.auth.sign_up({"email": em, "password": pw})
                        if res.user:
                            supabase.table("profili").insert({"id": res.user.id, "nickname": nk}).execute()
                            st.success("Creato! Ora fai il login.")
                    st.rerun()
                except Exception as e: st.error(e)
    else:
        st.success(f"Ciao {st.session_state.nickname}!")
        if st.button("ESCI (LOGOUT)"):
            st.session_state.clear()
            st.rerun()

# --- 5. TABS ---
t1, t2, t3, t4, t5 = st.tabs(["🔥 CUCINA", "📦 DISPENSA", "🛒 SPESA", "📖 ARCHIVIO", "💬 FEEDBACK"])

with t1:
    st.header("Generatore Ricette AI")
    if st.session_state.user_id:
        if st.button("📥 Carica dalla Dispensa"):
            d = supabase.table("dispensa").select("ingrediente").eq("user_id", st.session_state.user_id).execute()
            st.session_state.ing_temp = ", ".join([x['ingrediente'] for x in d.data])
    
    ing = st.text_area("Cosa hai in frigo?", value=st.session_state.get('ing_temp', ""))
    if st.button("GENERA ORA ✨"):
        if not st.session_state.user_id and st.session_state.count_ospite >= 2:
            st.error("Limite ospite raggiunto!")
        else:
            with st.spinner("Chef al lavoro..."):
                res = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=[{"role":"user","content":f"Ricetta HTML per: {ing}"}])
                st.session_state.ultima_ricetta = res.choices[0].message.content
                if not st.session_state.user_id: st.session_state.count_ospite += 1
            st.rerun()

    if st.session_state.ultima_ricetta:
        st.markdown(st.session_state.ultima_ricetta, unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        c1.download_button("📄 Scarica PDF", data=format_pdf(st.session_state.ultima_ricetta), file_name="ricetta.pdf")
        if st.session_state.user_id:
            if c2.button("⭐ Salva in Archivio"):
                supabase.table("ricette").insert({"user_id":st.session_state.user_id, "contenuto":st.session_state.ultima_ricetta}).execute()
                st.toast("Salvata!")

with t2:
    st.header("La tua Dispensa")
    if st.session_state.user_id:
        nuovo = st.text_input("Aggiungi ingrediente:")
        if st.button("AGGIUNGI ➕"):
            if nuovo:
                supabase.table("dispensa").insert({"user_id":st.session_state.user_id, "ingrediente":nuovo}).execute()
                st.rerun()
        st.write("---")
        dati = supabase.table("dispensa").select("*").eq("user_id", st.session_state.user_id).execute()
        for i in dati.data:
            c1, c2 = st.columns([4,1])
            c1.write(f"{get_emoji(i['ingrediente'])} {i['ingrediente']}")
            if c2.button("🗑️", key=f"del_d_{i['id']}"):
                supabase.table("dispensa").delete().eq("id", i['id']).execute()
                st.rerun()
    else: block_screen("Dispensa")

with t3:
    st.header("Lista della Spesa")
    if st.session_state.user_id:
        s_item = st.text_input("Cosa comprare?")
        if st.button("METTI IN LISTA 🛒"):
            if s_item:
                supabase.table("lista_spesa").insert({"user_id":st.session_state.user_id, "item":s_item}).execute()
                st.rerun()
        st.write("---")
        spesa = supabase.table("lista_spesa").select("*").eq("user_id", st.session_state.user_id).execute()
        for s in spesa.data:
            c1, c2 = st.columns([4,1])
            c1.write(f"⬜ {s['item']}")
            if c2.button("✔️", key=f"del_s_{s['id']}"):
                supabase.table("lista_spesa").delete().eq("id", s['id']).execute()
                st.rerun()
    else: block_screen("Spesa")

with t4:
    st.header("Archivio Ricette")
    if st.session_state.user_id:
        mie = supabase.table("ricette").select("*").eq("user_id", st.session_state.user_id).execute()
        if not mie.data: st.info("Ancora niente qui.")
        for r in mie.data:
            with st.expander(f"Ricetta del {r['created_at'][:10]} 🍴"):
                st.markdown(r['contenuto'], unsafe_allow_html=True)
                if st.button("Elimina", key=f"dr_{r['id']}"):
                    supabase.table("ricette").delete().eq("id", r['id']).execute()
                    st.rerun()
    else: block_screen("Archivio")

with t5:
    st.header("Feedback")
    if st.session_state.user_id:
        msg = st.text_area("Suggerimenti?")
        voto = st.slider("Voto", 1, 5, 5)
        if st.button("INVIA"):
            supabase.table("feedback").insert({"user_id":st.session_state.user_id, "messaggio":msg, "voto":voto}).execute()
            st.success("Inviato!")
    else: block_screen("Feedback")
