import streamlit as st
import pandas as pd
from datetime import datetime, date
import time
import gspread
import json

# --- 1. CONFIGURAZIONE ---
st.set_page_config(page_title="Gestione Diemmeauto Cloud", layout="wide")

# ID FOGLIO GOOGLE
GOOGLE_SHEET_ID = "18Aw9zqQLSvQUy8fG1D2g67kTHa1vkIsnvTs90GaHjjM"

# NOMI FOGLI
SHEET_LAVORI = "Lavori_In_Corso"
SHEET_STORICO = "Storico"
SHEET_AGENDA = "Agenda"

# LISTA MECCANICI (Modificala qui se serve)
LISTA_OPERATORI = ["Antonio", "Simone", "Mauro"]

# --- 2. CONNESSIONE BLINDATA ---
def get_google_sheet():
    try:
        # TENTATIVO 1: Streamlit Cloud (Formato TOML)
        if "gcp_service_account" in st.secrets:
            creds = dict(st.secrets["gcp_service_account"])
            
            # FIX AUTOMATICO CHIAVE: converte \n testuali in veri a capo
            if "private_key" in creds:
                creds["private_key"] = creds["private_key"].replace("\\n", "\n")
            
            gc = gspread.service_account_from_dict(creds)
            return gc.open_by_key(GOOGLE_SHEET_ID)

        # TENTATIVO 2: Mac (File locale)
        else:
            gc = gspread.service_account(filename="chiave.json")
            return gc.open_by_key(GOOGLE_SHEET_ID)

    except Exception as e:
        st.error(f"❌ ERRORE CONNESSIONE: {e}")
        st.stop()

def get_worksheet_sicuro(sh, nome_foglio, colonne_default):
    try:
        return sh.worksheet(nome_foglio)
    except gspread.WorksheetNotFound:
        ws = sh.add_worksheet(title=nome_foglio, rows=100, cols=20)
        ws.append_row(colonne_default)
        return ws

def carica_dati(nome_worksheet, colonne_attese):
    try:
        sh = get_google_sheet()
        worksheet = get_worksheet_sicuro(sh, nome_worksheet, colonne_attese)
        data = worksheet.get_all_records()
        df = pd.DataFrame(data)
        if df.empty: return pd.DataFrame(columns=colonne_attese)
        df = df.astype(str)
        for col in colonne_attese:
            if col not in df.columns: df[col] = "" 
        return df
    except: return pd.DataFrame(columns=colonne_attese)

def salva_dati(df, nome_worksheet, colonne_attese):
    try:
        sh = get_google_sheet()
        worksheet = get_worksheet_sicuro(sh, nome_worksheet, colonne_attese)
        worksheet.clear()
        worksheet.update([df.columns.values.tolist()] + df.astype(str).values.tolist())
    except Exception as e:
        st.error(f"❌ Errore salvataggio: {e}")

# --- 3. INTERFACCIA ---
def add_bg():
    st.markdown("""
    <style>
    .stApp { background-image: url("https://images.unsplash.com/photo-1530046339160-ce3e4234721f?q=80&w=1920&auto=format&fit=crop"); background-attachment: fixed; background-size: cover; }
    [data-testid="stExpander"], [data-testid="stForm"], [data-testid="stContainer"] { background-color: rgba(255, 255, 255, 0.95) !important; border-radius: 12px; padding: 15px; }
    </style>
    """, unsafe_allow_html=True)
add_bg()
st.title("☁️ Diemmeauto - Gestionale")

col_in_corso = ["Targa", "Operatore", "Lavori da Eseguire", "Ora Ultimo Inizio", "Minuti Gia Fatti", "Stato"]
col_storico = ["Data", "Targa", "Operatore", "Lavori Eseguiti", "Ora Inizio", "Ora Fine", "Durata (min)"]
col_agenda = ["Data", "Ora", "Targa", "Lavoro", "Scaffale Ricambi", "Tempo Stimato (h)"]

df_in_corso = carica_dati(SHEET_LAVORI, col_in_corso)
df_storico = carica_dati(SHEET_STORICO, col_storico)
df_agenda = carica_dati(SHEET_AGENDA, col_agenda)

# MENU LATERALE
menu = st.sidebar.radio("📌 Menu", ["⏱️ Officina", "📅 Agenda", "📊 Admin"])

# --- SEZIONE 1: OFFICINA ---
if menu == "⏱️ Officina":
    st.header("🟢 Inizia Lavoro")
    oggi = date.today().strftime("%Y-%m-%d")
    app_oggi = pd.DataFrame()
    if not df_agenda.empty and 'Data' in df_agenda.columns: app_oggi = df_agenda[df_agenda['Data'] == oggi]
    t_def, l_def = "", ""
    if not app_oggi.empty:
        opts = ["-- Manuale --"] + [f"{r['Ora']} | {r['Targa']} | {r['Lavoro']}" for i, r in app_oggi.iterrows()]
        sel = st.selectbox("Seleziona da Agenda:", opts)
        if sel != "-- Manuale --":
            try:
                t_sel = sel.split(" | ")[1]
                row = app_oggi[app_oggi['Targa'] == t_sel].iloc[0]
                t_def = row['Targa']
                l_def = f"{row['Lavoro']} [Scaffale: {row['Scaffale Ricambi']}]"
            except: pass
    with st.container():
        c1, c2, c3 = st.columns(3)
        op = c1.selectbox("Operatore", LISTA_OPERATORI)
        ta = c2.text_input("Targa", value=t_def).upper()
        de = c3.text_input("Lavori", value=l_def)
        if st.button("INIZIA 🚀", type="primary", use_container_width=True):
            if ta and de:
                df_in_corso['Operatore'] = df_in_corso['Operatore'].astype(str)
                if not df_in_corso[df_in_corso['Operatore'] == op].empty: st.error("Operatore occupato!")
                else:
                    nuovo = {"Targa": ta, "Operatore": op, "Lavori da Eseguire": de, "Ora Ultimo Inizio": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "Minuti Gia Fatti": "0", "Stato": "IN CORSO"}
                    df_in_corso = pd.concat([df_in_corso, pd.DataFrame([nuovo])], ignore_index=True)
                    salva_dati(df_in_corso, SHEET_LAVORI, col_in_corso)
