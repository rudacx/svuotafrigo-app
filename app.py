import streamlit as st
import stripe
from groq import Groq
from supabase import create_client
import urllib.parse

# --- 1. CONFIGURAZIONE E STILE ---
st.set_page_config(page_title="Svuotafrigo Pro", layout="wide")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    .stApp { background-color: #0E1117; color: #FFFFFF; }
    .recipe-card { background: #1E232D; padding: 30px; border-radius: 20px; border: 1px solid #30363D; margin-top: 20px; }
    h1, h2, h3 { color: #00FFAA !important; }
    
    /* Pulsante Login Appariscente nel rettangolo arancione */
    .login-float {
        position: fixed;
        top: 15px;
        left: 60px;
        z-index: 9999;
        background: linear-gradient(90deg, #00FFAA, #00CC88);
        color: #0E1117 !important;
        padding: 6px 15px;
        border-radius: 50px;
        font-weight: 800;
        font-size: 0.8rem;
        text-decoration: none;
        box-shadow: 0 4px 15px rgba(0, 255, 170, 0.3);
        transition: 0.3s;
        animation: pulse 2s infinite;
        display: inline-block;
    }
    
    @keyframes pulse {
        0% { box-shadow: 0 0 0 0 rgba(0, 255, 170, 0.7); }
        70% { box-shadow: 0 0 0 10px rgba(0, 255, 170, 0); }
        100% { box-shadow: 0 0 0 0 rgba(0, 255, 170, 0); }
    }

    .pro-box { background: linear-gradient(145deg, #252b36, #1a1f26); padding: 20px; border-radius: 15px; border: 1px solid #3d444d; margin-bottom: 15px; text-align: center; }
    .pro-title { color: #00FFAA; font-weight: 700; font-size: 1.1rem; }
    .pro-price { color: #ffffff; font-size: 1.5rem; font-weight: 800; }
    div.stButton > button { border-radius: 12px !important; font-weight: 700 !important; transition: 0.3s; }
    </style>
""", unsafe_allow_html=True)

# --- 2. CONNESSIONI (Secrets) ---
URL = st.secrets["SUPABASE_URL"]
KEY = st.secrets["SUPABASE_KEY"]
GROQ_AD = st.secrets["GROQ_API_KEY"]
stripe.api_key = st.secrets["STRIPE_API_KEY"]

supabase = create_client(URL, KEY)
client = Groq(api_key=GROQ_AD)

ID_GOLD = "price_1TD86OBBE2wDwi0CI4KlvKFJ"   
ID_DIAMOND = "price_1TD88HBBE2wDwi0CV9d2heo2"

# --- 3. SESSION STATE ---
if "user_id" not in st.session_state: st.session_state.user_id = None
if "nickname" not in st.session_state: st.session_state.nickname = "Chef"
if "is_premium" not in st.session_state: st.session_state.is_premium = "Free"
if "user_email" not in st.session_state: st.session_state.user_email = ""
if "ultima_ricetta" not in st.session_state: st.session_state.ultima_ricetta = None
if "ingredienti_estratti" not in st.session_state: st.session_state.ingredienti_estratti = []
if "count_ospite" not in st.session_state: st.session_state.count_ospite = 0

# --- 4. LOGICA PULSANTE LOGIN (RETTANGOLO ARANCIONE) ---
if st.session_state.user_id is None:
    st.markdown('<a href="#menu" class="login-float">👋 LOGIN QUI</a>', unsafe_allow_html=True)

# --- 5. SIDEBAR ---
st.sidebar.title("👤 My Kitchen")

if st.session_state.user_id is None:
    scelta = st.sidebar.selectbox("Menu", ["Login", "Crea Account"])
    with st.sidebar.form("auth"):
        e = st.text_input("Email")
        p = st.text_input("Password", type="password")
        n = st.text_input("Nickname") if scelta == "Crea Account" else ""
        if st.form_submit_button("Entra"):
            try:
                if scelta == "Login":
                    res = supabase.auth.sign_in_with_password({"email": e, "password": p})
                    st.session_state.user_id, st.session_state.user_email = res.user.id, e
                    prof = supabase.table("profili").select("*").eq("id", res.user.id).execute()
                    if prof.data:
                        st.session_state.nickname = prof.data[0].get("nickname", "Chef")
                        st.session_state.is_premium = prof.data[0].get("subscription_plan", "Free")
                else:
                    res = supabase.auth.sign_up({"email": e, "password": p})
                    if res.user:
                        supabase.table("profili").insert({"id": res.user.id, "nickname": n}).execute()
                    st.success("Account creato! Accedi ora.")
                st.rerun()
            except Exception as ex: st.error(f"Errore: {ex}")
else:
    st.sidebar.success(f"Chef {st.session_state.nickname}")
    st.sidebar.write(f"Piano: **{st.session_state.is_premium}**")
    
    if st.session_state.is_premium == "Free":
        st.sidebar.markdown("---")
        st.sidebar.markdown('<div class="pro-box"><div class="pro-title">🥇 GOLD</div><div class="pro-price">9.99€</div></div>', unsafe_allow_html=True)
        if st.sidebar.button("SBLOCCA LIMITE"):
            sess = stripe.checkout.Session.create(payment_method_types=['card'], line_items=[{'price': ID_GOLD, 'quantity': 1}], mode='subscription', success_url="https://svuotafrigo-app.streamlit.app/", cancel_url="https://svuotafrigo-app.streamlit.app/", customer_email=st.session_state.user_email)
            st.sidebar.link_button("💳 PAGA ORA", sess.url)

    if st.sidebar.button("Logout 🚪", use_container_width=True):
        st.session_state.clear()
        st.rerun()

# --- 6. TABS ---
t1, t2, t3, t4, t5 = st.tabs(["🔥 CUCINA", "📦 DISPENSA", "🛒 SPESA", "📖 ARCHIVIO", "💬 FEEDBACK"])

with t1:
    st.title("👨‍🍳 Svuotafrigo AI")
    lock_guest = not st.session_state.user_id and st.session_state.count_ospite >= 2
    if lock_guest: st.warning("Limite ospiti raggiunto. Accedi per continuare!")
    
    ing = st.text_area("Cosa hai in frigo?", placeholder="Es: farina di mais, uova...")
    
    if st.button("GENERA ✨", use_container_width=True, disabled=lock_guest, key="main_gen_btn"):
        if not ing:
            st.warning("Inserisci degli ingredienti!")
        else:
            with st.spinner("Lo Chef sta scrivendo..."):
                prompt = f"""Crea una ricetta con {ing}. 
                Rispondi SEMPRE in questo formato:
                [LISTA] ingrediente1, ingrediente2 [/LISTA]
                [HTML] 
                <h2 style='color: #00FFAA;'>🍳 Titolo</h2>
                <h4 style='color: #00FFAA;'>🛒 Ingredienti:</h4><ul><li>...</li></ul>
                <h4 style='color: #00FFAA;'>👨‍🍳 Preparazione:</h4><ol><li>...</li></ol>
                [/HTML]"""
                try:
                    r = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=[{"role":"user","content": prompt}])
                    raw = r.choices[0].message.content
                    
                    if "[LISTA]" in raw and "[HTML]" in raw:
                        st.session_state.ingredienti_estratti = raw.split("[LISTA]")[1].split("[/LISTA]")[0].strip().split(",")
                        st.session_state.ultima_ricetta = raw.split("[HTML]")[1].split("[/HTML]")[0].strip()
                    else:
                        st.session_state.ultima_ricetta = raw
                    
                    if not st.session_state.user_id: st.session_state.count_ospite += 1
                    st.rerun()
                except Exception as e: st.error(f"Errore: {e}")

    if st.session_state.ultima_ricetta:
        # Pulizia display
        disp_text = st.session_state.ultima_ricetta.replace("[HTML]", "").replace("[/HTML]", "").replace("[LISTA]", "").split("[/LISTA]")[-1].strip()
        st.markdown(f'<div class="recipe-card">{disp_text}</div>', unsafe_allow_html=True)
        
        if st.session_state.user_id:
            st.subheader("🛒 Ti manca qualcosa?")
            cols = st.columns(3)
            for idx, item in enumerate(st.session_state.ingredienti_estratti):
                if item.strip():
                    if cols[idx % 3].button(f"+ {item.strip()}", key=f"add_{idx}"):
                        supabase.table("spesa").insert({"user_id": st.session_state.user_id, "prodotto": item.strip()}).execute()
                        st.toast(f"{item.strip()} aggiunto!")

            if st.button("💾 SALVA IN ARCHIVIO", use_container_width=True, key="save_main"):
                supabase.table("ricette").insert({"user_id": st.session_state.user_id, "contenuto": st.session_state.ultima_ricetta}).execute()
                st.success("Salvata!")

# --- TAB DISPENSA ---
with t2:
    st.header("📦 La tua Dispensa")
    if st.session_state.user_id:
        with st.form("disp_f"):
            i = st.text_input("Ingrediente")
            if st.form_submit_button("Aggiungi"):
                supabase.table("dispensa").insert({"user_id": st.session_state.user_id, "ingrediente": i}).execute()
                st.rerun()
        res = supabase.table("dispensa").select("*").eq("user_id", st.session_state.user_id).execute()
        for d in res.data:
            c1, c2 = st.columns([0.8, 0.2])
            c1.write(f"✅ {d['ingrediente']}")
            if c2.button("🗑️", key=f"del_d_{d['id']}"):
                supabase.table("dispensa").delete().eq("id", d['id']).execute()
                st.rerun()
    else: st.info("Accedi per usare la dispensa.")

# --- TAB SPESA ---
with t3:
    st.header("🛒 Lista della Spesa")
    if st.session_state.user_id:
        if st.button("🗑️ SVUOTA TUTTO", key="clear_all"):
            supabase.table("spesa").delete().eq("user_id", st.session_state.user_id).execute()
            st.rerun()
        lista = supabase.table("spesa").select("*").eq("user_id", st.session_state.user_id).execute()
        for s in lista.data:
            col1, col2 = st.columns([0.8, 0.2])
            col1.write(f"🛒 {s['prodotto']}") 
            if col2.button("❌", key=f"del_s_{s['id']}"):
                supabase.table("spesa").delete().eq("id", s['id']).execute()
                st.rerun()
    else: st.info("Accedi per la lista spesa.")

# --- TAB ARCHIVIO ---
with t4:
    st.header("📖 Archivio")
    if st.session_state.user_id:
        res = supabase.table("ricette").select("*").eq("user_id", st.session_state.user_id).execute()
        for r in res.data:
            with st.expander(f"Ricetta del {r['created_at'][:10]}"):
                st.markdown(r['contenuto'].replace("[HTML]", "").replace("[/HTML]", ""), unsafe_allow_html=True)
                if st.button("Elimina", key=f"del_r_{r['id']}"):
                    supabase.table("ricette").delete().eq("id", r['id']).execute()
                    st.rerun()
    else: st.warning("Accedi per l'archivio.")

# --- TAB FEEDBACK ---
with t5:
    st.header("💬 Feedback")
    if st.session_state.user_id:
        v = st.slider("Voto", 1, 5, 5)
        m = st.text_area("Messaggio")
        if st.button("Invia", key="feed_btn"):
            supabase.table("feedback").insert({"user_id": st.session_state.user_id, "voto": v, "messaggio": m}).execute()
            st.success("Grazie!")
    else: st.info("Accedi per i feedback.")
