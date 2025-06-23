import re
import json

def jsonFormat(raw_response: str) -> dict:

    cleaned = re.sub(r"^[`']{3}json|[`']{3}$", "", raw_response.strip(), flags=re.IGNORECASE | re.MULTILINE).strip()

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as e:
        print("Failed to parse JSON:", e)
        return {}