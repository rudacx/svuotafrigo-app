import streamlit as st
import stripe
from groq import Groq
from supabase import create_client
from fpdf import FPDF
import re
import io

# --- 1. CONFIGURAZIONI E DESIGN ---
st.set_page_config(page_title="Svuotafrigo App", layout="wide")

# CSS per il richiamo "Login qui!" e stile schede
st.markdown("""
    <style>
    @keyframes bounce {
        0%, 20%, 50%, 80%, 100% {transform: translateX(0);}
        40% {transform: translateX(10px);}
        60% {transform: translateX(5px);}
    }
    .login-hint {
        position: fixed; top: 12px; left: 60px; z-index: 999999;
        background-color: #ff4b4b; color: white; padding: 6px 15px;
        border-radius: 20px; font-weight: bold; font-size: 14px;
        animation: bounce 2s infinite; box-shadow: 2px 2px 10px rgba(0,0,0,0.3);
    }
    .login-hint:after {
        content: ''; position: absolute; left: -10px; top: 50%;
        margin-top: -10px; border-top: 10px solid transparent;
        border-bottom: 10px solid transparent; border-right: 10px solid #ff4b4b;
    }
    .recipe-container {
        background:#1E1E1E; padding:25px; border-radius:15px; 
        border-left:6px solid #ff4b4b; color: white; 
        box-shadow: 0 4px 15px rgba(0,0,0,0.5); margin-bottom: 20px;
    }
    </style>
""", unsafe_allow_html=True)

# API KEYS
URL = "https://ixkrnsarskqgwwuudqms.supabase.co"
KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Iml4a3Juc2Fyc2txZ3d3dXVkcW1zIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzM5Mjk5NDYsImV4cCI6MjA4OTUwNTk0Nn0.2_5BIu8g6bfjki91Uk_syMC7g8OTtQIb8yYnApEz3j8"
GROQ_AD = "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"
stripe.api_key = "sk_test_51TD7vwBBE2wDwi0CS5b18fA0sd6CqNclpupLdSZHVB9INo23zKGRErg3gtQL1ObzfztxfjCZY14wPUVQDBh98XeB00IeP2wsSK"

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
    clean_text = re.sub('<[^<]+?>', '', text).encode('latin-1', 'ignore').decode('latin-1')
    pdf.multi_cell(0, 10, txt=clean_text)
    return pdf.output(dest='S').encode('latin-1')

def get_emoji(n):
    n = str(n).lower()
    mapping = {"uov": "🥚", "pata": "🥔", "carn": "🍗", "past": "🍝", "pomo": "🍅", "form": "🧀", "pesc": "🐟", "lat": "🥛"}
    for k, v in mapping.items():
        if k in n: return v
    return "🟢"

# --- 3. SESSION STATE ---
for key, val in {"user_id": None, "is_premium": False, "nickname": "", "ultima_ricetta": "", "ing_input": "", "count_ospite": 0}.items():
    if key not in st.session_state: st.session_state[key] = val

# --- 4. SIDEBAR ---
if st.session_state.user_id is None:
    st.markdown('<div class="login-hint">⬅️ Login qui!</div>', unsafe_allow_html=True)

st.sidebar.title("👤 Account")
if st.session_state.user_id is None:
    scelta = st.sidebar.selectbox("Cosa vuoi fare?", ["Login", "Crea Account"])
    with st.sidebar.form("auth_form"):
        email = st.text_input("Email")
        pwd = st.text_input("Password", type="password")
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
                else:
                    res = supabase.auth.sign_up({"email": email, "password": pwd})
                    if res.user:
                        supabase.table("profili").insert({"id": res.user.id, "nickname": nick}).execute()
                        st.success("Account creato! Accedi ora.")
                st.rerun()
            except: st.error("Errore autenticazione. Riprova.")
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
                prompt = f"Sei uno chef {mod}. Crea ricetta HTML (usa h2 e li) per: {ing}. Tempo: {tmp}.{macros}"
                res = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=[{"role": "user", "content": prompt}])
                st.session_state.ultima_ricetta = res.choices[0].message.content
                if not st.session_state.user_id: st.session_state.count_ospite += 1
                st.rerun()

    if st.session_state.ultima_ricetta:
        st.markdown(f'<div class="recipe-container">{st.session_state.ultima_ricetta}</div>', unsafe_allow_html=True)
        col_v, col_p = st.columns(2)
        with col_v:
            if st.session_state.is_premium:
                # Sanificazione testo per JS
                txt_js = re.sub('<[^<]+?>', '', st.session_state.ultima_ricetta).replace("'", "\\'").replace("\n", " ")
                st.components.v1.html(f"""
                    <div style="background: #262730; padding: 10px; border-radius: 10px; border: 1px solid #444; display: flex; align-items: center; justify-content: center; font-family: sans-serif;">
                        <button id="playBtn" style="background: #ff4b4b; border: none; color: white; padding: 10px 20px; border-radius: 5px; cursor: pointer; font-weight: bold; display: flex; align-items: center; gap: 10px;">
                            <span id="icon">▶️</span> Ascolta la Ricetta
                        </button>
                    </div>
                    <script>
                        const btn = document.getElementById('playBtn');
                        const icon = document.getElementById('icon');
                        let speaking = false;
                        const synth = window.speechSynthesis;
                        const utter = new SpeechSynthesisUtterance('{txt_js}');
                        utter.lang = 'it-IT';
                        utter.onend = () => {{ speaking = false; icon.innerText = '▶️'; }};
                        btn.onclick = () => {{
                            if(!speaking) {{ synth.speak(utter); speaking = true; icon.innerText = '⏸️'; }}
                            else {{ synth.cancel(); speaking = false; icon.innerText = '▶️'; }}
                        }};
                    </script>
                """, height=80)
            else:
                st.button("🔊 Sblocca Voce (Premium)", disabled=True, use_container_width=True)
        
        pdf_data = format_pdf(st.session_state.ultima_ricetta)
        col_p.download_button("📄 Scarica PDF", data=pdf_data, file_name="ricetta.pdf", use_container_width=True)

# --- TAB DISPENSA E ALTRI (Logica Supabase) ---
with t2:
    st.header("📦 La tua Dispensa")
    if st.session_state.user_id:
        n_i = st.text_input("Aggiungi ingrediente:")
        if st.button("Salva ➕"):
            if n_i:
                supabase.table("dispensa").insert({"user_id": st.session_state.user_id, "ingrediente": n_i}).execute()
                st.rerun()
        for i in supabase.table("dispensa").select("*").eq("user_id", st.session_state.user_id).execute().data:
            c1, c2 = st.columns([4,1])
            c1.write(f"{get_emoji(i['ingrediente'])} {i['ingrediente']}")
            if c2.button("🗑️", key=f"d_{i['id']}"):
                supabase.table("dispensa").delete().eq("id", i['id']).execute()
                st.rerun()
    else: st.error("🔒 Effettua il login per gestire la dispensa!")

with t3:
    st.header("🛒 Lista della Spesa")
    if st.session_state.user_id:
        m = st.text_input("Cosa comprare?")
        if st.button("Aggiungi 🛒"):
            if m:
                supabase.table("lista_spesa").insert({"user_id": st.session_state.user_id, "item": m}).execute()
                st.rerun()
        for s in supabase.table("lista_spesa").select("*").eq("user_id", st.session_state.user_id).execute().data:
            c1, c2 = st.columns([4,1])
            c1.write(f"⬜ {s['item']}")
            if c2.button("✔️", key=f"s_{s['id']}"):
                supabase.table("lista_spesa").delete().eq("id", s['id']).execute()
                st.rerun()
    else: st.error("🔒 Login richiesto.")

with t4:
    st.header("📖 Archivio")
    if st.session_state.user_id:
        # Qui potresti aggiungere un tasto "Salva Ricetta" nel Tab 1 per popolare questa tabella
        ricette = supabase.table("ricette").select("*").eq("user_id", st.session_state.user_id).execute()
        for r in ricette.data:
            with st.expander(f"Ricetta del {r['created_at'][:10]}"):
                st.markdown(r['contenuto'], unsafe_allow_html=True)
    else: st.error("🔒 Login richiesto.")

with t5:
    st.header("Feedback 📣")
    if st.session_state.user_id:
        f = st.text_area("Suggerimenti?")
        if st.button("Invia 🚀"):
            if f:
                supabase.table("feedback").insert({"user_id": st.session_state.user_id, "messaggio": f}).execute()
                st.success("Grazie!")
    else: st.error("🔒 Login richiesto.")
