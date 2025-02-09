import os
import pandas as pd
import streamlit as st
from datetime import datetime
from database import save_employee_prefs  # Använder databasen istället för CSV

# ========== KONFIGURATION ==========
PREFERENCE_COLUMNS = [
    "Datum", 
    "Sjukhus",
    "Användarnamn",
    "Arbetsbelastning (%)",
    "Prioriterade arbetsformer",
    "Max sammanhängande dagar",
    "Minsta lediga dagar"
]

# ========== FUNKTIONER ==========
def save_preferences(data):
    """Sparar preferenser till databasen via SQLite istället för CSV-fil"""
    try:
        # Om "experience" inte anges av medarbetaren, sätt ett standardvärde (t.ex. 1)
        if "experience" not in data:
            data["experience"] = 1
        # Anropa funktionen i database.py
        save_employee_prefs(data)
        return True
    except Exception as e:
        st.error(f"Fel vid sparande: {str(e)}")
        return False

# Exempel på hur övrig kod kan se ut (du kan självklart behålla övriga delar)
def main_employee_interface():
    """Huvudgränssnitt för anställda"""
    st.title(f"🧑⚕️ Anställdsida - {st.session_state.hospital}")
    st.markdown("---")

    with st.form(key="preferences_form_basic"):
        st.subheader("📋 Schemapreferenser")

        # Användarinformation
        col1, col2 = st.columns(2)
        with col1:
            user_name = st.text_input(
                "Ditt namn",
                help="Ange ditt fullständiga namn för identifiering"
            )
        st.session_state.user_name = user_name

        # Arbetsinställningar
        st.markdown("### 🎚️ Arbetsinställningar")
        workload = st.slider(
            "Önskad arbetsbelastning (%)",
            50, 100, 75,
            step=5,
            help="Välj hur många procent av full arbetstid du önskar arbeta denna vecka"
        )
        st.session_state.workload = workload

        # Arbetsformspreferenser
        work_types = st.multiselect(
            "Prioriterade arbetsformer",
            options=["Nattjour", "Dagskift", "Kvällsskift", "Helg", "Administration"],
            default=["Dagskift"],
            help="Välj de arbetsformer du föredrar (flerval möjligt)"
        )
        st.session_state.work_types = work_types

        # Begränsningar
        st.markdown("### ⚠️ Begränsningar")
        col1, col2 = st.columns(2)
        with col1:
            max_consecutive_days = st.number_input(
                "Max antal sammanhängande arbetsdagar",
                min_value=1,
                max_value=7,
                value=5,
                help="Max antal dagar i rad du kan arbeta"
            )
            st.session_state.max_consecutive_days = max_consecutive_days
        with col2:
            min_days_off = st.number_input(
                "Minsta antal lediga dagar/vecka",
                min_value=1,
                max_value=3,
                value=2,
                help="Minsta antal dagar du måste ha ledigt per vecka"
            )
            st.session_state.min_days_off = min_days_off

        if st.form_submit_button("💾 Spara preferenser"):
            if not st.session_state.user_name.strip():
                st.error("Vänligen ange ditt namn")
            else:
                data = {
                    "hospital": st.session_state.hospital,
                    "name": st.session_state.user_name.strip(),
                    "workload": st.session_state.workload,
                    "work_types": st.session_state.work_types,
                    "max_consecutive_days": st.session_state.max_consecutive_days,
                    "min_days_off": st.session_state.min_days_off
                    # "experience" lämnas inte här – det ska bestämmas av chefen
                }
                if save_preferences(data):
                    st.success("✅ Dina preferenser har sparats!")
                    st.balloons()

    # Historiksektion (om du vill visa den via databasen kan du implementera en get_employee_prefs-funktion)
    st.markdown("---")
    st.subheader("📜 Tidigare sparade preferenser")
    st.info("Preferenserna sparas nu i databasen (SQLite). Kontrollera din databas (vardschema.db) för att se registrerade anställda.")

def show():
    """Huvudfunktion för sidvisning"""
    if "hospital" not in st.session_state or "user_type" not in st.session_state:
        st.warning("⛔ Vänligen logga in först")
        st.stop()
    if st.session_state.user_type != "anställd":
        st.error("🔐 Du har inte behörighet att visa denna sida")
        st.stop()

    main_employee_interface()

    st.markdown("---")
    if st.button("🚪 Logga ut"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

show()
