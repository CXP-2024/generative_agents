import json
import datetime
import re


print(f"\033[9;35m--- perceive, retrieve, plan and reflect --\033[0m")

def __func_clean_up(gpt_response, prompt=""):
    # if "~" in the 7th ot the 8th char, remove the first 7 chars
    gpt_response = gpt_response.strip()
    if gpt_response[6] == "~" or gpt_response[7] == "~":
        gpt_response = gpt_response[8:]
    new_schedule = prompt + " " + gpt_response.strip()
    new_schedule = new_schedule.split("The revised schedule:")[-1].strip()
    new_schedule = new_schedule.split("\n")

    ret_temp = []
    for i in new_schedule: 
      ret_temp += [i.split(" -- ")]

    ret = []
    for time_str, action in ret_temp:
      start_time = time_str.split(" ~ ")[0].strip()
      end_time = time_str.split(" ~ ")[1].strip()
      delta = datetime.datetime.strptime(end_time, "%H:%M") - datetime.datetime.strptime(start_time, "%H:%M")
      delta_min = int(delta.total_seconds()/60)
      if delta_min < 0: delta_min = 0
      ret += [[action, delta_min]]

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

gpt_response = """02:25 -- still attempting measured long jumps  
02:25 ~ 02:35 -- reviewing jump recordings with Arthur  
02:35 ~ 02:45 -- doing cool-down stretches  
02:45 ~ 02:55 -- packing up her training gear  
02:55 ~ 03:00 -- walking back home with Arthur """
print(gpt_response)

prompt = """Task: revise the schedule

Example:
Here was Maria Helon's originally planned schedule from 00:00 AM to 03:00 AM. 
00:00 ~ 00:10 -- warming up with light stretches
00:10 ~ 00:20 -- jogging around the track to get her heart rate up
00:20 ~ 00:35 -- practicing short approach jumps with Arthur
00:35 ~ 00:45 -- adjusting her technique based on Arthur's feedback
00:45 ~ 00:55 -- attempting full approach jumps
00:55 ~ 01:00 -- cooling down with a slow walk and hydration
01:00 ~ 01:10 -- warming up with light stretches
01:10 ~ 01:25 -- practicing her run-up technique
01:25 ~ 01:45 -- working on her takeoff form with Arthur's feedback
01:45 ~ 02:10 -- attempting full long jumps while Arthur records
02:10 ~ 02:25 -- reviewing the recorded jumps with Arthur
02:25 ~ 02:45 -- adjusting her technique based on feedback
02:45 ~ 02:55 -- doing a final set of jumps
02:55 ~ 03:00 -- cooling down with light stretches

However, Maria Helon unexpectedly spent 13 minutes attempting full approach jumps (conversing about Maria Helon asked Sam for tips on improving her full approach jumps, and Sam demonstrated her technique, emphasizing knee drive and arm control, leading to Maria practicing with her guidance and showing improvement, with Isabella offering to train together again in the future.). Based on this unexpected event, please revise Maria Helon's schedule from 00:00 AM to 03:00 AM (ensuring it finishes by 03:00 AM).

Only modify the schedule between 00:00 AM and 03:00 AM. Any activities before 00:00 AM or after 03:00 AM should remain unchanged so you need't to include them in the output.

The result schedule:
00:00 ~ 00:10 -- warming up with light stretches
00:10 ~ 00:20 -- jogging around the track to get her heart rate up
00:20 ~ 00:35 -- practicing short approach jumps with Arthur
00:35 ~ 00:45 -- adjusting her technique based on Arthur's feedback
00:45 ~ 00:50 -- attempting full approach jumps
00:50 ~ 01:03 -- attempting full approach jumps (conversing about Maria Helon asked Sam for tips on improving her full approach jumps, and Sam demonstrated his technique, emphasizing knee drive and arm control, leading to Maria practicing with his guidance and showing improvement, with Arthur offering to train together again in the future.)
01:03 ~ 01:10 -- cooling down with a slow walk and hydration
01:10 ~ 01:25 -- practicing her run-up technique
01:25 ~ 01:45 -- working on her takeoff form with Arthur's feedback
01:45 ~ 02:00 -- attempting full long jumps while Arthur records
02:00 ~ 02:10 -- STILL attempting full long jumps while Arthur records
02:10 ~ 02:25 -- reviewing the recorded jumps with Arthur
02:25 ~ 02:45 -- adjusting her technique based on feedback
02:45 ~ 02:55 -- doing a final set of jumps
02:55 ~ 03:00 -- cooling down with light stretches



YOUR TASK:
Here was Maria Lopez's originally planned schedule from 01:00 AM to 03:00 AM. 
01:00 ~ 01:10 -- warming up with stretching exercises
01:10 ~ 01:30 -- practicing her long jump technique
01:30 ~ 01:35 -- taking a short water break
01:35 ~ 01:50 -- discussing form adjustments with Arthur
01:50 ~ 02:05 -- doing sprint drills to improve takeoff speed
02:05 ~ 02:25 -- attempting measured long jumps
02:25 ~ 02:35 -- reviewing jump recordings with Arthur
02:35 ~ 02:45 -- doing cool-down stretches
02:45 ~ 02:55 -- packing up her training gear
02:55 ~ 03:00 -- walking back home with Arthur



However, Maria Lopez unexpectedly spent 13 minutes attempting measured long jumps (conversing about Maria Lopez sought Arthur Burton's advice on improving her long jump technique, particularly her takeoff height, and Arthur provided tips on driving her knee up, ensuring explosive last two steps, and swinging her arms higher and faster, with Maria practicing jumps under Arthur's observation and feedback.). Based on this unexpected event, please revise Maria Lopez's schedule from 01:00 AM to 03:00 AM (ensuring it finishes by 03:00 AM).

Only modify the schedule between 01:00 AM and 03:00 AM. Any activities before 01:00 AM or after 03:00 AM should remain unchanged so you need't to include them in the output.

IMPORTANT FORMATTING INSTRUCTIONS:
- Format each time block as "START_TIME ~ END_TIME" (e.g., "08:00 ~ 09:30")
- Your first time block must start exactly at the specified start time
- Your last time block must end exactly at the specified end time
- Break activities that cross hour boundaries into separate entries
- Ensure time increments are continuous and preferably in 5-minute intervals
- When an activity spans from one hour to the next, split it at the hour boundary and prefix the continuation with "still"
- For example, if an activity runs from "09:45 ~ 10:15", split it into:
	"09:45 ~ 10:00 -- [activity name]"
	"10:00 ~ 10:15 -- still [activity name]"
- This rule applies to ALL activities that span across hour boundaries (e.g., XX:55 to YY:08)
- Another example: For "16:55 ~ 17:08 -- walking in the park", output:
	"16:55 ~ 17:00 -- walking in the park"
	"17:00 ~ 17:08 -- still walking in the park"

The revised schedule:
01:00 ~ 01:10 -- warming up with stretching exercises
01:10 ~ 01:30 -- practicing her long jump technique
01:30 ~ 01:35 -- taking a short water break
01:35 ~ 01:50 -- discussing form adjustments with Arthur
01:50 ~ 02:05 -- doing sprint drills to improve takeoff speed
02:05 ~ 02:10 -- attempting measured long jumps
02:10 ~ 02:23 -- attempting measured long jumps (conversing about Maria Lopez sought Arthur Burton's advice on improving her long jump technique, particularly her takeoff height, and Arthur provided tips on driving her knee up, ensuring explosive last two steps, and swinging her arms higher and faster, with Maria practicing jumps under Arthur's observation and feedback.)
02:23 ~"""

print(__func_validate(gpt_response, prompt))
output = __func_clean_up(gpt_response, prompt)
print(output)

ret = output
for thought, evi_raw in ret.items(): 
      evidence_node_id = [evi_raw]
      ret[thought] = evidence_node_id