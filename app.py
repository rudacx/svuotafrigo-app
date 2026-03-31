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
    .pro-box { background: linear-gradient(145deg, #252b36, #1a1f26); padding: 20px; border-radius: 15px; border: 1px solid #3d444d; margin-bottom: 15px; text-align: center; }
    .pro-title { color: #00FFAA; font-weight: 700; font-size: 1.1rem; }
    .pro-price { color: #ffffff; font-size: 1.5rem; font-weight: 800; }
    div.stButton > button { border-radius: 12px !important; font-weight: 700 !important; transition: 0.3s; }
    </style>
""", unsafe_allow_html=True)

# --- 2. CONNESSIONI ---
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

# --- 4. SIDEBAR ---
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
        
        st.sidebar.markdown('<div class="pro-box"><div class="pro-title">💎 DIAMOND</div><div class="pro-price">14.99€</div></div>', unsafe_allow_html=True)
        if st.sidebar.button("SBLOCCA DIAMOND"):
            sess = stripe.checkout.Session.create(payment_method_types=['card'], line_items=[{'price': ID_DIAMOND, 'quantity': 1}], mode='subscription', success_url="https://svuotafrigo-app.streamlit.app/", cancel_url="https://svuotafrigo-app.streamlit.app/", customer_email=st.session_state.user_email)
            st.sidebar.link_button("💎 DIVENTA DIAMANTE", sess.url)

    if st.sidebar.button("Logout 🚪", use_container_width=True):
        st.session_state.clear()
        st.rerun()

# --- 5. TABS ---
t1, t2, t3, t4, t5 = st.tabs(["🔥 CUCINA", "📦 DISPENSA", "🛒 SPESA", "📖 ARCHIVIO", "💬 FEEDBACK"])

with t1:
    st.title("👨‍🍳 Svuotafrigo AI")
    lock_guest = not st.session_state.user_id and st.session_state.count_ospite >= 2
    if lock_guest: st.warning("Limite ospiti raggiunto. Accedi per continuare!")
    
    ing = st.text_area("Cosa hai in frigo?", placeholder="Es: uova, farina, latte...")
    
    if st.button("GENERA ✨", use_container_width=True, disabled=lock_guest, key="btn_main_gen"):
        if not ing:
            st.warning("Scrivi qualcosa!")
        else:
            with st.spinner("Lo Chef sta cucinando l'idea..."):
                prompt = f"""Crea una ricetta con {ing}. 
                Rispondi SEMPRE in questo formato preciso:
                [LISTA] ingrediente1, ingrediente2 [/LISTA]
                [HTML] 
                <h2 style='color: #00FFAA;'>🍳 Titolo</h2>
                <h4 style='color: #00FFAA;'>🛒 Ingredienti:</h4><ul><li>...</li></ul>
                <h4 style='color: #00FFAA;'>👨‍🍳 Preparazione:</h4><ol><li>...</li></ol>
                [/HTML]"""
                try:
                    r = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=[{"role":"user","content": prompt}])
                    raw = r.choices[0].message.content
                    
                    # Estrazione ingredienti per i bottoni
                    if "[LISTA]" in raw and "[/LISTA]" in raw:
                        st.session_state.ingredienti_estratti = raw.split("[LISTA]")[1].split("[/LISTA]")[0].strip().split(",")
                    
                    # Estrazione HTML della ricetta
                    if "[HTML]" in raw and "[/HTML]" in raw:
                        st.session_state.ultima_ricetta = raw.split("[HTML]")[1].split("[/HTML]")[0].strip()
                    else:
                        st.session_state.ultima_ricetta = raw
                    
                    if not st.session_state.user_id: st.session_state.count_ospite += 1
                    st.rerun()
                except Exception as e:
                    st.error(f"Errore: {e}")

    if st.session_state.ultima_ricetta:
        # --- PULIZIA FINALE AGGRESSIVA ---
        # Rimuoviamo manualmente ogni tag che potrebbe essere "sfuggito" alla cattura dell'IA
        pulizia = st.session_state.ultima_ricetta
        tags_da_levare = ["[LISTA]", "[/LISTA]", "[HTML]", "[/HTML]"]
        
        # Se l'IA ha scritto la lista degli ingredienti nel corpo del testo, la tagliamo via
        if "[/LISTA]" in pulizia:
            pulizia = pulizia.split("[/LISTA]")[-1].strip()
            
        for tag in tags_da_levare:
            pulizia = pulizia.replace(tag, "")
            
        st.markdown(f'<div class="recipe-card">{pulizia.strip()}</div>', unsafe_allow_html=True)
        
        if st.session_state.user_id:
            # Bottoni Spesa
            st.subheader("🛒 Ti manca qualcosa?")
            disp = supabase.table("dispensa").select("ingrediente").eq("user_id", st.session_state.user_id).execute()
            lista_dispensa = [i['ingrediente'].lower() for i in disp.data]
            
            cols = st.columns(3)
            for idx, item in enumerate(st.session_state.ingredienti_estratti):
                clean_item = item.strip().lower()
                if clean_item and clean_item not in lista_dispensa:
                    if cols[idx % 3].button(f"+ {clean_item}", key=f"btn_add_{idx}"):
                        supabase.table("spesa").insert({"user_id": st.session_state.user_id, "prodotto": clean_item}).execute()
                        st.toast(f"{clean_item} aggiunto!")

            # Salvataggio
            res_count = supabase.table("ricette").select("id").eq("user_id", st.session_state.user_id).execute()
            if st.session_state.is_premium == "Free" and len(res_count.data) >= 5:
                st.warning("⚠️ Limite raggiunto.")
            else:
                if st.button("💾 SALVA IN ARCHIVIO", use_container_width=True, key="save_recipe_final"):
                    supabase.table("ricette").insert({"user_id": st.session_state.user_id, "contenuto": st.session_state.ultima_ricetta}).execute()
                    st.success("Salvata!")
                    st.rerun()

        # Condivisione Premium
        if st.session_state.is_premium != "Free":
            st.markdown("---")
            msg_whatsapp = urllib.parse.quote(f"Guarda questa ricetta creata con Svuotafrigo AI!\n\n{pulizia}")
            st.link_button("🟢 Condividi su WhatsApp", f"https://wa.me/?text={msg_whatsapp}")

# --- RESTANTI TAB (T2, T3, T4, T5) ---
with t2:
    st.header("📦 La tua Dispensa")
    if st.session_state.user_id:
        with st.form("dispensa_form"):
            item = st.text_input("Aggiungi ingrediente")
            if st.form_submit_button("Inserisci"):
                supabase.table("dispensa").insert({"user_id": st.session_state.user_id, "ingrediente": item}).execute()
                st.rerun()
        res = supabase.table("dispensa").select("*").eq("user_id", st.session_state.user_id).execute()
        for i in res.data:
            c1, c2 = st.columns([0.8, 0.2])
            c1.write(f"✅ {i['ingrediente']}")
            if c2.button("🗑️", key=f"del_d_{i['id']}"):
                supabase.table("dispensa").delete().eq("id", i['id']).execute()
                st.rerun()
    else:
        st.info("Loggati per usare la dispensa.")

with t3:
    st.header("🛒 Lista della Spesa")
    if st.session_state.user_id:
        if st.button("🗑️ SVUOTA LISTA", key="clear_spesa"):
            supabase.table("spesa").delete().eq("user_id", st.session_state.user_id).execute()
            st.rerun()
        lista = supabase.table("spesa").select("*").eq("user_id", st.session_state.user_id).execute()
        for s in lista.data:
            col1, col2 = st.columns([0.8, 0.2])
            col1.write(f"🛒 {s['prodotto']}") 
            if col2.button("❌", key=f"del_s_{s['id']}"):
                supabase.table("spesa").delete().eq("id", s['id']).execute()
                st.rerun()
    else:
        st.info("Loggati per la spesa.")

with t4:
    st.header("📖 Archivio")
    if st.session_state.user_id:
        res = supabase.table("ricette").select("*").eq("user_id", st.session_state.user_id).execute()
        for r in res.data:
            with st.expander(f"Ricetta del {r['created_at'][:10]}"):
                # Anche qui puliamo i tag per l'archivio
                testo_arch = r['contenuto'].replace("[HTML]", "").replace("[/HTML]", "").replace("[LISTA]", "").split("[/LISTA]")[-1]
                st.markdown(testo_arch, unsafe_allow_html=True)
                if st.button("Elimina", key=f"del_r_{r['id']}"):
                    supabase.table("ricette").delete().eq("id", r['id']).execute()
                    st.rerun()
    else:
        st.warning("Accedi per l'archivio.")

with t5:
    st.header("💬 Feedback")
    if st.session_state.user_id:
        v = st.slider("Voto", 1, 5, 5)
        c = st.text_area("Messaggio")
        if st.button("Invia", key="send_f"):
            supabase.table("feedback").insert({"user_id": st.session_state.user_id, "voto": v, "messaggio": c}).execute()
            st.success("Inviato!")
    else:
        st.info("Loggati per il feedback.")
