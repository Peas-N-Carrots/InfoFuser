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
from pydantic import BaseModel, Field

sys.path.append(str(Path(__file__).resolve().parent.parent))

# Import agentic-doc library components
try:
    from agentic_doc.parse import parse
    from agentic_doc.utils import viz_parsed_document
    from agentic_doc.config import VisualizationConfig
    AGENTIC_DOC_AVAILABLE = True
except ImportError:
    AGENTIC_DOC_AVAILABLE = False

# Pydantic models for structured extraction
class PatientBasicInfo(BaseModel):
    """Basic patient demographic information"""
    age: int = Field(description="the age of the patient in years")
    gender: str = Field(description="the gender of the patient (male/female)")
    height: float = Field(description="the height of the patient in centimeters")
    weight: float = Field(description="the weight of the patient in kilograms")
    bmi: float = Field(description="the BMI (body mass index) of the patient")

class MedicalConditions(BaseModel):
    """Medical conditions and health issues"""
    conditions: List[str] = Field(default=[], description="list of medical conditions, diagnoses, or health issues")
    medications: List[str] = Field(default=[], description="list of current medications or prescriptions")
    allergies: List[str] = Field(default=[], description="list of known allergies or adverse reactions")
    dietary_restrictions: List[str] = Field(default=[], description="list of dietary restrictions or special diet requirements")

class LabResults(BaseModel):
    """Laboratory test results and vital signs"""
    cholesterol: Optional[str] = Field(None, description="cholesterol level value")
    glucose: Optional[str] = Field(None, description="glucose or blood sugar level")
    blood_pressure: Optional[str] = Field(None, description="blood pressure reading (systolic/diastolic)")
    hemoglobin: Optional[str] = Field(None, description="hemoglobin level")
    vitamin_d: Optional[str] = Field(None, description="vitamin D level")
    heart_rate: Optional[str] = Field(None, description="heart rate or pulse")

class HealthGoals(BaseModel):
    """Patient health goals and objectives"""
    weight_goals: List[str] = Field(default=[], description="weight loss, weight gain, or weight maintenance goals")
    fitness_goals: List[str] = Field(default=[], description="exercise, fitness, or physical activity goals")
    health_objectives: List[str] = Field(default=[], description="general health improvement objectives or targets")

# Health data structures (keeping existing enums and dataclasses)
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
    """Analyzes parsed medical documents to extract health information using LandingAI's structured extraction"""
    
    @staticmethod
    def extract_patient_info_structured(file_path: str) -> PatientProfile:
        """Extract patient information using LandingAI's structured field extraction"""
        profile = PatientProfile()
        
        try:
            # Extract basic patient information
            basic_results = parse(file_path, extraction_model=PatientBasicInfo)
            if basic_results and len(basic_results) > 0:
                basic_info = basic_results[0].extraction
                if basic_info:
                    profile.age = basic_info.age
                    profile.gender = basic_info.gender
                    profile.height = basic_info.height
                    profile.weight = basic_info.weight
                    profile.bmi = basic_info.bmi
                    
                    # Calculate BMI if not provided but height and weight are available
                    if not profile.bmi and profile.height and profile.weight:
                        profile.bmi = profile.weight / ((profile.height / 100) ** 2)
            
            # Extract medical conditions
            conditions_results = parse(file_path, extraction_model=MedicalConditions)
            if conditions_results and len(conditions_results) > 0:
                conditions_info = conditions_results[0].extraction
                if conditions_info:
                    profile.conditions = [c for c in conditions_info.conditions if c and len(c.strip()) > 2]
                    profile.medications = [m for m in conditions_info.medications if m and len(m.strip()) > 2]
                    profile.allergies = [a for a in conditions_info.allergies if a and len(a.strip()) > 1]
                    profile.dietary_restrictions = [d for d in conditions_info.dietary_restrictions if d and len(d.strip()) > 2]
            
            # Extract lab results
            lab_results = parse(file_path, extraction_model=LabResults)
            if lab_results and len(lab_results) > 0:
                lab_info = lab_results[0].extraction
                if lab_info:
                    # Convert lab results to dictionary format
                    lab_dict = {}
                    if lab_info.cholesterol:
                        lab_dict['cholesterol'] = lab_info.cholesterol
                    if lab_info.glucose:
                        lab_dict['glucose'] = lab_info.glucose
                    if lab_info.blood_pressure:
                        lab_dict['blood_pressure'] = lab_info.blood_pressure
                    if lab_info.hemoglobin:
                        lab_dict['hemoglobin'] = lab_info.hemoglobin
                    if lab_info.vitamin_d:
                        lab_dict['vitamin_d'] = lab_info.vitamin_d
                    if lab_info.heart_rate:
                        lab_dict['heart_rate'] = lab_info.heart_rate
                    
                    profile.recent_labs = lab_dict
            
            # Extract health goals
            goals_results = parse(file_path, extraction_model=HealthGoals)
            if goals_results and len(goals_results) > 0:
                goals_info = goals_results[0].extraction
                if goals_info:
                    # Convert extracted goals to HealthGoal objects
                    for weight_goal in goals_info.weight_goals:
                        if 'loss' in weight_goal.lower() or 'lose' in weight_goal.lower():
                            profile.goals.append(HealthGoal(goal_type=GoalType.WEIGHT_LOSS))
                        elif 'gain' in weight_goal.lower():
                            profile.goals.append(HealthGoal(goal_type=GoalType.WEIGHT_GAIN))
                    
                    for fitness_goal in goals_info.fitness_goals:
                        if 'muscle' in fitness_goal.lower():
                            profile.goals.append(HealthGoal(goal_type=GoalType.MUSCLE_GAIN))
                        else:
                            profile.goals.append(HealthGoal(goal_type=GoalType.GENERAL_HEALTH))
                    
                    for health_obj in goals_info.health_objectives:
                        if 'energy' in health_obj.lower():
                            profile.goals.append(HealthGoal(goal_type=GoalType.ENERGY_BOOST))
                        else:
                            profile.goals.append(HealthGoal(goal_type=GoalType.GENERAL_HEALTH))
        
        except Exception as e:
            st.error(f"Error extracting structured data: {str(e)}")
            # Fallback to the original text-based extraction if structured extraction fails
            profile = HealthAnalyzer.extract_patient_info_fallback(file_path)
        
        return profile
    
    @staticmethod
    def extract_patient_info_fallback(file_path: str) -> PatientProfile:
        """Fallback extraction method using markdown parsing (original method)"""
        profile = PatientProfile()
        
        try:
            # Parse document to get markdown content
            results = parse(file_path)
            if not results or len(results) == 0:
                return profile
            
            markdown_content = results[0].markdown
            if not markdown_content:
                return profile
            
            # Use the original regex-based extraction as fallback
            profile = HealthAnalyzer._extract_from_markdown(markdown_content)
            
        except Exception as e:
            st.error(f"Error in fallback extraction: {str(e)}")
        
        return profile
    
    @staticmethod
    def _extract_from_markdown(markdown_content: str) -> PatientProfile:
        """Original markdown-based extraction method (kept as fallback)"""
        profile = PatientProfile()
        
        # Extract basic demographics with more flexible patterns
        age_patterns = [
            r'age[:\s]+(\d+)',
            r'(\d+)\s*years?\s*old',
            r'age\s*(\d+)',
            r'dob.*(\d{4})',  # birth year
        ]
        
        for pattern in age_patterns:
            age_match = re.search(pattern, markdown_content.lower())
            if age_match:
                if 'dob' in pattern:
                    # Calculate age from birth year
                    birth_year = int(age_match.group(1))
                    current_year = datetime.now().year
                    profile.age = current_year - birth_year
                else:
                    profile.age = int(age_match.group(1))
                break
        
        # Enhanced gender extraction
        gender_patterns = [
            r'gender[:\s]+(male|female|m|f)',
            r'sex[:\s]+(male|female|m|f)',
            r'\b(male|female)\b',
            r'patient.*\b(he|she|his|her)\b'
        ]
        
        for pattern in gender_patterns:
            gender_match = re.search(pattern, markdown_content.lower())
            if gender_match:
                gender = gender_match.group(1).lower()
                if gender in ['male', 'm', 'he', 'his']:
                    profile.gender = 'Male'
                elif gender in ['female', 'f', 'she', 'her']:
                    profile.gender = 'Female'
                break
        
        # Enhanced measurements extraction
        height_patterns = [
            r'height[:\s]+(\d+(?:\.\d+)?)\s*(?:cm|centimeters)',
            # r'height[:\s]+(\d+)\s*[\'\"]\s*(\d+)\s*[\"\'']',  # feet and inches
            r'(\d+(?:\.\d+)?)\s*cm',
            r'height.*?(\d+(?:\.\d+)?)'
        ]
        
        for pattern in height_patterns:
            height_match = re.search(pattern, markdown_content.lower())
            if height_match:
                if '\"' in pattern or '\'' in pattern:
                    # Convert feet and inches to cm
                    feet = int(height_match.group(1))
                    inches = int(height_match.group(2)) if height_match.group(2) else 0
                    profile.height = (feet * 30.48) + (inches * 2.54)
                else:
                    profile.height = float(height_match.group(1))
                break
        
        weight_patterns = [
            r'weight[:\s]+(\d+(?:\.\d+)?)\s*(?:kg|kilograms)',
            r'weight[:\s]+(\d+(?:\.\d+)?)\s*(?:lbs?|pounds)',
            r'(\d+(?:\.\d+)?)\s*kg',
            r'(\d+(?:\.\d+)?)\s*lbs?',
            r'weight.*?(\d+(?:\.\d+)?)'
        ]
        
        for pattern in weight_patterns:
            weight_match = re.search(pattern, markdown_content.lower())
            if weight_match:
                weight_value = float(weight_match.group(1))
                if 'lbs' in pattern or 'pounds' in pattern:
                    # Convert pounds to kg
                    profile.weight = weight_value * 0.453592
                else:
                    profile.weight = weight_value
                break
        
        # Calculate BMI if both height and weight available
        if profile.height and profile.weight:
            profile.bmi = profile.weight / ((profile.height / 100) ** 2)
        
        # Extract conditions from checkboxes and text (enhanced for medical forms)
        # Look for "yes" checkboxes in medical questionnaires
        yes_conditions = []
        lines = markdown_content.split('\n')
        
        for line in lines:
            # Check for marked "yes" items in tables
            if '✓' in line and 'yes' in line.lower():
                # Extract condition name from the line
                condition_match = re.search(r'([^|]*?)\s*\|\s*✓', line)
                if condition_match:
                    condition = condition_match.group(1).strip()
                    if condition and len(condition) > 3:  # Filter out short/meaningless entries
                        yes_conditions.append(condition)
        
        # Also look for traditional condition patterns
        conditions_patterns = [
            r'diagnosis[:\s]+(.*?)(?:\n|$)',
            r'condition[s]?[:\s]+(.*?)(?:\n|$)',
            r'medical history[:\s]+(.*?)(?:\n|$)',
            r'history of[:\s]+(.*?)(?:\n|$)'
        ]
        
        profile.conditions = []
        for pattern in conditions_patterns:
            matches = re.finditer(pattern, markdown_content.lower())
            for match in matches:
                conditions_text = match.group(1)
                conditions = re.split(r'[,;]', conditions_text)
                profile.conditions.extend([c.strip() for c in conditions if c.strip() and len(c.strip()) > 2])
        
        # Add conditions from checkbox analysis
        profile.conditions.extend(yes_conditions)
        
        # Remove duplicates and clean up
        profile.conditions = list(set([c for c in profile.conditions if c and len(c) > 2]))
        
        # Extract medications with enhanced patterns
        med_patterns = [
            r'medication[s]?[:\s]+(.*?)(?:\n|$)',
            r'prescription[s]?[:\s]+(.*?)(?:\n|$)',
            r'drug[s]?[:\s]+(.*?)(?:\n|$)',
            r'taking[:\s]+(.*?)(?:\n|$)',
            r'current.*medication[s]?[:\s]+(.*?)(?:\n|$)'
        ]
        
        profile.medications = []
        for pattern in med_patterns:
            matches = re.finditer(pattern, markdown_content.lower())
            for match in matches:
                meds_text = match.group(1)
                medications = re.split(r'[,;]', meds_text)
                profile.medications.extend([m.strip() for m in medications if m.strip() and len(m.strip()) > 2])
        
        # Remove duplicates
        profile.medications = list(set([m for m in profile.medications if m and len(m) > 2]))
        
        # Extract allergies with enhanced patterns
        allergy_patterns = [
            r'allergies?[:\s]+(.*?)(?:\n|$)',
            r'allergic to[:\s]+(.*?)(?:\n|$)',
            r'drug allergies?[:\s]+(.*?)(?:\n|$)',
            r'food allergies?[:\s]+(.*?)(?:\n|$)'
        ]
        
        profile.allergies = []
        for pattern in allergy_patterns:
            allergy_match = re.search(pattern, markdown_content.lower())
            if allergy_match:
                allergies_text = allergy_match.group(1)
                if 'none' not in allergies_text.lower() and 'no' not in allergies_text.lower():
                    allergies = re.split(r'[,;]', allergies_text)
                    profile.allergies.extend([a.strip() for a in allergies if a.strip() and len(a.strip()) > 1])
        
        # Remove duplicates
        profile.allergies = list(set([a for a in profile.allergies if a and len(a) > 1]))
        
        # Extract lab values with enhanced patterns
        lab_patterns = {
            'cholesterol': r'cholesterol[:\s]+(\d+(?:\.\d+)?)',
            'glucose': r'glucose[:\s]+(\d+(?:\.\d+)?)',
            'blood_pressure': r'blood pressure[:\s]+(\d+/\d+)',
            'hemoglobin': r'hemoglobin[:\s]+(\d+(?:\.\d+)?)',
            'vitamin_d': r'vitamin d[:\s]+(\d+(?:\.\d+)?)',
            'bmi': r'bmi[:\s]+(\d+(?:\.\d+)?)'
        }
        
        profile.recent_labs = {}
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
    st.markdown("**AI-powered health document analysis with LandingAI structured extraction**")
    
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
        
        # Extraction method selection
        st.subheader("🔧 Extraction Method")
        extraction_method = st.radio(
            "Choose extraction method:",
            ["Structured (LandingAI)", "Fallback (Regex)"],
            help="Structured uses LandingAI's Pydantic models, Fallback uses regex patterns"
        )
        
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
        
        # Store extraction method in session state
        st.session_state.extraction_method = extraction_method
    
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
            
            # Extract health information using selected method
            profiles = []
            extraction_method = st.session_state.get('extraction_method', 'Structured (LandingAI)')
            
            if extraction_method == 'Structured (LandingAI)':
                # Use structured extraction for each file
                for file_path in file_paths:
                    profile = HealthAnalyzer.extract_patient_info_structured(file_path)
                    profiles.append(profile)
            else:
                # Use fallback method with parsed markdown
                for result in results:
                    if result.markdown:
                        profile = HealthAnalyzer._extract_from_markdown(result.markdown)
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
        gender_display = profile.gender if profile.gender else "Not specified"
        st.markdown(f'<div class="health-metric"><h3>{gender_display}</h3><p>Gender</p></div>', unsafe_allow_html=True)
    
    with col3:
        weight_display = f"{profile.weight:.1f} kg" if profile.weight else "Not specified"
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
    
    # Additional metrics row
    if profile.height:
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            height_display = f"{profile.height:.0f} cm" if profile.height else "Not specified"
            st.markdown(f'<div class="health-metric"><h3>{height_display}</h3><p>Height</p></div>', unsafe_allow_html=True)
    
    # Detailed information
    col1, col2 = st.columns(2)
    
    with col1:
        # Medical Conditions
        st.subheader("🏥 Medical Conditions")
        if profile.conditions:
            # Format conditions as a clean list
            conditions_text = ""
            for condition in profile.conditions:
                # Clean up condition names
                clean_condition = condition.strip()
                if clean_condition:
                    conditions_text += f"• **{clean_condition.title()}**\n"
            
            if conditions_text:
                st.markdown(conditions_text)
            else:
                st.markdown("*None reported*")
        else:
            st.markdown("*None reported*")
        
        # Medications
        st.subheader("💊 Medications")
        if profile.medications:
            medications_text = ""
            for medication in profile.medications:
                clean_medication = medication.strip()
                if clean_medication:
                    medications_text += f"• **{clean_medication.title()}**\n"
            
            if medications_text:
                st.markdown(medications_text)
            else:
                st.markdown("*None reported*")
        else:
            st.markdown("*None reported*")
    
    with col2:
        # Allergies
        st.subheader("⚠️ Allergies")
        if profile.allergies:
            allergies_text = ""
            for allergy in profile.allergies:
                clean_allergy = allergy.strip()
                if clean_allergy:
                    allergies_text += f"• **{clean_allergy.title()}**\n"
            
            if allergies_text:
                st.markdown(allergies_text)
            else:
                st.markdown("*None reported*")
        else:
            st.markdown("*None reported*")
        
        # Recent Lab Results
        st.subheader("🔬 Recent Lab Results")
        if profile.recent_labs:
            lab_text = ""
            for lab, value in profile.recent_labs.items():
                lab_name = lab.replace('_', ' ').title()
                lab_text += f"• **{lab_name}**: {value}\n"
            
            if lab_text:
                st.markdown(lab_text)
            else:
                st.markdown("*No recent lab results*")
        else:
            st.markdown("*No recent lab results*")
    
    # Debug section (optional - can be removed in production)
    with st.expander("🔍 Debug Information (Raw Data)", expanded=False):
        st.write("**Profile Data:**")
        profile_dict = {
            "Age": profile.age,
            "Gender": profile.gender,
            "Height": profile.height,
            "Weight": profile.weight,
            "BMI": profile.bmi,
            "Conditions": profile.conditions,
            "Medications": profile.medications,
            "Allergies": profile.allergies,
            "Recent Labs": profile.recent_labs
        }
        st.json(profile_dict)

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