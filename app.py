# app.py
import streamlit as st

# ========== KONFIGURATION ==========
HOSPITAL_OPTIONS = ["Karolinska", "Sahlgrenska", "Danderyd"]
THEME_CONFIG = {
    "primaryColor": "#1E88E5",
    "backgroundColor": "#FFFFFF",
    "secondaryBackgroundColor": "#F0F2F6",
    "textColor": "#000000",
    "font": "sans serif"
}

# ========== HJÄLPFUNKTIONER ==========
def clear_session():
    """Rensar all session state data"""
    keys = list(st.session_state.keys())
    for key in keys:
        del st.session_state[key]

# ========== LANDNINGSSIDA ==========
def show_landing_page():
    """Visar startsidan med sjukhusval och rollval"""
    st.set_page_config(
        page_title="VårdSchema Pro",
        page_icon="🏥",
        layout="centered"
    )
    
    # Header-sektion
    st.title("Välkommen till VårdSchema Pro")
    st.markdown("---")
    
    # Huvudinnehåll
    with st.container():
        col1, col2 = st.columns([3, 2])
        
        with col1:
            # Sjukhusval
            hospital = st.selectbox(
                "Välj ditt sjukhus",
                HOSPITAL_OPTIONS,
                index=0,
                help="Välj det sjukhus där du är verksam"
            )
            
        with col2:
            # Rollval
            st.markdown("### Välj din roll")
            role_col1, role_col2 = st.columns(2)
            
            with role_col1:
                if st.button(
                    "Medarbetare 🧑⚕️",
                    help="Logga in som vårdpersonal",
                    use_container_width=True
                ):
                    st.session_state.hospital = hospital
                    st.session_state.user_type = "anställd"
                    st.rerun()
            
            with role_col2:
                if st.button(
                    "Chef 👨💼",
                    help="Logga in som chef eller administratör",
                    use_container_width=True
                ):
                    st.session_state.hospital = hospital
                    st.session_state.user_type = "chef"
                    st.rerun()

    # Footer-sektion
    st.markdown("---")
    st.caption("""
        **Systeminformation:**  
        Version 2.1.0 | Senast uppdaterad: 2024-05-15  
        Drivs av Streamlit | [Support](mailto:support@vardschema.se)
    """)

# ========== ROUTING-HANTERING ==========
def handle_routing():
    """Hanterar navigering mellan sidor"""
    if st.session_state.user_type == "chef":
        st.switch_page("pages/1_Chefsida.py")
    elif st.session_state.user_type == "anställd":
        st.switch_page("pages/2_Anstalld.py")
    else:
        st.error("Ogiltig användartyp")
        clear_session()
        st.rerun()

# ========== HUVUDFUNKTION ==========
def main():
    """Huvudfunktion för applikationen"""
    # Initialisera session state vid första laddningen
    if "initialized" not in st.session_state:
        st.session_state.initialized = True
        clear_session()
    
    # Visa rätt innehåll baserat på inloggningsstatus
    if "hospital" not in st.session_state or "user_type" not in st.session_state:
        show_landing_page()
    else:
        handle_routing()

if __name__ == "__main__":
    main()