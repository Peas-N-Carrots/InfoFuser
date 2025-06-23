from google import genai
from model.jsonFormat import jsonFormat

# Uses an LLM API to generate personalized health goals and recommendations based on a patient's medical data.
# input: JSON object containing a patient's medical data and history.
# output: A structured JSON object with daily, short-term, medium-term, and long-term goals, along with general recommendations.

def advise(input):
    client = genai.Client()

    prompt = prompt = f"""
    You are a clinical decision-support assistant.  
    Given a JSON object containing a patient’s medical data and history, generate a structured set of personalized goals and recommendations that reflect best practices in preventative and therapeutic healthcare.  

    Be extremely specific in your suggestions. Consider the patient’s age, sex, health conditions, medications, and lifestyle indicators. For example, suggest:

    - Specific foods or meal patterns (e.g., "Include a breakfast of steel-cut oats with berries and flaxseeds to support cholesterol levels")
    - Types of exercises suited to the patient’s condition (e.g., "15 minutes of low-impact water aerobics if experiencing joint pain")
    - Medications or supplements they should adhere to (e.g., "Continue 20mg atorvastatin daily in the evening, with food")
    - Skincare and sunscreen if relevant (e.g., "Apply broad-spectrum SPF 50 zinc oxide sunscreen daily, especially if taking photosensitizing meds")
    - Behavioral or lifestyle changes, supported with examples or routines
    - Monitoring activities (e.g., "Check fasting glucose 3 times per week using home monitor")
    - Return a single valid MD object only, with no extra explanation

    Return your response in this structured MD format:

    # Health Goals & Recommendations

    ## 🗓 Daily Goals
    - Eat a Mediterranean-style lunch with grilled salmon, quinoa, and leafy greens.
    - Apply SPF 50 sunscreen before going outside, especially on face and hands.
    - Take 10mg of Lisinopril with breakfast and monitor blood pressure after dinner.

    ## ⏳ Short-Term Goals (Next 1–2 Weeks)
    - Schedule a lipid panel blood test within the next 7 days.
    - Begin a light walking routine: 15 minutes after dinner, 5×/week.

    ## 📆 Medium-Term Goals (1–3 Months)
    - Reduce A1C to below 6.5% through consistent dietary choices and medication adherence.
    - Integrate 2 strength training sessions per week using bodyweight exercises like squats and wall pushups.

    ## 🏁 Long-Term Goals (3+ Months)
    - Maintain LDL cholesterol under 100 mg/dL and BMI in the 22–25 range.
    - Establish a 7–8 hour sleep schedule to support long-term cardiovascular health.

    ## ✅ General Recommendations
    - Eat fatty fish (e.g., salmon, sardines) twice a week to support heart health.
    - Avoid added sugars by replacing soda with sparkling water and lemon.
    - Use a daily fragrance-free moisturizer containing ceramides to manage dry skin.
    - Use a daily pill organizer to improve medication adherence.


    Be detailed and personalized in your output. Make sure your suggestions are clinically safe, realistic, and adapted to the patient’s profile.

    Here is the patient's data:
    {input}
    """
    response = client.models.generate_content(
        model="gemini-2.0-flash", contents=prompt
    )
    return response.text