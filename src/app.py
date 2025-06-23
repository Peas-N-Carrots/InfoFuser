import streamlit as st
import pandas as pd
import json
import tempfile
import os
from datetime import datetime
from typing import List, Dict, Any
import io

# Import your custom modules
try:
    from model.extract import extract
    from model.combine import combine
    from model.advise import advise
except ImportError:
    st.error("Please ensure your model modules (extract, combine, advise) are available in the model/ directory")
    st.stop()

# Page configuration
st.set_page_config(
    page_title="Medical Document Analyzer",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state
if 'patient_profile' not in st.session_state:
    st.session_state.patient_profile = {}
if 'processed_documents' not in st.session_state:
    st.session_state.processed_documents = []
if 'recommendations' not in st.session_state:
    st.session_state.recommendations = ""

def save_uploaded_file(uploaded_file) -> str:
    """Save uploaded file to temporary directory and return path"""
    with tempfile.NamedTemporaryFile(delete=False, suffix=f".{uploaded_file.name.split('.')[-1]}") as tmp_file:
        tmp_file.write(uploaded_file.getvalue())
        return tmp_file.name

def process_documents(file_paths: List[str]) -> Dict[str, Any]:
    """Process uploaded documents using your model functions"""
    try:
        with st.spinner("Extracting data from documents..."):
            documents = extract(file_paths)
        
        with st.spinner("Combining and analyzing data..."):
            combined_data = combine(documents)
        
        return combined_data
    except Exception as e:
        st.error(f"Error processing documents: {str(e)}")
        return {}

def format_patient_data_as_markdown(data: Any, level: int = 1) -> str:
    """Convert patient data to formatted markdown"""
    if isinstance(data, dict):
        markdown = ""
        for key, value in data.items():
            header_level = "#" * min(level + 1, 6)
            clean_key = key.replace('_', ' ').title()
            markdown += f"\n{header_level} {clean_key}\n\n"
            markdown += format_patient_data_as_markdown(value, level + 1)
        return markdown
    elif isinstance(data, list):
        if not data:
            return "*No data available*\n\n"
        markdown = ""
        for item in data:
            if isinstance(item, (dict, list)):
                markdown += format_patient_data_as_markdown(item, level)
            else:
                markdown += f"- {str(item)}\n"
        return markdown + "\n"
    else:
        return f"{str(data)}\n\n"

def display_formatted_content(content: str, title: str = ""):
    """Display content as formatted markdown with custom styling"""
    if title:
        st.markdown(f"## {title}")
    
    # Add custom CSS for better formatting
    st.markdown("""
    <style>
    .medical-content {
        background-color: #fafafa;
        padding: 20px;
        border-radius: 10px;
        border-left: 4px solid #1f77b4;
        margin: 10px 0;
    }
    .medical-content h1, .medical-content h2, .medical-content h3 {
        color: #1f77b4;
        margin-top: 20px;
        margin-bottom: 10px;
    }
    .medical-content ul {
        margin-left: 20px;
    }
    .medical-content li {
        margin-bottom: 5px;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Display the content in a styled container
    st.markdown(f'<div class="medical-content">{content}</div>', unsafe_allow_html=True)
    
    # Also provide the raw markdown for copying
    with st.expander("📋 View Raw Markdown", expanded=False):
        st.code(content, language='markdown')

# Sidebar navigation
st.sidebar.title("🏥 Medical Document Analyzer")
page = st.sidebar.selectbox(
    "Navigate to:",
    ["Upload Documents", "Patient Profile", "Health Recommendations"]
)

# Main content based on selected page
if page == "Upload Documents":
    st.title("📄 Upload Medical Documents")
    st.markdown("Upload your medical documents (PDF or images) to create your patient profile.")
    
    # File uploader
    uploaded_files = st.file_uploader(
        "Choose your medical documents",
        type=['pdf', 'png', 'jpg', 'jpeg', 'tiff', 'bmp'],
        accept_multiple_files=True,
        help="Upload PDF files or images of your medical documents"
    )
    
    if uploaded_files:
        st.success(f"✅ {len(uploaded_files)} file(s) uploaded successfully!")
        
        # Display uploaded files
        with st.expander("Uploaded Files", expanded=True):
            for file in uploaded_files:
                col1, col2, col3 = st.columns([3, 1, 1])
                with col1:
                    st.write(f"📄 {file.name}")
                with col2:
                    st.write(f"{file.size / 1024:.1f} KB")
                with col3:
                    st.write(file.type)
        
        # Process documents button
        if st.button("🔍 Process Documents", type="primary"):
            # Save uploaded files temporarily
            temp_file_paths = []
            try:
                for uploaded_file in uploaded_files:
                    temp_path = save_uploaded_file(uploaded_file)
                    temp_file_paths.append(temp_path)
                
                # Process documents
                combined_data = process_documents(temp_file_paths)
                
                if combined_data:
                    st.session_state.patient_profile = combined_data
                    st.session_state.processed_documents = [f.name for f in uploaded_files]
                    
                    st.success("✅ Documents processed successfully!")
                    st.balloons()
                    
                    # Display summary
                    st.subheader("📊 Processing Summary")
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.metric("Documents Processed", len(uploaded_files))
                        st.metric("Data Sections Extracted", len(combined_data.keys()) if combined_data else 0)
                    
                    with col2:
                        st.write("**Extracted Sections:**")
                        if combined_data:
                            for section in combined_data.keys():
                                st.write(f"• {section.replace('_', ' ').title()}")
                    
                    st.info("👉 Go to 'Patient Profile' to review and edit your data, or 'Health Recommendations' to get personalized advice.")
                
            except Exception as e:
                st.error(f"Error processing documents: {str(e)}")
            
            finally:
                # Clean up temporary files
                for temp_path in temp_file_paths:
                    try:
                        os.unlink(temp_path)
                    except:
                        pass

elif page == "Patient Profile":
    st.title("👤 Patient Profile")
    
    if not st.session_state.patient_profile:
        st.warning("⚠️ No patient profile data available. Please upload and process documents first.")
        st.info("👈 Go to 'Upload Documents' to get started.")
    else:
        st.markdown("Your complete medical profile extracted from uploaded documents.")
        
        # Display processing info
        if st.session_state.processed_documents:
            with st.expander("📋 Processing Information", expanded=False):
                st.write("**Processed Documents:**")
                for doc in st.session_state.processed_documents:
                    st.write(f"• {doc}")
                st.write(f"**Last Updated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Convert profile data to markdown and display
        if st.session_state.patient_profile:
            # Handle both string and dict/object formats
            if isinstance(st.session_state.patient_profile, str):
                # If it's already a string (markdown), display it directly
                profile_markdown = st.session_state.patient_profile
            else:
                # Convert structured data to markdown
                profile_markdown = format_patient_data_as_markdown(st.session_state.patient_profile)
            
            # Display the formatted profile
            display_formatted_content(profile_markdown, "")
        
        # Export profile option
        st.subheader("📤 Export Profile")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            # Download as markdown
            if isinstance(st.session_state.patient_profile, str):
                profile_text = st.session_state.patient_profile
            else:
                profile_text = format_patient_data_as_markdown(st.session_state.patient_profile)
            
            st.download_button(
                label="⬇️ Download as Markdown",
                data=profile_text,
                file_name=f"patient_profile_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md",
                mime="text/markdown"
            )
        
        with col2:
            # Download as JSON
            if isinstance(st.session_state.patient_profile, str):
                profile_json = json.dumps({"profile": st.session_state.patient_profile}, indent=2)
            else:
                profile_json = json.dumps(st.session_state.patient_profile, indent=2)
            
            st.download_button(
                label="⬇️ Download as JSON",
                data=profile_json,
                file_name=f"patient_profile_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json"
            )
        
        with col3:
            # Copy to clipboard button
            if st.button("📋 Copy Profile"):
                if isinstance(st.session_state.patient_profile, str):
                    st.code(st.session_state.patient_profile, language='markdown')
                else:
                    profile_text = format_patient_data_as_markdown(st.session_state.patient_profile)
                    st.code(profile_text, language='markdown')

elif page == "Health Recommendations":
    st.title("💡 Health Recommendations")
    
    if not st.session_state.patient_profile:
        st.warning("⚠️ No patient profile data available. Please upload and process documents first.")
        st.info("👈 Go to 'Upload Documents' to get started.")
    else:
        st.markdown("Get personalized health recommendations based on your medical profile.")
        
        # Display current profile summary
        with st.expander("📊 Current Profile Summary", expanded=False):
            st.json(st.session_state.patient_profile)
        
        # Generate recommendations
        col1, col2 = st.columns([1, 3])
        
        with col1:
            if st.button("🔮 Generate Recommendations", type="primary"):
                try:
                    with st.spinner("Generating personalized recommendations..."):
                        recommendations = advise(st.session_state.patient_profile)
                        st.session_state.recommendations = recommendations
                        st.success("✅ Recommendations generated!")
                except Exception as e:
                    st.error(f"Error generating recommendations: {str(e)}")
        
        # Display recommendations
        if st.session_state.recommendations:
            st.subheader("📋 Your Personalized Recommendations")
            
            # Display recommendations as formatted content
            display_formatted_content(str(st.session_state.recommendations), "")
            
            # Action buttons
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if st.button("🔄 Regenerate"):
                    st.rerun()
            
            with col2:
                # Download as markdown
                recommendations_text = str(st.session_state.recommendations)
                st.download_button(
                    label="⬇️ Download as Markdown",
                    data=recommendations_text,
                    file_name=f"health_recommendations_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md",
                    mime="text/markdown"
                )
            
            with col3:
                # Copy recommendations
                if st.button("📋 Copy Recommendations"):
                    st.code(str(st.session_state.recommendations), language='markdown')
            
            # Disclaimer
            st.warning("⚠️ **Medical Disclaimer:** These recommendations are for informational purposes only and should not replace professional medical advice. Always consult with your healthcare provider before making any changes to your treatment or lifestyle.")

# Footer
st.sidebar.markdown("---")
st.sidebar.markdown("🏥 **Medical Document Analyzer**")
st.sidebar.markdown("Built with Streamlit")
st.sidebar.markdown("*Secure • Private • Efficient*")

# Add some styling
st.markdown("""
<style>
    .main > div {
        padding-top: 2rem;
    }
    .stButton > button {
        width: 100%;
    }
    .stSelectbox > div > div {
        background-color: #f0f2f6;
    }
</style>
""", unsafe_allow_html=True)