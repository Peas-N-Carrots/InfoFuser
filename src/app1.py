import streamlit as st
import tempfile
import os
import json
import zipfile
from io import BytesIO
from pathlib import Path
import pandas as pd
from datetime import datetime
import base64
import sys
sys.path.append(str(Path(__file__).resolve().parent.parent))  # Add parent directory to path
from combine import combine


# Import agentic-doc library components
try:
    from agentic_doc.parse import parse
    from agentic_doc.utils import viz_parsed_document
    from agentic_doc.config import VisualizationConfig
    AGENTIC_DOC_AVAILABLE = True
except ImportError:
    AGENTIC_DOC_AVAILABLE = False

def main():
    st.set_page_config(
        page_title="Agentic Document Parser",
        page_icon="📄",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Custom CSS for better styling
    st.markdown("""
    <style>
    .main-header {
        text-align: center;
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 3rem;
        font-weight: bold;
        margin-bottom: 2rem;
    }
    .feature-box {
        background-color: #f0f2f6;
        padding: 1.5rem;
        border-radius: 10px;
        border-left: 5px solid #667eea;
        margin: 1rem 0;
    }
    .status-success {
        background-color: #d4edda;
        border-color: #c3e6cb;
        color: #155724;
        padding: 1rem;
        border-radius: 5px;
        margin: 1rem 0;
    }
    .status-error {
        background-color: #f8d7da;
        border-color: #f5c6cb;
        color: #721c24;
        padding: 1rem;
        border-radius: 5px;
        margin: 1rem 0;
    }
    .metric-card {
        background: white;
        padding: 1rem;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        text-align: center;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Main header
    st.markdown('<h1 class="main-header">🤖 Agentic Document Parser</h1>', unsafe_allow_html=True)
    st.markdown("**Extract structured data from visually complex documents with AI-powered parsing**")
    
    # Check if agentic-doc is available
    if not AGENTIC_DOC_AVAILABLE:
        st.error("❌ The `agentic-doc` library is not installed. Please install it with: `pip install agentic-doc`")
        st.stop()
    
    # Check for API key
    api_key = os.getenv('VISION_AGENT_API_KEY')
    if not api_key:
        st.warning("⚠️ Please set your VISION_AGENT_API_KEY environment variable")
        api_key = st.text_input("Enter your LandingAI API Key:", type="password")
        if api_key:
            os.environ['VISION_AGENT_API_KEY'] = api_key
        else:
            st.info("Get your API key from [LandingAI](https://landing.ai/)")
            st.stop()
    
    # Sidebar configuration
    with st.sidebar:
        st.header("⚙️ Configuration")
        
        # Parsing options
        st.subheader("Parsing Options")
        include_marginalia = st.checkbox("Include Marginalia", value=True, 
                                       help="Extract footer notes, page numbers, etc.")
        include_metadata = st.checkbox("Include Metadata in Markdown", value=True,
                                     help="Include metadata in the markdown output")
        
        # Visualization options
        st.subheader("Visualization Options")
        enable_viz = st.checkbox("Generate Visualizations", value=True,
                                help="Create annotated images showing extraction regions")
        
        if enable_viz:
            viz_thickness = st.slider("Bounding Box Thickness", 1, 5, 2)
            viz_opacity = st.slider("Text Background Opacity", 0.0, 1.0, 0.7, 0.1)
            viz_font_scale = st.slider("Font Scale", 0.3, 1.5, 0.6, 0.1)
        
        # Processing options
        st.subheader("Processing Options")
        batch_size = st.number_input("Batch Size", min_value=1, max_value=10, value=4,
                                   help="Number of files to process in parallel")
        max_workers = st.number_input("Max Workers", min_value=1, max_value=10, value=5,
                                    help="Number of threads per file")
        
        # Set environment variables
        os.environ['BATCH_SIZE'] = str(batch_size)
        os.environ['MAX_WORKERS'] = str(max_workers)
    
    # Main content area
    col1, col2 = st.columns([1, 3])
    
    with col1:
        st.header("📁 Upload Documents")
        
        # File uploader
        uploaded_files = st.file_uploader(
            "Choose files to parse",
            type=['pdf', 'png', 'jpg', 'jpeg', 'tiff', 'bmp'],
            accept_multiple_files=True,
            help="Supported formats: PDF, PNG, JPG, JPEG, TIFF, BMP"
        )
        
        if uploaded_files:
            st.success(f"✅ {len(uploaded_files)} file(s) uploaded successfully!")
            
            # Display file information
            file_info = []
            for file in uploaded_files:
                file_info.append({
                    "Filename": file.name,
                    "Type": file.type,
                    "Size": f"{file.size / 1024:.1f} KB"
                })
            
            df = pd.DataFrame(file_info)
            st.dataframe(df, use_container_width=True)
    
    with col2:
        st.header("🚀 Actions")
        
        if uploaded_files:
            if st.button("🔍 Parse Documents", type="primary", use_container_width=True):
                parse_documents(uploaded_files, include_marginalia, include_metadata, 
                              enable_viz, viz_thickness, viz_opacity, viz_font_scale)
        
        st.markdown("---")
        st.markdown("### 📊 Features")
        st.markdown("""
        - **Multi-format Support**: PDF, images, URLs
        - **Large Document Processing**: Handle 100+ page PDFs
        - **Parallel Processing**: Efficient batch processing
        - **Visual Groundings**: See extraction regions
        - **Structured Output**: JSON + Markdown formats
        - **Error Handling**: Automatic retries and recovery
        """)

def parse_documents(uploaded_files, include_marginalia, include_metadata, 
                   enable_viz, viz_thickness, viz_opacity, viz_font_scale):
    """Parse uploaded documents and display results"""
    
    # Create temporary directory for processing
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Save uploaded files to temporary directory
        file_paths = []
        for uploaded_file in uploaded_files:
            file_path = temp_path / uploaded_file.name
            with open(file_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            file_paths.append(str(file_path))
        
        # Progress tracking
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        try:
            status_text.text("🔄 Parsing documents...")
            progress_bar.progress(25)
            
            # Parse documents
            results = parse(
                file_paths,
                include_marginalia=include_marginalia,
                include_metadata_in_markdown=include_metadata
            )
            
            progress_bar.progress(75)
            status_text.text("✅ Parsing completed!")
            
            # Display results
            display_results(results, file_paths, uploaded_files, temp_path, 
                          enable_viz, viz_thickness, viz_opacity, viz_font_scale)
            
            progress_bar.progress(100)
            status_text.text("🎉 All processing completed!")
            
        except Exception as e:
            st.error(f"❌ Error parsing documents: {str(e)}")
            progress_bar.progress(0)
            status_text.text("❌ Parsing failed!")

def display_results(results, file_paths, uploaded_files, temp_path,
                   enable_viz, viz_thickness, viz_opacity, viz_font_scale):
    """Display parsing results with tabs for each document"""

    st.header("📊 Parsing Results")

    # Summary metrics
    col1, col2, col3, col4 = st.columns(4)

    total_chunks = sum(len(result.chunks) for result in results)
    total_pages = sum(getattr(result, 'page_count', 1) for result in results)
    avg_chunks_per_doc = total_chunks / len(results) if results else 0

    with col1:
        st.markdown(f'<div class="metric-card"><h3>{len(results)}</h3><p>Documents</p></div>', 
                   unsafe_allow_html=True)
    with col2:
        st.markdown(f'<div class="metric-card"><h3>{total_pages}</h3><p>Total Pages</p></div>', 
                   unsafe_allow_html=True)
    with col3:
        st.markdown(f'<div class="metric-card"><h3>{total_chunks}</h3><p>Total Chunks</p></div>', 
                   unsafe_allow_html=True)
    with col4:
        st.markdown(f'<div class="metric-card"><h3>{avg_chunks_per_doc:.1f}</h3><p>Avg Chunks/Doc</p></div>', 
                   unsafe_allow_html=True)

    # --- Combined Results Section ---
    if len(results) > 1:
        with st.expander("🧬 Show Combined Medical Data (Markdown)", expanded=False):
            with st.spinner("Combining documents..."):
                try:
                    combined_md = combine(results)
                    st.markdown("```markdown\n" + combined_md + "\n```")
                except Exception as e:
                    st.error(f"Error combining documents: {e}")

    # Create tabs for each document
    if len(results) == 1:
        # Single document - no tabs needed
        display_document_results(results[0], uploaded_files[0], file_paths[0], temp_path,
                               enable_viz, viz_thickness, viz_opacity, viz_font_scale, 0)
    else:
        # Multiple documents - use tabs
        tab_names = [f"📄 {file.name}" for file in uploaded_files]
        tabs = st.tabs(tab_names)
        for i, (tab, result, uploaded_file, file_path) in enumerate(zip(tabs, results, uploaded_files, file_paths)):
            with tab:
                display_document_results(result, uploaded_file, file_path, temp_path,
                                       enable_viz, viz_thickness, viz_opacity, viz_font_scale, i)

    # Bulk download section
    create_bulk_download(results, uploaded_files)

def display_document_results(result, uploaded_file, file_path, temp_path,
                           enable_viz, viz_thickness, viz_opacity, viz_font_scale, doc_index):
    """Display results for a single document"""
    
    # Document info
    st.subheader(f"📄 {uploaded_file.name}")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # Markdown output
        st.subheader("📝 Extracted Content (Markdown)")
        if result.markdown:
            st.markdown("```markdown\n" + result.markdown + "\n```")
        else:
            st.warning("No markdown content extracted")
    
    with col2:
        # Download buttons
        st.subheader("⬇️ Downloads")
        
        # Markdown download
        if result.markdown:
            st.download_button(
                label="📝 Download Markdown",
                data=result.markdown,
                file_name=f"{uploaded_file.name}.md",
                mime="text/markdown"
            )
        
        # JSON download
        json_data = {
            "filename": uploaded_file.name,
            "markdown": result.markdown,
            "chunks": [chunk.dict() if hasattr(chunk, 'dict') else str(chunk) for chunk in result.chunks],
            "metadata": {
                "processing_time": datetime.now().isoformat(),
                "chunk_count": len(result.chunks)
            }
        }
        
        st.download_button(
            label="📊 Download JSON",
            data=json.dumps(json_data, indent=2),
            file_name=f"{uploaded_file.name}.json",
            mime="application/json"
        )
    
    # Chunks analysis
    if result.chunks:
        st.subheader("🧩 Content Chunks Analysis")
        
        # Chunk type distribution
        chunk_types = {}
        for chunk in result.chunks:
            chunk_type = getattr(chunk, 'type', 'unknown')
            chunk_types[chunk_type] = chunk_types.get(chunk_type, 0) + 1
        
        if chunk_types:
            col1, col2 = st.columns(2)
            with col1:
                st.write("**Chunk Type Distribution:**")
                chunk_df = pd.DataFrame(list(chunk_types.items()), columns=['Type', 'Count'])
                st.dataframe(chunk_df, use_container_width=True)
            
            with col2:
                st.write("**Sample Chunks:**")
                for i, chunk in enumerate(result.chunks[:3]):  # Show first 3 chunks
                    with st.expander(f"Chunk {i+1} - {getattr(chunk, 'type', 'unknown')}"):
                        chunk_text = getattr(chunk, 'text', str(chunk))
                        st.text(chunk_text[:200] + "..." if len(chunk_text) > 200 else chunk_text)
    
    # Visualization
    if enable_viz and result.chunks:
        st.subheader("🎯 Document Visualization")
        
        try:
            # Create visualization config
            viz_config = VisualizationConfig(
                thickness=int(viz_thickness),
                text_bg_opacity=viz_opacity,
                font_scale=viz_font_scale
            )
            
            # Generate visualization
            viz_output_dir = temp_path / f"viz_{doc_index}"
            viz_output_dir.mkdir(exist_ok=True)
            
            images = viz_parsed_document(
                file_path,
                result,
                output_dir=str(viz_output_dir),
                viz_config=viz_config
            )
            
            if images:
                st.success(f"✅ Generated {len(images)} visualization page(s)")
                
                # Display visualizations
                for i, img in enumerate(images):
                    st.image(img, caption=f"Page {i+1} - Extraction Visualization", use_container_width=True)
            else:
                st.warning("No visualizations could be generated")
                
        except Exception as e:
            st.error(f"❌ Error generating visualization: {str(e)}")
    
    # Error handling
    if hasattr(result, 'errors') and result.errors:
        st.subheader("⚠️ Processing Errors")
        for error in result.errors:
            st.error(f"Page {error.get('page', 'unknown')}: {error.get('message', str(error))}")

def create_bulk_download(results, uploaded_files):
    """Create bulk download option for all results"""
    
    st.header("📦 Bulk Download")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("📦 Download All Results (ZIP)", type="secondary", use_container_width=True):
            # Create zip file in memory
            zip_buffer = BytesIO()
            
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                for result, uploaded_file in zip(results, uploaded_files):
                    base_name = uploaded_file.name.rsplit('.', 1)[0]
                    
                    # Add markdown file
                    if result.markdown:
                        zip_file.writestr(f"{base_name}.md", result.markdown)
                    
                    # Add JSON file
                    json_data = {
                        "filename": uploaded_file.name,
                        "markdown": result.markdown,
                        "chunks": [chunk.dict() if hasattr(chunk, 'dict') else str(chunk) for chunk in result.chunks],
                        "metadata": {
                            "processing_time": datetime.now().isoformat(),
                            "chunk_count": len(result.chunks)
                        }
                    }
                    zip_file.writestr(f"{base_name}.json", json.dumps(json_data, indent=2))
            
            zip_buffer.seek(0)
            
            st.download_button(
                label="⬇️ Download ZIP File",
                data=zip_buffer.getvalue(),
                file_name=f"agentic_doc_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip",
                mime="application/zip"
            )
    
    with col2:
        st.info("💡 The ZIP file contains all markdown and JSON outputs from your parsed documents.")

if __name__ == "__main__":
    main()