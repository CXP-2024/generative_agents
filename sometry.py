import json

def __func_clean_up(gpt_response, prompt=""):
    # if is a list, just return; else raise a ValueError
    if isinstance(gpt_response, list):
        return gpt_response
    else:
        raise ValueError("\033[1;31mOutput is not a list\033[0m")

gpt_response = """  {
  "output": [
    "What is Isabella Rodriguez's morning routine on February 13?",
    "What activities does Isabella Rodriguez perform at the cafe?",
    "How does Isabella Rodriguez prepare for the Valentine's Day event at the cafe?"
  ]
}"""
gpt_response = json.loads(gpt_response)["output"]
print(gpt_response)

gpt_response = __func_clean_up(gpt_response)
print(gpt_response)