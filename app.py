import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import uuid

# --- 1. CONFIGURAZIONE E COSTANTI ---
st.set_page_config(page_title="Autovalutazione Colloquio", page_icon="📝")

# COLORI DEL BRAND (MODIFICA QUESTI CODICI HEX PER I COLORI DI GENERA)
COLOR_PRIMARY = "#1f77b4"  # Colore principale (es. Blu)
COLOR_SECONDARY = "#ff7f0e" # Colore secondario (es. Arancione)
COLOR_ACCENT = "#2ca02c"   # Colore accento (es. Verde)

# DOMANDE E AREE
DOMANDE = {
    "Ascolto Attivo": [
        "Complessivamente come valuti la tua capacità di ascolto? (Non solo parole, ma segnali non verbali)",
        "Quanto ti ritieni in grado di approfondire ciò che hai appena sentito facendo domande?",
        "Quando l'interlocutore fa una pausa, quanto sei in grado di resistere all'impulso di interromperlo?"
    ],
    "Empatia e Gestione Emozioni": [
        "Quanto ti ritieni in grado di creare un ambiente rilassato che metta l'interlocutore a proprio agio?",
        "Quanto ti ritieni in grado di gestire le tue emozioni rimanendo calmo anche in tensione?",
        "Quanto riesci a percepire lo stato d'animo dell'interlocutore e modificare il tuo approccio?"
    ],
    "Competenze Informative (Domande)": [
        "Quanto sai strutturare le domande per far emergere esempi concreti (comportamenti/competenze)?",
        "Quanto sei in grado di formulare domande che valutino le 'soft skills'?",
        "Quanto riesci ad evitare domande da 'sì/no' formulando domande che richiedono risposte elaborate?"
    ],
    "Competenze di Equità (Obiettività)": [
        "Quanto sei consapevole dei tuoi pregiudizi e cerchi di non farti influenzare?",
        "Quanto sei capace di basarti su fatti e dati concreti anziché su impressioni o simpatia?",
        "Quanto ti ritieni in grado di applicare lo stesso metro di giudizio a tutti?"
    ]
}

# FEEDBACK TESTUALE
FEEDBACK_INFO = {
    "Ascolto Attivo": {
        "title": "🟢 Se devi potenziare l'Ascolto Attivo:",
        "goal": "Obiettivo: Passare dal semplice 'sentire' all'ascolto generativo.",
        "actions": [
            "**Azione 1 (Non verbale):** Osserva il linguaggio del corpo. I segnali corrispondono alle parole?",
            "**Azione 2 (Restituzione):** Riassumi con parole tue ciò che l'altro ha detto per verificare la comprensione.",
            "**Azione 3 (Apertura):** Usa domande come 'Mi puoi raccontare di più su...?' per incoraggiare la narrazione."
        ]
    },
    "Empatia e Gestione Emozioni": {
        "title": "🔵 Se devi potenziare l'Empatia:",
        "goal": "Obiettivo: Sintonizzarsi sulla lunghezza d'onda dell'altro per ridurre le difese.",
        "actions": [
            "**Azione 1 (Immedesimazione):** Prima del colloquio, rifletti sulle possibili ansie dell'interlocutore.",
            "**Azione 2 (Postura):** Mantieni un linguaggio del corpo accogliente (non incrociare le braccia).",
            "**Azione 3 (Mindfulness):** Gestisci la tua ansia con la respirazione."
        ]
    },
    "Competenze Informative (Domande)": {
        "title": "🟠 Se devi potenziare la Formulazione delle Domande:",
        "goal": "Obiettivo: Raccogliere informazioni utili, non solo conferme.",
        "actions": [
            "**Azione 1 (Tecnica STAR):** Chiedi Situazione, Task, Azione, Risultato per avere esempi concreti.",
            "**Azione 2 (Specificità):** Prepara le domande in anticipo focalizzandole su comportamenti passati.",
            "**Azione 3 (Simulazione):** Fai pratica con colleghi (colloqui fittizi)."
        ]
    },
    "Competenze di Equità (Obiettività)": {
        "title": "🟣 Se devi potenziare l'Obiettività:",
        "goal": "Obiettivo: Basare la valutazione sui fatti, riducendo i bias cognitivi.",
        "actions": [
            "**Azione 1 (Struttura):** Usa una griglia di valutazione strutturata per basarti su criteri oggettivi.",
            "**Azione 2 (Focus sui dati):** Valuta la qualità della risposta, non l'emozione di chi risponde.",
            "**Azione 3 (Consapevolezza):** Attento all'effetto alone e al bias di conferma."
        ]
    }
}

# --- 2. FUNZIONI DI SUPPORTO ---

def save_to_google_sheet(data_dict):
    """Salva i dati su Google Sheet. Ritorna True se successo, False se errore."""
    try:
        # Recupera le credenziali dai Secrets di Streamlit
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds_dict = st.secrets["gcp_service_account"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        
        # Apre il foglio (sostituisci con il nome esatto del tuo foglio se diverso)
        sheet = client.open("Dati Autovalutazione GENERA").sheet1
        
        # Prepara la riga
        row = [
            data_dict["identificativo"],
            data_dict["genere"],
            data_dict["eta"],
            data_dict["titolo_studio"],
            data_dict["job"]
        ]
        # Aggiunge i punteggi
        for area in DOMANDE:
            for i in range(len(DOMANDE[area])):
                key = f"{area}_{i}"
                row.append(data_dict.get(key, 0))
                
        sheet.append_row(row)
        return True
    except Exception as e:
        st.error(f"⚠️ Impossibile salvare i dati nel cloud (Errore: {e}). Il feedback verrà comunque mostrato.")
        return False

def create_radar_chart(scores):
    """Crea un grafico radar con i punteggi medi per area."""
    labels = list(scores.keys())
    # Normalizza i punteggi su base 10 per il grafico (dato che il max per area è 18)
    # Oppure usiamo il valore assoluto. Max score per area = 3 domande * 6 punti = 18.
    values = list(scores.values())
    
    # Chiudi il cerchio del grafico
    values += values[:1]
    angles = np.linspace(0, 2*np.pi, len(labels), endpoint=False).tolist()
    angles += angles[:1]
    
    fig, ax = plt.subplots(figsize=(6, 6), subplot_kw=dict(polar=True))
    ax.fill(angles, values, color=COLOR_PRIMARY, alpha=0.25)
    ax.plot(angles, values, color=COLOR_PRIMARY, linewidth=2)
    
    ax.set_yticklabels([])
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(labels, fontsize=10)
    
    # Scala massima fissa a 18
    ax.set_ylim(0, 18)
    
    return fig

# --- 3. INTERFACCIA UTENTE (MAIN) ---

def main():
    # CSS per Footer e Logo responsivo
    st.markdown("""
        <style>
        .footer {position: fixed; left: 0; bottom: 0; width: 100%; background-color: #f1f1f1; color: #555; text-align: center; padding: 10px; font-size: 12px;}
        [data-testid="stImage"] {display: block; margin-left: auto; margin-right: auto;}
        </style>
        """, unsafe_allow_html=True)

    # --- HEADER ---
    try:
        st.image("GENERA Logo Colore.png", use_container_width=True)
    except:
        st.warning("Immagine 'GENERA Logo Colore.png' non trovata. Caricala nella repository.")

    st.title("Autovalutazione della competenza nel condurre un colloquio")

    # --- INTRODUZIONE ---
    if 'submitted' not in st.session_state:
        st.markdown("""
        ### Benvenuto/a.
        
        Spesso pensiamo all'organizzazione come a una macchina, ma in realtà essa è una comunità di persone, una **"macchina con l'anima"**. In questo contesto, il colloquio non è un semplice interrogatorio o una procedura burocratica, ma lo strumento principe per la **cura della relazione**.

        Il colloquio è un momento di scambio in cui si incontrano non solo informazioni, ma persone. Non è mai neutro: è un evento relazionale dove elementi cognitivi ed emotivi si intrecciano. L'obiettivo non è solo scambiare dati, ma **generare nuove informazioni** e nuove possibilità di crescita.

        Questa App ti aiuta a valutare il tuo "potere personale" nella conduzione del colloquio.
        """)
        
        st.info("Proseguendo nella compilazione acconsento a che i dati raccolti potranno essere utilizzati in forma aggregata esclusivamente per finalità statistiche.")
        
        if st.button("👉 INIZIA L'AUTOVALUTAZIONE"):
            st.session_state['started'] = True
            st.rerun()

    # --- QUESTIONARIO E DATI ---
    elif 'started' in st.session_state and 'submitted' not in st.session_state:
        
        with st.form("assessment_form"):
            st.markdown("### Informazioni Generali")
            
            col1, col2 = st.columns(2)
            with col1:
                nome = st.text_input("Nome o Nickname")
                eta = st.selectbox("Età", ["fino a 20 anni", "21-30 anni", "31-40 anni", "41-50 anni", "51-60 anni", "61-70 anni", "più di 70 anni"])
                titolo = st.selectbox("Titolo di studio", ["licenza media", "qualifica professionale", "diploma di maturità", "laurea triennale", "laurea magistrale (o ciclo unico)", "titolo post lauream"])
            
            with col2:
                genere = st.selectbox("Genere", ["Maschile", "Femminile", "Non binario", "Non risponde"])
                job = st.selectbox("Job", ["imprenditore", "top manager", "middle manager", "impiegato", "operaio", "tirocinante", "libero professionista"])
            
            st.markdown("---")
            st.markdown("### Questionario")
            st.caption("Valuta la tua abilità su una scala da 1 (Pessima) a 6 (Ottima).")

            responses = {}
            
            # Generazione dinamica delle domande
            for area, questions in DOMANDE.items():
                st.subheader(area)
                for idx, q in enumerate(questions):
                    key = f"{area}_{idx}"
                    # Scala Likert a 6 punti (1-6)
                    responses[key] = st.slider(q, min_value=1, max_value=6, value=3, key=key)
                st.markdown(" ")

            submitted = st.form_submit_button("Calcola il mio Profilo")
            
            if submitted:
                if not nome:
                    st.error("Per favore inserisci un nome o nickname.")
                else:
                    # Calcolo Punteggi
                    scores_by_area = {}
                    total_score = 0
                    
                    for area in DOMANDE:
                        area_total = 0
                        for i in range(len(DOMANDE[area])):
                            area_total += responses[f"{area}_{i}"]
                        scores_by_area[area] = area_total
                        total_score += area_total
                    
                    # Preparazione dati per salvataggio
                    user_data = {
                        "identificativo": f"{datetime.now().strftime('%Y%m%d%H%M')}_{str(uuid.uuid4())[:4]}",
                        "genere": genere,
                        "eta": eta,
                        "titolo_studio": titolo,
                        "job": job,
                        **responses # Unisce le risposte singole
                    }
                    
                    # Salvataggio
                    save_success = save_to_google_sheet(user_data)
                    
                    # Salvataggio in session state per visualizzare i risultati
                    st.session_state['submitted'] = True
                    st.session_state['scores'] = scores_by_area
                    st.session_state['total'] = total_score
                    st.rerun()

    # --- RISULTATI ---
    elif 'submitted' in st.session_state:
        scores = st.session_state['scores']
        
        st.markdown("## 📊 Il Tuo Profilo di Potere")
        st.write(f"**Punteggio Totale:** {st.session_state['total']} / 72")
        
        # Grafico Radar
        fig = create_radar_chart(scores)
        st.pyplot(fig)
        
        st.markdown("---")
        st.markdown("### Aree di Miglioramento")
        st.write("Di seguito le aree dove puoi aprire nuove possibilità (punteggio < 11 su 18):")
        
        areas_to_improve = False
        for area, score in scores.items():
            # Soglia: 18 è il max. 11 è circa il 60%.
            if score < 11:
                areas_to_improve = True
                content = FEEDBACK_INFO[area]
                with st.expander(f"{content['title']} (Punteggio: {score}/18)", expanded=True):
                    st.markdown(f"_{content['goal']}_")
                    for action in content['actions']:
                        st.markdown(f"- {action}")
        
        if not areas_to_improve:
            st.success("Complimenti! Hai ottenuto punteggi alti in tutte le aree. Continua a coltivare queste competenze.")

        if st.button("Ricomincia"):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()

    # --- FOOTER ---
    st.markdown('<div class="footer">Powered by GÉNERA</div>', unsafe_allow_html=True)

if __name__ == "__main__":
    main()
