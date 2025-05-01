import json
import datetime
import re


def __func_clean_up(gpt_response, prompt=""):
    gpt_response = gpt_response.strip()
    ret = dict()
    for i in gpt_response.split("\n"): 
      row = i.split(". ")[1]
      thought = row.split("(because of ")[0].strip()
      evi_raw = row.split("(because of ")[1].split(")")[0].strip()
      evi_raw = re.findall(r'\d+', evi_raw)
      evi_raw = [int(i.strip()) for i in evi_raw]
      ret[thought] = evi_raw
    return ret

def __func_validate(gpt_response, prompt=""): 
    # TODO -- this sometimes generates error 
    try: 
      __func_clean_up(gpt_response, prompt)
    except Exception as e:
      print("\033[1;31mError: in run gpt_prompt_task_decomp's validate\033[0m")
      print(e)
      return False
    return True

gpt_response = """1. Klaus Mueller is deeply engaged in academic research (because of 1, 2, 4, 5, 6, 7, 10, 12, 13, 24, 25, 28)  
2. Klaus Mueller maintains a structured daily routine (because of 0, 15, 18, 19, 20, 21, 22, 23, 11, 17)  
3. Klaus Mueller is working on a research paper related to gentrification (because of 2, 4, 5, 6, 10, 12, 13, 25, 28)  
4. Klaus Mueller's workspace is frequently cluttered with research materials (because of 8, 10, 14, 25, 26, 27, 28)  
5. Klaus Mueller balances work with physical activity and relaxation (because of 0, 3:00-4:00 pm entry, 8:30-10:30 pm entry)"""
print(gpt_response)

prompt = """Input:
0. This is Klaus Mueller's plan for Monday February 13: wake up and complete the morning routine at 7:00 am, Wake up and complete morning routine from 7:00 am to 7:30 am, Go to the library at Oak Hill College from 7:45 am to 10:00 am, Write research paper at the library from 10:00 am to 12:00 pm, Have lunch at Hobbs Cafe from 12:00 pm to 1:00 pm, Continue writing research paper at the library from 1:00 pm to 3:00 pm, Long jumping at the playground from 3:00 pm to 4:00 pm, Return to the library and write research paper from 4:00 pm to 5:00 pm, Have dinner at Hobbs Cafe from 5:00 pm to 6:00 pm, Review and edit research paper at home from 6:30 pm to 8:30 pm, Relax and unwind from 8:30 pm to 10:30 pm, Prepare for bed at 10:30 pm, Sleep at 11:00 pm.
1. Klaus Mueller is taking notes on key findings
2. Klaus Mueller is reading an academic article on gentrification
3. Klaus Mueller is organizing his research notes
4. Klaus Mueller is reading an academic article on gentrification
5. Klaus Mueller is highlighting relevant quotes
6. Klaus Mueller is highlighting key points from the article
7. Klaus Mueller is cross-referencing sources
8. Klaus Mueller is organizing his research materials on the desk
9. Klaus Mueller is eating breakfast while checking his phone for updates
10. desk is in use by Klaus Mueller for summarizing the article in his notes
11. Klaus Mueller is packing his bag with research materials and laptop
12. Klaus Mueller is summarizing the article in his notes
13. Klaus Mueller is summarizing the article's main arguments
14. desk is being used for organizing research notes by Klaus Mueller
15. Klaus Mueller is waking up and stretching in bed
16. Klaus Mueller is opening his research paper document
17. Klaus Mueller is sleeping
18. Klaus Mueller is brushing his teeth
19. Klaus Mueller is drying off and getting dressed
20. bed is occupied by Klaus Mueller
21. closet is being accessed by Klaus Mueller for drying off and getting dressed
22. shower is in use by Klaus Mueller
23. Klaus Mueller is taking a quick shower
24. library table is being used by Klaus Mueller for cross-referencing sources
25. desk is occupied with an open academic article on gentrification, possibly with scattered notes or a laptop nearby
26. desk is being used with an open research paper document on it
27. desk is cluttered with research materials
28. desk is being used for summarizing an article's main arguments
29. toast and coffee


What 5 high-level insights can you infer from the above statements? (example format: insight (because of 1, 5, 3)) Remember you should end up with ")"
1."""

print(__func_validate(gpt_response, prompt))
output = __func_clean_up(gpt_response, prompt)
print(output)

ret = output
for thought, evi_raw in ret.items(): 
      evidence_node_id = [evi_raw]
      ret[thought] = evidence_node_id