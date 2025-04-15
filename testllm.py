# This code loads the OpenAI API key and base URL from environment variables using the dotenv package.
# It ensures that sensitive information is not hardcoded in the script, enhancing security.

# This code loads the OpenAI API key and base URL from environment variables using the dotenv package.
# It ensures that sensitive information is not hardcoded in the script, enhancing security.

from dotenv import load_dotenv
import os
import openai # Changed import

load_dotenv()
openai_api_key = os.environ.get("INFINI_API_KEY")
openai_base_url = os.environ.get("INFINI_BASE_URL")

#https://cloud.infini-ai.com/maas/v1
print(openai_api_key)
print(openai_base_url)

# Set API key and base URL globally for older versions
openai.api_key = openai_api_key
openai.api_base = openai_base_url

# You can choose a model from the following list
# Or you can log into your Infini-AI or SiliconFlow account, and find an available model you want to use.
# model = "Qwen/QVQ-72B-Preview"
# model="llama-3.3-70b-instruct"
'''
model="deepseek-r1-distill-qwen-32b"

# Use openai.ChatCompletion.create for older versions
response = openai.ChatCompletion.create(
  model=model,
  messages=[
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "Who won the world series in 2020?"},
    {"role": "assistant", "content": "The Los Angeles Dodgers won the World Series in 2020."},
    {"role": "user", "content": "Where was it played?"}
  ]
)
#print(response)
# Accessing the response content is the same, ignore the error = response.choices[0].message.content
print(response.choices[0].message.content)
'''

model="deepseek-v3"
response = openai.ChatCompletion.create(
  model=model,
  messages=[
    {"role": "system", "content": "you are just a table filler and do not output anything else"},
    {"role": "user", "content": "Fuck me"},
  ]
)
print("\n \033[0;32mHere are the responses of deepseek-v3\033[0m")
print(response.choices[0].message.content)


gpt_parameter = {"engine": "deepseek-v3", "max_tokens": 100, 
             "temperature": 0.8, "top_p": 1, "stream": False,
             "frequency_penalty": 0, "presence_penalty": 0, "stop": ["\n"]}

response = openai.ChatCompletion.create(
	model=model,
	messages=[
		{"role": "system", "content": "If you see daily scedules, you will be an assistant that fills in daily schedules based on character information. And in that case, you should only respond with finishing schedule entries, nothing else."},
    {"role": "user", "content": """Please complete Isabella Rodriguez's schedule for Monday, February 13. Continue the hourly format shown below, filling in her activities from 8:00 AM to 11:00 PM based on her traits and daily routine.
Character Information:
Name: Isabella Rodriguez
Age: 34
Innate traits: friendly, outgoing, hospitable
Learned traits: Isabella is a cafe owner of Hobbs Cafe who loves to make people feel welcome. She is always looking for ways to make the cafe a place where people can relax and enjoy themselves.
Currently: Isabella is planning a Valentine's Day party at Hobbs Cafe on February 14th, 2023 at 5pm. She is gathering party materials and telling everyone to join from 5pm to 7pm.
Lifestyle: Isabella goes to bed around 11pm, wakes up around 6am.
Daily routine: Isabella opens Hobbs Cafe at 8am everyday, works at the counter until 8pm, then closes the cafe.

Partial schedule (continue from here):
[(ID:jQBb7L) Monday February 13 -- 00:00 AM] Activity: Isabella is sleeping
[(ID:QFqNeu) Monday February 13 -- 01:00 AM] Activity: Isabella is sleeping
[(ID:6ruJdg) Monday February 13 -- 02:00 AM] Activity: Isabella is sleeping
[(ID:gvUW7s) Monday February 13 -- 03:00 AM] Activity: Isabella is sleeping
[(ID:FMvOQS) Monday February 13 -- 04:00 AM] Activity: Isabella is sleeping
[(ID:Gz6Nig) Monday February 13 -- 05:00 AM] Activity: Isabella is sleeping
[(ID:tREB7P) Monday February 13 -- 06:00 AM] Activity: Isabella is sleeping
[(ID:oMQctV) Monday February 13 -- 07:00 AM] Activity: Isabella is sleeping
[(ID:oMQctV) Monday February 13 -- 08:00 AM] Activity: """}
	],
	temperature=gpt_parameter["temperature"],
	max_tokens=gpt_parameter["max_tokens"],
	top_p=gpt_parameter["top_p"],
	frequency_penalty=gpt_parameter["frequency_penalty"],
	presence_penalty=gpt_parameter["presence_penalty"],
	stream=gpt_parameter["stream"],
	stop=gpt_parameter["stop"],
)
print(response.choices[0].message.content)




print("\n----- Testing Embedding API -----")
print("Note: The Infini AI endpoint may not support the same embedding models as OpenAI")

# Use a simple fallback approach for embeddings when API fails
def create_fake_embedding(text, dimension=1536):
    """Create a deterministic fake embedding when the API doesn't support embeddings"""
    import numpy as np
    import hashlib
    
    # Create a deterministic seed from the text
    text_hash = hashlib.md5(text.encode()).hexdigest()
    seed = int(text_hash, 16) % (2**32)
    
    # Generate a consistent embedding vector for the same text
    np.random.seed(seed)
    embedding = np.random.uniform(-1, 1, dimension).tolist()
    
    return embedding

# First try with standard OpenAI embedding model
text = "Monday: 10-14 today I want sth to eat"
try:
    print(f"\nAttempting to get embedding with model 'bge-m3'...")
    response2_raw = openai.Embedding.create(input=[text], model="bge-m3")
    #embedding = openai.Embedding.create(
    #        input=[text], model="deepseek-v3")['data'][0]['embedding']
    #print(f"Embedding dimension: {len(embedding)}")
    
    # Try to extract embedding 
    if hasattr(response2_raw, 'data') and len(response2_raw.data) > 0:
        embedding = response2_raw.data[0].embedding
    elif isinstance(response2_raw, dict) and 'data' in response2_raw:
        embedding = response2_raw['data'][0]['embedding']
    else:
        print("Unexpected response format, trying fallback...")
        raise ValueError("Unexpected response format")
        
    print("Successfully got embedding from API!")
    print(f"Embedding dimension: {len(embedding)}")
    print(f"First few values: {embedding[:5]}")
    
except Exception as e:
    print(f"API embedding failed: {e}")
    print("Using local fallback embedding generation instead...")
    
    # Create a fake embedding
    embedding = create_fake_embedding(text)
    print(f"Created fallback embedding with dimension: {len(embedding)}")
    print(f"First few values: {embedding[:5]}")
    
print("\nEmbedding generation complete!")

'''
# https://api.siliconflow.cn/v1
from dotenv import load_dotenv
import os
load_dotenv()
openai_api_key = os.environ.get("SF_API_KEY")
openai_base_url = os.environ.get("SF_BASE_URL")

print(openai_base_url)  

prompt = '帮我创建一个<Genshin Impact>角色，你需要仿照该游戏的其他角色进行设计，要求角色设定以及技能简介'
openai.api_key = openai_api_key
openai.api_base = openai_base_url

# You can choose a model from the following list
# Or you can log into your Infini-AI or SiliconFlow account, and find an available model you want to use.
model="deepseek-ai/DeepSeek-V3"

response = openai.ChatCompletion.create(
  model=model,
  messages=[
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": prompt},
  ]
)
#print(response)
print(response.choices[0].message.content)
'''