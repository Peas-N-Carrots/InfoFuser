import streamlit as st
import json
import tempfile
import os
from io import BytesIO
import pandas as pd
from datetime import datetime
import base64

# Import your custom modules
from model.extract import extract
from model.combine import combine
from model.advise import advise

# Set page configuration
st.set_page_config(
    page_title="Medical Document Analyzer",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #1e3a8a;
        text-align: center;
        margin-bottom: 2rem;
    }
    .section-header {
        font-size: 1.8rem;
        color: #059669;
        border-bottom: 2px solid #059669;
        padding-bottom: 0.5rem;
        margin: 2rem 0 1rem 0;
    }
    .info-box {
        background-color: #f0f9ff;
        border-left: 4px solid #0ea5e9;
        padding: 1rem;
        margin: 1rem 0;
        border-radius: 0.25rem;
    }
    .success-box {
        background-color: #f0fdf4;
        border-left: 4px solid #22c55e;
        padding: 1rem;
        margin: 1rem 0;
        border-radius: 0.25rem;
    }
    .warning-box {
        background-color: #fffbeb;
        border-left: 4px solid #f59e0b;
        padding: 1rem;
        margin: 1rem 0;
        border-radius: 0.25rem;
    }
</style>
""", unsafe_allow_html=True)

# Function to safely clean up temporary files
def cleanup_temp_files(temp_files):
    """Clean up temporary files"""
    for temp_file in temp_files:
        try:
            if os.path.exists(temp_file):
                os.unlink(temp_file)
        except Exception as e:
            st.warning(f"Could not delete temporary file {temp_file}: {e}")

# Alternative extract function that handles the agentic_doc structure better
def extract_documents_optimized(file_paths):
    """
    Optimized extraction using agentic_doc's batch processing
    Returns a flat list of document objects
    """
    try:
        # Use the batch processing feature of agentic_doc
        from agentic_doc.parse import parse
        
        # Parse all files at once (more efficient)
        all_results = parse(file_paths)
        
        # Flatten if needed (parse returns list of lists for multiple files)
        flattened_docs = []
        for result in all_results:
            if isinstance(result, list):
                flattened_docs.extend(result)
            else:
                flattened_docs.append(result)
        
        return flattened_docs
    except Exception as e:
        st.error(f"Error in optimized extraction: {e}")
        # Fall back to original method
        return extract(file_paths)

def main():
    """Main function to run the Streamlit app"""
    # The entire Streamlit app logic is already defined above
    # This function exists to provide a proper entry point if needed
    pass

# Initialize session state
if 'patient_profile' not in st.session_state:
    st.session_state.patient_profile = None
if 'recommendations' not in st.session_state:
    st.session_state.recommendations = None
if 'uploaded_files' not in st.session_state:
    st.session_state.uploaded_files = []

# Run the main app
if __name__ == "__main__":
    main()

# Sidebar navigation
st.sidebar.title("Navigation")
page = st.sidebar.selectbox(
    "Choose a page:",
    ["📤 Upload Documents", "👤 Patient Profile", "💡 Health Recommendations"]
)

# Main app header
st.markdown('<h1 class="main-header">🏥 Medical Document Analyzer</h1>', unsafe_allow_html=True)

if page == "📤 Upload Documents":
    st.markdown('<h2 class="section-header">Upload Medical Documents</h2>', unsafe_allow_html=True)
    
    st.markdown("""
    <div class="info-box">
        <strong>Instructions:</strong>
        <ul>
            <li>Upload PDF files or images of your medical documents</li>
            <li>Supported formats: PDF, JPG, JPEG, PNG</li>
            <li>Multiple files can be uploaded at once</li>
            <li>Documents will be analyzed to create your comprehensive patient profile</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)
    
    # File uploader
    uploaded_files = st.file_uploader(
        "Choose medical document files",
        type=['pdf', 'jpg', 'jpeg', 'png'],
        accept_multiple_files=True,
        key="medical_docs"
    )
    
    if uploaded_files:
        st.success(f"✅ {len(uploaded_files)} file(s) uploaded successfully!")
        
        # Show uploaded files
        st.subheader("Uploaded Files:")
        for i, file in enumerate(uploaded_files):
            st.write(f"{i+1}. {file.name} ({file.size} bytes)")
        
        # Process documents button
        if st.button("🔄 Process Documents", type="primary"):
            with st.spinner("Processing documents... This may take a few minutes."):
                try:
                    # Save uploaded files temporarily
                    temp_files = []
                    for file in uploaded_files:
                        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{file.name.split('.')[-1]}") as tmp_file:
                            tmp_file.write(file.read())
                            temp_files.append(tmp_file.name)
                    
                    # Extract data from documents
                    st.info("📄 Extracting data from documents...")
                    extracted_docs = extract(temp_files)
                    
                    # Since parse() returns a list for each file, get the first document from each
                    flattened_docs = []
                    for doc_list in extracted_docs:
                        if isinstance(doc_list, list) and len(doc_list) > 0:
                            flattened_docs.append(doc_list[0])  # Get first document from each file
                        else:
                            flattened_docs.append(doc_list)
                    
                    # Combine extracted data
                    st.info("🔗 Combining document data...")
                    combined_data = combine(flattened_docs)
                    
                    # Debug: Let's see what combine returns
                    st.write("Debug - Combined data preview:", combined_data[:200] + "..." if len(combined_data) > 200 else combined_data)
                    
                    # Parse the JSON response
                    try:
                        patient_profile = json.loads(combined_data)
                        st.session_state.patient_profile = patient_profile
                        st.session_state.uploaded_files = uploaded_files
                        
                        st.markdown("""
                        <div class="success-box">
                            <strong>✅ Processing Complete!</strong><br>
                            Your patient profile has been created successfully. Navigate to the "Patient Profile" page to view and edit your data.
                        </div>
                        """, unsafe_allow_html=True)
                        
                    except json.JSONDecodeError:
                        st.error("Error parsing the generated patient profile. Please try again.")
                    
                    # Clean up temporary files
                    cleanup_temp_files(temp_files)
                        
                except Exception as e:
                    st.error(f"An error occurred during processing: {str(e)}")

elif page == "👤 Patient Profile":
    st.markdown('<h2 class="section-header">Patient Profile</h2>', unsafe_allow_html=True)
    
    if st.session_state.patient_profile is None:
        st.markdown("""
        <div class="warning-box">
            <strong>⚠️ No Patient Profile Found</strong><br>
            Please upload and process your medical documents first using the "Upload Documents" page.
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div class="info-box">
            <strong>Your Medical Profile:</strong><br>
            Review and edit your extracted medical information below. You can modify any fields as needed.
        </div>
        """, unsafe_allow_html=True)
        
        # Create editable form
        with st.form("patient_profile_form"):
            st.subheader("📝 Edit Your Information")
            
            # Convert profile to editable format
            profile_json = json.dumps(st.session_state.patient_profile, indent=2)
            
            edited_profile = st.text_area(
                "Patient Profile (JSON format)",
                value=profile_json,
                height=400,
                help="Edit your patient profile in JSON format. Be careful to maintain valid JSON syntax."
            )
            
            col1, col2 = st.columns(2)
            with col1:
                if st.form_submit_button("💾 Save Changes", type="primary"):
                    try:
                        updated_profile = json.loads(edited_profile)
                        st.session_state.patient_profile = updated_profile
                        st.success("✅ Profile updated successfully!")
                    except json.JSONDecodeError:
                        st.error("❌ Invalid JSON format. Please check your syntax.")
            
            with col2:
                if st.form_submit_button("🔄 Reset to Original"):
                    st.rerun()
        
        # Display profile in a more readable format
        st.subheader("📊 Profile Summary")
        
        # Create tabs for different sections
        if isinstance(st.session_state.patient_profile, dict):
            # Extract key information for display
            profile = st.session_state.patient_profile
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**Personal Information:**")
                personal_info = {k: v for k, v in profile.items() if k.lower() in 
                               ['name', 'age', 'gender', 'date_of_birth', 'phone', 'email', 'address']}
                for key, value in personal_info.items():
                    st.write(f"• **{key.replace('_', ' ').title()}:** {value}")
            
            with col2:
                st.markdown("**Medical Information:**")
                medical_info = {k: v for k, v in profile.items() if k.lower() in 
                              ['conditions', 'medications', 'allergies', 'blood_type', 'height', 'weight']}
                for key, value in medical_info.items():
                    if isinstance(value, list):
                        st.write(f"• **{key.replace('_', ' ').title()}:** {', '.join(map(str, value))}")
                    else:
                        st.write(f"• **{key.replace('_', ' ').title()}:** {value}")

elif page == "💡 Health Recommendations":
    st.markdown('<h2 class="section-header">Personalized Health Recommendations</h2>', unsafe_allow_html=True)
    
    if st.session_state.patient_profile is None:
        st.markdown("""
        <div class="warning-box">
            <strong>⚠️ No Patient Profile Found</strong><br>
            Please upload and process your medical documents first, then create your patient profile.
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div class="info-box">
            <strong>AI-Generated Health Recommendations:</strong><br>
            Based on your medical profile, we'll generate personalized health goals and recommendations.
        </div>
        """, unsafe_allow_html=True)
        
        if st.button("🎯 Generate Recommendations", type="primary"):
            with st.spinner("Generating personalized recommendations..."):
                try:
                    recommendations_json = advise(json.dumps(st.session_state.patient_profile))
                    recommendations = json.loads(recommendations_json)
                    st.session_state.recommendations = recommendations
                    
                except Exception as e:
                    st.error(f"Error generating recommendations: {str(e)}")
        
        # Display recommendations if available
        if st.session_state.recommendations:
            recommendations = st.session_state.recommendations
            
            # Daily Goals
            st.subheader("🌅 Daily Goals")
            for i, goal in enumerate(recommendations.get('daily_goals', []), 1):
                st.write(f"{i}. {goal}")
            
            # Short-term Goals
            st.subheader("📅 Short-term Goals (1-4 weeks)")
            for i, goal in enumerate(recommendations.get('short_term_goals', []), 1):
                st.write(f"{i}. {goal}")
            
            # Medium-term Goals
            st.subheader("📆 Medium-term Goals (1-6 months)")
            for i, goal in enumerate(recommendations.get('medium_term_goals', []), 1):
                st.write(f"{i}. {goal}")
            
            # Long-term Goals
            st.subheader("🎯 Long-term Goals (6+ months)")
            for i, goal in enumerate(recommendations.get('long_term_goals', []), 1):
                st.write(f"{i}. {goal}")
            
            # General Recommendations
            st.subheader("💡 General Recommendations")
            for i, rec in enumerate(recommendations.get('general_recommendations', []), 1):
                st.write(f"{i}. {rec}")
            
            # Download recommendations
            st.subheader("📥 Download Recommendations")
            recommendations_json = json.dumps(recommendations, indent=2)
            st.download_button(
                label="💾 Download as JSON",
                data=recommendations_json,
                file_name=f"health_recommendations_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json"
            )

# Footer
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #6b7280; font-size: 0.9rem;">
    <p>🏥 Medical Document Analyzer | Built with Streamlit</p>
    <p><strong>Disclaimer:</strong> This tool provides informational recommendations only. Always consult with healthcare professionals for medical decisions.</p>
</div>
""", unsafe_allow_html=True)