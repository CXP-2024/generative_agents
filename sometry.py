import json

curr_gpt_response = """
{"output": "being slept in"}
"""

# convert the dictionary to a JSON string
#curr_gpt_response = json.dumps(curr_gpt_response)

curr_gpt_response = json.loads(curr_gpt_response)["output"]

print(curr_gpt_response)