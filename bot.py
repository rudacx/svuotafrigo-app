import streamlit as st
import stripe
from groq import Groq
from supabase import create_client
from fpdf import FPDF
import re
import io

# --- 1. CONFIGURAZIONI E DESIGN PREMIUM (CSS) ---
st.set_page_config(page_title="Svuotafrigo AI", layout="wide", initial_sidebar_state="expanded")

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
    }
    .recipe-container h2 { color: #ff4b4b; font-weight: 700; border-bottom: 1px solid #30363d; padding-bottom: 10px; }
    .recipe-container ul { list-style-type: none; padding-left: 0; }
    .recipe-container li::before { content: "• "; color: #ff4b4b; font-weight: bold; }

    /* Box Messaggio Errore/Login Personalizzato */
    .login-lock-box {
        background: rgba(255, 75, 75, 0.05);
        border: 1px dashed #ff4b4b;
        border-radius: 12px;
        padding: 40px;
        text-align: center;
        margin: 20px 0;
    }

    /* Hint Login Animato in alto a sinistra */
    .login-hint {
        position: fixed; top: 12px; left: 60px; z-index: 9999;
        background: linear-gradient(135deg, #ff4b4b, #ff7575);
        color: white; padding: 8px 18px; border-radius: 50px;
        font-weight: 600; font-size: 13px; animation: bounce 2s infinite;
        box-shadow: 0 4px 15px rgba(255, 75, 75, 0.4);
    }
    @keyframes bounce { 0%, 20%, 50%, 80%, 100% {transform: translateX(0);} 40% {transform: translateX(10px);} 60% {transform: translateX(5px);} }

    /* Miglioramento Bottoni */
    .stButton>button {
        border-radius: 10px;
        font-weight: 600;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    }
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 5px 15px rgba(255, 75, 75, 0.2);
    }
    </style>
""", unsafe_allow_html=True)

# API KEYS
URL = "https://ixkrnsarskqgwwuudqms.supabase.co"
KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Iml4a3Juc2Fyc2txZ3d3dXVkcW1zIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzM5Mjk5NDYsImV4cCI6MjA4OTUwNTk0Nn0.2_5BIu8g6bfjki91Uk_syMC7g8OTtQIb8yYnApEz3j8"
GROQ_AD = "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"
stripe.api_key = "sk_test_51TD7vwBBE2wDwi0CS5b18fA0sd6CqNclpupLdSZHVB9INo23zKGRErg3gtQL1ObzfztxfjCZY14wPUVQDBh98XeB00IeP2wsSK".strip()

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
    mapping = {"uov": "🥚", "pata": "🥔", "carn": "🍗", "past": "🍝", "pomo": "🍅", "form": "🧀", "pesc": "🐟", "lat": "🥛", "olio": "🫗", "pane": "🥖"}
    for k, v in mapping.items():
        if k in n: return v
    return "🟢"

def show_login_lock(sezione_nome):
    st.markdown(f"""
        <div class="login-lock-box">
            <h2 style="color:#ff4b4b; margin:0;">🔒 Sezione Riservata</h2>
            <p style="color:#8b949e; font-size:1.1em;">Accedi per salvare e gestire la tua {sezione_nome}.</p>
        </div>
    """, unsafe_allow_html=True)
    if st.button(f"Vai al Login 👤", key=f"lock_{sezione_nome}", use_container_width=True):
        st.info("Usa il menu a sinistra per entrare!")

# --- 3. SESSION STATE ---
if "user_id" not in st.session_state: st.session_state.user_id = None
if "nickname" not in st.session_state: st.session_state.nickname = ""
if "is_premium" not in st.session_state: st.session_state.is_premium = False
if "ultima_ricetta" not in st.session_state: st.session_state.ultima_ricetta = ""

# --- 4. SIDEBAR (ACCOUNT) ---
if st.session_state.user_id is None:
    st.markdown('<div class="login-hint">⬅️ Login qui!</div>', unsafe_allow_html=True)
    with st.sidebar:
        st.title("👤 Account")
        modo = st.radio("Scegli:", ["Login", "Registrati"])
        with st.form("auth_form"):
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
                            st.success("Account creato! Fai il login.")
                    st.rerun()
                except Exception as e: st.error("Dati non validi")
else:
    with st.sidebar:
        st.success(f"Ciao, {st.session_state.nickname}!")
        st.write(f"Piano: {'💎 DIAMOND' if st.session_state.is_premium else '👨‍🍳 STANDARD'}")
        if st.button("Logout 🚪", use_container_width=True):
            st.session_state.clear()
            st.rerun()

# --- 5. TABS PRINCIPALI ---
t1, t2, t3, t4, t5 = st.tabs(["🔥 Cucina AI", "📦 Dispensa", "🛒 Spesa", "📖 Archivio", "💬 Feedback"])

with t1:
    st.header("Chef Virtuale")
    ing = st.text_area("Cosa hai in frigo oggi?", placeholder="Esempio: 2 uova, mezza cipolla, pasta...")
    
    col1, col2 = st.columns(2)
    tempo = col1.select_slider("Tempo massimo:", ["15 min", "30 min", "60 min"])
    mood = col2.selectbox("Stile Chef:", ["Simpatico", "Professionale", "Cattivissimo"])

    if st.button("GENERA RICETTA ✨", use_container_width=True):
        with st.spinner("Lo Chef sta creando un capolavoro..."):
            prompt = f"Sei uno chef {mood}. Crea una ricetta HTML elegante (usa h2, li, strong) per questi ingredienti: {ing}. Tempo: {tempo}."
            res = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=[{"role": "user", "content": prompt}])
            st.session_state.ultima_ricetta = res.choices[0].message.content
            st.rerun()

    if st.session_state.ultima_ricetta:
        st.markdown(f'<div class="recipe-container">{st.session_state.ultima_ricetta}</div>', unsafe_allow_html=True)
        
        cv, cp = st.columns(2)
        with cv:
            if st.session_state.is_premium:
                txt_audio = re.sub('<[^<]+?>', '', st.session_state.ultima_ricetta).replace("'", "\\'").replace("\n", " ")
                st.components.v1.html(f"""
                    <button id='speakBtn' style='width:100%; padding:12px; background:#ff4b4b; color:white; border:none; border-radius:10px; font-weight:700; cursor:pointer; font-family:sans-serif;'>🔊 ASCOLTA LA RICETTA</button>
                    <script>
                        const btn = document.getElementById('speakBtn');
                        let speaking = false;
                        btn.onclick = () => {{
                            if(!speaking) {{
                                const u = new SpeechSynthesisUtterance('{txt_audio}');
                                u.lang = 'it-IT';
                                u.onend = () => {{ speaking = false; btn.innerText = '🔊 ASCOLTA LA RICETTA'; }};
                                window.speechSynthesis.speak(u);
                                speaking = true;
                                btn.innerText = '🛑 FERMA LETTURA';
                            }} else {{
                                window.speechSynthesis.cancel();
                                speaking = false;
                                btn.innerText = '🔊 ASCOLTA LA RICETTA';
                            }}
                        }};
                    </script>
                """, height=70)
            else:
                if st.button("🔊 Sblocca Voce (Premium)", use_container_width=True):
                    st.toast("Passa a Diamond per l'audio! 💎")
        with cp:
            pdf_file = format_pdf(st.session_state.ultima_ricetta)
            st.download_button("📄 SCARICA PDF", data=pdf_file, file_name="ricetta.pdf", use_container_width=True)

with t2:
    if st.session_state.user_id:
        st.header("📦 La tua Dispensa")
        nuovo = st.text_input("Aggiungi ingrediente:")
        if st.button("Salva ➕"):
            if nuovo:
                supabase.table("dispensa").insert({"user_id": st.session_state.user_id, "ingrediente": nuovo}).execute()
                st.rerun()
        
        items = supabase.table("dispensa").select("*").eq("user_id", st.session_state.user_id).execute().data
        for i in items:
            c1, c2 = st.columns([5,1])
            c1.write(f"{get_emoji(i['ingrediente'])} **{i['ingrediente']}**")
            if c2.button("🗑️", key=f"del_{i['id']}"):
                supabase.table("dispensa").delete().eq("id", i['id']).execute()
                st.rerun()
    else: show_login_lock("Dispensa")

with t3:
    if st.session_state.user_id:
        st.header("🛒 Lista Spesa")
        sp_item = st.text_input("Cosa manca?")
        if st.button("Aggiungi a Spesa"):
            if sp_item:
                supabase.table("lista_spesa").insert({"user_id": st.session_state.user_id, "item": sp_item}).execute()
                st.rerun()
        
        lista = supabase.table("lista_spesa").select("*").eq("user_id", st.session_state.user_id).execute().data
        for s in lista:
            c1, c2 = st.columns([5,1])
            c1.write(f"⬜ {s['item']}")
            if c2.button("✔️", key=f"check_{s['id']}"):
                supabase.table("lista_spesa").delete().eq("id", s['id']).execute()
                st.rerun()
    else: show_login_lock("Lista Spesa")

with t4:
    if st.session_state.user_id:
        st.header("📖 Archivio Ricette")
        ricette = supabase.table("ricette").select("*").eq("user_id", st.session_state.user_id).execute().data
        if not ricette: st.info("Ancora nessuna ricetta salvata.")
        for r in ricette:
            with st.expander(f"🍴 Ricetta del {r['created_at'][:10]}"):
                st.markdown(r['contenuto'], unsafe_allow_html=True)
                if st.button("Elimina", key=f"dr_{r['id']}"):
                    supabase.table("ricette").delete().eq("id", r['id']).execute()
                    st.rerun()
    else: show_login_lock("Archivio")

with t5:
    if st.session_state.user_id:
        st.header("Feedback 📣")
        f_msg = st.text_area("Suggerimenti?")
        if st.button("Invia Feedback"):
            if f_msg:
                supabase.table("feedback").insert({"user_id":st.session_state.user_id, "messaggio":f_msg}).execute()
                st.success("Grazie mille!")
    else: show_login_lock("Feedback")
