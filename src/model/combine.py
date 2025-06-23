from google import genai

from model.jsonFormat import jsonFormat

# Uses an LLM API to combine the data of multiple medical documents into a single JSON object.
# input: Array of extracted documents from the extract.py extract function.
# output: A single JSON object that combines the data from all inputted documents.

def combine(documents):
    client = genai.Client()

    prompt = f"""You are an intelligent medical data assistant.

    Merge the following MD objects to complete a patient's superset of medical data.
    This data will be used to give the patient daily health related goals.

    Follow these rules:
    - Combine related fields to avoid redundancy (e.g. first_name + last_name vs full_name)
    - Avoid redundant or duplicate data
    - Preserve all unique data
    - Fields that are not filled out or non applicable may be omitted
    - Return a single valid JSON object only, with no extra explanation.
    - Format and structure the output in a way that makes the data easy to read and understandable
    """
    
    for i, doc in enumerate(documents):
        prompt += f"\n\nMD {i}:\n{doc[0].markdown}"

    response = client.models.generate_content(
        model="gemini-2.0-flash", contents=prompt
    )
    return jsonFormat(response.text)
