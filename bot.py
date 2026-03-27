import streamlit as st
import stripe
from groq import Groq
from supabase import create_client
from fpdf import FPDF
import re

# --- 1. CONFIGURAZIONE E STILE ---
st.set_page_config(page_title="Svuotafrigo App", layout="wide")

st.markdown("""
    <style>
    @keyframes bounce { 0%, 20%, 50%, 80%, 100% {transform: translateX(0);} 40% {transform: translateX(10px);} 60% {transform: translateX(5px);} }
    .login-hint {
        position: fixed; top: 12px; left: 60px; z-index: 9999;
        background-color: #ff4b4b; color: white; padding: 6px 15px;
        border-radius: 20px; font-weight: bold; font-size: 14px;
        animation: bounce 2s infinite;
    }
    /* Stile per i bottoni standard di Streamlit per farli somigliare alla tua foto */
    .stButton>button { border-radius: 8px; }
    </style>
""", unsafe_allow_html=True)

# API
URL = "https://ixkrnsarskqgwwuudqms.supabase.co"
KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Iml4a3Juc2Fyc2txZ3d3dXVkcW1zIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzM5Mjk5NDYsImV4cCI6MjA4OTUwNTk0Nn0.2_5BIu8g6bfjki91Uk_syMC7g8OTtQIb8yYnApEz3j8"
GROQ_AD = "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"

supabase = create_client(URL, KEY)
client = Groq(api_key=GROQ_AD)

# --- 2. LA FUNZIONE CHE REPLICA IL TUO SCREENSHOT ---
def crea_blocco_identico(messaggio_rosso, chiave_bottone):
    # 1. Rettangolo Rosso (Errore)
    st.error(f"🔒 {messaggio_rosso}")
    
    # 2. Bottone Grigio "Vai al Login"
    if st.button("Vai al Login 👤", key=chiave_bottone):
        st.info("Apri il menu in alto a sinistra!")
        
    # 3. Rettangolo Blu (Info)
    st.info("Apri il menu in alto a sinistra!")

# --- 3. SESSION STATE ---
if "user_id" not in st.session_state: st.session_state.user_id = None
if "nickname" not in st.session_state: st.session_state.nickname = ""

if not st.session_state.user_id:
    st.markdown('<div class="login-hint">⬅️ 📥 Login qui!</div>', unsafe_allow_html=True)

# --- 4. SIDEBAR ---
with st.sidebar:
    st.title("👤 Account")
    if st.session_state.user_id is None:
        modo = st.radio("Scegli:", ["Login", "Registrati"])
        with st.form("auth_form"):
            e = st.text_input("Email")
            p = st.text_input("Password", type="password")
            n = st.text_input("Nickname") if modo == "Registrati" else ""
            if st.form_submit_button("Conferma"):
                try:
                    if modo == "Login":
                        res = supabase.auth.sign_in_with_password({"email": e, "password": p})
                        st.session_state.user_id = res.user.id
                        prof = supabase.table("profili").select("*").eq("id", res.user.id).execute()
                        if prof.data: st.session_state.nickname = prof.data[0]["nickname"]
                    else:
                        res = supabase.auth.sign_up({"email": e, "password": p})
                        if res.user:
                            supabase.table("profili").insert({"id": res.user.id, "nickname": n}).execute()
                            st.success("Account creato! Fai il login.")
                    st.rerun()
                except Exception as ex: st.error(ex)
    else:
        st.success(f"Loggato come: {st.session_state.nickname}")
        if st.button("Logout"):
            st.session_state.clear()
            st.rerun()

# --- 5. TABS ---
t1, t2, t3, t4, t5 = st.tabs(["🔥 Cucina AI", "📦 Dispensa", "🛒 Spesa", "📖 Archivio", "💬 Feedback"])

with t1:
    st.header("Generatore di Ricette")
    ing = st.text_area("Quali ingredienti hai?", placeholder="Es: uova, farina...")
    if st.button("Genera Ricetta ✨"):
        with st.spinner("Chef al lavoro..."):
            res = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=[{"role":"user","content":f"Ricetta per: {ing}"}])
            st.write(res.choices[0].message.content)

with t2:
    st.header("📦 La tua Dispensa")
    if st.session_state.user_id:
        st.write("Qui puoi gestire la tua dispensa...")
        # (Codice per aggiungere/eliminare ingredienti)
    else:
        crea_blocco_identico("Loggati per gestire la tua dispensa!", "btn_dispensa")

with t3:
    st.header("🛒 Lista della Spesa")
    if st.session_state.user_id:
        st.write("Qui puoi gestire la tua spesa...")
    else:
        # QUI REPLICHIAMO IL BLOCCO DELLA TUA FOTO
        crea_blocco_identico("Loggati per salvare la lista della spesa!", "btn_spesa")

with t4:
    st.header("📖 Archivio")
    if st.session_state.user_id:
        st.write("Qui vedi le tue ricette...")
    else:
        # QUI REPLICHIAMO IL BLOCCO DELLA TUA FOTO
        crea_blocco_identico("Loggati per vedere le tue ricette salvate!", "btn_archivio")

with t5:
    st.header("💬 Feedback")
    if st.session_state.user_id:
        st.write("Lascia un feedback...")
    else:
        # QUI REPLICHIAMO IL BLOCCO DELLA TUA FOTO
        crea_blocco_identico("Loggati per inviare un feedback!", "btn_feedback")
