import streamlit as st
import stripe
from groq import Groq
from supabase import create_client
from fpdf import FPDF
import re
import io

# --- 1. CONFIGURAZIONI E DESIGN (CSS) ---
st.set_page_config(page_title="Svuotafrigo App", layout="wide")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap');
    
    /* Reset Font */
    html, body, [class*="st-"] {
        font-family: 'Inter', sans-serif;
    }

    /* Card della Ricetta */
    .recipe-container {
        background-color: #1a1c24;
        border: 1px solid #30363d;
        border-radius: 16px;
        padding: 30px;
        margin-top: 20px;
        box-shadow: 0 10px 30px rgba(0,0,0,0.4);
        color: #e6edf3;
    }
    .recipe-container h1, .recipe-container h2 { color: #ff4b4b !important; font-weight: 700; }
    .recipe-container strong { color: #ff4b4b; }

    /* Box Messaggio Errore/Login */
    .login-lock-box {
        background: rgba(255, 75, 75, 0.05);
        border: 1px dashed #ff4b4b;
        border-radius: 12px;
        padding: 40px;
        text-align: center;
        margin: 20px 0;
    }

    /* Hint Login Animato */
    .login-hint {
        position: fixed; top: 12px; left: 60px; z-index: 9999;
        background: #ff4b4b;
        color: white; padding: 8px 18px; border-radius: 50px;
        font-weight: 600; font-size: 13px; animation: bounce 2s infinite;
    }
    @keyframes bounce { 0%, 100% {transform: translateX(0);} 50% {transform: translateX(10px);} }
    </style>
""", unsafe_allow_html=True)

# API KEYS
URL = "https://ixkrnsarskqgwwuudqms.supabase.co"
KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Iml4a3Juc2Fyc2txZ3d3dXVkcW1zIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzM5Mjk5NDYsImV4cCI6MjA4OTUwNTk0Nn0.2_5BIu8g6bfjki91Uk_syMC7g8OTtQIb8yYnApEz3j8"
GROQ_AD = "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"
stripe.api_key = "sk_test_51TD7vwBBE2wDwi0CS5b18fA0sd6CqNclpupLdSZHVB9INo23zKGRErg3gtQL1ObzfztxfjCZY14wPUVQDBh98XeB00IeP2wsSK".strip()

supabase = create_client(URL, KEY)
client = Groq(api_key=GROQ_AD)

# --- 2. FUNZIONI DI SUPPORTO ---
def pulisci_output_ai(testo):
    """Rimuove i blocchi di codice markdown e il testo extra dell'IA"""
    testo = re.sub(r"```html", "", testo, flags=re.IGNORECASE)
    testo = re.sub(r"```", "", testo)
    return testo.strip()

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

# --- 3. SESSION STATE ---
if "user_id" not in st.session_state: st.session_state.user_id = None
if "nickname" not in st.session_state: st.session_state.nickname = ""
if "is_premium" not in st.session_state: st.session_state.is_premium = False
if "ultima_ricetta" not in st.session_state: st.session_state.ultima_ricetta = ""

# --- 4. SIDEBAR ---
with st.sidebar:
    st.title("👤 Account")
    if st.session_state.user_id is None:
        st.markdown('<div class="login-hint">⬅️ Login qui!</div>', unsafe_allow_html=True)
        modo = st.radio("Scegli:", ["Login", "Registrati"])
        with st.form("auth"):
            email = st.text_input("Email")
            pwd = st.text_input("Password", type="password")
            nick = st.text_input("Nickname") if modo == "Registrati" else ""
            if st.form_submit_button("CONFERMA"):
                try:
                    if modo == "Login":
                        res = supabase.auth.sign_in_with_password({"email": email, "password": pwd})
                        st.session_state.user_id = res.user.id
                        p = supabase.table("profili").select("*").eq("id", res.user.id).execute()
                        if p.data: 
                            st.session_state.nickname = p.data[0]["nickname"]
                            st.session_state.is_premium = p.data[0].get("is_premium", False)
                    else:
                        res = supabase.auth.sign_up({"email": email, "password": pwd})
                        if res.user:
                            supabase.table("profili").insert({"id": res.user.id, "nickname": nick}).execute()
                            st.success("Account creato! Accedi.")
                    st.rerun()
                except: st.error("Errore autenticazione")
    else:
        st.success(f"Ciao, {st.session_state.nickname}!")
        if st.button("Logout 🚪", use_container_width=True):
            st.session_state.clear()
            st.rerun()

# --- 5. TABS ---
t1, t2, t3, t4 = st.tabs(["🔥 Cucina AI", "📦 Dispensa", "🛒 Spesa", "📖 Archivio"])

with t1:
    st.header("Chef Virtuale")
    ing = st.text_area("Cosa hai in frigo?", placeholder="Esempio: uova, farina, latte...")
    
    if st.button("GENERA RICETTA ✨", use_container_width=True):
        with st.spinner("Lo Chef sta cucinando..."):
            prompt = f"Sei uno chef stellato. Genera SOLO codice HTML (usa h2 e li) per una ricetta con: {ing}. Non aggiungere spiegazioni prima o dopo."
            res = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=[{"role": "user", "content": prompt}])
            st.session_state.ultima_ricetta = pulisci_output_ai(res.choices[0].message.content)
            st.rerun()

    if st.session_state.ultima_ricetta:
        st.markdown(f'<div class="recipe-container">{st.session_state.ultima_ricetta}</div>', unsafe_allow_html=True)
        cv, cp = st.columns(2)
        with cv:
            if st.session_state.is_premium:
                txt = re.sub('<[^<]+?>', '', st.session_state.ultima_ricetta).replace("'", "\\'")
                st.components.v1.html(f"""
                    <button id='v' style='width:100%; padding:12px; background:#ff4b4b; color:white; border:none; border-radius:8px; font-weight:bold; cursor:pointer;'>🔊 ASCOLTA</button>
                    <script>
                        document.getElementById('v').onclick = () => {{
                            const u = new SpeechSynthesisUtterance('{txt}');
                            u.lang = 'it-IT';
                            window.speechSynthesis.speak(u);
                        }};
                    </script>
                """, height=70)
            else:
                st.button("🔊 Sblocca Voce (Premium)", disabled=True, use_container_width=True)
        with cp:
            pdf = format_pdf(st.session_state.ultima_ricetta)
            st.download_button("📄 PDF", data=pdf, file_name="ricetta.pdf", use_container_width=True)

with t2:
    if st.session_state.user_id:
        st.header("📦 La tua Dispensa")
        n = st.text_input("Aggiungi ingrediente:")
        if st.button("Aggiungi"):
            supabase.table("dispensa").insert({"user_id": st.session_state.user_id, "ingrediente": n}).execute()
            st.rerun()
        items = supabase.table("dispensa").select("*").eq("user_id", st.session_state.user_id).execute().data
        for i in items:
            c1, c2 = st.columns([5,1])
            c1.write(f"{get_emoji(i['ingrediente'])} {i['ingrediente']}")
            if c2.button("🗑️", key=i['id']):
                supabase.table("dispensa").delete().eq("id", i['id']).execute()
                st.rerun()
    else:
        st.markdown('<div class="login-lock-box">🔒 Accedi per la Dispensa</div>', unsafe_allow_html=True)

with t3:
    if st.session_state.user_id:
        st.header("🛒 Lista Spesa")
        s_item = st.text_input("Cosa comprare?")
        if st.button("Salva Spesa"):
            supabase.table("lista_spesa").insert({"user_id": st.session_state.user_id, "item": s_item}).execute()
            st.rerun()
        lista = supabase.table("lista_spesa").select("*").eq("user_id", st.session_state.user_id).execute().data
        for s in lista:
            c1, c2 = st.columns([5,1])
            c1.write(f"⬜ {s['item']}")
            if c2.button("✔️", key=f"s_{s['id']}"):
                supabase.table("lista_spesa").delete().eq("id", s['id']).execute()
                st.rerun()
    else:
        st.markdown('<div class="login-lock-box">🔒 Accedi per la Spesa</div>', unsafe_allow_html=True)

with t4:
    if st.session_state.user_id:
        st.header("📖 Archivio")
        m = supabase.table("ricette").select("*").eq("user_id", st.session_state.user_id).execute().data
        for r in m:
            with st.expander(f"Ricetta del {r['created_at'][:10]}"):
                st.markdown(r['contenuto'], unsafe_allow_html=True)
    else:
        st.markdown('<div class="login-lock-box">🔒 Accedi per l\'Archivio</div>', unsafe_allow_html=True)
