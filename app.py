import streamlit as st
from groq import Groq
from supabase import create_client
import re

# 1. CONFIGURAZIONE PAGINA E GRAFICA INTER
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
        border: none;
        padding: 10px 20px;
    }
    </style>
""", unsafe_allow_html=True)

# 2. COLLEGAMENTO API (Assicurati di averle nei Secrets di Streamlit!)
client = Groq(api_key=st.secrets["GROQ_API_KEY"])
supabase = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

# 3. FUNZIONE PULIZIA TESTO
def super_clean(text):
    # Rimuove blocchi di codice dell'AI
    text = re.sub(r"```html|```", "", text)
    # Cerca il primo titolo e scarta i saluti iniziali dell'AI
    match = re.search(r"<(h1|h2).*", text, re.DOTALL | re.IGNORECASE)
    return match.group(0).strip() if match else text.strip()

# 4. INTERFACCIA A TAB
tab1, tab2 = st.tabs(["🔍 Crea Ricetta", "📚 Archivio"])

if "ultima_ricetta" not in st.session_state:
    st.session_state.ultima_ricetta = None

with tab1:
    st.title("👨‍🍳 SvuotaFrigo AI")
    ingredienti = st.text_input("Cosa hai in frigo?", placeholder="Esempio: uova, farina, pomodoro...")

    if st.button("Genera Ricetta"):
        if ingredienti:
            prompt = f"Crea una ricetta con {ingredienti}. Usa SOLO tag HTML come <h1>, <p>, <ul>, <li>. Non scrivere saluti o commenti, solo la ricetta."
            
            completion = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}]
            )
            
            # Puliamo e salviamo in session_state
            st.session_state.ultima_ricetta = super_clean(completion.choices[0].message.content)
        else:
            st.warning("Inserisci almeno un ingrediente!")

    # Visualizzazione Risultato e Tasto Salva
    if st.session_state.ultima_ricetta:
        st.markdown(f'<div class="recipe-card">{st.session_state.ultima_ricetta}</div>', unsafe_allow_html=True)
        
        if st.button("💾 SALVA NELL'ARCHIVIO", use_container_width=True):
            try:
                # Salvataggio su Supabase
                data = {"content": st.session_state.ultima_ricetta}
                supabase.table("ricette").insert(data).execute()
                st.success("Ricetta salvata correttamente!")
            except Exception as e:
                st.error(f"Errore durante il salvataggio: {e}")

with tab2:
    st.subheader("Le tue ricette salvate")
    # Qui caricheremo la lista da Supabase nel prossimo step se questo funziona
    st.info("Qui appariranno le ricette che hai salvato.")
