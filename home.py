# home.py
import streamlit as st

def main():
    st.set_page_config(page_title="Schemaläggningssystem", layout="wide")
    
    # Visa endast om användaren inte är inloggad
    if "hospital" not in st.session_state or "user_type" not in st.session_state:
        st.title("Välkommen till Schemaläggningssystemet")
        st.markdown("---")
        
        col1, col2 = st.columns([3, 2])
        with col1:
            hospital = st.selectbox(
                "Välj ditt sjukhus",
                ["Karolinska", "Sahlgrenska", "Danderyd"]
            )
            
        with col2:
            st.markdown("### Välj användartyp")
            col_emp, col_mgr = st.columns(2)
            with col_emp:
                if st.button("Medarbetare 🧑⚕️"):
                    st.session_state.hospital = hospital
                    st.session_state.user_type = "employee"
                    st.rerun()
            with col_mgr:
                if st.button("Chef 👨💼"):
                    st.session_state.hospital = hospital
                    st.session_state.user_type = "manager"
                    st.rerun()

        st.markdown("---")
        st.caption("Systemet för smart och rättvis schemaläggning i vården")

    # Routing baserat på användartyp
    else:
        if st.session_state.user_type == "employee":
            from anstalld_sida import employee_page
            employee_page()
        else:
            from chefsida import chef_page

if __name__ == "__main__":
    main()
