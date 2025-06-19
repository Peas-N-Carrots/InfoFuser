from agentic_doc.parse import parse
from google import genai



# Parse a local file
# result1 = parse("doc/Examination.pdf", extraction_model=patient)
# result2 = parse("doc/Nutrition.pdf", extraction_model=patient)

def combine(documents):
    # documents = ["doc/Examination.pdf", "doc/Nutrition.pdf"]

    # results = parse(documents)

    client = genai.Client()

    prompt = f"""You are an intelligent medical data assistant.

    Merge the following MD objects to complete a patient's superset of medical data.
    This data will be used to give the patient daily health related goals.

    Follow these rules:
    - Combine related fields to avoid redundancy (e.g. first_name + last_name vs full_name)
    - Avoid redundant or duplicate data
    - Preserve all unique data
    - Fields that are not filled out or non applicable may be omitted
    - Return a single valid JSON object only, with no extra explanation
    - Format and structure the output in a way that makes the data easy to read and understandable
    """
    # MD 1:
    # {results[0].markdown}

    # MD 2:
    # {results[1].markdown}"""
    
    for i, doc in enumerate(documents):
        prompt += f"\n\nMD {i}:\n{doc.markdown}"

    response = client.models.generate_content(
        model="gemini-2.0-flash", contents=prompt
    )
    return response.text

    # print(result1[0].extraction)
    # print(result2[0].extraction)