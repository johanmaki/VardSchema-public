# chefsida.py
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from collections import defaultdict
import random
import glob

def load_preferences():
    # Ladda sparade preferenser (anpassa för databas)
    files = glob.glob(f"preferences/{st.session_state.hospital}_*.csv")
    if not files:
        return pd.DataFrame()
    
    dfs = []
    for file in files:
        df = pd.read_csv(file)
        dfs.append(df)
    return pd.concat(dfs, ignore_index=True)

def chef_page():
    # Originalkod från app.py med anpassningar
    st.title(f"Chefsida - {st.session_state.hospital}")
    
    # Ladda anställdas preferenser
    preferences = load_preferences()
    if not preferences.empty:
        st.subheader("Anställdas preferenser")
        st.dataframe(preferences)
    
    # Originalfunktionalitet
    from original_app import main_chef_function
    main_chef_function()
    
    # Logga ut-knapp
    st.markdown("---")
    if st.button("Logga ut"):
        del st.session_state.hospital
        del st.session_state.user_type
        st.rerun()

# Flytta originalkoden till en separat funktion
def main_chef_function():
    # Här skulle du flytta den befintliga app.py-koden
    # (Begränsat utrymme, se nästa svar för full implementation)