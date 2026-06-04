import json
# imports json python library
from jsonschema import validate
# imports the validate function from the jsonschema package

with open("runtime_budget.policy.json", "r", encoding="utf-8") as file:
# opens `runtime_budget.policy.json` as `file` in `read` mode using UTF-8 encoding
  data = json.load(file)
# reads the JSON file contents and stores them as `data`

with open("RuntimeBudgetPolicy.schema.json", "r", encoding="utf-8") as file:
# opens `RuntimeBudgetPolicy.schema.json` as `file` in `read` mode using UTF-8 encoding
  schema = json.load(file)
# reads the JSON schema file contents and stores them as `schema`

validate(instance=data, schema=schema)
# validates the loaded policy data against the loaded schema rules

print("Data validated with schema.")
# prints confirmation in the terminal
