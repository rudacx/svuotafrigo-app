import streamlit as st
import stripe
from groq import Groq
from supabase import create_client
from fpdf import FPDF
import re
import time

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
            success_url="http://localhost:8501/?success=true",
            cancel_url="http://localhost:8501/",
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
    clean_text = re.sub('<[^<]+?>', '', text)
    clean_text = clean_text.encode('ascii', 'ignore').decode('ascii')
    pdf.multi_cell(0, 10, txt=clean_text)
    return pdf.output()
    
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

if query_params.get("type") == "recovery":
    st.warning("⚠️ Modalità Reset Password")
    nuova_pwd = st.text_input("Inserisci la nuova Password", type="password")
    if st.button("Aggiorna Password 🔐"):
        supabase.auth.update_user({"password": nuova_pwd})
        st.success("Password aggiornata! Ora puoi accedere.")
        st.query_params.clear()

# --- 4. SIDEBAR ---
st.sidebar.title("👤 My Kitchen Account")
if st.session_state.user_id is None:
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
    st.sidebar.success(f"Bentornato, {st.session_state.nickname}!")
    st.sidebar.write(f"Piano: {'💎 DIAMOND' if st.session_state.is_premium else '👨‍🍳 STANDARD'}")
    
    if not st.session_state.is_premium:
        st.sidebar.markdown("---")
        opzione = st.sidebar.radio("Scegli upgrade:", ["Gold (6 mesi) €9,99", "Diamond (1 anno) €19,99"])
        
        # --- LINK VANTAGGI PREMIUM ---
        with st.sidebar.expander("✨ Cosa include il Premium?"):
            st.markdown("""
            Passando a un piano superiore sbloccherai:
            - **Archivio illimitato**: Salva quante ricette vuoi.
            - **Dispensa infinita**: Aggiungi tutti i tuoi ingredienti.
            - **Lettura Vocale**: Lo Chef ti guida a voce mentre cucini.
            - **Tabella Macro & Kcal**: Calcoli nutrizionali per ogni ricetta (Solo Diamond).
            - **Supporto Prioritario**: Risolviamo i tuoi problemi subito.
            """)
        
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
    st.header("Generatore di Ricette Intelligente")
    if st.session_state.user_id:
        if st.button("Carica dalla Dispensa 📦"):
            items = supabase.table("dispensa").select("ingrediente").eq("user_id", st.session_state.user_id).execute()
            if items.data:
                st.session_state.ing_input = ", ".join([i['ingrediente'] for i in items.data])
                st.rerun()
            else: st.warning("La tua dispensa è vuota!")

    ing = st.text_area("Quali ingredienti hai?", value=st.session_state.ing_input, placeholder="Es: uova, farina, pomodoro...")
    c1, c2 = st.columns(2)
    tmp = c1.selectbox("Tempo massimo", ["15 min", "30 min", "60 min"])
    mod = c2.selectbox("Personalità dello Chef", ["Simpatico", "Professionale", "Cattivissimo"])

    if st.button("Genera Ricetta ✨", use_container_width=True):
        if not st.session_state.user_id and st.session_state.count_ospite >= 2:
            st.error("Accedi per generare altre ricette!")
        else:
            with st.spinner("Lo Chef sta scrivendo per te..."):
                macros = ""
                if st.session_state.is_premium:
                    macros = " Inoltre, genera una tabella HTML con i Macro (Proteine, Carboidrati, Grassi) e le calorie totali."
                prompt = f"Sei uno chef {mod}. Crea una ricetta in HTML elegante (usa <h4> per i titoli e <b> per i passaggi) usando: {ing}. Tempo: {tmp}.{macros} Alla fine aggiungi il costo stimato."
                res = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=[{"role": "user", "content": prompt}])
                st.session_state.ultima_ricetta = res.choices[0].message.content
                if not st.session_state.user_id: st.session_state.count_ospite += 1
            st.rerun()

    if st.session_state.ultima_ricetta:
        st.markdown("""<style>.recipe-card { background-color: #1E1E1E; padding: 25px; border-radius: 15px; border-left: 6px solid #ff4b4b; color: #f0f0f0; line-height: 1.6; } .recipe-card h4 { color: #ff4b4b !important; font-family: 'serif'; } table { width: 100%; border: 1px solid #444; border-collapse: collapse; margin: 10px 0; } th, td { border: 1px solid #444; padding: 10px; text-align: left; }</style>""", unsafe_allow_html=True)
        st.markdown(f'<div class="recipe-card"><h4>👨‍🍳 La tua Ricetta</h4>{st.session_state.ultima_ricetta}</div>', unsafe_allow_html=True)
        
        st.markdown("---")
        st.subheader("🎤 Assistente in Cucina")
        col_v, col_t = st.columns(2)
        with col_v:
            if st.session_state.is_premium:
                clean_speech = re.sub('<[^<]+?>', '', st.session_state.ultima_ricetta).replace("'", "\\'").replace("\n", " ")
                st.components.v1.html(f"<button id='p' style='width:100%; padding:12px; background:#ff4b4b; color:white; border:none; border-radius:8px; font-weight:bold; cursor:pointer;'>🔊 Leggi Ricetta</button><script>const s = new SpeechSynthesisUtterance('{clean_speech}'); s.lang = 'it-IT'; document.getElementById('p').onclick = () => {{ window.speechSynthesis.cancel(); window.speechSynthesis.speak(s); }};</script>", height=70)
            else: st.info("🎤 Lettura Vocale disponibile solo per utenti Premium 💎")
        
        with col_t:
            timer_m = st.number_input("Timer (minuti):", 1, 60, 10)
            if st.button("Avvia Timer ⏱️"): st.toast(f"Timer da {timer_m} min avviato!")

        c_a, c_b = st.columns(2)
        if st.session_state.user_id:
            if c_a.button("💾 Salva in Archivio", use_container_width=True):
                count_res = supabase.table("ricette").select("id", count="exact").eq("user_id", st.session_state.user_id).execute()
                if not st.session_state.is_premium and (count_res.count or 0) >= 5:
                    st.error("Hai raggiunto il limite di 5 ricette. Passa a Premium! 💎")
                else:
                    supabase.table("ricette").insert({"user_id": st.session_state.user_id, "contenuto": st.session_state.ultima_ricetta}).execute()
                    st.success("Ricetta salvata!")
        
        pdf_bytes = format_pdf(st.session_state.ultima_ricetta)
        c_b.download_button("📄 Scarica PDF", data=pdf_bytes, file_name="ricetta.pdf", use_container_width=True)

with t2:
    st.header("📦 Dispensa")
    if st.session_state.user_id:
        disp_count = supabase.table("dispensa").select("id", count="exact").eq("user_id", st.session_state.user_id).execute()
        n_ing = st.text_input("Aggiungi ingrediente:")
        if st.button("Aggiungi ➕"):
            if not st.session_state.is_premium and (disp_count.count or 0) >= 10:
                st.error("Dispensa piena (max 10). Upgrade a Diamond per spazio infinito! 💎")
            else:
                supabase.table("dispensa").insert({"user_id": st.session_state.user_id, "ingrediente": n_ing}).execute()
                st.rerun()
        for i in supabase.table("dispensa").select("*").eq("user_id", st.session_state.user_id).execute().data:
            col1, col2 = st.columns([4,1])
            col1.write(f"{get_emoji(i['ingrediente'])} {i['ingrediente']}")
            if col2.button("🗑️", key=f"d_{i['id']}"):
                supabase.table("dispensa").delete().eq("id", i['id']).execute()
                st.rerun()

with t3:
    st.header("🛒 Lista della Spesa")
    if st.session_state.user_id:
        manca = st.text_input("Cosa ti serve?")
        if st.button("Aggiungi alla lista 🛒"):
            supabase.table("lista_spesa").insert({"user_id": st.session_state.user_id, "item": manca}).execute()
            st.rerun()
        for s in supabase.table("lista_spesa").select("*").eq("user_id", st.session_state.user_id).execute().data:
            c1, c2 = st.columns([4,1])
            c1.write(f"⬜ {s['item']}")
            if c2.button("✔️", key=f"s_{s['id']}"):
                supabase.table("lista_spesa").delete().eq("id", s['id']).execute()
                st.rerun()

with t4:
    st.header("📖 Il tuo Archivio")
    if st.session_state.user_id:
        mie_ricette = supabase.table("ricette").select("*").eq("user_id", st.session_state.user_id).execute()
        st.info(f"Ricette salvate: {len(mie_ricette.data)} / {'∞' if st.session_state.is_premium else '5'}")
        for r in mie_ricette.data:
            with st.expander(f"Ricetta del {r['created_at'][:10]} 🍴"):
                st.markdown(r['contenuto'], unsafe_allow_html=True)
                if st.button("Elimina Ricetta 🗑️", key=f"del_rec_{r['id']}"):
                    supabase.table("ricette").delete().eq("id", r['id']).execute()
                    st.rerun()

# ... (tutto il resto del tuo codice rimane identico) ...

with t5:
    st.header("Feedback 📣")
    if st.session_state.user_id:
        voto = st.slider("Voto app", 1, 5, 5)
        msg = st.text_area("Suggerimenti?")
        
        if st.button("Invia 🚀"):
            if msg:
                try:
                    # Usiamo un dizionario base per evitare errori di colonne mancanti nel DB
                    dati_feedback = {
                        "user_id": st.session_state.user_id, 
                        "messaggio": msg, 
                        "voto": voto
                    }
                    
                    # Se il nickname esiste nella sessione, proviamo a inserirlo
                    if st.session_state.nickname:
                        dati_feedback["nickname"] = st.session_state.nickname
                    
                    supabase.table("feedback").insert(dati_feedback).execute()
                    st.success("Grazie per il tuo feedback!")
                except Exception as e:
                    # Se fallisce per colpa del nickname, riprova senza
                    try:
                        supabase.table("feedback").insert({
                            "user_id": st.session_state.user_id, 
                            "messaggio": msg, 
                            "voto": voto
                        }).execute()
                        st.success("Inviato con successo!")
                    except:
                        st.error(f"Errore nell'invio: {e}")
            else:
                st.warning("Scrivi un messaggio prima di inviare.")
