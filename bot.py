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

# Manifest per PWA
st.markdown('<link rel="manifest" href="./manifest.json">', unsafe_allow_html=True)

# CSS Avanzato: Font Inter, Card Ricetta e Animazioni
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
    
    html, body, [class*="st-"] {
        font-family: 'Inter', sans-serif;
    }

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
    .login-hint:after {
        content: ''; position: absolute; left: -10px; top: 50%;
        margin-top: -10px; border-top: 10px solid transparent;
        border-bottom: 10px solid transparent; border-right: 10px solid #ff4b4b;
    }

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
    .recipe-card h1, .recipe-card h2, .recipe-card h3 {
        color: #ff4b4b !important;
        font-weight: 700;
    }
    .recipe-card ul, .recipe-card ol {
        margin-left: 20px;
    }
    </style>
""", unsafe_allow_html=True)

# API KEYS
URL = "https://ixkrnsarskqgwwuudqms.supabase.co"
KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Iml4a3Juc2Fyc2txZ3d3dXVkcW1zIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzM5Mjk5NDYsImV4cCI6MjA4OTUwNTk0Nn0.2_5BIu8g6bfjki91Uk_syMC7g8OTtQIb8yYnApEz3j8"
GROQ_AD = "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"
stripe.api_key = "sk_test_51TD7vwBBE2wDwi0CS5b18fA0sd6CqNclpupLdSZHVB9INo23zKGRErg3gtQL1ObzfztxfjCZY14wPUVQDBh98XeB00IeP2wsSK".strip()

ID_GOLD = "price_1TD86OBBE2wDwi0CI4KlvKFJ"
ID_DIAMOND = "price_1TD88HBBE2wDwi0CV9d2heo2"

supabase = create_client(URL, KEY)
client = Groq(api_key=GROQ_AD)

# --- 2. FUNZIONI DI SUPPORTO ---
def crea_sessione_stripe(id_prezzo):
    try:
        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{'price': id_prezzo, 'quantity': 1}],
            mode='subscription',
            success_url="https://svuotafrigo-app-4cvkjntg8gklzrkp5sjbuh.streamlit.app/",
            cancel_url="https://svuotafrigo-app-4cvkjntg8gklzrkp5sjbuh.streamlit.app/",
        )
        return session.url
    except Exception as e:
        st.error(f"Errore Stripe: {e}")
        return None

def format_pdf(text):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    clean_text = re.sub('<[^<]+?>', '', text)
    clean_text = clean_text.encode('latin-1', 'ignore').decode('latin-1')
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
if "is_premium" not in st.session_state: st.session_state.is_premium = False
if "nickname" not in st.session_state: st.session_state.nickname = ""
if "ultima_ricetta" not in st.session_state: st.session_state.ultima_ricetta = ""
if "ing_input" not in st.session_state: st.session_state.ing_input = ""
if "count_ospite" not in st.session_state: st.session_state.count_ospite = 0

# Richiamo Login se non loggato
if st.session_state.user_id is None:
    st.markdown('<div class="login-hint">⬅️ Login qui!</div>', unsafe_allow_html=True)

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
                    st.rerun()
                elif scelta == "Crea Account":
                    res = supabase.auth.sign_up({"email": email, "password": pwd})
                    if res.user:
                        supabase.table("profili").insert({"id": res.user.id, "nickname": nick}).execute()
                        st.success("Account creato! Fai il login.")
            except Exception as e: st.error(f"Errore: {e}")
else:
    st.sidebar.success(f"Ciao, {st.session_state.nickname}!")
    st.sidebar.write(f"Piano: {'💎 DIAMOND' if st.session_state.is_premium else '👨‍🍳 STANDARD'}")
    if not st.session_state.is_premium:
        opzione = st.sidebar.radio("Upgrade:", ["Gold €9,99", "Diamond €19,99"])
        if st.sidebar.button("Attiva Premium 💳"):
            url = crea_sessione_stripe(ID_DIAMOND if "Diamond" in opzione else ID_GOLD)
            if url: st.sidebar.link_button("Vai al pagamento", url)
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
    else:
        st.info("💡 **Tip:** Effettua il login per usare la tua dispensa salvata!")

    ing = st.text_area("Cosa hai in frigo?", value=st.session_state.ing_input)
    c1, c2 = st.columns(2)
    tmp = c1.selectbox("Tempo", ["15 min", "30 min", "60 min"])
    mod = c2.selectbox("Chef", ["Simpatico", "Professionale", "Cattivissimo"])

    if st.button("Genera Ricetta ✨", use_container_width=True):
        if not st.session_state.user_id and st.session_state.count_ospite >= 2:
            st.warning("⚠️ Limite raggiunto! Accedi per generare infinite ricette.")
        else:
            with st.spinner("Lo Chef sta scrivendo..."):
                macros = " Aggiungi tabella Macro e Kcal in HTML." if st.session_state.is_premium else ""
                prompt = f"Sei uno chef {mod}. Crea ricetta HTML (usa h2 per i titoli) per: {ing}. Tempo: {tmp}.{macros}"
                res = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=[{"role": "user", "content": prompt}])
                # Pulizia base per evitare errori "bourgabase"
                raw_content = res.choices[0].message.content
                st.session_state.ultima_ricetta = re.sub(r"```html|```", "", raw_content).strip()
                if not st.session_state.user_id: st.session_state.count_ospite += 1
            st.rerun()

    if st.session_state.ultima_ricetta:
        st.markdown(f'<div class="recipe-card">{st.session_state.ultima_ricetta}</div>', unsafe_allow_html=True)
        
        col_v, col_p, col_s = st.columns(3)
        
        with col_v:
            if st.session_state.is_premium:
                txt = re.sub('<[^<]+?>', '', st.session_state.ultima_ricetta).replace("'", " ").replace("\n", " ")
                st.components.v1.html(f"<button id='v' style='width:100%; padding:12px; background:#ff4b4b; color:white; border:none; border-radius:8px; cursor:pointer; font-weight:bold;'>🔊 Leggi</button><script>document.getElementById('v').onclick=()=>{{const s=new SpeechSynthesisUtterance('{txt}');s.lang='it-IT';window.speechSynthesis.speak(s);}};</script>", height=70)
            else:
                if st.button("🔊 Sblocca Voce (Premium)", use_container_width=True): st.toast("Passa a Diamond!")
        
        with col_p:
            pdf_data = format_pdf(st.session_state.ultima_ricetta)
            st.download_button("📄 Scarica PDF", data=pdf_data, file_name="ricetta.pdf", mime="application/pdf", use_container_width=True)
            
        with col_s:
            if st.session_state.user_id:
                if st.button("💾 Salva in Archivio", use_container_width=True):
                    try:
                        supabase.table("ricette").insert({
                            "user_id": st.session_state.user_id,
                            "contenuto": st.session_state.ultima_ricetta
                        }).execute()
                        st.success("Salvata nel Tab Archivio! 📖")
                    except Exception as e:
                        st.error("Errore salvataggio")
            else:
                st.button("💾 Salva (Login richiesto)", disabled=True, use_container_width=True)

with t2:
    st.header("📦 La tua Dispensa")
    if st.session_state.user_id:
        n_i = st.text_input("Aggiungi ingrediente:")
        if st.button("Salva ➕", key="btn_disp"):
            if n_i:
                supabase.table("dispensa").insert({"user_id": st.session_state.user_id, "ingrediente": n_i}).execute()
                st.rerun()
        for i in supabase.table("dispensa").select("*").eq("user_id", st.session_state.user_id).execute().data:
            c1, c2 = st.columns([4,1])
            c1.write(f"{get_emoji(i['ingrediente'])} {i['ingrediente']}")
            if c2.button("🗑️", key=f"d_{i['id']}"):
                supabase.table("dispensa").delete().eq("id", i['id']).execute()
                st.rerun()
    else:
        st.error("🔒 Loggati per gestire la tua dispensa!")

with t3:
    st.header("🛒 Lista della Spesa")
    if st.session_state.user_id:
        m = st.text_input("Cosa devi comprare?", key="input_spesa")
        if st.button("Aggiungi 🛒", key="btn_spesa"):
            if m:
                supabase.table("lista_spesa").insert({"user_id": st.session_state.user_id, "item": m}).execute()
                st.rerun()
        for s in supabase.table("lista_spesa").select("*").eq("user_id", st.session_state.user_id).execute().data:
            c1, c2 = st.columns([4,1])
            c1.write(f"⬜ {s['item']}")
            if c2.button("✔️", key=f"s_{s['id']}"):
                supabase.table("lista_spesa").delete().eq("id", s['id']).execute()
                st.rerun()
    else:
        st.error("🔒 Loggati per salvare la lista della spesa!")

with t4:
    st.header("📖 Archivio Ricette")
    if st.session_state.user_id:
        mie = supabase.table("ricette").select("*").eq("user_id", st.session_state.user_id).order("created_at", desc=True).execute()
        if not mie.data:
            st.info("Non hai ancora ricette salvate.")
        for r in mie.data:
            with st.expander(f"🍴 Ricetta del {r['created_at'][:10]} {r['created_at'][11:16]}"):
                st.markdown(r['contenuto'], unsafe_allow_html=True)
                if st.button("Elimina Ricetta", key=f"del_arc_{r['id']}"):
                    supabase.table("ricette").delete().eq("id", r['id']).execute()
                    st.rerun()
    else:
        st.error("🔒 Loggati per consultare il tuo archivio!")

with t5:
    st.header("Feedback 📣")
    if st.session_state.user_id:
        f = st.text_area("Come possiamo migliorare?")
        if st.button("Invia Feedback 🚀"):
            if f:
                supabase.table("feedback").insert({"user_id": st.session_state.user_id, "messaggio": f}).execute()
                st.success("Ricevuto, grazie!")
    else:
        st.warning("Accedi per inviarci un feedback.")
