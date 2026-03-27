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
    .stButton>button { width: 100%; border-radius: 10px; font-weight: bold; }
    </style>
""", unsafe_allow_html=True)

# API
URL = "https://ixkrnsarskqgwwuudqms.supabase.co"
KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Iml4a3Juc2Fyc2txZ3d3dXVkcW1zIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzM5Mjk5NDYsImV4cCI6MjA4OTUwNTk0Nn0.2_5BIu8g6bfjki91Uk_syMC7g8OTtQIb8yYnApEz3j8"
GROQ_AD = "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"

supabase = create_client(URL, KEY)
client = Groq(api_key=GROQ_AD)

# --- 2. FUNZIONI ---
def get_emoji(n):
    n = str(n).lower()
    m = {"uov":"🥚","pata":"🥔","carn":"🍗","past":"🍝","pomo":"🍅","form":"🧀","pesc":"🐟","lat":"🥛","olio":"🫗","pane":"🥖"}
    for k, v in m.items():
        if k in n: return v
    return "🟢"

def mostra_blocco_sezione(nome_chiave, msg):
    st.error(f"🔒 {msg}")
    if st.button("Vai al Login 👤", key=f"btn_l_{nome_chiave}"):
        st.info("Apri il menu in alto a sinistra!")
    st.info("Apri il menu in alto a sinistra!")

# --- 3. SESSION STATE ---
if "user_id" not in st.session_state: st.session_state.user_id = None
if "nickname" not in st.session_state: st.session_state.nickname = ""
if "ultima_ricetta" not in st.session_state: st.session_state.ultima_ricetta = ""

if not st.session_state.user_id:
    st.markdown('<div class="login-hint">⬅️ 📥 Login qui!</div>', unsafe_allow_html=True)

# --- 4. SIDEBAR ---
with st.sidebar:
    st.title("👤 Account")
    if st.session_state.user_id is None:
        modo = st.radio("Scegli:", ["Login", "Registrati"])
        with st.form("auth"):
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
                            st.success("Creato!")
                    st.rerun()
                except Exception as ex: st.error(ex)
    else:
        st.success(f"Ciao {st.session_state.nickname}!")
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
            st.session_state.ultima_ricetta = res.choices[0].message.content
    if st.session_state.ultima_ricetta:
        st.markdown(st.session_state.ultima_ricetta)

with t2:
    st.header("📦 La tua Dispensa")
    if st.session_state.user_id:
        with st.form("add_d"):
            nuovo = st.text_input("Aggiungi ingrediente:")
            if st.form_submit_button("SALVA"):
                if nuovo:
                    supabase.table("dispensa").insert({"user_id":st.session_state.user_id, "ingrediente":nuovo}).execute()
                    st.rerun()
        dati = supabase.table("dispensa").select("*").eq("user_id", st.session_state.user_id).execute()
        for i in dati.data:
            c1, c2 = st.columns([4,1])
            c1.write(f"{get_emoji(i['ingrediente'])} {i['ingrediente']}")
            if c2.button("🗑️", key=f"d_{i['id']}"):
                supabase.table("dispensa").delete().eq("id", i['id']).execute()
                st.rerun()
    else:
        mostra_blocco_sezione("dispensa", "Loggati per gestire la tua dispensa!")

with t3:
    st.header("🛒 Lista della Spesa")
    if st.session_state.user_id:
        with st.form("add_s"):
            item = st.text_input("Cosa manca?")
            if st.form_submit_button("AGGIUNGI"):
                if item:
                    supabase.table("lista_spesa").insert({"user_id":st.session_state.user_id, "item":item}).execute()
                    st.rerun()
        spesa = supabase.table("lista_spesa").select("*").eq("user_id", st.session_state.user_id).execute()
        for s in spesa.data:
            c1, c2 = st.columns([4,1])
            c1.write(f"⬜ {s['item']}")
            if c2.button("✔️", key=f"s_{s['id']}"):
                supabase.table("lista_spesa").delete().eq("id", s['id']).execute()
                st.rerun()
    else:
        mostra_blocco_sezione("spesa", "Loggati per salvare la lista della spesa!")

with t4:
    st.header("📖 Archivio")
    if st.session_state.user_id:
        mie = supabase.table("ricette").select("*").eq("user_id", st.session_state.user_id).execute()
        for r in mie.data:
            with st.expander(f"Ricetta del {r['created_at'][:10]}"):
                st.markdown(r['contenuto'])
                if st.button("Elimina", key=f"r_{r['id']}"):
                    supabase.table("ricette").delete().eq("id", r['id']).execute()
                    st.rerun()
    else:
        mostra_blocco_sezione("archivio", "Loggati per vedere le tue ricette salvate!")

with t5:
    st.header("💬 Feedback")
    if st.session_state.user_id:
        f = st.text_area("Suggerimenti?")
        if st.button("INVIA"):
            supabase.table("feedback").insert({"user_id":st.session_state.user_id, "messaggio":f}).execute()
            st.success("Grazie!")
    else:
        mostra_blocco_sezione("feedback", "Loggati per inviare un feedback!")
