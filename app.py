import streamlit as st
import stripe
from groq import Groq
from supabase import create_client
from fpdf import FPDF
import re
import io
import webbrowser

# --- 1. CONFIGURAZIONI ---
st.set_page_config(page_title="Svuotafrigo App", layout="wide")

# Credenziali (Usa st.secrets per sicurezza in produzione!)
URL = "https://ixkrnsarskqgwwuudqms.supabase.co"
KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Iml4a3Juc2Fyc2txZ3d3dXVkcW1zIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzM5Mjk5NDYsImV4cCI6MjA4OTUwNTk0Nn0.2_5BIu8g6bfjki91Uk_syMC7g8OTtQIb8yYnApEz3j8"
GROQ_AD = "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"
stripe.api_key = "sk_test_51TD7vwBBE2wDwi0CS5b18fA0sd6CqNclpupLdSZHVB9INo23zKGRErg3gtQL1ObzfztxfjCZY14wPUVQDBh98XeB00IeP2wsSK".strip()

# ID Prodotti Stripe (Assicurati che questi ID siano corretti nella tua dashboard Stripe)
ID_GOLD = "price_1TD86OBBE2wDwi0CI4KlvKFJ"
ID_DIAMOND = "price_1TD88HBBE2wDwi0CV9d2heo2"

supabase = create_client(URL, KEY)
client = Groq(api_key=GROQ_AD)

# --- 2. FUNZIONI ---
def format_pdf(text):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    # Pulizia tag HTML per il PDF
    clean = re.sub('<[^<]+?>', '', text).encode('latin-1', 'ignore').decode('latin-1')
    pdf.multi_cell(0, 10, txt=clean)
    return pdf.output(dest='S').encode('latin-1')

def create_checkout_session(price_id, user_email):
    try:
        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{'price': price_id, 'quantity': 1}],
            mode='subscription',
            success_url="https://svuotafrigo-app.streamlit.app/?success=true",
            cancel_url="https://svuotafrigo-app.streamlit.app/?cancel=true",
            customer_email=user_email,
        )
        return session.url
    except Exception as e:
        st.error(f"Errore Stripe: {e}")
        return None

# --- 3. SESSION STATE ---
if "user_id" not in st.session_state: st.session_state.user_id = None
if "is_premium" not in st.session_state: st.session_state.is_premium = "Free"
if "user_email" not in st.session_state: st.session_state.user_email = ""
if "ultima_ricetta" not in st.session_state: st.session_state.ultima_ricetta = None
if "count_ospite" not in st.session_state: st.session_state.count_ospite = 0

# --- 4. SIDEBAR (Login & Abbonamento) ---
st.sidebar.title("👤 My Kitchen")

if st.session_state.user_id is None:
    scelta = st.sidebar.selectbox("Menu", ["Login", "Crea Account"])
    with st.sidebar.form("auth"):
        e = st.text_input("Email")
        p = st.text_input("Password", type="password")
        nick = st.text_input("Nickname") if scelta == "Crea Account" else ""
        if st.form_submit_button("Entra"):
            try:
                if scelta == "Login":
                    res = supabase.auth.sign_in_with_password({"email": e, "password": p})
                    st.session_state.user_id = res.user.id
                    st.session_state.user_email = e
                    # Recupera profilo
                    prof = supabase.table("profili").select("*").eq("id", res.user.id).execute()
                    if prof.data:
                        st.session_state.nickname = prof.data[0]["nickname"]
                        st.session_state.is_premium = prof.data[0].get("subscription_plan", "Free")
                else:
                    res = supabase.auth.sign_up({"email": e, "password": p})
                    if res.user:
                        supabase.table("profili").insert({"id": res.user.id, "nickname": nick, "subscription_plan": "Free"}).execute()
                    st.success("Account creato! Fai il login.")
                st.rerun()
            except Exception as ex: st.error(f"Errore: {ex}")
else:
    st.sidebar.success(f"Ciao {st.session_state.nickname}!")
    st.sidebar.write(f"Piano attuale: **{st.session_state.is_premium}**")
    
    # Sezione Abbonamenti nella Sidebar
    if st.session_state.is_premium == "Free":
        st.sidebar.markdown("---")
        st.sidebar.subheader("Diventa Pro 🚀")
        if st.sidebar.button("Abbonati a GOLD (5€/mese)"):
            url = create_checkout_session(ID_GOLD, st.session_state.user_email)
            if url: st.sidebar.link_button("Paga ora", url)
            
        if st.sidebar.button("Abbonati a DIAMOND (10€/mese)"):
            url = create_checkout_session(ID_DIAMOND, st.session_state.user_email)
            if url: st.sidebar.link_button("Paga ora", url)
    
    if st.sidebar.button("Logout 🚪"): 
        st.session_state.clear()
        st.rerun()

# --- 5. TABS ---
t1, t2, t3, t4 = st.tabs(["🔥 Cucina", "📦 Dispensa", "🛒 Spesa", "📖 Archivio"])

with t1:
    st.header("Generatore Ricette AI")
    
    # Controllo limiti per ospiti e utenti free
    limite_raggiunto = False
    if not st.session_state.user_id and st.session_state.count_ospite >= 2:
        limite_raggiunto = True
        st.warning("⚠️ Hai raggiunto il limite di 2 ricette come ospite. Accedi per continuare!")
    
    ing = st.text_area("Cosa hai in frigo?", placeholder="Esempio: uova, farina, latte...")
    
    if st.button("Genera Ricetta ✨", use_container_width=True, disabled=limite_raggiunto):
        with st.spinner("Lo Chef sta scrivendo..."):
            prompt = f"Crea una ricetta con {ing}. Usa tag HTML (h1, h2, p, ul, li). Sii creativo!"
            res = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=[{"role":"user","content":prompt}])
            st.session_state.ultima_ricetta = res.choices[0].message.content
            if not st.session_state.user_id:
                st.session_state.count_ospite += 1
            st.rerun()

    if st.session_state.ultima_ricetta:
        st.markdown('<div style="background-color: #1e1e1e; padding: 20px; border-radius: 10px; border: 1px solid #00ffaa;">', unsafe_allow_html=True)
        st.markdown(st.session_state.ultima_ricetta, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Funzioni Extra (PDF e Salva)
        col1, col2 = st.columns(2)
        with col1:
            st.download_button("📄 Scarica PDF", data=format_pdf(st.session_state.ultima_ricetta), file_name="ricetta.pdf")
        with col2:
            if st.session_state.user_id:
                if st.button("💾 Salva in Archivio"):
                    supabase.table("ricette").insert({"user_id": st.session_state.user_id, "content": st.session_state.ultima_ricetta}).execute()
                    st.success("Salvata!")
            else:
                st.info("Loggati per salvare le ricette!")

with t4:
    if st.session_state.user_id:
        st.header("📖 Il tuo Archivio")
        res = supabase.table("ricette").select("*").eq("user_id", st.session_state.user_id).execute()
        if res.data:
            for r in res.data:
                with st.expander(f"Ricetta del {r['created_at'][:10]}"):
                    st.markdown(r['content'], unsafe_allow_html=True)
        else:
            st.write("Non hai ancora salvato ricette.")
    else:
        st.error("🔒 Accedi per vedere il tuo archivio.")
