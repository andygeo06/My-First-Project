import streamlit as st

def render_accountability_header(module_name):
    """Reusable UI component for accountability across all modules."""
    st.info(f"📍 **Module:** {module_name}")
    
    with st.expander("🔐 Accountability & Verification", expanded=True):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            # Hospital Name (Can be a dropdown or text)
            hosp_name = st.text_input("Hospital Name", 
                                      value=st.session_state.get('hosp_name', ""),
                                      placeholder="Full Name of Facility")
        with col2:
            encoder = st.text_input("Name of Encoder", 
                                    value=st.session_state.get('encoder_name', ""),
                                    placeholder="Firstname Lastname")
        with col3:
            position = st.text_input("Position/Designation", 
                                     value=st.session_state.get('position', ""),
                                     placeholder="e.g., Administrative Officer V")
            
        # Update session state so it persists across modules
        st.session_state.hosp_name = hosp_name
        st.session_state.encoder_name = encoder
        st.session_state.position = position

    # Validation Check
    if not hosp_name or not encoder:
        st.warning("⚠️ Please fill in accountability details to enable submission.")
        return False
    return True

def module_hospital_mooe():
    st.title("🏥 Hospital MOOE Data Entry")
    
    # Render the accountability block
    is_ready = render_accountability_header("Hospital MOOE")
    
    # The actual data entry fields
    st.markdown("---")
    st.subheader("Financial Metrics")
    mooe_val = st.number_input("Current Operating Expenditures", min_value=0)
    
    # Submission logic only if accountability is filled
    if st.button("Finalize Submission", disabled=not is_ready):
        payload = {
            "hospital_name": st.session_state.hosp_name,
            "encoder": st.session_state.encoder_name,
            "position": st.session_state.position,
            "data": {"mooe": mooe_val}
        }
        # Call your sync_data function here to write to 'Mod3'
        st.success("Data and Accountability record saved.")
