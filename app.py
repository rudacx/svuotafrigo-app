import streamlit as st
from groq import Groq
from supabase import create_client
import re

# 1. CONFIGURAZIONE PAGINA E STILE (INTER FONT + DARK MODE)
st.set_page_config(page_title="SvuotaFrigo AI", layout="centered")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;700&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    .stApp { background-color: #0E1117; color: #FFFFFF; }
    .recipe-card {
        background-color: #1E232D;
        padding: 25px;
        border-radius: 15px;
        border: 1px solid #30363D;
        margin-top: 20px;
        line-height: 1.6;
    }
    h1, h2, h3 { color: #00FFAA !important; margin-bottom: 15px; }
    .stButton>button {
        background-color: #00FFAA !important;
        color: #000000 !important;
        font-weight: bold;
        border-radius: 8px;
        width: 100%;
        border: none;
    }
    </style>
""", unsafe_allow_html=True)

# 2. INIZIALIZZAZIONE CLIENTI (Prende i dati dai Secrets che hai salvato)
try:
    client = Groq(api_key=st.secrets["GROQ_API_KEY"])
    supabase = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
except Exception as e:
    st.error("Errore di configurazione: controlla i Secrets su Streamlit Cloud.")

# 3. FUNZIONE DI PULIZIA (Rimuove scarti dell'AI e tag orfani)
def super_clean(text):
    # Rimuove blocchi di codice tipo ```html
    text = re.sub(r"```html|```", "", text)
    # Cerca il primo titolo h1 o h2 e scarta tutto quello che c'è prima (saluti, intro)
    match = re.search(r"<(h1|h2).*", text, re.DOTALL | re.IGNORECASE)
    return match.group(0).strip() if match else text.strip()

# 4. INTERFACCIA A TAB
tab1, tab2 = st.tabs(["🔍 Generatore", "📚 Archivio"])

if "ultima_ricetta" not in st.session_state:
    st.session_state.ultima_ricetta = None

with tab1:
    st.title("👨‍🍳 SvuotaFrigo AI")
    ingredienti = st.text_input("Quali ingredienti hai?", placeholder="Es: Tonno, cipolla, pasta...")

    if st.button("Genera Ricetta ✨"):
        if ingredienti:
            with st.spinner("L'AI sta cucinando per te..."):
                prompt = f"""Crea una ricetta deliziosa usando: {ingredienti}. 
                REGOLE: Usa SOLO tag HTML (<h1>, <h2>, <p>, <ul>, <li>). 
                NON scrivere introduzioni tipo 'Ecco la ricetta'. 
                Inizia direttamente con il titolo in <h1>."""
                
                try:
                    completion = client.chat.completions.create(
                        model="llama-3.3-70b-versatile",
                        messages=[{"role": "user", "content": prompt}]
                    )
                    # Pulizia automatica del risultato
                    st.session_state.ultima_ricetta = super_clean(completion.choices[0].message.content)
                except Exception as e:
                    st.error(f"Errore nella generazione: {e}")
        else:
            st.warning("Ehi! Dimmi almeno un ingrediente.")

    # Visualizzazione Risultato e Tasto Salva
    if st.session_state.ultima_ricetta:
        st.markdown(f'<div class="recipe-card">{st.session_state.ultima_ricetta}</div>', unsafe_allow_html=True)
        
        st.write("---")
        if st.button("💾 SALVA NELL'ARCHIVIO"):
            try:
                # Inserimento su Supabase (Tabella: ricette, Colonna: content)
                data = {"content": st.session_state.ultima_ricetta}
                supabase.table("ricette").insert(data).execute()
                st.success("Ricetta salvata in Supabase!")
            except Exception as e:
                st.error(f"Errore nel salvataggio: {e}")

with tab2:
    st.subheader("Le tue Ricette Salvate")
    try:
        response = supabase.table("ricette").select("*").order("created_at", desc=True).execute()
        for ricetta in response.data:
            with st.expander(f"Ricetta del {ricetta['created_at'][:10]}"):
                st.markdown(ricetta['content'], unsafe_allow_html=True)
    except Exception as e:
        st.error(f"Errore nel caricamento delle ricette: {e}")
