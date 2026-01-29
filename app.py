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

# LISTA MECCANICI
LISTA_OPERATORI = ["Antonio", "Simone", "Mauro"]

# --- 2. CONNESSIONE ---
def get_google_sheet():
    try:
        if "gcp_service_account" in st.secrets:
            creds = dict(st.secrets["gcp_service_account"])
            if "private_key" in creds:
                creds["private_key"] = creds["private_key"].replace("\\n", "\n")
            gc = gspread.service_account_from_dict(creds)
            return gc.open_by_key(GOOGLE_SHEET_ID)
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
