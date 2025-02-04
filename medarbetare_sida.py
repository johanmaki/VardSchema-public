# anstalld_sida.py
import streamlit as st
import pandas as pd
from datetime import datetime

def save_preferences(data):
    # Sparar preferenser till CSV (kan ersättas med databas)
    df = pd.DataFrame([data])
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"preferences/{st.session_state.hospital}_{timestamp}.csv"
    df.to_csv(filename, index=False)

def employee_page():
    st.title(f"Anställdsida - {st.session_state.hospital}")
    
    with st.form("preference_form"):
        st.subheader("Dina schemapreferenser")
        
        # Schemaönskemål
        st.markdown("### Önskad arbetsbelastning (%)")
        workload = st.slider("Välj önskad procentuell arbetsbelastning", 50, 100, 75)
        
        # Prioriteringar
        st.markdown("### Prioriteringstyper")
        work_types = st.multiselect(
            "Välj önskade arbetsformer",
            ["Nattjour", "Dagskift", "Kvällsskift", "Helg", "Administration"],
            default=["Dagskift"]
        )
        
        # Begränsningar
        st.markdown("### Begränsningar")
        col1, col2 = st.colums(2)
        with col1:
            max_consecutive_days = st.number_input("Max antal sammanhängande arbetsdagar", 1, 7, 5)
        with col2:
            min_days_off = st.number_input("Minsta antal lediga dagar/vecka", 1, 3, 2)
            
        # Submit-knapp
        if st.form_submit_button("Spara preferenser"):
            preferences = {
                "workload": workload,
                "work_types": ", ".join(work_types),
                "max_consecutive_days": max_consecutive_days,
                "min_days_off": min_days_off,
                "timestamp": datetime.now()
            }
            save_preferences(preferences)
            st.success("Dina preferenser har sparats!")
    
    st.markdown("---")
    if st.button("Logga ut"):
        del st.session_state.hospital
        del st.session_state.user_type
        st.rerun()
