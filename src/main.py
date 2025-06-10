from agentic_doc.parse import parse
from google import genai



# Parse a local file
result1 = parse("doc/Examination.pdf")
result2 = parse("doc/Nutrition.pdf")
# print(result[0].markdown)  # Get the extracted data as markdown
# print(result[0].chunks)  # Get the extracted data as structured chunks of content



client = genai.Client()

prompt = f"""You are an intelligent markdown (MD) data assistant.

Merge the following two MD objects. Follow these rules:
- Combine related fields (e.g. first_name + last_name vs full_name)
- Avoid redundant or duplicate data
- Preserve all unique fields
- Return a single valid JSON object only, with no extra explanation

MD 1:
{result1[0].markdown}

MD 2:
{result2[0].markdown}"""

response = client.models.generate_content(
    model="gemini-2.0-flash", contents=prompt
)
print(response.text)


# def main():
#     print("Hello from main!")

# if __name__ == "__main__":
#     main()