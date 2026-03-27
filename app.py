import streamlit as st
import stripe
from groq import Groq
from supabase import create_client
from fpdf import FPDF
import re
import io

# --- 1. CONFIGURAZIONE E STILE ---
st.set_page_config(page_title="Svuotafrigo Pro", layout="wide")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    .stApp { background-color: #0E1117; color: #FFFFFF; }
    .recipe-card { background: #1E232D; padding: 30px; border-radius: 20px; border: 1px solid #30363D; margin-top: 20px; }
    h1, h2, h3 { color: #00FFAA !important; }
    .pro-box { background: linear-gradient(145deg, #252b36, #1a1f26); padding: 20px; border-radius: 15px; border: 1px solid #3d444d; margin-bottom: 15px; text-align: center; }
    .pro-title { color: #00FFAA; font-weight: 700; font-size: 1.1rem; }
    .pro-price { color: #ffffff; font-size: 1.5rem; font-weight: 800; }
    div.stButton > button { border-radius: 12px !important; font-weight: 700 !important; }
    </style>
""", unsafe_allow_html=True)

# --- 2. CONNESSIONI ---
URL = st.secrets["SUPABASE_URL"]
KEY = st.secrets["SUPABASE_KEY"]
GROQ_AD = st.secrets["GROQ_API_KEY"]
stripe.api_key = st.secrets["STRIPE_API_KEY"]

supabase = create_client(URL, KEY)
client = Groq(api_key=GROQ_AD)

ID_GOLD = "price_1TD86OBBE2wDwi0CI4KlvKFJ"   # 9.99€
ID_DIAMOND = "price_1TD88HBBE2wDwi0CV9d2heo2" # 14.99€

# --- 3. SESSION STATE ---
if "user_id" not in st.session_state: st.session_state.user_id = None
if "nickname" not in st.session_state: st.session_state.nickname = "Chef"
if "is_premium" not in st.session_state: st.session_state.is_premium = "Free"
if "user_email" not in st.session_state: st.session_state.user_email = ""
if "ultima_ricetta" not in st.session_state: st.session_state.ultima_ricetta = None
if "count_ospite" not in st.session_state: st.session_state.count_ospite = 0

# --- 4. SIDEBAR COMPLETA ---
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
                    st.success("Account creato! Fai il Login.")
                st.rerun()
            except Exception as ex: st.error(f"Errore: {ex}")
else:
    st.sidebar.success(f"Ciao {st.session_state.nickname}!")
    st.sidebar.write(f"Piano attuale: **{st.session_state.is_premium}**")
    
    if st.session_state.is_premium == "Free":
        st.sidebar.markdown("---")
        st.sidebar.markdown("🚀 **DIVENTA PRO**")
        
        # CARD GOLD
        st.sidebar.markdown('<div class="pro-box"><div class="pro-title">🥇 SEMESTRALE</div><div class="pro-price">9.99€</div></div>', unsafe_allow_html=True)
        if st.sidebar.button("ATTIVA GOLD", use_container_width=True):
            sess = stripe.checkout.Session.create(payment_method_types=['card'], line_items=[{'price': ID_GOLD, 'quantity': 1}], mode='subscription', success_url="https://svuotafrigo-app.streamlit.app/", cancel_url="https://svuotafrigo-app.streamlit.app/", customer_email=st.session_state.user_email)
            st.sidebar.link_button("💳 PAGA ORA", sess.url, use_container_width=True)

        # CARD DIAMOND
        st.sidebar.markdown('<div class="pro-box"><div class="pro-title">💎 ANNUALE</div><div class="pro-price">14.99€</div></div>', unsafe_allow_html=True)
        if st.sidebar.button("ATTIVA DIAMOND", use_container_width=True):
            sess = stripe.checkout.Session.create(payment_method_types=['card'], line_items=[{'price': ID_DIAMOND, 'quantity': 1}], mode='subscription', success_url="https://svuotafrigo-app.streamlit.app/", cancel_url="https://svuotafrigo-app.streamlit.app/", customer_email=st.session_state.user_email)
            st.sidebar.link_button("💳 PAGA ORA", sess.url, use_container_width=True)

    if st.sidebar.button("Logout 🚪", use_container_width=True):
        st.session_state.clear()
        st.rerun()

# --- 5. TABS ---
t1, t2, t3, t4, t5 = st.tabs(["🔥 CUCINA", "📦 DISPENSA", "🛒 SPESA", "📖 ARCHIVIO", "💬 FEEDBACK"])

with t1:
    st.title("👨‍🍳 Svuotafrigo AI")
    lock = not st.session_state.user_id and st.session_state.count_ospite >= 2
    ing = st.text_area("Cosa hai in frigo?", placeholder="Es: uova, pancetta...")
    if st.button("GENERA ✨", use_container_width=True, disabled=lock):
        with st.spinner("Creazione..."):
            r = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=[{"role":"user","content":f"Ricetta HTML: {ing}"}])
            st.session_state.ultima_ricetta = r.choices[0].message.content
            if not st.session_state.user_id: st.session_state.count_ospite += 1
            st.rerun()

    if st.session_state.ultima_ricetta:
        st.markdown(f'<div class="recipe-card">{st.session_state.ultima_ricetta}</div>', unsafe_allow_html=True)
        if st.session_state.user_id and st.button("💾 SALVA IN ARCHIVIO"):
            try:
                supabase.table("ricette").insert({"user_id": st.session_state.user_id, "content": st.session_state.ultima_ricetta}).execute()
                st.success("Salvata!")
            except Exception as e: st.error(f"Errore: {e}")

with t2:
    st.header("📦 Dispensa")
    if st.session_state.user_id:
        with st.form("dispensa_add"):
            item = st.text_input("Cosa hai comprato?")
            if st.form_submit_button("Aggiungi"):
                supabase.table("dispensa").insert({"user_id": st.session_state.user_id, "ingrediente": item}).execute()
                st.rerun()
        # Mostra Lista
        data = supabase.table("dispensa").select("*").eq("user_id", st.session_state.user_id).execute()
        for i in data.data: st.write(f"✅ {i['ingrediente']}")
    else: st.warning("Accedi per usare la dispensa.")

with t4:
    st.header("📖 Archivio")
    if st.session_state.user_id:
        res = supabase.table("ricette").select("*").eq("user_id", st.session_state.user_id).execute()
        for r in res.data:
            with st.expander(f"Ricetta del {r['created_at'][:10]}"):
                st.markdown(r['content'], unsafe_allow_html=True)

with t5:
    st.header("💬 Feedback")
    if st.session_state.user_id:
        v = st.slider("Voto", 1, 5, 5)
        c = st.text_area("Suggerimenti")
        if st.button("Invia"):
            supabase.table("feedback").insert({"user_id": st.session_state.user_id, "voto": v, "commento": c}).execute()
            st.success("Grazie!")
