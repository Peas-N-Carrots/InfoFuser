from agentic_doc.parse import parse

# Calls a document extraction API to parse the contents of multiple .pdf or image medical documents.
# input: Array of file paths to .pdf or image files.
# output: Array of parsed documents to be passed into the combine.py combine function.

def extract(files):
    results = []
    
    for file in files:
        results.append(parse(file))
    
    return results