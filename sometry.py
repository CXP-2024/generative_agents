import json
import datetime


def __func_clean_up(gpt_response, prompt=""):
        if "[" in gpt_response:
            cr = gpt_response.split("[")[-1].strip()
        if "]" in cr:
            cr = cr.split("]")[0].strip()
        if cr == "yes" or cr == "no":
            return cr
        print("\033[1;31mError: in run gpt_prompt_decide_to_talk's clean_up: the cleaned gpt:", cr, "\033[0m")
        return False

def __func_validate(gpt_response, prompt=""): 
    try: 
      if __func_clean_up(gpt_response, prompt) == "yes" or __func_clean_up(gpt_response, prompt) == "no":
        return True
      print("\033[1;31mError: in run gpt_prompt_decide_to_talk's validate: the cleaned gpt_response: ", __func_clean_up(gpt_response, prompt), "\033[0m")
      return False     
    except Exception as e:
      print("\033[1;31mError: in run gpt_prompt_decide_to_talk's validate\033[0m")
      print(e)
      return False 

gpt_response = """ Context: [Klaus Mueller was saving and backing up his research files. Right now, it is February 13, 2023, 11:00:00 AM. Maria Lopez and Klaus Mueller last chatted at about . Maria Lopez is on the way to walking to the physics lecture hall. Klaus Mueller is on the way to saving and backing up his research files.]  
Question: [Would Maria Lopez initiate a conversation with Klaus Mueller?]  
Reasoning: [Maria Lopez is walking to a lecture hall, likely focused on getting there on time. Klaus Mueller is occupied with backing up files, which requires concentration. There is no indication of urgency or a prior plan to talk. Both are engaged in separate tasks.]  
Answer in "yes" or "no": [no] """
print(gpt_response)

prompt = """Here was Maria Lopez's originally planned schedule from 10:00 AM to 12:00 PM. 
10:00 ~ 10:10 -- studying physics at Hobbs Cafe (walking to Hobbs Cafe)
10:10 ~ 10:15 -- studying physics at Hobbs Cafe (ordering a coffee and finding a seat)
10:15 ~ 10:35 -- studying physics at Hobbs Cafe (reviewing her physics notes)
10:35 ~ 11:05 -- studying physics at Hobbs Cafe (working on practice problems)
11:05 ~ 11:10 -- studying physics at Hobbs Cafe (taking a short break to stretch)
11:10 ~ 11:35 -- studying physics at Hobbs Cafe (reading the next chapter in her textbook)
11:35 ~ 11:50 -- studying physics at Hobbs Cafe (summarizing key concepts)
11:50 ~ 11:55 -- studying physics at Hobbs Cafe (packing up her study materials)
11:55 ~ 12:00 -- studying physics at Hobbs Cafe (checking her phone for messages)


But Maria Lopez unexpectedly ended up studying physics at Hobbs Cafe (conversing about Maria Lopez and Klaus Mueller discussing their academic work, leisure activities, and potential collaboration on a Twitch stream about sociology in gaming communities, culminating in plans for Klaus to join Maria's stream next Thursday at 8 pm.) for 16 minutes. Revise Maria Lopez's schedule from 10:00 AM to 12:00 PM accordingly (it has to end by 12:00 PM). 
The revised schedule:
10:00 ~ 10:10 -- studying physics at Hobbs Cafe (walking to Hobbs Cafe)
10:10 ~ 10:15 -- studying physics at Hobbs Cafe (ordering a coffee and finding a seat)
10:15 ~ 10:35 -- studying physics at Hobbs Cafe (reviewing her physics notes)
10:35 ~ 11:05 -- studying physics at Hobbs Cafe (working on practice problems)
11:05 ~ 11:05 -- studying physics at Hobbs Cafe (on the way to taking a short break to stretch)
11:05 ~ 11:21 -- studying physics at Hobbs Cafe (conversing about Maria Lopez and Klaus Mueller discussing their academic work, leisure activities, and potential collaboration on a Twitch stream about sociology in gaming communities, culminating in plans for Klaus to join Maria's stream next Thursday at 8 pm.)
11:21 ~"""

print(__func_validate(gpt_response, prompt))
gpt_response = __func_clean_up(gpt_response, prompt)
print(gpt_response)