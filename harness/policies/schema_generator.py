import json
# imports json python library
from runtime_budget import RuntimeBudgetPolicy
# imports the pydantic class from the python model file

schema = RuntimeBudgetPolicy.model_json_schema()
# requests json schema generation from the model class imported

with open("RuntimeBudgetPolicy.schema.json", "w", encoding="utf-8") as file:
# open/creates `RuntimeBudgetPolicy.schema.json` as a `file` to `write` with utf-8 encoding
    json.dump(schema, file, indent=2)
# writes the requested schema from the imported pydantic class as json

print("Schema written.")
# prints in the terminal
