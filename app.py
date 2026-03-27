import streamlit as st
import stripe
from groq import Groq
from supabase import create_client
import re

# --- CONFIGURAZIONE ---
st.set_page_config(page_title="Svuotafrigo Pro", layout="wide")

# Connessioni dai Secrets
try:
    client = Groq(api_key=st.secrets["GROQ_API_KEY"])
    supabase = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
    stripe.api_key = st.secrets["STRIPE_API_KEY"]
except:
    st.error("Errore nei Secrets! Verifica SUPABASE_URL e le API Key.")

# IDs Prodotti Stripe
ID_GOLD = "price_1TD86OBBE2wDwi0CI4KlvKFJ"   
ID_DIAMOND = "price_1TD88HBBE2wDwi0CV9d2heo2"

# --- SESSION STATE ---
if "user_id" not in st.session_state: st.session_state.user_id = None
if "ultima_ricetta" not in st.session_state: st.session_state.ultima_ricetta = None

# --- UI TABS ---
t1, t2, t3, t4, t5 = st.tabs(["🔥 CUCINA", "📦 DISPENSA", "🛒 SPESA", "📖 ARCHIVIO", "💬 FEEDBACK"])

with t1:
    st.title("👨‍🍳 Generatore Ricette")
    ing = st.text_area("Cosa hai in frigo?", placeholder="Es: uova, farina...")
    if st.button("GENERA ✨", use_container_width=True):
        with st.spinner("Creazione..."):
            r = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=[{"role":"user","content":f"Ricetta HTML: {ing}"}])
            st.session_state.ultima_ricetta = r.choices[0].message.content
    
    if st.session_state.ultima_ricetta:
        st.markdown(f'<div style="background:#1E232D;padding:20px;border-radius:15px;">{st.session_state.ultima_ricetta}</div>', unsafe_allow_html=True)
        if st.session_state.user_id and st.button("💾 SALVA IN ARCHIVIO"):
            try:
                # Inserimento nella colonna 'content'
                supabase.table("ricette").insert({"user_id": st.session_state.user_id, "content": st.session_state.ultima_ricetta}).execute()
                st.success("Salvata!")
            except Exception as e:
                st.error(f"Errore: {e}")

with t2:
    st.header("📦 Dispensa")
    if st.session_state.user_id:
        item = st.text_input("Aggiungi ingrediente")
        if st.button("Aggiungi"):
            # Usa la tabella 'dispensa' che vedo nel tuo DB
            supabase.table("dispensa").insert({"user_id": st.session_state.user_id, "ingrediente": item}).execute()
            st.rerun()
        
        # Visualizzazione
        data = supabase.table("dispensa").select("*").eq("user_id", st.session_state.user_id).execute()
        for i in data.data: st.write(f"✅ {i['ingrediente']}")
    else: st.warning("Esegui il login per usare la dispensa.")

with t5:
    st.header("💬 Feedback")
    voto = st.slider("Voto", 1, 5, 5)
    msg = st.text_area("Commento")
    if st.button("Invia Feedback"):
        if st.session_state.user_id:
            # Salvataggio nella tabella 'feedback'
            supabase.table("feedback").insert({"user_id": st.session_state.user_id, "voto": voto, "commento": msg}).execute()
            st.success("Grazie!")
        else: st.error("Accedi per inviare feedback.")
