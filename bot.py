import streamlit as st
import stripe
from groq import Groq
from supabase import create_client
from fpdf import FPDF
import re
import io

# --- 1. CONFIGURAZIONI E STILE ---
st.set_page_config(page_title="Svuotafrigo App", layout="wide")

# CSS per il fumetto "Login qui!" e per i bottoni giganti rossi
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
    /* Stile per i bottoni di login nelle TAB */
    .stButton>button { 
        width: 100%; 
        border-radius: 15px; 
        font-weight: bold; 
        height: 4em; 
        background-color: #ff4b4b; 
        color: white;
        border: 2px solid white;
    }
    </style>
""", unsafe_allow_html=True)

# Mostra il fumetto solo se non loggato
if "user_id" not in st.session_state or st.session_state.user_id is None:
    st.markdown('<div class="login-hint">⬅️ Clicca qui per il Login!</div>', unsafe_allow_html=True)

# API KEYS (Le tue chiavi originali)
URL = "https://ixkrnsarskqgwwuudqms.supabase.co"
KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Iml4a3Juc2Fyc2txZ3d3dXVkcW1zIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzM5Mjk5NDYsImV4cCI6MjA4OTUwNTk0Nn0.2_5BIu8g6bfjki91Uk_syMC7g8OTtQIb8yYnApEz3j8"
GROQ_AD = "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"

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

def mostra_tasto_login(nome_sezione):
    st.error(f"🔒 La sezione **{nome_sezione}** è riservata agli utenti registrati.")
    st.write("---")
    if st.button(f"🚀 ACCEDI ORA PER USARE {nome_sezione.upper()}", key=f"login_btn_{nome_sezione}"):
        st.info("Clicca sulle due freccette '>>' in alto a sinistra per aprire il pannello di Login!")

# --- 3. SESSION STATE ---
if "user_id" not in st.session_state: st.session_state.user_id = None
if "nickname" not in st.session_state: st.session_state.nickname = ""
if "ultima_ricetta" not in st.session_state: st.session_state.ultima_ricetta = ""
if "count_ospite" not in st.session_state: st.session_state.count_ospite = 0

# --- 4. SIDEBAR (LOGIN/REGISTRAZIONE) ---
with st.sidebar:
    st.title("👤 Area Personale")
    if st.session_state.user_id is None:
        mode = st.radio("Cosa vuoi fare?", ["Login", "Registrati"])
        with st.form("auth_form"):
            e = st.text_input("Email")
            p = st.text_input("Password", type="password")
            n = st.text_input("Nickname (solo per registrazione)") if mode == "Registrati" else ""
            submit = st.form_submit_button("CONFERMA")
            if submit:
                try:
                    if mode == "Login":
                        res = supabase.auth.sign_in_with_password({"email": e, "password": p})
                        st.session_state.user_id = res.user.id
                        prof = supabase.table("profili").select("*").eq("id", res.user.id).execute()
                        if prof.data: st.session_state.nickname = prof.data[0]["nickname"]
                    else:
                        res = supabase.auth.sign_up({"email": e, "password": p})
                        if res.user:
                            supabase.table("profili").insert({"id": res.user.id, "nickname": n}).execute()
                            st.success("Registrato! Ora fai il login.")
                    st.rerun()
                except Exception as ex: st.error(f"Errore: {ex}")
    else:
        st.success(f"Loggato come: {st.session_state.nickname}")
        if st.button("LOGOUT 🚪"):
            st.session_state.clear()
            st.rerun()

# --- 5. TABS PRINCIPALI ---
t1, t2, t3, t4, t5 = st.tabs(["🔥 Cucina AI", "📦 Dispensa", "🛒 Spesa", "📖 Archivio", "💬 Feedback"])

# --- TAB 1: CUCINA ---
with t1:
    st.header("Generatore di Ricette")
    if not st.session_state.user_id:
        st.warning(f"Sei in modalità Ospite. Generazioni rimaste: {2 - st.session_state.count_ospite}")
    
    # Se loggato, può caricare dalla dispensa
    if st.session_state.user_id:
        if st.button("📥 Carica ingredienti dalla Dispensa"):
            items = supabase.table("dispensa").select("ingrediente").eq("user_id", st.session_state.user_id).execute()
            if items.data:
                st.session_state.temp_ing = ", ".join([i['ingrediente'] for i in items.data])
            else:
                st.info("La tua dispensa è vuota!")

    ing_input = st.text_area("Cosa hai in frigo?", value=getattr(st.session_state, 'temp_ing', ""))
    
    if st.button("GENERA RICETTA ✨"):
        if not st.session_state.user_id and st.session_state.count_ospite >= 2:
            st.error("Hai esaurito le prove gratuite! Accedi per continuare.")
        elif not ing_input:
            st.warning("Inserisci almeno un ingrediente!")
        else:
            with st.spinner("Lo Chef sta scrivendo..."):
                res = client.chat.completions.create(
                    model="llama-3.3-70b-versatile", 
                    messages=[{"role": "user", "content": f"Sei uno chef stellato. Crea una ricetta professionale in HTML con questi ingredienti: {ing_input}"}]
                )
                st.session_state.ultima_ricetta = res.choices[0].message.content
                if not st.session_state.user_id: st.session_state.count_ospite += 1
            st.rerun()

    if st.session_state.ultima_ricetta:
        st.markdown(st.session_state.ultima_ricetta, unsafe_allow_html=True)
        # Tasti per scaricare o salvare
        c1, c2 = st.columns(2)
        with c1:
            st.download_button("📄 Scarica PDF", data=format_pdf(st.session_state.ultima_ricetta), file_name="ricetta.pdf")
        with c2:
            if st.session_state.user_id:
                if st.button("⭐ Salva in Archivio"):
                    supabase.table("ricette").insert({"user_id": st.session_state.user_id, "contenuto": st.session_state.ultima_ricetta}).execute()
                    st.success("Salvata!")

# --- TAB 2: DISPENSA ---
with t2:
    st.header("📦 La tua Dispensa")
    if st.session_state.user_id:
        with st.form("add_dispensa"):
            nuovo = st.text_input("Aggiungi ingrediente:")
            if st.form_submit_button("AGGIUNGI ➕"):
                if nuovo:
                    supabase.table("dispensa").insert({"user_id": st.session_state.user_id, "ingrediente": nuovo}).execute()
                    st.rerun()
        
        st.subheader("I tuoi prodotti:")
        dati = supabase.table("dispensa").select("*").eq("user_id", st.session_state.user_id).execute()
        for i in dati.data:
            col_a, col_b = st.columns([4,1])
            col_a.write(f"{get_emoji(i['ingrediente'])} {i['ingrediente']}")
            if col_b.button("🗑️", key=f"del_d_{i['id']}"):
                supabase.table("dispensa").delete().eq("id", i['id']).execute()
                st.rerun()
    else:
        mostra_tasto_login("Dispensa")

# --- TAB 3: SPESA ---
with t3:
    st.header("🛒 Lista della Spesa")
    if st.session_state.user_id:
        with st.form("add_spesa"):
            item_spesa = st.text_input("Cosa devi comprare?")
            if st.form_submit_button("AGGIUNGI ALLA LISTA 🛒"):
                if item_spesa:
                    supabase.table("lista_spesa").insert({"user_id": st.session_state.user_id, "item": item_spesa}).execute()
                    st.rerun()
        
        st.subheader("Da comprare:")
        lista = supabase.table("lista_spesa").select("*").eq("user_id", st.session_state.user_id).execute()
        for s in lista.data:
            col_a, col_b = st.columns([4,1])
            col_a.write(f"⬜ {s['item']}")
            if col_b.button("✔️", key=f"del_s_{s['id']}"):
                supabase.table("lista_spesa").delete().eq("id", s['id']).execute()
                st.rerun()
    else:
        mostra_tasto_login("Lista della Spesa")

# --- TAB 4: ARCHIVIO ---
with t4:
    st.header("📖 Archivio Ricette")
    if st.session_state.user_id:
        ricette_salvate = supabase.table("ricette").select("*").eq("user_id", st.session_state.user_id).execute()
        if not ricette_salvate.data:
            st.info("Non hai ancora salvato nessuna ricetta.")
        for r in ricette_salvate.data:
            with st.expander(f"Ricetta del {r['created_at'][:10]} 🍴"):
                st.markdown(r['contenuto'], unsafe_allow_html=True)
                if st.button("Elimina 🗑️", key=f"del_r_{r['id']}"):
                    supabase.table("ricette").delete().eq("id", r['id']).execute()
                    st.rerun()
    else:
        mostra_tasto_login("Archivio")

# --- TAB 5: FEEDBACK ---
with t5:
    st.header("💬 Feedback")
    if st.session_state.user_id:
        msg = st.text_area("Cosa possiamo migliorare?")
        voto = st.slider("Voto da 1 a 5", 1, 5, 5)
        if st.button("INVIA FEEDBACK 🚀"):
            if msg:
                supabase.table("feedback").insert({
                    "user_id": st.session_state.user_id, 
                    "messaggio": msg, 
                    "voto": voto
                }).execute()
                st.success("Grazie mille!")
    else:
        mostra_tasto_login("Feedback")s
