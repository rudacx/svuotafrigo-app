import streamlit as st
import stripe
from groq import Groq
from supabase import create_client
from fpdf import FPDF
import re
import io

# --- 1. CONFIGURAZIONI E STILE ---
st.set_page_config(page_title="Svuotafrigo App", layout="wide")
st.markdown('<link rel="manifest" href="./manifest.json">', unsafe_allow_html=True)

# CSS per il fumetto "Login qui!" che sparisce dopo 60 secondi
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

# Database e API
URL = "https://ixkrnsarskqgwwuudqms.supabase.co"
KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Iml4a3Juc2Fyc2txZ3d3dXVkcW1zIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzM5Mjk5NDYsImV4cCI6MjA4OTUwNTk0Nn0.2_5BIu8g6bfjki91Uk_syMC7g8OTtQIb8yYnApEz3j8"
GROQ_AD = "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"
stripe.api_key = "sk_test_51TD7vwBBE2wDwi0CS5b18fA0sd6CqNclpupLdSZHVB9INo23zKGRErg3gtQL1ObzfztxfjCZY14wPUVQDBh98XeB00IeP2wsSK".strip()

ID_GOLD, ID_DIAMOND = "price_1TD86OBBE2wDwi0CI4KlvKFJ", "price_1TD88HBBE2wDwi0CV9d2heo2"

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
    mapping = {"uov": "🥚", "pata": "🥔", "carn": "🍗", "past": "🍝", "pomo": "🍅", "form": "🧀", "pesc": "🐟", "lat": "🥛", "olio": "🫗", "pane": "🥖"}
    for k, v in mapping.items():
        if k in n: return v
    return "🟢"

def login_message(tab_name):
    st.error(f"🔒 Accedi per usare la sezione {tab_name}")
    if st.button(f"Vai al Login 👤", key=f"go_log_{tab_name}"):
        st.info("Apri il menu in alto a sinistra (dove c'era il fumetto rosso)!")

# --- 3. SESSION STATE ---
if "user_id" not in st.session_state: st.session_state.user_id = None
if "is_premium" not in st.session_state: st.session_state.is_premium = False
if "nickname" not in st.session_state: st.session_state.nickname = ""
if "ultima_ricetta" not in st.session_state: st.session_state.ultima_ricetta = ""
if "ing_input" not in st.session_state: st.session_state.ing_input = ""
if "count_ospite" not in st.session_state: st.session_state.count_ospite = 0

# --- 4. SIDEBAR ---
st.sidebar.title("👤 Account")
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
            except Exception as e: st.error(f"Errore: {e}")
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
                macros = " Aggiungi tabella Macro e Kcal in HTML." if st.session_state.is_premium else ""
                prompt = f"Sei uno chef {mod}. Crea ricetta HTML elegante per: {ing}. Tempo: {tmp}.{macros}"
                res = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=[{"role": "user", "content": prompt}])
                st.session_state.ultima_ricetta = res.choices[0].message.content
                if not st.session_state.user_id: st.session_state.count_ospite += 1
            st.rerun()

    if st.session_state.ultima_ricetta:
        st.markdown(f'<div style="background:#1E1E1E; padding:20px; border-radius:10px; border-left:5px solid #ff4b4b;">{st.session_state.ultima_ricetta}</div>', unsafe_allow_html=True)
        col_v, col_p = st.columns(2)
        with col_v:
            if st.session_state.is_premium:
                txt = re.sub('<[^<]+?>', '', st.session_state.ultima_ricetta).replace("'", " ").replace("\n", " ")
                st.components.v1.html(f"<button id='v' style='width:100%; padding:10px; background:#ff4b4b; color:white; border:none; border-radius:5px;'>🔊 Leggi</button><script>document.getElementById('v').onclick=()=>{{const s=new SpeechSynthesisUtterance('{txt}');s.lang='it-IT';window.speechSynthesis.speak(s);}};</script>", height=60)
            else:
                if st.button("🔊 Sblocca Voce (Premium)"): st.warning("Passa a Diamond per la lettura vocale!")
        
        pdf_data = format_pdf(st.session_state.ultima_ricetta)
        col_p.download_button("📄 Scarica PDF", data=pdf_data, file_name="ricetta.pdf", mime="application/pdf", use_container_width=True)

with t2:
    if st.session_state.user_id:
        st.header("📦 La tua Dispensa")
        n_i = st.text_input("Aggiungi ingrediente:")
        if st.button("Salva ➕"):
            supabase.table("dispensa").insert({"user_id": st.session_state.user_id, "ingrediente": n_i}).execute()
            st.rerun()
        # Mostra gli ingredienti presenti
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
        m = st.text_input("Cosa devi comprare?")
        if st.button("Aggiungi alla lista 🛒"):
            supabase.table("lista_spesa").insert({"user_id": st.session_state.user_id, "item": m}).execute()
            st.rerun()
        # Mostra la lista spesa
        res_spesa = supabase.table("lista_spesa").select("*").eq("user_id", st.session_state.user_id).execute()
        for s in res_spesa.data:
            c1, c2 = st.columns([4,1])
            c1.write(f"⬜ {s['item']}")
            if c2.button("✔️", key=f"s_{s['id']}"):
                supabase.table("lista_spesa").delete().eq("id", s['id']).execute()
                st.rerun()
    else: login_message("Lista Spesa")

with t4:
    if st.session_state.user_id:
        st.header("📖 Archivio Ricette")
        mie = supabase.table("ricette").select("*").eq("user_id", st.session_state.user_id).execute()
        if not mie.data:
            st.info("Non hai ancora ricette salvate.")
        for r in mie.data:
            with st.expander(f"Ricetta del {r['created_at'][:10]} 🍴"):
                st.markdown(r['contenuto'], unsafe_allow_html=True)
                if st.button("Elimina Ricetta 🗑️", key=f"del_rec_{r['id']}"):
                    supabase.table("ricette").delete().eq("id", r['id']).execute()
                    st.rerun()
    else: login_message("Archivio")

with t5:
    if st.session_state.user_id:
        st.header("Feedback 📣")
        f_msg = st.text_area("Cosa ne pensi dell'app? Suggerimenti?")
        voto = st.slider("Voto", 1, 5, 5)
        if st.button("Invia Feedback 🚀"):
            if f_msg:
                supabase.table("feedback").insert({
                    "user_id": st.session_state.user_id, 
                    "messaggio": f_msg,
                    "voto": voto
                }).execute()
                st.success("Grazie! Il tuo feedback è stato inviato.")
            else:
                st.warning("Scrivi un messaggio prima di inviare.")
    else: login_message("Feedback")
