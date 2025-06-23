from model.extract import extract
from model.combine import combine
from model.advise import advise

files = ["doc/Examination.pdf", "doc/Nutrition.pdf"]

documents = extract(files)
combined_data = combine(documents)
print(combined_data)
advice = advise(combined_data)
print(advice)
