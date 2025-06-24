# InfoFuser
This project is a demo to extract and combine the contents of multiple medical documents into a complete "patient profile superset." Additionally, it allows gives the user personalized health/fitness advice based on their medical history

The project uses LandingAI Agentic Document Extraction API along with the Google Gemini API to extract documents, merge them on similar fields, and analize the combined set of data. The frontend is made with Streamlit.

The main problem I wanted to solve with this project was organizing the largely unstructured and unstandardized format of data in the medical and health industries. A nutritionist's and doctor's forms may both have your name, age, height, and weight on them, but a super set should only contain this data one time per field. AI models currently seem like the most promising solution to this problem as it would be much harder for an algoritrm to reason whether fields are considered the same. Take this example ->
- Signature: _John Doe_
- Last Name: _Doe_
- First Name: _John_
These fields should be condensed into one field, Name: John Doe. However, it is imposible to use hard coded specific field extraction to predict any field that any person's personal health record may contain.

Hopefully someone finds this concept somewhat useful or interesting. If so, feel free to reach out on LinkedIn: https://www.linkedin.com/in/joe-maloney-ncsu/

Full disclosure, Claude AI was used to generate the majority of the frontend script while the backend scripts were alternatively fully hand-coded.
