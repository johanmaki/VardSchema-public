# app.py
import streamlit as st

def main():
    st.set_page_config(
        page_title="VårdSchema Pro",
        page_icon="🏥",
        layout="centered"
    )

    # Debugging
    st.sidebar.write("Debug-session:", st.session_state)

    # Routing-logik
    if "user_type" in st.session_state:
        handle_routing()
    else:
        show_landing_page()

def show_landing_page():
    st.title("Välkommen till VårdSchema!!!")
    
    hospital = st.selectbox(
        "Välj ditt sjukhus",
        ["Karolinska", "Sahlgrenska", "Danderyd"]
    )
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Medarbetare 🧑⚕️", key="emp_btn", use_container_width=True):
            st.session_state.update({
                "hospital": hospital,
                "user_type": "anställd"
            })
            st.rerun()
    
    with col2:
        if st.button("Chef 👨💼", key="chef_btn", use_container_width=True):
            st.session_state.update({
                "hospital": hospital,
                "user_type": "chef"
            })
            st.rerun()

def handle_routing():
    if st.session_state.user_type == "chef":
        st.switch_page("pages/1_Chefsida.py")
    elif st.session_state.user_type == "anställd":
        st.switch_page("pages/2_Anstalld.py")
    else:
        st.error("Ogiltig användartyp")
        st.session_state.clear()
        st.rerun()

if __name__ == "__main__":
    main()