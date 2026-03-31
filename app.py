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
    
    /* PULSANTE LOGIN NEL RETTANGOLO ARANCIONE */
    .login-anchor {
        position: fixed;
        top: 12px;
        left: 55px; 
        z-index: 999999;
    }
    .login-float {
        background: linear-gradient(90deg, #00FFAA, #00CC88);
        color: #0E1117 !important;
        padding: 8px 18px;
        border-radius: 50px;
        font-weight: 800;
        font-size: 14px;
        text-decoration: none;
        box-shadow: 0 4px 15px rgba(0, 255, 170, 0.4);
        transition: 0.3s;
        animation: pulse 2s infinite;
        border: none;
        cursor: pointer;
    }
    
    @keyframes pulse {
        0% { box-shadow: 0 0 0 0 rgba(0, 255, 170, 0.7); }
        70% { box-shadow: 0 0 0 12px rgba(0, 255, 170, 0); }
        100% { box-shadow: 0 0 0 0 rgba(0, 255, 170, 0); }
    }

    .pro-box { background: linear-gradient(145deg, #252b36, #1a1f26); padding: 20px; border-radius: 15px; border: 1px solid #3d444d; margin-bottom: 15px; text-align: center; }
    .pro-title { color: #00FFAA; font-weight: 700; font-size: 1.1rem; }
    .pro-price { color: #ffffff; font-size: 1.5rem; font-weight: 800; }
    div.stButton > button { border-radius: 12px !important; font-weight: 700 !important; }
    </style>
""", unsafe_allow_html=True)

# --- 2. CONNESSIONI ---
URL, KEY = st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"]
GROQ_AD = st.secrets["GROQ_API_KEY"]
stripe.api_key = st.secrets["STRIPE_API_KEY"]
supabase = create_client(URL, KEY)
client = Groq(api_key=GROQ_AD)

# ID Prodotti Stripe
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

# --- 4. IL PULSANTE NEL RETTANGOLO ARANCIONE ---
if st.session_state.user_id is None:
    st.markdown('''
        <div class="login-anchor">
            <a href="javascript:window.parent.document.querySelector('.stSidebar').scrollIntoView();" class="login-float">
                👋 ACCEDI QUI
            </a>
        </div>
    ''', unsafe_allow_html=True)

# --- 5. SIDEBAR ---
with st.sidebar:
    st.title("👤 My Kitchen")
    if st.session_state.user_id is None:
        scelta = st.selectbox("Menu", ["Login", "Crea Account"])
        with st.form("auth"):
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
                        if res.user: supabase.table("profili").insert({"id": res.user.id, "nickname": n}).execute()
                        st.success("Account creato! Accedi ora.")
                    st.rerun()
                except Exception as ex: st.error(f"Errore: {ex}")
    else:
        st.success(f"Chef {st.session_state.nickname}")
        st.write(f"Piano: **{st.session_state.is_premium}**")
        
        # Gestione Premium nella Sidebar
        if st.session_state.is_premium == "Free":
            st.markdown("---")
            st.markdown('<div class="pro-box"><div class="pro-title">🥇 GOLD</div><div class="pro-price">9.99€</div></div>', unsafe_allow_html=True)
            if st.button("SBLOCCA ORA"):
                sess = stripe.checkout.Session.create(payment_method_types=['card'], line_items=[{'price': ID_GOLD, 'quantity': 1}], mode='subscription', success_url="https://svuotafrigo-app.streamlit.app/", cancel_url="https://svuotafrigo-app.streamlit.app/", customer_email=st.session_state.user_email)
                st.link_button("💳 PAGA", sess.url)

        if st.button("Logout 🚪", use_container_width=True):
            st.session_state.clear()
            st.rerun()

# --- 6. TABS ---
t1, t2, t3, t4, t5 = st.tabs(["🔥 CUCINA", "📦 DISPENSA", "🛒 SPESA", "📖 ARCHIVIO", "💬 FEEDBACK"])

with t1:
    st.title("👨‍🍳 Svuotafrigo AI")
    lock = not st.session_state.user_id and st.session_state.count_ospite >= 2
    if lock: st.warning("Limite ospiti raggiunto. Accedi per continuare!")
    
    ing = st.text_area("Cosa hai in frigo?", placeholder="Es: uova, farina, latte...")
    
    if st.button("GENERA ✨", use_container_width=True, disabled=lock, key="gen_btn"):
        if not ing:
            st.warning("Scrivi almeno un ingrediente!")
        else:
            with st.spinner("Chef al lavoro..."):
                prompt = f"""Crea una ricetta con {ing}. 
                Rispondi SEMPRE in questo formato preciso:
                [LISTA] ingrediente1, ingrediente2 [/LISTA]
                [HTML] 
                <h2 style='color: #00FFAA;'>🍳 Titolo</h2>
                <h4 style='color: #00FFAA;'>🛒 Ingredienti:</h4><ul><li>...</li></ul>
                <h4 style='color: #00FFAA;'>👨‍🍳 Preparazione:</h4><ol><li>...</li></ol>
                [/HTML]"""
                try:
                    r = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=[{"role":"user","content":prompt}])
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
        # Pulizia totale dei tag tecnici per la visualizzazione
        pulizia = st.session_state.ultima_ricetta.replace("[HTML]","").replace("[/HTML]","").replace("[LISTA]","")
        if "[/LISTA]" in pulizia: pulizia = pulizia.split("[/LISTA]")[-1]
        
        st.markdown(f'<div class="recipe-card">{pulizia.strip()}</div>', unsafe_allow_html=True)
        
        if st.session_state.user_id:
            st.subheader("🛒 Ti manca qualcosa?")
            cols = st.columns(3)
            for idx, item in enumerate(st.session_state.ingredienti_estratti):
                clean_item = item.strip().lower()
                if clean_item:
                    if cols[idx % 3].button(f"+ {clean_item}", key=f"at_{idx}"):
                        supabase.table("spesa").insert({"user_id": st.session_state.user_id, "prodotto": clean_item}).execute()
                        st.toast(f"{clean_item} aggiunto!")

            if st.button("💾 SALVA IN ARCHIVIO", use_container_width=True, key="sv"):
                supabase.table("ricette").insert({"user_id": st.session_state.user_id, "contenuto": st.session_state.ultima_ricetta}).execute()
                st.success("Salvata!")

# --- TAB 2: DISPENSA ---
with t2:
    st.header("📦 La tua Dispensa")
    if st.session_state.user_id:
        with st.form("disp_form"):
            new_item = st.text_input("Aggiungi ingrediente")
            if st.form_submit_button("Inserisci"):
                supabase.table("dispensa").insert({"user_id": st.session_state.user_id, "ingrediente": new_item}).execute()
                st.rerun()
        res = supabase.table("dispensa").select("*").eq("user_id", st.session_state.user_id).execute()
        for i in res.data:
            c1, c2 = st.columns([0.8, 0.2])
            c1.write(f"✅ {i['ingrediente']}")
            if c2.button("🗑️", key=f"del_d_{i['id']}"):
                supabase.table("dispensa").delete().eq("id", i['id']).execute()
                st.rerun()
    else: st.info("👋 Hey Chef! Accedi per gestire la tua dispensa.")

# --- TAB 3: SPESA ---
with t3:
    st.header("🛒 Lista della Spesa")
    if st.session_state.user_id:
        if st.button("🗑️ SVUOTA TUTTO", key="clear_spesa"):
            supabase.table("spesa").delete().eq("user_id", st.session_state.user_id).execute()
            st.rerun()
        lista = supabase.table("spesa").select("*").eq("user_id", st.session_state.user_id).execute()
        for s in lista.data:
            col1, col2 = st.columns([0.8, 0.2])
            col1.write(f"🛒 {s['prodotto']}") 
            if col2.button("❌", key=f"del_s_{s['id']}"):
                supabase.table("spesa").delete().eq("id", s['id']).execute()
                st.rerun()
    else: st.info("Accedi per la lista della spesa.")

# --- TAB 4: ARCHIVIO ---
with t4:
    st.header("📖 Archivio Ricette")
    if st.session_state.user_id:
        res = supabase.table("ricette").select("*").eq("user_id", st.session_state.user_id).execute()
        for r in res.data:
            with st.expander(f"Ricetta del {r['created_at'][:10]}"):
                arch_text = r['contenuto'].replace("[HTML]", "").replace("[/HTML]", "").replace("[LISTA]", "")
                if "[/LISTA]" in arch_text: arch_text = arch_text.split("[/LISTA]")[-1]
                st.markdown(arch_text, unsafe_allow_html=True)
                if st.button("Elimina", key=f"del_r_{r['id']}"):
                    supabase.table("ricette").delete().eq("id", r['id']).execute()
                    st.rerun()
    else: st.warning("Accedi per vedere le tue ricette salvate.")

# --- TAB 5: FEEDBACK ---
with t5:
    st.header("💬 Feedback")
    if st.session_state.user_id:
        voto = st.slider("Voto", 1, 5, 5)
        msg = st.text_area("Cosa ne pensi?")
        if st.button("Invia Feedback"):
            supabase.table("feedback").insert({"user_id": st.session_state.user_id, "voto": voto, "messaggio": msg}).execute()
            st.success("Feedback Inviato.")
    else: st.info("Accedi per lasciarci un feedback.")
