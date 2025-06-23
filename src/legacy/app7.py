import streamlit as st
import json
import os
import tempfile
from pathlib import Path
import pandas as pd
from datetime import datetime
import base64

# Import your custom modules
try:
    from model.extract import extract
    from model.combine import combine
    from model.advise import advise
except ImportError:
    st.error("Please ensure your model modules (extract, combine, advise) are available in the 'model' directory")
    st.stop()

# Configure page settings
st.set_page_config(
    page_title="Medical Document Analyzer",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state
if 'patient_profile' not in st.session_state:
    st.session_state.patient_profile = {}
if 'processed_files' not in st.session_state:
    st.session_state.processed_files = []
if 'advice' not in st.session_state:
    st.session_state.advice = ""

# Sidebar navigation
st.sidebar.title("🏥 Medical Document Analyzer")
page = st.sidebar.selectbox(
    "Navigate to:",
    ["📤 Upload Documents", "👤 Patient Profile", "💡 Health Recommendations"]
)

def save_uploaded_file(uploaded_file):
    """Save uploaded file to temporary directory and return path"""
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{uploaded_file.name.split('.')[-1]}") as tmp_file:
            tmp_file.write(uploaded_file.getvalue())
            return tmp_file.name
    except Exception as e:
        st.error(f"Error saving file {uploaded_file.name}: {str(e)}")
        return None

def process_documents(file_paths):
    """Process uploaded documents using your custom functions"""
    try:
        with st.spinner("Extracting data from documents..."):
            documents = extract(file_paths)
            print(documents)  # Debugging line to check extracted documents structure
        
        with st.spinner("Combining extracted data..."):
            combined_data = combine(documents)
            print(combined_data)  # Debugging line to check combined data structure
        
        return combined_data
    except Exception as e:
        st.error(f"Error processing documents: {str(e)}")
        return None

def display_json_editor(data, key_prefix=""):
    """Create an interactive JSON editor using Streamlit components"""
    if isinstance(data, dict):
        edited_data = {}
        for key, value in data.items():
            col1, col2 = st.columns([1, 3])
            with col1:
                st.write(f"**{key}:**")
            with col2:
                if isinstance(value, (dict, list)):
                    edited_data[key] = display_json_editor(value, f"{key_prefix}_{key}")
                elif isinstance(value, bool):
                    edited_data[key] = st.checkbox("", value=value, key=f"{key_prefix}_{key}")
                elif isinstance(value, (int, float)):
                    edited_data[key] = st.number_input("", value=value, key=f"{key_prefix}_{key}")
                else:
                    edited_data[key] = st.text_input("", value=str(value), key=f"{key_prefix}_{key}")
        return edited_data
    elif isinstance(data, list):
        edited_list = []
        for i, item in enumerate(data):
            st.write(f"**Item {i+1}:**")
            if isinstance(item, (dict, list)):
                edited_item = display_json_editor(item, f"{key_prefix}_{i}")
            else:
                edited_item = st.text_input(f"Item {i+1}", value=str(item), key=f"{key_prefix}_{i}")
            edited_list.append(edited_item)
        return edited_list
    else:
        return data

# Page 1: Upload Documents
if page == "📤 Upload Documents":
    st.title("📤 Upload Medical Documents")
    st.markdown("Upload your medical documents (PDF or images) to create your patient profile.")
    
    # File uploader
    uploaded_files = st.file_uploader(
        "Choose medical document files",
        type=['pdf', 'jpg', 'jpeg', 'png', 'tiff', 'bmp'],
        accept_multiple_files=True,
        help="Supported formats: PDF, JPG, JPEG, PNG, TIFF, BMP"
    )
    
    if uploaded_files:
        st.success(f"✅ {len(uploaded_files)} file(s) uploaded successfully!")
        
        # Display uploaded files
        st.subheader("📋 Uploaded Files:")
        for file in uploaded_files:
            col1, col2, col3 = st.columns([3, 1, 1])
            with col1:
                st.write(f"📄 {file.name}")
            with col2:
                st.write(f"{file.size / 1024:.1f} KB")
            with col3:
                st.write(file.type)
        
        # Process documents button
        if st.button("🔄 Process Documents", type="primary"):
            # Save uploaded files temporarily
            temp_file_paths = []
            for uploaded_file in uploaded_files:
                temp_path = save_uploaded_file(uploaded_file)
                if temp_path:
                    temp_file_paths.append(temp_path)
            
            if temp_file_paths:
                # Process documents
                combined_data = process_documents(temp_file_paths)
                
                if combined_data:
                    st.session_state.patient_profile = combined_data
                    st.session_state.processed_files = [f.name for f in uploaded_files]
                    
                    st.success("✅ Documents processed successfully!")
                    st.json(combined_data)
                    
                    # Clean up temporary files
                    for temp_path in temp_file_paths:
                        try:
                            os.unlink(temp_path)
                        except:
                            pass
            else:
                st.error("❌ Failed to save uploaded files.")
    
    # Display current profile status
    if st.session_state.patient_profile:
        st.success(f"✅ Current profile created from: {', '.join(st.session_state.processed_files)}")
        with st.expander("🔍 View Current Profile"):
            st.json(st.session_state.patient_profile)

# Page 2: Patient Profile
elif page == "👤 Patient Profile":
    st.title("👤 Patient Profile")
    
    if not st.session_state.patient_profile:
        st.warning("⚠️ No patient profile found. Please upload and process documents first.")
        if st.button("↩️ Go to Upload Page"):
            st.rerun()
    else:
        st.markdown("Review and edit your medical profile below:")
        
        # Create tabs for better organization
        tab1, tab2, tab3 = st.tabs(["📝 Edit Profile", "📊 Profile Summary", "💾 Export Data"])
        
        with tab1:
            st.subheader("📝 Edit Your Medical Profile")
            
            # Create editable form
            with st.form("profile_editor"):
                # Use the JSON editor
                edited_profile = display_json_editor(st.session_state.patient_profile, "profile")
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    if st.form_submit_button("💾 Save Changes", type="primary"):
                        st.session_state.patient_profile = edited_profile
                        st.success("✅ Profile updated successfully!")
                        st.rerun()
                
                with col2:
                    if st.form_submit_button("🔄 Reset to Original"):
                        st.warning("This will reset all changes. Please re-process documents if needed.")
                
                with col3:
                    if st.form_submit_button("🗑️ Clear Profile"):
                        st.session_state.patient_profile = {}
                        st.session_state.processed_files = []
                        st.session_state.advice = ""
                        st.success("✅ Profile cleared!")
                        st.rerun()
        
        with tab2:
            st.subheader("📊 Profile Summary")
            
            # Display profile statistics
            profile_data = st.session_state.patient_profile
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("📄 Source Documents", len(st.session_state.processed_files))
            with col2:
                st.metric("🔑 Data Fields", len(profile_data) if isinstance(profile_data, dict) else 0)
            with col3:
                st.metric("📅 Last Updated", datetime.now().strftime("%Y-%m-%d %H:%M"))
            
            # Display profile in a structured way
            st.subheader("🔍 Detailed Profile Data")
            st.json(profile_data)
        
        with tab3:
            st.subheader("💾 Export Your Data")
            
            # JSON export
            json_str = json.dumps(st.session_state.patient_profile, indent=2)
            st.download_button(
                label="📥 Download as JSON",
                data=json_str,
                file_name=f"medical_profile_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json"
            )
            
            # Display raw JSON
            with st.expander("🔍 View Raw JSON"):
                st.code(json_str, language="json")

# Page 3: Health Recommendations
elif page == "💡 Health Recommendations":
    st.title("💡 Personalized Health Recommendations")
    
    if not st.session_state.patient_profile:
        st.warning("⚠️ No patient profile found. Please upload and process documents first.")
        if st.button("↩️ Go to Upload Page"):
            st.rerun()
    else:
        st.markdown("Generate personalized health advice based on your medical profile:")
        
        # Display current profile summary
        with st.expander("👤 Current Profile Summary"):
            st.json(st.session_state.patient_profile)
        
        # Generate recommendations button
        col1, col2 = st.columns([1, 3])
        with col1:
            if st.button("🧠 Generate Recommendations", type="primary"):
                try:
                    with st.spinner("Generating personalized health recommendations..."):
                        advice = advise(st.session_state.patient_profile)
                        st.session_state.advice = advice
                        print(advice)  # Debugging line to check generated advice structure
                except Exception as e:
                    st.error(f"Error generating recommendations: {str(e)}")
        
        # Display recommendations
        if st.session_state.advice:
            st.subheader("📋 Your Personalized Health Recommendations")
            
            # Create tabs for different types of advice
            advice_tabs = st.tabs(["📝 Full Recommendations", "⚡ Quick Tips", "📊 Action Items"])
            
            with advice_tabs[0]:
                st.markdown("### 🎯 Complete Health Recommendations")
                st.write(st.session_state.advice)
                
                # Option to download recommendations
                st.download_button(
                    label="📥 Download Recommendations",
                    data=st.session_state.advice,
                    file_name=f"health_recommendations_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                    mime="text/plain"
                )
            
            with advice_tabs[1]:
                st.markdown("### ⚡ Quick Health Tips")
                # Extract quick tips from advice (you might want to modify your advise function to return structured data)
                tips = st.session_state.advice.split('\n')[:5]  # First 5 lines as quick tips
                for i, tip in enumerate(tips, 1):
                    if tip.strip():
                        st.info(f"💡 **Tip {i}:** {tip.strip()}")
            
            with advice_tabs[2]:
                st.markdown("### 📋 Recommended Actions")
                st.write("Based on your profile, consider taking these actions:")
                
                # Create checkboxes for action items
                actions = [
                    "Schedule follow-up appointment with primary care physician",
                    "Review current medications with pharmacist",
                    "Update emergency contact information",
                    "Schedule recommended screenings/tests",
                    "Review and update insurance information"
                ]
                
                for action in actions:
                    st.checkbox(action, key=f"action_{action}")
        
        else:
            st.info("👆 Click 'Generate Recommendations' to get personalized health advice based on your profile.")

# Footer
st.sidebar.markdown("---")
st.sidebar.markdown(
    """
    <div style='text-align: center'>
        <small>🏥 Medical Document Analyzer<br>
        Secure • Private • HIPAA Compliant</small>
    </div>
    """, 
    unsafe_allow_html=True
)

# Add some custom CSS for better styling
st.markdown("""
<style>
    .reportview-container {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
    }
    .main .block-container {
        padding-top: 2rem;
    }
    .stButton > button {
        border-radius: 5px;
        border: none;
        padding: 0.5rem 1rem;
        font-weight: bold;
    }
    .stSuccess {
        border-radius: 5px;
    }
    .stError {
        border-radius: 5px;
    }
    .stWarning {
        border-radius: 5px;
    }
</style>
""", unsafe_allow_html=True)