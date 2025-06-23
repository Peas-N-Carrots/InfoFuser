import streamlit as st
import tempfile
import os
import json
import zipfile
from io import BytesIO
from pathlib import Path
import pandas as pd
from datetime import datetime, timedelta
import base64
import sys
import re
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum

sys.path.append(str(Path(__file__).resolve().parent.parent))

# Import agentic-doc library components
try:
    from agentic_doc.parse import parse
    from agentic_doc.utils import viz_parsed_document
    from agentic_doc.config import VisualizationConfig
    AGENTIC_DOC_AVAILABLE = True
except ImportError:
    AGENTIC_DOC_AVAILABLE = False

# Health data structures
class GoalType(Enum):
    WEIGHT_LOSS = "weight_loss"
    WEIGHT_GAIN = "weight_gain"
    MUSCLE_GAIN = "muscle_gain"
    GENERAL_HEALTH = "general_health"
    DISEASE_MANAGEMENT = "disease_management"
    ENERGY_BOOST = "energy_boost"

@dataclass
class HealthGoal:
    goal_type: GoalType
    target_value: Optional[float] = None
    target_date: Optional[datetime] = None
    priority: int = 1  # 1-5 scale

@dataclass
class PatientProfile:
    age: Optional[int] = None
    gender: Optional[str] = None
    height: Optional[float] = None  # cm
    weight: Optional[float] = None  # kg
    bmi: Optional[float] = None
    conditions: List[str] = None
    medications: List[str] = None
    allergies: List[str] = None
    dietary_restrictions: List[str] = None
    activity_level: Optional[str] = None
    goals: List[HealthGoal] = None
    recent_labs: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.conditions is None:
            self.conditions = []
        if self.medications is None:
            self.medications = []
        if self.allergies is None:
            self.allergies = []
        if self.dietary_restrictions is None:
            self.dietary_restrictions = []
        if self.goals is None:
            self.goals = []
        if self.recent_labs is None:
            self.recent_labs = {}

class HealthAnalyzer:
    """Analyzes parsed medical documents to extract health information"""
    
    @staticmethod
    def extract_patient_info(markdown_content: str) -> PatientProfile:
        """Extract patient information from parsed document content"""
        profile = PatientProfile()
        
        # Extract basic demographics
        age_match = re.search(r'age[:\s]+(\d+)', markdown_content.lower())
        if age_match:
            profile.age = int(age_match.group(1))
        
        gender_match = re.search(r'gender[:\s]+(male|female|m|f)', markdown_content.lower())
        if gender_match:
            profile.gender = gender_match.group(1)
        
        # Extract measurements
        height_match = re.search(r'height[:\s]+(\d+(?:\.\d+)?)\s*(?:cm|centimeters)', markdown_content.lower())
        if height_match:
            profile.height = float(height_match.group(1))
        
        weight_match = re.search(r'weight[:\s]+(\d+(?:\.\d+)?)\s*(?:kg|kilograms)', markdown_content.lower())
        if weight_match:
            profile.weight = float(weight_match.group(1))
        
        # Calculate BMI if both height and weight available
        if profile.height and profile.weight:
            profile.bmi = profile.weight / ((profile.height / 100) ** 2)
        
        # Extract conditions
        conditions_patterns = [
            r'diagnosis[:\s]+(.*?)(?:\n|$)',
            r'condition[s]?[:\s]+(.*?)(?:\n|$)',
            r'medical history[:\s]+(.*?)(?:\n|$)'
        ]
        
        for pattern in conditions_patterns:
            matches = re.finditer(pattern, markdown_content.lower())
            for match in matches:
                conditions_text = match.group(1)
                # Split by common delimiters
                conditions = re.split(r'[,;]', conditions_text)
                profile.conditions.extend([c.strip() for c in conditions if c.strip()])
        
        # Extract medications
        med_patterns = [
            r'medication[s]?[:\s]+(.*?)(?:\n|$)',
            r'prescription[s]?[:\s]+(.*?)(?:\n|$)',
            r'drug[s]?[:\s]+(.*?)(?:\n|$)'
        ]
        
        for pattern in med_patterns:
            matches = re.finditer(pattern, markdown_content.lower())
            for match in matches:
                meds_text = match.group(1)
                medications = re.split(r'[,;]', meds_text)
                profile.medications.extend([m.strip() for m in medications if m.strip()])
        
        # Extract allergies
        allergy_match = re.search(r'allergies?[:\s]+(.*?)(?:\n|$)', markdown_content.lower())
        if allergy_match:
            allergies_text = allergy_match.group(1)
            allergies = re.split(r'[,;]', allergies_text)
            profile.allergies.extend([a.strip() for a in allergies if a.strip()])
        
        # Extract lab values
        lab_patterns = {
            'cholesterol': r'cholesterol[:\s]+(\d+(?:\.\d+)?)',
            'glucose': r'glucose[:\s]+(\d+(?:\.\d+)?)',
            'blood_pressure': r'blood pressure[:\s]+(\d+/\d+)',
            'hemoglobin': r'hemoglobin[:\s]+(\d+(?:\.\d+)?)',
            'vitamin_d': r'vitamin d[:\s]+(\d+(?:\.\d+)?)'
        }
        
        for lab_name, pattern in lab_patterns.items():
            match = re.search(pattern, markdown_content.lower())
            if match:
                profile.recent_labs[lab_name] = match.group(1)
        
        return profile
    
    @staticmethod
    def combine_profiles(profiles: List[PatientProfile]) -> PatientProfile:
        """Combine multiple patient profiles into one comprehensive profile"""
        combined = PatientProfile()
        
        for profile in profiles:
            # Take the most recent/complete data
            if profile.age and not combined.age:
                combined.age = profile.age
            if profile.gender and not combined.gender:
                combined.gender = profile.gender
            if profile.height and not combined.height:
                combined.height = profile.height
            if profile.weight and not combined.weight:
                combined.weight = profile.weight
            if profile.bmi and not combined.bmi:
                combined.bmi = profile.bmi
            
            # Combine lists (remove duplicates)
            combined.conditions.extend([c for c in profile.conditions if c not in combined.conditions])
            combined.medications.extend([m for m in profile.medications if m not in combined.medications])
            combined.allergies.extend([a for a in profile.allergies if a not in combined.allergies])
            combined.dietary_restrictions.extend([d for d in profile.dietary_restrictions if d not in combined.dietary_restrictions])
            
            # Merge lab values
            combined.recent_labs.update(profile.recent_labs)
        
        return combined

class RecommendationEngine:
    """Generates personalized health recommendations"""
    
    @staticmethod
    def generate_daily_recommendations(profile: PatientProfile, goals: List[HealthGoal]) -> Dict[str, List[str]]:
        """Generate daily recommendations based on patient profile and goals"""
        recommendations = {
            "nutrition": [],
            "exercise": [],
            "lifestyle": [],
            "medical": [],
            "monitoring": []
        }
        
        # Nutrition recommendations
        if profile.bmi:
            if profile.bmi < 18.5:
                recommendations["nutrition"].append("Focus on calorie-dense, nutritious foods to support healthy weight gain")
                recommendations["nutrition"].append("Include 5-6 smaller meals throughout the day")
            elif profile.bmi > 25:
                recommendations["nutrition"].append("Create a moderate calorie deficit through portion control")
                recommendations["nutrition"].append("Emphasize high-fiber, low-calorie density foods")
        
        # Condition-specific recommendations
        conditions_lower = [c.lower() for c in profile.conditions]
        
        if any("diabetes" in c for c in conditions_lower):
            recommendations["nutrition"].append("Monitor carbohydrate intake and choose low-glycemic foods")
            recommendations["monitoring"].append("Check blood glucose levels as prescribed")
            recommendations["exercise"].append("Include 30 minutes of moderate exercise daily to improve insulin sensitivity")
        
        if any("hypertension" in c or "high blood pressure" in c for c in conditions_lower):
            recommendations["nutrition"].append("Limit sodium intake to less than 2,300mg per day")
            recommendations["lifestyle"].append("Practice stress-reduction techniques like deep breathing")
            recommendations["monitoring"].append("Monitor blood pressure regularly")
        
        if any("heart" in c or "cardiac" in c for c in conditions_lower):
            recommendations["nutrition"].append("Follow a heart-healthy diet rich in omega-3 fatty acids")
            recommendations["exercise"].append("Engage in low-impact cardio as approved by your physician")
        
        # Goal-specific recommendations
        for goal in goals:
            if goal.goal_type == GoalType.WEIGHT_LOSS:
                recommendations["nutrition"].append("Aim for 1-2 pounds of weight loss per week through diet and exercise")
                recommendations["exercise"].append("Combine cardio and strength training for optimal fat loss")
            elif goal.goal_type == GoalType.MUSCLE_GAIN:
                recommendations["nutrition"].append("Consume 1.6-2.2g of protein per kg of body weight daily")
                recommendations["exercise"].append("Focus on progressive resistance training 3-4 times per week")
            elif goal.goal_type == GoalType.ENERGY_BOOST:
                recommendations["lifestyle"].append("Maintain consistent sleep schedule (7-9 hours nightly)")
                recommendations["nutrition"].append("Balance macronutrients and avoid energy crashes with complex carbs")
        
        # Age-specific recommendations
        if profile.age:
            if profile.age >= 65:
                recommendations["exercise"].append("Include balance and flexibility exercises to prevent falls")
                recommendations["medical"].append("Ensure adequate calcium and vitamin D intake")
            elif profile.age <= 25:
                recommendations["lifestyle"].append("Establish healthy habits now for long-term wellness")
        
        # Lab-based recommendations
        if "cholesterol" in profile.recent_labs:
            try:
                cholesterol = float(profile.recent_labs["cholesterol"])
                if cholesterol > 200:
                    recommendations["nutrition"].append("Limit saturated fat and increase soluble fiber intake")
                    recommendations["medical"].append("Discuss cholesterol management with your healthcare provider")
            except ValueError:
                pass
        
        # General recommendations
        recommendations["nutrition"].append("Stay hydrated with 8-10 glasses of water daily")
        recommendations["lifestyle"].append("Limit screen time before bed for better sleep quality")
        recommendations["medical"].append("Take medications as prescribed and track any side effects")
        
        # Remove empty categories
        return {k: v for k, v in recommendations.items() if v}

def main():
    st.set_page_config(
        page_title="Personal Health Companion",
        page_icon="🏥",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Custom CSS for better styling
    st.markdown("""
    <style>
    .main-header {
        text-align: center;
        background: linear-gradient(90deg, #00c6ff 0%, #0072ff 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 3rem;
        font-weight: bold;
        margin-bottom: 2rem;
    }
    .feature-box {
        background-color: #f0f8ff;
        padding: 1.5rem;
        border-radius: 10px;
        border-left: 5px solid #0072ff;
        margin: 1rem 0;
    }
    .recommendation-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1rem;
        border-radius: 10px;
        margin: 0.5rem 0;
    }
    .health-metric {
        background: white;
        padding: 1rem;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        text-align: center;
        border-left: 4px solid #00c6ff;
    }
    .goal-card {
        background: linear-gradient(45deg, #ff9a9e 0%, #fecfef 100%);
        padding: 1rem;
        border-radius: 10px;
        margin: 0.5rem 0;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Main header
    st.markdown('<h1 class="main-header">🏥 Personal Health Companion</h1>', unsafe_allow_html=True)
    st.markdown("**AI-powered health document analysis and personalized daily recommendations**")
    
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
    
    # Initialize session state
    if "patient_profile" not in st.session_state:
        st.session_state.patient_profile = PatientProfile()
    if "health_goals" not in st.session_state:
        st.session_state.health_goals = []
    if "recommendations" not in st.session_state:
        st.session_state.recommendations = {}
    
    # Sidebar configuration
    with st.sidebar:
        st.header("⚙️ Settings")
        
        # Health Goals Section
        st.subheader("🎯 Health Goals")
        
        goal_type = st.selectbox(
            "Select Goal Type:",
            options=[goal.value for goal in GoalType],
            format_func=lambda x: x.replace('_', ' ').title()
        )
        
        if st.button("Add Goal"):
            new_goal = HealthGoal(goal_type=GoalType(goal_type))
            st.session_state.health_goals.append(new_goal)
            st.success(f"Added goal: {goal_type.replace('_', ' ').title()}")
        
        # Display current goals
        if st.session_state.health_goals:
            st.write("**Current Goals:**")
            for i, goal in enumerate(st.session_state.health_goals):
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.write(f"• {goal.goal_type.value.replace('_', ' ').title()}")
                with col2:
                    if st.button("🗑️", key=f"del_goal_{i}"):
                        st.session_state.health_goals.pop(i)
                        st.rerun()
        
        st.markdown("---")
        
        # Parsing options
        st.subheader("📄 Document Parsing")
        include_marginalia = st.checkbox("Include Marginalia", value=True)
        include_metadata = st.checkbox("Include Metadata", value=True)
        
        # Processing options
        st.subheader("⚙️ Processing Options")
        batch_size = st.number_input("Batch Size", min_value=1, max_value=10, value=4)
        max_workers = st.number_input("Max Workers", min_value=1, max_value=10, value=5)
        
        os.environ['BATCH_SIZE'] = str(batch_size)
        os.environ['MAX_WORKERS'] = str(max_workers)
    
    # Main content tabs
    tab1, tab2, tab3, tab4 = st.tabs(["📁 Upload Documents", "👤 Patient Profile", "💡 Daily Recommendations", "📊 Health Dashboard"])
    
    with tab1:
        st.header("📁 Upload Health Documents")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            uploaded_files = st.file_uploader(
                "Upload your health documents (EHR, lab results, nutritionist questionnaires, etc.)",
                type=['pdf', 'png', 'jpg', 'jpeg', 'tiff', 'bmp'],
                accept_multiple_files=True,
                help="Supported formats: PDF, PNG, JPG, JPEG, TIFF, BMP"
            )
            
            if uploaded_files:
                st.success(f"✅ {len(uploaded_files)} file(s) uploaded successfully!")
                
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
            st.markdown("""
            <div class="feature-box">
            <h4>📋 Supported Documents</h4>
            <ul>
            <li>Electronic Health Records (EHR)</li>
            <li>Lab test results</li>
            <li>Nutritionist questionnaires</li>
            <li>Prescription lists</li>
            <li>Medical history forms</li>
            <li>Discharge summaries</li>
            </ul>
            </div>
            """, unsafe_allow_html=True)
        
        if uploaded_files:
            if st.button("🔍 Analyze Documents", type="primary", use_container_width=True):
                analyze_documents(uploaded_files, include_marginalia, include_metadata)
    
    with tab2:
        display_patient_profile()
    
    with tab3:
        display_daily_recommendations()
    
    with tab4:
        display_health_dashboard()

def analyze_documents(uploaded_files, include_marginalia, include_metadata):
    """Analyze uploaded health documents"""
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Save uploaded files
        file_paths = []
        for uploaded_file in uploaded_files:
            file_path = temp_path / uploaded_file.name
            with open(file_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            file_paths.append(str(file_path))
        
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
            
            progress_bar.progress(50)
            status_text.text("🧠 Analyzing health data...")
            
            # Extract health information
            profiles = []
            for result in results:
                if result.markdown:
                    profile = HealthAnalyzer.extract_patient_info(result.markdown)
                    profiles.append(profile)
            
            progress_bar.progress(75)
            
            # Combine profiles
            if profiles:
                combined_profile = HealthAnalyzer.combine_profiles(profiles)
                st.session_state.patient_profile = combined_profile
                
                # Generate recommendations
                recommendations = RecommendationEngine.generate_daily_recommendations(
                    combined_profile, st.session_state.health_goals
                )
                st.session_state.recommendations = recommendations
            
            progress_bar.progress(100)
            status_text.text("✅ Analysis completed!")
            
            st.success("🎉 Documents analyzed successfully! Check the Patient Profile and Daily Recommendations tabs.")
            
        except Exception as e:
            st.error(f"❌ Error analyzing documents: {str(e)}")
            progress_bar.progress(0)
            status_text.text("❌ Analysis failed!")

def display_patient_profile():
    """Display patient profile information"""
    
    st.header("👤 Patient Profile")
    
    profile = st.session_state.patient_profile
    
    if not any([profile.age, profile.gender, profile.height, profile.weight, profile.conditions]):
        st.info("📋 No patient data available. Please upload and analyze health documents first.")
        return
    
    # Basic information
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        age_display = profile.age if profile.age else "Not specified"
        st.markdown(f'<div class="health-metric"><h3>{age_display}</h3><p>Age</p></div>', unsafe_allow_html=True)
    
    with col2:
        gender_display = profile.gender.title() if profile.gender else "Not specified"
        st.markdown(f'<div class="health-metric"><h3>{gender_display}</h3><p>Gender</p></div>', unsafe_allow_html=True)
    
    with col3:
        weight_display = f"{profile.weight} kg" if profile.weight else "Not specified"
        st.markdown(f'<div class="health-metric"><h3>{weight_display}</h3><p>Weight</p></div>', unsafe_allow_html=True)
    
    with col4:
        bmi_display = f"{profile.bmi:.1f}" if profile.bmi else "Not calculated"
        bmi_category = ""
        if profile.bmi:
            if profile.bmi < 18.5:
                bmi_category = "(Underweight)"
            elif profile.bmi < 25:
                bmi_category = "(Normal)"
            elif profile.bmi < 30:
                bmi_category = "(Overweight)"
            else:
                bmi_category = "(Obese)"
        st.markdown(f'<div class="health-metric"><h3>{bmi_display}</h3><p>BMI {bmi_category}</p></div>', unsafe_allow_html=True)
    
    # Detailed information
    col1, col2 = st.columns(2)
    
    with col1:
        if profile.conditions:
            st.subheader("🏥 Medical Conditions")
            for condition in profile.conditions:
                st.write(f"• {condition}")
        
        if profile.medications:
            st.subheader("💊 Medications")
            for medication in profile.medications:
                st.write(f"• {medication}")
    
    with col2:
        if profile.allergies:
            st.subheader("⚠️ Allergies")
            for allergy in profile.allergies:
                st.write(f"• {allergy}")
        
        if profile.recent_labs:
            st.subheader("🔬 Recent Lab Results")
            for lab, value in profile.recent_labs.items():
                st.write(f"• {lab.replace('_', ' ').title()}: {value}")

def display_daily_recommendations():
    """Display personalized daily recommendations"""
    
    st.header("💡 Your Daily Health Recommendations")
    st.write(f"*Generated on {datetime.now().strftime('%B %d, %Y')}*")
    
    recommendations = st.session_state.recommendations
    
    if not recommendations:
        st.info("🤖 No recommendations available. Please upload and analyze your health documents first.")
        return
    
    # Display recommendations by category
    for category, recs in recommendations.items():
        if recs:
            icon_map = {
                "nutrition": "🥗",
                "exercise": "🏃‍♂️",
                "lifestyle": "🌟",
                "medical": "⚕️",
                "monitoring": "📊"
            }
            
            st.subheader(f"{icon_map.get(category, '📋')} {category.title()} Recommendations")
            
            for i, recommendation in enumerate(recs):
                st.markdown(f"""
                <div class="recommendation-card">
                <strong>#{i+1}</strong> {recommendation}
                </div>
                """, unsafe_allow_html=True)
    
    # Action items
    st.subheader("✅ Today's Action Items")
    
    action_items = []
    if "nutrition" in recommendations:
        action_items.append("Plan and prep healthy meals based on nutrition recommendations")
    if "exercise" in recommendations:
        action_items.append("Schedule your daily exercise session")
    if "monitoring" in recommendations:
        action_items.append("Take and record your health measurements")
    if "medical" in recommendations:
        action_items.append("Review medication schedule and medical recommendations")
    
    for item in action_items:
        st.checkbox(item, key=f"action_{hash(item)}")

def display_health_dashboard():
    """Display health dashboard with visualizations"""
    
    st.header("📊 Health Dashboard")
    
    profile = st.session_state.patient_profile
    goals = st.session_state.health_goals
    
    if not profile.age and not profile.weight and not profile.conditions:
        st.info("📊 No health data available for dashboard. Please upload and analyze documents first.")
        return
    
    # Health goals progress
    if goals:
        st.subheader("🎯 Health Goals")
        
        for goal in goals:
            st.markdown(f"""
            <div class="goal-card">
            <h4>{goal.goal_type.value.replace('_', ' ').title()}</h4>
            <p>Priority: {'⭐' * goal.priority}</p>
            </div>
            """, unsafe_allow_html=True)
    
    # Health metrics visualization
    if profile.bmi or profile.weight:
        st.subheader("📈 Health Metrics")
        
        # Create sample progress data (in a real app, this would come from historical data)
        dates = [datetime.now() - timedelta(days=x) for x in range(30, 0, -1)]
        
        if profile.weight:
            # Sample weight trend (in real app, this would be historical data)
            weights = [profile.weight + (i * 0.1) for i in range(-15, 15)]  # Sample trend
            
            weight_df = pd.DataFrame({
                'Date': dates,
                'Weight (kg)': weights
            })
            
            st.line_chart(weight_df.set_index('Date'))
    
    # Risk factors
    st.subheader("⚠️ Health Risk Assessment")
    
    risk_factors = []
    
    if profile.bmi and profile.bmi > 30:
        risk_factors.append("High BMI (Obesity)")
    
    if any("diabetes" in c.lower() for c in profile.conditions):
        risk_factors.append("Diabetes Management Required")
    
    if any("hypertension" in c.lower() for c in profile.conditions):
        risk_factors.append("Hypertension Monitoring Required")
    
    if not risk_factors:
        st.success("✅ No immediate risk factors identified based on available data")
    else:
        for risk in risk_factors:
            st.warning(f"⚠️ {risk}")
    
    # Medication adherence tracker
    if profile.medications:
        st.subheader("💊 Medication Tracking")
        
        for med in profile.medications:
            col1, col2 = st.columns([3, 1])
            with col1:
                st.write(f"**{med}**")
            with col2:
                st.checkbox("Taken today", key=f"med_{hash(med)}")

if __name__ == "__main__":
    main()