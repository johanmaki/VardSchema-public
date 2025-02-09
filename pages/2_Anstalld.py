# pages/2_Anstalld.py

import pandas as pd
import os
import streamlit as st
from datetime import datetime
from database import save_employee_prefs

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
    """Sparar preferenser till CSV-fil"""
    try:
        os.makedirs("preferences", exist_ok=True)
        filename = f"preferences/{st.session_state.hospital}_preferenser.csv"
        
        # Skapa ny DataFrame med aktuella data
        new_data = pd.DataFrame([{
            "Datum": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "Sjukhus": st.session_state.hospital,
            "Användarnamn": data.get("name", "Anonymous"),
            "Arbetsbelastning (%)": data["workload"],
            "Prioriterade arbetsformer": ", ".join(data["work_types"]),
            "Max sammanhängande dagar": data["max_consecutive_days"],
            "Minsta lediga dagar": data["min_days_off"]
        }])
        
        # Lägg till i befintlig fil eller skapa ny
        if os.path.exists(filename):
            existing_data = pd.read_csv(filename)
            updated_data = pd.concat([existing_data, new_data], ignore_index=True)
        else:
            updated_data = new_data

        updated_data.to_csv(filename, index=False)
        return True
    except Exception as e:
        st.error(f"Fel vid sparande: {str(e)}")
        return False

def main_employee_interface():
    """Huvudgränssnitt för anställda - sparar grundläggande preferenser."""
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

        # Arbetsinställningar med runda tal (steg om 5)
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
                    "name": st.session_state.user_name.strip(),
                    "workload": st.session_state.workload,
                    "work_types": st.session_state.work_types,
                    "max_consecutive_days": st.session_state.max_consecutive_days,
                    "min_days_off": st.session_state.min_days_off
                }
                if save_preferences(data):
                    st.success("✅ Dina preferenser har sparats!")
                    st.balloons()

    # Historiksektion
    st.markdown("---")
    st.subheader("📜 Tidigare sparade preferenser")
    try:
        filename = f"preferences/{st.session_state.hospital}_preferenser.csv"
        if os.path.exists(filename):
            history_df = pd.read_csv(filename)
            if "user_name" in st.session_state and st.session_state.user_name:
                history_df = history_df[history_df["Användarnamn"] == st.session_state.user_name.strip()]
            if not history_df.empty:
                st.dataframe(
                    history_df.sort_values("Datum", ascending=False),
                    use_container_width=True,
                    hide_index=True
                )
            else:
                st.info("Inga tidigare preferenser hittades")
        else:
            st.info("Inga sparade preferenser ännu")
    except Exception as e:
        st.error(f"Kunde inte ladda historik: {str(e)}")

def show():
    """Huvudfunktion för sidvisning"""
    # Autentiseringskontroll
    if "hospital" not in st.session_state or "user_type" not in st.session_state:
        st.warning("⛔ Vänligen logga in först")
        st.stop()
    if st.session_state.user_type != "anställd":
        st.error("🔐 Du har inte behörighet att visa denna sida")
        st.stop()

    # Visa huvudgränssnittet med grundläggande preferenser
    main_employee_interface()

    # Logga ut-sektion
    st.markdown("---")
    if st.button("🚪 Logga ut"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

show()
