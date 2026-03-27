import streamlit as st
import stripe
from groq import Groq
from supabase import create_client
from fpdf import FPDF
import re
import io

# --- 1. CONFIGURAZIONI ---
st.set_page_config(page_title="Svuotafrigo App", layout="wide")

# Credenziali dai Secrets di Streamlit
URL = st.secrets["SUPABASE_URL"]
KEY = st.secrets["SUPABASE_KEY"]
GROQ_AD = st.secrets["GROQ_API_KEY"]
stripe.api_key = st.secrets["STRIPE_API_KEY"]

# ID Prodotti Stripe
ID_GOLD = "price_1TD86OBBE2wDwi0CI4KlvKFJ"
ID_DIAMOND = "price_1TD88HBBE2wDwi0CV9d2heo2"

supabase = create_client(URL, KEY)
client = Groq(api_key=GROQ_AD)

# --- 2. FUNZIONI UTILI ---
def format_pdf(text):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    # Pulizia tag HTML per evitare errori nel PDF
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

# --- 3. SESSION STATE (Inizializzazione per evitare AttributeError) ---
if "user_id" not in st.session_state: st.session_state.user_id = None
if "nickname" not in st.session_state: st.session_state.nickname = "Chef"
if "is_premium" not in st.session_state: st.session_state.is_premium = "Free"
if "user_email" not in st.session_state: st.session_state.user_email = ""
if "ultima_ricetta" not in st.session_state: st.session_state.ultima_ricetta = None
if "count_ospite" not in st.session_state: st.session_state.count_ospite = 0

# --- 4. SIDEBAR (Login & Abbonamenti) ---
st.sidebar.title("👤 My Kitchen")

if st.session_state.user_id is None:
    scelta = st.sidebar.selectbox("Menu", ["Login", "Crea Account"])
    with st.sidebar.form("auth"):
        e = st.text_input("Email")
        p = st.text_input("Password", type="password")
        nick_new = st.text_input("Nickname") if scelta == "Crea Account" else ""
        if st.form_submit_button("Entra"):
            try:
                if scelta == "Login":
                    res = supabase.auth.sign_in_with_password({"email": e, "password": p})
                    st.session_state.user_id = res.user.id
                    st.session_state.user_email = e
                    # Recupero dati profilo
                    prof = supabase.table("profili").select("*").eq("id", res.user.id).execute()
                    if prof.data:
                        st.session_state.nickname = prof.data[0].get("nickname", "Chef")
                        st.session_state.is_premium = prof.data[0].get("subscription_plan", "Free")
                else:
                    res = supabase.auth.sign_up({"email": e, "password": p})
                    if res.user:
                        supabase.table("profili").insert({
                            "id": res.user.id, 
                            "nickname": nick_new, 
                            "subscription_plan": "Free"
                        }).execute()
                    st.success("Account creato! Fai il login.")
                st.rerun()
            except Exception as ex: st.error(f"Errore: {ex}")
else:
    st.sidebar.success(f"Ciao {st.session_state.nickname}!")
    st.sidebar.write(f"Piano: **{st.session_state.is_premium}**")
    
    # Sezione Stripe
    if st.session_state.is_premium == "Free":
        st.sidebar.markdown("---")
        st.sidebar.subheader("🚀 Passa a Pro")
        if st.sidebar.button("Abbonati a GOLD (5€)"):
            url = create_checkout_session(ID_GOLD, st.session_state.user_email)
            if url: st.sidebar.link_button("Vai al pagamento", url)
            
        if st.sidebar.button("Abbonati a DIAMOND (10€)"):
            url = create_checkout_session(ID_DIAMOND, st.session_state.user_email)
            if url: st.sidebar.link_button("Vai al pagamento", url)
    
    if st.sidebar.button("Logout 🚪"): 
        st.session_state.clear()
        st.rerun()

# --- 5. INTERFACCIA PRINCIPALE (TABS) ---
t1, t2, t3, t4 = st.tabs(["🔥 Cucina", "📦 Dispensa", "🛒 Spesa", "📖 Archivio"])

with t1:
    st.header("Generatore Ricette AI")
    
    # Limite Ospite
    blobloccato = False
    if not st.session_state.user_id and st.session_state.count_ospite >= 2:
        blobloccato = True
        st.warning("⚠️ Limite raggiunto! Accedi per generare altre ricette.")
    
    ing = st.text_area("Cosa c'è in frigo?", placeholder="Es: pasta, tonno, capperi...")
    
    if st.button("Genera ✨", use_container_width=True, disabled=blobloccato):
        with st.spinner("Lo Chef sta creando..."):
            prompt = f"Crea una ricetta con: {ing}. Usa tag HTML (h1, h2, p, ul, li). Non scrivere chiacchiere."
            res = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=[{"role":"user","content":prompt}])
            st.session_state.ultima_ricetta = res.choices[0].message.content
            if not st.session_state.user_id:
                st.session_state.count_ospite += 1
            st.rerun()

    if st.session_state.ultima_ricetta:
        # Box grafico per la ricetta
        st.markdown(f'<div style="background-color: #1e1e1e; padding: 25px; border-radius: 15px; border: 1px solid #00ffaa;">{st.session_state.ultima_ricetta}</div>', unsafe_allow_html=True)
        
        c1, c2 = st.columns(2)
        with c1:
            st.download_button("📄 Scarica PDF", data=format_pdf(st.session_state.ultima_ricetta), file_name="ricetta.pdf")
        with c2:
            if st.session_state.user_id:
                if st.button("💾 Salva in Archivio"):
                    try:
                        supabase.table("ricette").insert({"user_id": st.session_state.user_id, "content": st.session_state.ultima_ricetta}).execute()
                        st.success("Salvata nell'archivio!")
                    except Exception as e:
                        st.error(f"Errore: {e}")
            else:
                st.info("Loggati per salvare!")

with t4:
    if st.session_state.user_id:
        st.header("📖 Il tuo Archivio")
        try:
            res = supabase.table("ricette").select("*").eq("user_id", st.session_state.user_id).execute()
            if res.data:
                for r in res.data:
                    with st.expander(f"Ricetta del {r['created_at'][:10]}"):
                        st.markdown(r['content'], unsafe_allow_html=True)
            else:
                st.write("Archivio vuoto.")
        except:
            st.write("Nessuna ricetta trovata.")
    else:
        st.error("🔒 Accedi per vedere l'archivio.")
