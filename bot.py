import streamlit as st
st.markdown('<link rel="manifest" href="./manifest.json">', unsafe_allow_html=True)
import stripe
from groq import Groq
from supabase import create_client
from fpdf import FPDF
import re
import time
import io

# --- 1. CONFIGURAZIONI ---
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

def get_emoji(n):
    n = str(n).lower()
    mapping = {"uov": "🥚", "pata": "🥔", "carn": "🍗", "past": "🍝", "pomo": "🍅", "form": "🧀", "pesc": "🐟", "lat": "🥛", "olio": "🫗", "pane": "🥖"}
    for k, v in mapping.items():
        if k in n: return v
    return "🟢"

def format_pdf(text):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    # Rimuoviamo tag HTML e caratteri speciali per il PDF
    clean_text = re.sub('<[^<]+?>', '', text)
    clean_text = clean_text.encode('latin-1', 'ignore').decode('latin-1')
    pdf.multi_cell(0, 10, txt=clean_text)
    # Restituiamo i bytes pronti per il download
    return pdf.output(dest='S').encode('latin-1')

# --- 3. GESTIONE SESSIONE ---
if "user_id" not in st.session_state: st.session_state.user_id = None
if "is_premium" not in st.session_state: st.session_state.is_premium = False
if "nickname" not in st.session_state: st.session_state.nickname = ""
if "ultima_ricetta" not in st.session_state: st.session_state.ultima_ricetta = ""
if "ing_input" not in st.session_state: st.session_state.ing_input = ""
if "count_ospite" not in st.session_state: st.session_state.count_ospite = 0

query_params = st.query_params

if query_params.get("success") == "true":
    if st.session_state.user_id:
        supabase.table("profili").update({"is_premium": True}).eq("id", st.session_state.user_id).execute()
        st.session_state.is_premium = True
        st.balloons()
    st.query_params.clear()

# --- 4. SIDEBAR ---
if st.session_state.user_id is None:
    st.sidebar.title("👉 Accedi Qui! 👈")
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
                elif scelta == "Recupero Password":
                    supabase.auth.reset_password_for_email(email)
                    st.info("Email di reset inviata!")
            except Exception as e: st.error(f"Errore: {e}")
else:
    st.sidebar.title("👤 Account")
    st.sidebar.success(f"Bentornato, {st.session_state.nickname}!")
    st.sidebar.write(f"Piano: {'💎 DIAMOND' if st.session_state.is_premium else '👨‍🍳 STANDARD'}")
    
    if not st.session_state.is_premium:
        st.sidebar.markdown("---")
        opzione = st.sidebar.radio("Scegli upgrade:", ["Gold (6 mesi) €9,99", "Diamond (1 anno) €19,99"])
        if st.sidebar.button("Attiva Premium 💳", use_container_width=True):
            id_scelto = ID_DIAMOND if "Diamond" in opzione else ID_GOLD
            url = crea_sessione_stripe(id_scelto)
            if url: st.sidebar.link_button("Procedi al pagamento 🛡️", url)
    
    if st.sidebar.button("Logout 🚪", use_container_width=True):
        st.session_state.clear()
        st.rerun()

# --- 5. INTERFACCIA PRINCIPALE ---
t1, t2, t3, t4, t5 = st.tabs(["🔥 Cucina AI", "📦 Dispensa", "🛒 Spesa", "📖 Archivio", "💬 Feedback"])

with t1:
    st.header("Generatore di Ricette")
    if st.session_state.user_id:
        if st.button("Carica dalla Dispensa 📦"):
            items = supabase.table("dispensa").select("ingrediente").eq("user_id", st.session_state.user_id).execute()
            if items.data:
                st.session_state.ing_input = ", ".join([i['ingrediente'] for i in items.data])
                st.rerun()
            else: st.warning("La tua dispensa è vuota!")
    
    # Alert Premium per la cucina
    if st.session_state.user_id and not st.session_state.is_premium:
        st.info("💡 **Consiglio:** Passa a Diamond per avere anche i calcoli nutrizionali!")

    ing = st.text_area("Quali ingredienti hai?", value=st.session_state.ing_input, placeholder="Es: uova, farina...")
    c1, c2 = st.columns(2)
    tmp = c1.selectbox("Tempo massimo", ["15 min", "30 min", "60 min"])
    mod = c2.selectbox("Chef", ["Simpatico", "Professionale", "Cattivissimo"])

    if st.button("Genera Ricetta ✨", use_container_width=True):
        if not st.session_state.user_id and st.session_state.count_ospite >= 2:
            st.error("Accedi per generare altre ricette! (Max 2 per ospiti)")
        else:
            with st.spinner("Lo Chef sta scrivendo..."):
                macros = " Inoltre, genera una tabella HTML con i Macro e calorie." if st.session_state.is_premium else ""
                prompt = f"Sei uno chef {mod}. Crea una ricetta in HTML elegante usando: {ing}. Tempo: {tmp}.{macros}"
                res = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=[{"role": "user", "content": prompt}])
                st.session_state.ultima_ricetta = res.choices[0].message.content
                if not st.session_state.user_id: st.session_state.count_ospite += 1
            st.rerun()

    if st.session_state.ultima_ricetta:
        st.markdown(f'<div style="background-color:#1E1E1E; padding:20px; border-radius:10px; border-left:5px solid #ff4b4b;">{st.session_state.ultima_ricetta}</div>', unsafe_allow_html=True)
        
        col_v, col_t = st.columns(2)
        with col_v:
            if st.session_state.is_premium:
                clean_speech = re.sub('<[^<]+?>', '', st.session_state.ultima_ricetta).replace("'", " ").replace("\n", " ")
                st.components.v1.html(f"<button id='p' style='width:100%; padding:10px; background:#ff4b4b; color:white; border:none; border-radius:5px; cursor:pointer;'>🔊 Leggi</button><script>const s = new SpeechSynthesisUtterance('{clean_speech}'); s.lang = 'it-IT'; document.getElementById('p').onclick = () => {{ window.speechSynthesis.speak(s); }};</script>", height=60)
            else:
                if st.button("🔊 Leggi (Premium)", use_container_width=True): st.warning("Sblocca il piano Diamond per la lettura vocale!")

        c_a, c_b = st.columns(2)
        if st.session_state.user_id:
            if c_a.button("💾 Salva", use_container_width=True):
                count_res = supabase.table("ricette").select("id", count="exact").eq("user_id", st.session_state.user_id).execute()
                if not st.session_state.is_premium and (count_res.count or 0) >= 5:
                    st.error("Limite 5 ricette raggiunto! Diventa Premium 💎")
                else:
                    supabase.table("ricette").insert({"user_id": st.session_state.user_id, "contenuto": st.session_state.ultima_ricetta}).execute()
                    st.success("Salvata!")
        
        pdf_data = format_pdf(st.session_state.ultima_ricetta)
        c_b.download_button("📄 PDF", data=pdf_data, file_name="ricetta.pdf", mime="application/pdf", use_container_width=True)

with t2:
    st.header("📦 Dispensa")
    if st.session_state.user_id:
        disp_count = supabase.table("dispensa").select("id", count="exact").eq("user_id", st.session_state.user_id).execute()
        n_ing = st.text_input("Nuovo ingrediente:")
        if st.button("Aggiungi ➕"):
            if not st.session_state.is_premium and (disp_count.count or 0) >= 10:
                st.error("Limite 10 ingredienti. Passa a Diamond! 💎")
            else:
                supabase.table("dispensa").insert({"user_id": st.session_state.user_id, "ingrediente": n_ing}).execute()
                st.rerun()
        for i in supabase.table("dispensa").select("*").eq("user_id", st.session_state.user_id).execute().data:
            c1, c2 = st.columns([4,1])
            c1.write(f"{get_emoji(i['ingrediente'])} {i['ingrediente']}")
            if c2.button("🗑️", key=f"d_{i['id']}"):
                supabase.table("dispensa").delete().eq("id", i['id']).execute()
                st.rerun()
    else:
        st.warning("⚠️ Loggati per usare la Dispensa e caricare gli ingredienti automaticamente!")

with t3:
    st.header("🛒 Lista Spesa")
    if st.session_state.user_id:
        manca = st.text_input("Cosa manca?")
        if st.button("Aggiungi 🛒"):
            supabase.table("lista_spesa").insert({"user_id": st.session_state.user_id, "item": manca}).execute()
            st.rerun()
        for s in supabase.table("lista_spesa").select("*").eq("user_id", st.session_state.user_id).execute().data:
            c1, c2 = st.columns([4,1])
            c1.write(f"⬜ {s['item']}")
            if c2.button("✔️", key=f"s_{s['id']}"):
                supabase.table("lista_spesa").delete().eq("id", s['id']).execute()
                st.rerun()
    else:
        st.warning("⚠️ Loggati per salvare la tua lista della spesa!")

with t4:
    st.header("📖 Archivio")
    if st.session_state.user_id:
        mie = supabase.table("ricette").select("*").eq("user_id", st.session_state.user_id).execute()
        st.info(f"Salvate: {len(mie.data)} / {'∞' if st.session_state.is_premium else '5'}")
        for r in mie.data:
            with st.expander(f"Ricetta {r['created_at'][:10]}"):
                st.markdown(r['contenuto'], unsafe_allow_html=True)
                if st.button("Elimina", key=f"del_{r['id']}"):
                    supabase.table("ricette").delete().eq("id", r['id']).execute()
                    st.rerun()
    else:
        st.warning("⚠️ Loggati per archiviare le tue ricette preferite!")

with t5:
    st.header("Feedback 📣")
    if st.session_state.user_id:
        msg = st.text_area("Suggerimenti?")
        if st.button("Invia 🚀"):
            supabase.table("feedback").insert({"user_id": st.session_state.user_id, "messaggio": msg}).execute()
            st.success("Grazie!")
    else:
        st.warning("⚠️ Accedi per inviarci un feedback.")
