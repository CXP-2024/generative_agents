"""
Author: Joon Sung Park (joonspk@stanford.edu)

File: plan.py
Description: This defines the "Plan" module for generative agents. 
"""
import datetime
import math
import random 
import sys
import time
sys.path.append('../../')

from global_methods import *
from persona.prompt_template.run_gpt_prompt import *
from persona.cognitive_modules.retrieve import *
from persona.cognitive_modules.converse import *
from persona.cognitive_modules.utils_func import *

##############################################################################
# CHAPTER 2: Generate
##############################################################################

def generate_wake_up_hour(persona):
  """
  Generates the time when the persona wakes up. This becomes an integral part
  of our process for generating the persona's daily plan.
  
  Persona state: identity stable set, lifestyle, first_name

  INPUT: 
    persona: The Persona class instance 
  OUTPUT: 
    an integer signifying the persona's wake up hour
  EXAMPLE OUTPUT: 
    8
  """
  if debug: print ("GNS FUNCTION: <generate_wake_up_hour>")
  return run_gpt_prompt_wake_up_hour(persona)


def generate_first_daily_plan(persona, wake_up_hour): 
  """
  Generates the daily plan for the persona. 
  Basically the long term planning that spans a day. Returns a list of actions
  that the persona will take today. Usually comes in the following form: 
  'wake up and complete the morning routine at 6:00 am', 
  'eat breakfast at 7:00 am',.. 
  Note that the actions come without a period. 

  Persona state: identity stable set, lifestyle, cur_data_str, first_name

  INPUT: 
    persona: The Persona class instance 
    wake_up_hour: an integer that indicates when the hour the persona wakes up 
                  (e.g., 8)
  OUTPUT: 
    a list of daily actions in broad strokes.
  EXAMPLE OUTPUT: 
    ['wake up and complete the morning routine at 6:00 am', 
     'have breakfast and brush teeth at 6:30 am',
     'work on painting project from 8:00 am to 12:00 pm', 
     'have lunch at 12:00 pm', 
     'take a break and watch TV from 2:00 pm to 4:00 pm', 
     'work on painting project from 4:00 pm to 6:00 pm', 
     'have dinner at 6:00 pm', 'watch TV from 7:00 pm to 8:00 pm']
  """
  if debug: print ("GNS FUNCTION: <generate_first_daily_plan>")
  return run_gpt_prompt_daily_plan(persona, wake_up_hour)[0]


def generate_hourly_schedule(persona, wake_up_hour, sleep_hour): 
  """
  Based on the daily req, creates an hourly schedule -- one hour at a time. 
  The form of the action for each of the hour is something like below: 
  "sleeping in her bed"
  
  The output is basically meant to finish the phrase, "x is..."

  Persona state: identity stable set, daily_plan

  INPUT: 
    persona: The Persona class instance 
    persona: Integer form of the wake up hour for the persona.  
  OUTPUT: 
    a list of activities and their duration in minutes: 
  EXAMPLE OUTPUT: 
    [['sleeping', 360], ['waking up and starting her morning routine', 60], 
     ['eating breakfast', 60],..
  """
  if debug: print ("GNS FUNCTION: <generate_hourly_schedule>")
  if sleep_hour > wake_up_hour:
    sleep_hour -= 24
  hour_str = ["00:00 AM", "01:00 AM", "02:00 AM", "03:00 AM", "04:00 AM", 
              "05:00 AM", "06:00 AM", "07:00 AM", "08:00 AM", "09:00 AM", 
              "10:00 AM", "11:00 AM", "12:00 PM", "01:00 PM", "02:00 PM", 
              "03:00 PM", "04:00 PM", "05:00 PM", "06:00 PM", "07:00 PM",
              "08:00 PM", "09:00 PM", "10:00 PM", "11:00 PM"]
  n_m1_activity = []
  diversity_repeat_count = 3
  for i in range(diversity_repeat_count): 
    n_m1_activity_set = set(n_m1_activity)
    if len(n_m1_activity_set) < 5: 
      n_m1_activity = []
      for count, curr_hour_str in enumerate(hour_str):
        if sleep_hour <= count < wake_up_hour: 
          n_m1_activity += ["sleeping"]
        else: 
          n_m1_activity += [run_gpt_prompt_generate_hourly_schedule(
                          persona, curr_hour_str, n_m1_activity, hour_str)[0]]
  
  # Step 1. Compressing the hourly schedule to the following format: 
  # The integer indicates the number of hours. They should add up to 24. 
  # [['sleeping', 6], ['waking up and starting her morning routine', 1], 
  # ['eating breakfast', 1], ['getting ready for the day', 1], 
  # ['working on her painting', 2], ['taking a break', 1], 
  # ['having lunch', 1], ['working on her painting', 3], 
  # ['taking a break', 2], ['working on her painting', 2], 
  # ['relaxing and watching TV', 1], ['going to bed', 1], ['sleeping', 2]]
  _n_m1_hourly_compressed = []
  prev = None 
  prev_count = 0
  for i in n_m1_activity: 
    if i != prev:
      prev_count = 1 
      _n_m1_hourly_compressed += [[i, prev_count]]
      prev = i
    else: 
      if _n_m1_hourly_compressed: 
        _n_m1_hourly_compressed[-1][1] += 1

  # Step 2. Expand to min scale (from hour scale)
  # [['sleeping', 360], ['waking up and starting her morning routine', 60], 
  # ['eating breakfast', 60],..
  n_m1_hourly_compressed = []
  for task, duration in _n_m1_hourly_compressed: 
    n_m1_hourly_compressed += [[task, duration*60]]

  return n_m1_hourly_compressed

def generate_task_decomp(persona, task, duration): 

  """
  A few shot decomposition of a task given the task description 

  Persona state: identity stable set, curr_date_str, first_name

  INPUT: 
    persona: The Persona class instance 
    task: the description of the task at hand in str form
          (e.g., "waking up and starting her morning routine")
    duration: an integer that indicates the number of minutes this task is 
              meant to last (e.g., 60)
  OUTPUT: 
    a list of list where the inner list contains the decomposed task 
    description and the number of minutes the task is supposed to last. 
  EXAMPLE OUTPUT: 
    [['going to the bathroom', 5], ['getting dressed', 5], 
     ['eating breakfast', 15], ['checking her email', 5], 
     ['getting her supplies ready for the day', 15], 
     ['starting to work on her painting', 15]] 

  """
  if debug: print ("GNS FUNCTION: <generate_task_decomp>")
  return run_gpt_prompt_task_decomp(persona, task, duration)[0]


def generate_action_sector(act_desp, persona, maze): 
  """TODO 
  Given the persona and the task description, choose the action_sector. 

  Persona state: identity stable set, n-1 day schedule, daily plan

  INPUT: 
    act_desp: description of the new action (e.g., "sleeping")
    persona: The Persona class instance 
  OUTPUT: 
    action_arena (e.g., "bedroom 2")
  EXAMPLE OUTPUT: 
    "bedroom 2"
  """
  if debug: print ("GNS FUNCTION: <generate_action_sector>")
  return run_gpt_prompt_action_sector(act_desp, persona, maze)[0]


def generate_action_arena(act_desp, persona, maze, act_world, act_sector): 
  """TODO 
  Given the persona and the task description, choose the action_arena. 

  Persona state: identity stable set, n-1 day schedule, daily plan

  INPUT: 
    act_desp: description of the new action (e.g., "sleeping")
    persona: The Persona class instance 
  OUTPUT: 
    action_arena (e.g., "bedroom 2")
  EXAMPLE OUTPUT: 
    "bedroom 2"
  """
  if debug: print ("GNS FUNCTION: <generate_action_arena>")
  return run_gpt_prompt_action_arena(act_desp, persona, maze, act_world, act_sector)[0]


def generate_action_game_object(act_desp, act_address, persona, maze):
  """TODO
  Given the action description and the act address (the address where
  we expect the action to task place), choose one of the game objects. 

  Persona state: identity stable set, n-1 day schedule, daily plan

  INPUT: 
    act_desp: the description of the action (e.g., "sleeping")
    act_address: the arena where the action will take place: 
               (e.g., "dolores double studio:double studio:bedroom 2")
    persona: The Persona class instance 
  OUTPUT: 
    act_game_object: 
  EXAMPLE OUTPUT: 
    "bed"
  """
  if debug: print ("GNS FUNCTION: <generate_action_game_object>")
  if not persona.s_mem.get_str_accessible_arena_game_objects(act_address): 
    return "<random>"
  return run_gpt_prompt_action_game_object(act_desp, persona, maze, act_address)[0]


def generate_action_pronunciatio(act_desp, persona): 
  """TODO 
  Given an action description, creates an emoji string description via a few
  shot prompt. 

  Does not really need any information from persona. 

  INPUT: 
    act_desp: the description of the action (e.g., "sleeping")
    persona: The Persona class instance
  OUTPUT: 
    a string of emoji that translates action description.
  EXAMPLE OUTPUT: 
    "🧈🍞"
  """
  if debug: print ("GNS FUNCTION: <generate_action_pronunciatio>")
  try: 
    x = run_gpt_prompt_pronunciatio(act_desp, persona)[0]
  except: 
    x = "🙂"

  if not x: 
    return "🙂"
  return x


def generate_action_event_triple(act_desp, persona): 
  """TODO 

  INPUT: 
    act_desp: the description of the action (e.g., "sleeping")
    persona: The Persona class instance
  OUTPUT: 
    a string of emoji that translates action description.
  EXAMPLE OUTPUT: 
    "🧈🍞"
  """
  if debug: print ("GNS FUNCTION: <generate_action_event_triple>")
  return run_gpt_prompt_event_triple(act_desp, persona)[0]


def generate_act_obj_desc(act_game_object, act_desp, persona): 
  if debug: print ("GNS FUNCTION: <generate_act_obj_desc>")
  result = run_gpt_prompt_act_obj_desc(act_game_object, act_desp, persona)
  if result is None:
    return f"\033[0;31m warning!!!!! the result of gpt is none {act_game_object} is idle \033[0m"  # Default value when result is None
  return result[0]


def generate_act_obj_event_triple(act_game_object, act_obj_desc, persona): 
  if debug: print ("GNS FUNCTION: <generate_act_obj_event_triple>")
  return run_gpt_prompt_act_obj_event_triple(act_game_object, act_obj_desc, persona)[0]


def generate_convo(maze, init_persona, target_persona): 
  # Synchronize times by using the latest time between both agents
  # This will happen since person are move sequentially, and the current time of persona is updated only when they move.
  if init_persona.scratch.curr_time > target_persona.scratch.curr_time:
        target_persona.scratch.curr_time = init_persona.scratch.curr_time.replace()
  elif target_persona.scratch.curr_time > init_persona.scratch.curr_time:
        init_persona.scratch.curr_time = target_persona.scratch.curr_time.replace()
  curr_loc = maze.access_tile(init_persona.scratch.curr_tile)

  # convo = run_gpt_prompt_create_conversation(init_persona, target_persona, curr_loc)[0]
  # convo = agent_chat_v1(maze, init_persona, target_persona)
  convo = agent_chat_v2(maze, init_persona, target_persona)
  all_utt = ""

  for row in convo: 
    speaker = row[0]
    utt = row[1]
    all_utt += f"{speaker}: {utt}\n"

  convo_length = math.ceil(int(len(all_utt)/8) / 30) # this will be the time of the conversation
  if convo_length <= 5:
    print("\033[1;9;33m warning!!!!! the length of conversation is too short and change to 6min\033[0m")
    convo_length = 6

  # show current time:
  print("\033[0;33m-----in generate_convo----- init_persona", init_persona.name, "current time:", init_persona.scratch.curr_time.strftime('%A %B %d %H:%M'), "\033[0m")
  print("\033[0;33m-----in generate_convo----- target_persona", target_persona.name, "current time:", target_persona.scratch.curr_time.strftime('%A %B %d %H:%M'), "\033[0m")
	# If current time + convo_length 's corresponding plan event is "sleeping", change the convo_length to sleeping event start time - current time
  # 计算当前时间（从午夜0:00开始的分钟数）
  current_time_mins = int(init_persona.scratch.curr_time.hour * 60 + init_persona.scratch.curr_time.minute)

  # 检查是否会延续到睡眠时间，并在需要时调整对话长度
  if convo_length > 0:
    elapsed_time = 0
    for i, (act, dur) in enumerate(init_persona.scratch.f_daily_schedule):
        if elapsed_time <= current_time_mins < elapsed_time + dur:
            # 检查当前时间+对话长度是否会落在未来的"sleeping"事件中
            remaining_time = elapsed_time + dur - current_time_mins
            check_time = elapsed_time + dur
            
            # 如果对话会持续超过当前事件
            if convo_length > remaining_time:
                # 检查后续事件
                for j in range(i+1, len(init_persona.scratch.f_daily_schedule)):
                    next_act, next_dur = init_persona.scratch.f_daily_schedule[j]
                    if "sleeping" in next_act.lower() and current_time_mins + convo_length >= check_time:
                        # 调整对话长度到睡眠开始前
                        convo_length = check_time - current_time_mins
                        print(f"\033[0;33m---Adjusted conversation length to {convo_length} minutes to avoid extending into sleep time--\033[0m")
                        break
                    check_time += next_dur
            break
        elapsed_time += dur
  # for target_persone, also check the schedule
  # 检查是否会延续到睡眠时间，并在需要时调整对话长度
  if convo_length > 0:
    elapsed_time = 0
    for i, (act, dur) in enumerate(target_persona.scratch.f_daily_schedule):
        if elapsed_time <= current_time_mins < elapsed_time + dur:
            # 检查当前时间+对话长度是否会落在未来的"sleeping"事件中
            remaining_time = elapsed_time + dur - current_time_mins
            check_time = elapsed_time + dur
            
            # 如果对话会持续超过当前事件
            if convo_length > remaining_time:
                # 检查后续事件
                for j in range(i+1, len(target_persona.scratch.f_daily_schedule)):
                    next_act, next_dur = target_persona.scratch.f_daily_schedule[j]
                    if "sleeping" in next_act.lower() and current_time_mins + convo_length >= check_time:
                        # 调整对话长度到睡眠开始前
                        convo_length = check_time - current_time_mins
                        print(f"\033[0;33m---Adjusted conversation length to {convo_length} minutes to avoid extending into sleep time--\033[0m")
                        break
                    check_time += next_dur
            break
        elapsed_time += dur
  

  if debug: print ("GNS FUNCTION: <generate_convo>")
  return convo, convo_length


def generate_convo_summary(persona, convo): 
  convo_summary = run_gpt_prompt_summarize_conversation(persona, convo)[0]
  return convo_summary


def generate_decide_to_talk(init_persona, target_persona, retrieved): 
  x =run_gpt_prompt_decide_to_talk(init_persona, target_persona, retrieved)[0]
  if debug: print ("GNS FUNCTION: <generate_decide_to_talk>")

  if x == "yes": 
    return True
  else: 
    return False


def generate_decide_to_react(init_persona, target_persona, retrieved): 
  if debug: print ("GNS FUNCTION: <generate_decide_to_react>")
  return run_gpt_prompt_decide_to_react(init_persona, target_persona, retrieved)[0]


def generate_new_decomp_schedule(persona, inserted_act, inserted_act_dur,  start_hour, end_hour): 
  # Step 1: Setting up the core variables for the function. 
  # <p> is the persona whose schedule we are editing right now. 
  p = persona
  # <today_min_pass> indicates the number of minutes that have passed today. 
  today_min_pass = (int(p.scratch.curr_time.hour) * 60 
                    + int(p.scratch.curr_time.minute)) # remove + 1
  
  # Step 2: We need to create <main_act_dur> and <truncated_act_dur>. 
  # These are basically a sub-component of <f_daily_schedule> of the persona,
  # but focusing on the current decomposition. 
  # Here is an example for <main_act_dur>: 
  # ['wakes up and completes her morning routine (wakes up at 6am)', 5]
  # ['wakes up and completes her morning routine (wakes up at 6am)', 5]
  # ['wakes up and completes her morning routine (uses the restroom)', 5]
  # ['wakes up and completes her morning routine (washes her ...)', 10]
  # ['wakes up and completes her morning routine (makes her bed)', 5]
  # ['wakes up and completes her morning routine (eats breakfast)', 15]
  # ['wakes up and completes her morning routine (gets dressed)', 10]
  # ['wakes up and completes her morning routine (leaves her ...)', 5]
  # ['wakes up and completes her morning routine (starts her ...)', 5]
  # ['preparing for her day (waking up at 6am)', 5]
  # ['preparing for her day (making her bed)', 5]
  # ['preparing for her day (taking a shower)', 15]
  # ['preparing for her day (getting dressed)', 5]
  # ['preparing for her day (eating breakfast)', 10]
  # ['preparing for her day (brushing her teeth)', 5]
  # ['preparing for her day (making coffee)', 5]
  # ['preparing for her day (checking her email)', 5]
  # ['preparing for her day (starting to work on her painting)', 5]
  # 
  # And <truncated_act_dur> concerns only until where an event happens. 
  # ['wakes up and completes her morning routine (wakes up at 6am)', 5]
  # ['wakes up and completes her morning routine (wakes up at 6am)', 2]
  main_act_dur = []
  truncated_act_dur = []
  dur_sum = 0 # duration sum
  count = 0 # enumerate count
  truncated_fin = False 

  print(f"DEBUG::: {persona.scratch.name}, Current time: {persona.scratch.curr_time}")

  # Initialize tracking variables
  current_activity_found = False
  start_time = 0  # Start time of current activity

  # First pass: find all activities in the specified time range
  for act, dur in p.scratch.f_daily_schedule:
    activity_start = dur_sum
    activity_end = dur_sum + dur
    dur_sum = activity_end
    
    # Check if activity falls within our target time window
    if (activity_end > start_hour * 60) and (activity_start < end_hour * 60): # shouldn't have "="
        main_act_dur.append([act, dur])
        
        # Case 1: Activity is completely in the past
        if activity_end <= today_min_pass:
            truncated_act_dur.append([act, dur])
            print(f"DEBUG::: PAST ACTIVITY - start: {activity_start}, end: {activity_end}, " 
                  f"today_min_pass: {today_min_pass}, activity: {act}, duration: {dur}")
            
        # Case 2: Current ongoing activity (spans the current time)
        elif activity_start <= today_min_pass and activity_end > today_min_pass:
            if not current_activity_found:  # Ensure we only add the current activity once
                elapsed = today_min_pass - activity_start
                truncated_act_dur.append([act, elapsed])
                current_activity_found = True
                print(f"DEBUG::: CURRENT ACTIVITY - start: {activity_start}, end: {activity_end}, "
                      f"elapsed: {elapsed}, activity: {act}, original duration: {dur}")
            
        # For activities in the future, we don't include them in truncated_act_dur

  persona_name = persona.name 
  main_act_dur = main_act_dur

  original_text = truncated_act_dur[-1][0]
  if "(" in original_text:
    base_part = original_text.split("(")[0].strip()
    inside_part = original_text.split("(")[-1].rstrip(")")
    truncated_act_dur[-1][0] = f"{base_part} (on the way to {inside_part})"
  else:
    # Handle case with no parentheses
    truncated_act_dur[-1][0] = f"{original_text}"

  if "(" in truncated_act_dur[-1][0]: 
    inserted_act = truncated_act_dur[-1][0].split("(")[0].strip() + " (" + inserted_act + ")"
  else:
    inserted_act = truncated_act_dur[-1][0] + " (" + inserted_act + ")"

  # To do inserted_act_dur+1 below is an important decision but I'm not sure
  # if I understand the full extent of its implications. Might want to 
  # revisit. 
  truncated_act_dur += [[inserted_act, inserted_act_dur]]
  start_time_hour = (datetime.datetime(2022, 10, 31, 0, 0) 
                   + datetime.timedelta(hours=start_hour))
  end_time_hour = (datetime.datetime(2022, 10, 31, 0, 0) 
                   + datetime.timedelta(hours=end_hour))
  print ("DEBUG:::--in generate_new_decom_schedule---- obtain start_time_hour and end_time_hour ", start_time_hour, end_time_hour)
	# show main_act_dur and truncated_act_dur
  print("\033[0;33m-----in generate_new_decomp_schedule-----", persona.name, "main_act_dur:\033[0m")
  for i in main_act_dur:
    print("\033[0;33m", i, "\033[0m")

  if debug: print ("GNS FUNCTION: <generate_new_decomp_schedule>")
  return run_gpt_prompt_new_decomp_schedule(persona, 
                                            main_act_dur, 
                                            truncated_act_dur, 
                                            start_time_hour,
                                            end_time_hour,
                                            inserted_act,
                                            inserted_act_dur)[0]


##############################################################################
# CHAPTER 3: Plan
##############################################################################
def print_retrieved_items(persona_name, focal_points, retrieved):
    """格式化打印检索到的记忆项，提高可读性"""
    print(f"\033[0;33m-------in agent_chat_v2------, {persona_name} finish retrieved.\033[0m")
    
    total_items = 0
    for key, items in retrieved.items():
        total_items += len(items)
        print(f"\033[0;33m  >> Topic: '{key}' - Found {len(items)} memories\033[0m")
        
        # 只显示前3个项目的实际内容
        for i, item in enumerate(items[:10]):
            memory_content = item.embedding_key if hasattr(item, 'embedding_key') else str(item)
            print(f"\033[0;36m    {i+1}. {memory_content[:100]}{'...' if len(memory_content) > 100 else ''}\033[0m")
        
        # 如果有更多项目，只显示数量
        if len(items) > 10:
            print(f"\033[0;36m    ... and {len(items) - 10} more items\033[0m")
    
    print(f"\033[0;33m  Total: {total_items} memories retrieved\033[0m")

def revise_identity(persona): 
  p_name = persona.scratch.name

  focal_points = [f"{p_name}'s plan for {persona.scratch.get_str_curr_date_str()}.",
                  f"Important recent events for {p_name}'s life."]
  print("\033[0;33m-----in revise_identity-----", persona.name, "start retrieve\033[0m")
  retrieved = new_retrieve(persona, focal_points)
  print_retrieved_items(p_name, focal_points, retrieved)

  statements = "[Statements]\n"
  for key, val in retrieved.items():
    for i in val: 
      statements += f"{i.created.strftime('%A %B %d -- %H:%M %p')}: {i.embedding_key}\n"

  # print (";adjhfno;asdjao;idfjo;af", p_name)
  plan_prompt = statements + "\n"
  plan_prompt += f"Given the statements above, is there anything that {p_name} should remember as they plan for"
  plan_prompt += f" *{persona.scratch.curr_time.strftime('%A %B %d')}*? "
  plan_prompt += f"If there is any scheduling information, be as specific as possible (include date, time, and location if stated in the statement)\n\n"
  plan_prompt += f"Write the response from {p_name}'s perspective."
  print("\033[0;33m-----in revise_identity-----", persona.name, "ask gpt for plan_note\033[0m")
  plan_note = ChatGPT_single_request(plan_prompt)
  # print (plan_note)

  thought_prompt = statements + "\n"
  thought_prompt += f"Given the statements above, how might we summarize {p_name}'s feelings about their days up to now?\n\n"
  thought_prompt += f"Write the response from {p_name}'s perspective."
  print("\033[0;33m-----in revise_identity-----", persona.name, "ask gpt for thought_note\033[0m")
  thought_note = ChatGPT_single_request(thought_prompt)
  # print (thought_note)

  currently_prompt = f"{p_name}'s status from {(persona.scratch.curr_time - datetime.timedelta(days=1)).strftime('%A %B %d')}:\n"
  currently_prompt += f"{persona.scratch.currently}\n\n"
  currently_prompt += f"{p_name}'s thoughts at the end of {(persona.scratch.curr_time - datetime.timedelta(days=1)).strftime('%A %B %d')}:\n" 
  currently_prompt += (plan_note + thought_note).replace('\n', '') + "\n\n"
  currently_prompt += f"It is now {persona.scratch.curr_time.strftime('%A %B %d')}. Given the above, write {p_name}'s status for {persona.scratch.curr_time.strftime('%A %B %d')} that reflects {p_name}'s thoughts at the end of {(persona.scratch.curr_time - datetime.timedelta(days=1)).strftime('%A %B %d')}. Write this in third-person talking about {p_name}."
  currently_prompt += f"If there is any scheduling information, be as specific as possible (include date, time, and location if stated in the statement).\n\n"
  currently_prompt += "Follow this format below:\nStatus: <new status>"
  # print ("DEBUG ;adjhfno;asdjao;asdfsidfjo;af", p_name)
  # print (currently_prompt)
  print("\033[0;33m-----in revise_identity-----", persona.name, "ask gpt for new_currently\033[0m")
  new_currently = ChatGPT_single_request(currently_prompt)
  # print (new_currently)
  # print (new_currently[10:])

  persona.scratch.currently = new_currently

  daily_req_prompt = persona.scratch.get_str_iss() + "\n"
  daily_req_prompt += f"Today is {persona.scratch.curr_time.strftime('%A %B %d')}. Here is {persona.scratch.name}'s plan today in broad-strokes (with the time of the day. e.g., have a lunch at 12:00 pm, watch TV from 7 to 8 pm).\n\n"
  daily_req_prompt += f"Follow this format (the list should have 4~6 items but no more):\n"
  daily_req_prompt += f"1. wake up and complete the morning routine at <time>, 2. ..."

  print("\033[0;33m-----in revise_identity-----", persona.name, "ask gpt for new_daily_req\033[0m")
  new_daily_req = ChatGPT_single_request(daily_req_prompt)
  new_daily_req = new_daily_req.replace('\n', ' ')
  print ("WE ARE HERE!!!", new_daily_req)
  persona.scratch.daily_plan_req = new_daily_req


def _long_term_planning(persona, new_day): 
  """
  Formulates the persona's daily long-term plan if it is the start of a new 
  day. This basically has two components: first, we create the wake-up hour, 
  and second, we create the hourly schedule based on it. 
  INPUT
    new_day: Indicates whether the current time signals a "First day",
             "New day", or False (for neither). This is important because we
             create the personas' long term planning on the new day. 
  """
  # We start by creating the wake up hour for the persona. 
  sleep_hour, wake_up_hour = generate_wake_up_hour(persona)[0]

  # When it is a new day, we start by creating the daily_req of the persona.
  # Note that the daily_req is a list of strings that describe the persona's
  # day in broad strokes.
  if new_day == "First day": 
    # Bootstrapping the daily plan for the start of then generation:
    # if this is the start of generation (so there is no previous day's 
    # daily requirement, or if we are on a new day, we want to create a new
    # set of daily requirements.
    persona.scratch.daily_req = generate_first_daily_plan(persona, 
                                                          wake_up_hour)
  elif new_day == "New day":
    print("\033[1;36m-----It's a new day!!!!!!!!!!!!!------", persona.scratch.name, "-----\033[0m")
    print("\033[1;36m-----start revise_identity to collect necessary for new plan-----\033[0m")
    revise_identity(persona)

    # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - TODO
    # We need to create a new daily_req here... use the same function as above to solve the TODO
    persona.scratch.daily_req = generate_first_daily_plan(persona, 
                                                          wake_up_hour)
    #persona.scratch.daily_req = persona.scratch.daily_req

  # Based on the daily_req, we create an hourly schedule for the persona, 
  # which is a list of todo items with a time duration (in minutes) that 
  # add up to 24 hours.
  persona.scratch.f_daily_schedule = generate_hourly_schedule(persona, 
                                                              wake_up_hour, sleep_hour)
  persona.scratch.f_daily_schedule_hourly_org = (persona.scratch
                                                   .f_daily_schedule[:])


  # Added March 4 -- adding plan to the memory.
  thought = f"This is {persona.scratch.name}'s plan for {persona.scratch.curr_time.strftime('%A %B %d')}:"
  for i in persona.scratch.daily_req: 
    thought += f" {i},"
  thought = thought[:-1] + "."
  created = persona.scratch.curr_time
  expiration = persona.scratch.curr_time + datetime.timedelta(days=30)
  s, p, o = (persona.scratch.name, "plan", persona.scratch.curr_time.strftime('%A %B %d'))
  keywords = set(["plan"])
  thought_poignancy = 5
  thought_embedding_pair = (thought, get_embedding(thought))
  print("\033[0;33m-----in _long_term_planning-----", persona.name, "add plan to memory. Current time:", persona.scratch.curr_time, "\033[0m")
  persona.a_mem.add_thought(created, expiration, s, p, o, 
                            thought, keywords, thought_poignancy, 
                            thought_embedding_pair, None)

  # print("Sleeping for 20 seconds...")
  # time.sleep(10)
  # print("Done sleeping!")


def _determine_action(persona, maze): 
  """
  Creates the next action sequence for the persona. 
  """
  def determine_decomp(act_desp, act_dura):
    """
    Determines whether to decompose an action based on its description and duration.
    """
    # List of terms that indicate pure sleeping activities
    sleep_terms = ["sleeping", "asleep", "in bed sleeping", "taking a nap"]
    # List of terms that indicate waking up or getting ready activities
    wakeup_terms = ["waking up", "getting up", "out of bed", "morning routine"]
    
    # Check if this is a wake-up activity - these should be decomposed
    if any(term in act_desp.lower() for term in wakeup_terms):
      return True
      
    # Check if this is a pure sleeping activity - these should not be decomposed
    if any(term in act_desp.lower() for term in sleep_terms):
      return False
      
    # Handle other sleep-related activities
    if "sleep" in act_desp.lower() or "bed" in act_desp.lower():
      # Only long sleep activities are not decomposed 
      if act_dura > 60:
        return False
    
    # Default: decompose all other activities
    return True

  # The goal of this function is to get us the action associated with 
  # <curr_index>.
  curr_index = persona.scratch.get_f_daily_schedule_index()
  curr_index_60 = persona.scratch.get_f_daily_schedule_index(advance=60)

  # * Improved Decompose Logic * 
  # Check if the current activity is sleeping
  current_activity = persona.scratch.f_daily_schedule[curr_index][0].lower() if curr_index < len(persona.scratch.f_daily_schedule) else ""
  sleep_terms = ["sleeping", "asleep", "taking a nap"]
  is_sleeping = any(term in current_activity for term in sleep_terms)

  # Case 1: First hour of the day
  if curr_index == 0:
    act_desp, act_dura = persona.scratch.f_daily_schedule[curr_index]
    if act_dura >= 60 and determine_decomp(act_desp, act_dura): 
      print("\033[0;33m------in _determine_action------", persona.name, "original f_daily_schedule\033[0m")
      show_f_daily_schedule_better(persona)
      persona.scratch.f_daily_schedule[curr_index:curr_index+1] = generate_task_decomp(persona, act_desp, act_dura)
      print("\033[0;33m------in _determine_action------", persona.name, "after decomp f_daily_schedule\033[0m")
      show_f_daily_schedule_better(persona)
    
    if curr_index_60 + 1 < len(persona.scratch.f_daily_schedule):
      act_desp, act_dura = persona.scratch.f_daily_schedule[curr_index_60+1]
      if act_dura >= 60 and determine_decomp(act_desp, act_dura): 
        print("\033[0;33m------in _determine_action------", persona.name, "original f_daily_schedule\033[0m")
        show_f_daily_schedule_better(persona)
        persona.scratch.f_daily_schedule[curr_index_60+1:curr_index_60+2] = generate_task_decomp(persona, act_desp, act_dura)
        print("\033[0;33m------in _determine_action------", persona.name, "after decomp f_daily_schedule\033[0m")
        show_f_daily_schedule_better(persona)

  # Case 2: Currently sleeping - check and decompose the next activity
  elif is_sleeping and curr_index + 1 < len(persona.scratch.f_daily_schedule):
    next_act_desp, next_act_dura = persona.scratch.f_daily_schedule[curr_index + 1]
    # Force decomposition of the first post-sleep activity if long enough
    if next_act_dura >= 60:
      print("\033[0;33m------in _determine_action------", persona.name, "decomposing post-sleep activity\033[0m")
      show_f_daily_schedule_better(persona)
      persona.scratch.f_daily_schedule[curr_index+1:curr_index+2] = generate_task_decomp(persona, next_act_desp, next_act_dura)
      print("\033[0;33m------in _determine_action------", persona.name, "after decomp f_daily_schedule\033[0m")
      show_f_daily_schedule_better(persona)

  # Case 3: Standard hour-ahead decomposition
  if curr_index_60 < len(persona.scratch.f_daily_schedule) and persona.scratch.curr_time.hour < 23:
    act_desp, act_dura = persona.scratch.f_daily_schedule[curr_index_60]
    if act_dura >= 60 and determine_decomp(act_desp, act_dura): 
      print("\033[0;33m------in _determine_action------", persona.name, "original f_daily_schedule\033[0m")
      show_f_daily_schedule_better(persona)
      persona.scratch.f_daily_schedule[curr_index_60:curr_index_60+1] = generate_task_decomp(persona, act_desp, act_dura)
      print("\033[0;33m------in _determine_action------", persona.name, "after decomp f_daily_schedule\033[0m")
      show_f_daily_schedule_better(persona)
  # * End of Decompose *
  

  # Generate an <Action> instance from the action description and duration. By
  # this point, we assume that all the relevant actions are decomposed and 
  # ready in f_daily_schedule. 
  print ("\033[0;33mDEBUG LJSDLFSKJF\033[0m")
  # for i in persona.scratch.f_daily_schedule: print (i)
  print ("current f_daily_schedule_index: ", curr_index)
  print (len(persona.scratch.f_daily_schedule))
  print (persona.scratch.name)
  print ("------")

  # 1440
  x_emergency = 0
  for i in persona.scratch.f_daily_schedule: 
    x_emergency += i[1]
# print ("x_emergency", x_emergency)

  if 1440 - x_emergency > 0: 
    print ("\033[1;31merror x_emergency__AAA", x_emergency, "\033[0m")
    # the total time is less than 24 hours, so we add sleeping time to the end of the schedule
    persona.scratch.f_daily_schedule += [["sleeping", 1440 - x_emergency]]  # Only add if there's time left

# If the total time is more than 24 hours, we need to adjust the last activity
  if 1440 - x_emergency < 0:
    print ("\033[1;31merror x_emergency__BBB", x_emergency, "\033[0m")
    # the total time is more than 24 hours, so we need to adjust the last activity
    last_act = persona.scratch.f_daily_schedule[-1]
    adjustment = 1440 - x_emergency  # This will be negative
    
    if last_act[1] + adjustment > 0:
      # Simple case: just adjust the last activity
      persona.scratch.f_daily_schedule[-1][1] += adjustment
    else:
      print("\033[1;31merror x_emergency__CCC", x_emergency, "\033[0m")
      # Complex case: need to reconstruct the entire schedule
      
      # Create a new schedule by accumulating time until we reach 1440
      new_schedule = []
      accumulated_time = 0
      
      for i, (activity, duration) in enumerate(persona.scratch.f_daily_schedule):
        if accumulated_time + duration <= 1440:
          # This activity fits completely
          new_schedule.append([activity, duration])
          accumulated_time += duration
        else:
          # This activity would exceed 1440, so we need to truncate it
          remaining_time = 1440 - accumulated_time
          if remaining_time > 0:
            # Add the truncated activity
            new_schedule.append([activity, remaining_time])
          break
      
      # Replace the original schedule with the reconstructed one
      persona.scratch.f_daily_schedule = new_schedule
      
      # Verify the total time is exactly 1440
      total_time = sum(act[1] for act in persona.scratch.f_daily_schedule)
      print(f"\033[0;32mReconstructed schedule total time: {total_time}\033[0m")



  act_desp, act_dura = persona.scratch.f_daily_schedule[curr_index] 



  # Finding the target location of the action and creating action-related
  # variables.
  act_world = maze.access_tile(persona.scratch.curr_tile)["world"]
  # act_sector = maze.access_tile(persona.scratch.curr_tile)["sector"]
  print("\033[0;33m------in _determine_action------", persona.name , " start get a new address\033[0m")
  act_sector = generate_action_sector(act_desp, persona, maze)
  act_arena = generate_action_arena(act_desp, persona, maze, act_world, act_sector)
  act_address = f"{act_world}:{act_sector}:{act_arena}"
  act_game_object = generate_action_game_object(act_desp, act_address,
                                                persona, maze)
  new_address = f"{act_world}:{act_sector}:{act_arena}:{act_game_object}"
  print("\033[0;33m------in _determine_action------", persona.name , " finished get a new address:", new_address, "\033[0m")
  act_pron = generate_action_pronunciatio(act_desp, persona)
  print("\033[0;33m------in _determine_action------", persona.name , " finished act_pron:", act_pron, "\033[0m")
  act_event = generate_action_event_triple(act_desp, persona)
  print("\033[0;33m------in _determine_action------", persona.name , " finished act_event_triple:", act_event ,"\033[0m")
  # Persona's actions also influence the object states. We set those up here. 
  act_obj_desp = generate_act_obj_desc(act_game_object, act_desp, persona)
  print("\033[0;33m------in _determine_action------", persona.name , " finished act_obj_desp:", act_obj_desp, "\033[0m")
  act_obj_pron = generate_action_pronunciatio(act_obj_desp, persona)
  print("\033[0;33m------in _determine_action------", persona.name , " finished act_obj_pron:", act_obj_pron, "\033[0m")
  act_obj_event = generate_act_obj_event_triple(act_game_object, 
                                                act_obj_desp, persona)
  print("\033[0;33m------in _determine_action------", persona.name , " finished act_obj_event:", act_obj_event, "\033[0m")

  # Adding the action to persona's queue. 
  persona.scratch.add_new_action(new_address, 
                                 int(act_dura), 
                                 act_desp, 
                                 act_pron, 
                                 act_event,
                                 None,
                                 None,
                                 None,
                                 None,
                                 act_obj_desp, 
                                 act_obj_pron, 
                                 act_obj_event)


def _choose_retrieved(persona, retrieved): 
  """
  Retrieved elements have multiple core "curr_events". We need to choose one
  event to which we are going to react to. We pick that event here. 
  INPUT
    persona: Current <Persona> instance whose action we are determining. 
    retrieved: A dictionary of <ConceptNode> that were retrieved from the 
               the persona's associative memory. This dictionary takes the
               following form: 
               dictionary[event.description] = 
                 {["curr_event"] = <ConceptNode>, 
                  ["events"] = [<ConceptNode>, ...], 
                  ["thoughts"] = [<ConceptNode>, ...] }
  """
  # Once we are done with the reflection, we might want to build a more  
  # complex structure here.
  
  # We do not want to take self events... for now 
  copy_retrieved = retrieved.copy()
  for event_desc, rel_ctx in copy_retrieved.items(): 
    curr_event = rel_ctx["curr_event"]
    if curr_event.subject == persona.name: 
      del retrieved[event_desc]

  # Always choose persona first.
  priority = []
  for event_desc, rel_ctx in retrieved.items(): 
    curr_event = rel_ctx["curr_event"]
    if (":" not in curr_event.subject 
        and curr_event.subject != persona.name): 
      priority += [rel_ctx]
  if priority: 
    return random.choice(priority)

  # Skip idle. 
  for event_desc, rel_ctx in retrieved.items(): 
    curr_event = rel_ctx["curr_event"]
    if "is idle" not in event_desc: 
      priority += [rel_ctx]
  if priority: 
    return random.choice(priority)
  print("\033[0;33m-----in _choose_retrieved-----", persona.name, "after remove self events and skip idle: no event\033[0m")
  return None


def _should_react(persona, retrieved, personas): 
  """
  Determines what form of reaction the persona should exihibit given the 
  retrieved values. 
  INPUT
    persona: Current <Persona> instance whose action we are determining. 
    retrieved: A dictionary of <ConceptNode> that were retrieved from the 
               the persona's associative memory. This dictionary takes the
               following form: 
               dictionary[event.description] = 
                 {["curr_event"] = <ConceptNode>, 
                  ["events"] = [<ConceptNode>, ...], 
                  ["thoughts"] = [<ConceptNode>, ...] }
    personas: A dictionary that contains all persona names as keys, and the 
              <Persona> instance as values. 
  """
  def lets_talk(init_persona, target_persona, retrieved):
    if (not target_persona.scratch.act_address 
        or not target_persona.scratch.act_description
        or not init_persona.scratch.act_address
        or not init_persona.scratch.act_description): 
      print("\033[0;33m-----in should_react-----", init_persona.name, "or", target_persona.name, " no address or description\033[0m")
      return False

    if ("sleeping" in target_persona.scratch.act_description 
        or "sleeping" in init_persona.scratch.act_description): 
      print("\033[0;33m-----in should_react-----", init_persona.name, "or", target_persona.name, " sleeping\033[0m")
      return False

    if init_persona.scratch.curr_time.hour == 23: 
      print("\033[0;33m-----in should_react-----", init_persona.name, "or", target_persona.name, " curr_time is 23h\033[0m")
      return False

    if "<waiting>" in target_persona.scratch.act_address: 
      print("\033[0;33m-----in should_react-----", init_persona.name, "or", target_persona.name, " waiting\033[0m")
      return False

    if (target_persona.scratch.chatting_with 
      or init_persona.scratch.chatting_with): 
      print("\033[0;33m-----in should_react-----", init_persona.name, "or", target_persona.name, " chatting now\033[0m")
      return False

    if (target_persona.name in init_persona.scratch.chatting_with_buffer): 
      if init_persona.scratch.chatting_with_buffer[target_persona.name] > 0: 
        print("\033[0;33m-----in should_react-----", init_persona.name, "or", target_persona.name, " chatting buffer more than 0, it's", init_persona.scratch.chatting_with_buffer[target_persona.name], " now\033[0m")
        return False

    print("\033[0;33m-----in should_react----- ", init_persona.name, "start ask gpt\033[0m")
    if generate_decide_to_talk(init_persona, target_persona, retrieved):

      return True

    return False

  def lets_react(init_persona, target_persona, retrieved): 
    if (not target_persona.scratch.act_address 
        or not target_persona.scratch.act_description
        or not init_persona.scratch.act_address
        or not init_persona.scratch.act_description): 
      print("\033[0;33m-----in should_react-----", init_persona.name, "or", target_persona.name, " no address or description\033[0m")
      return False

    if ("sleeping" in target_persona.scratch.act_description 
        or "sleeping" in init_persona.scratch.act_description):
      print("\033[0;33m-----in should_react-----", init_persona.name, "or", target_persona.name, " sleeping\033[0m")
      return False

    # return False
    if init_persona.scratch.curr_time.hour == 23: 
      print("\033[0;33m-----in should_react-----", init_persona.name, "or", target_persona.name, " curr_time is 23h\033[0m")
      return False

    if "waiting" in target_persona.scratch.act_description: 
      print("\033[0;33m-----in should_react-----", init_persona.name, "or", target_persona.name, " waiting\033[0m")
      return False
    if init_persona.scratch.planned_path == []:
      print("\033[0;33m-----in should_react-----", init_persona.name, "or", target_persona.name, " no planned path\033[0m")
      return False

    if (init_persona.scratch.act_address 
        != target_persona.scratch.act_address): 
      print("\033[0;33m-----in should_react-----", init_persona.name, "or", target_persona.name, " not in the same address\033[0m")
      return False

    print("\033[0;33m-----in should_react----- ", init_persona.name, "start ask gpt\033[0m")
    react_mode = generate_decide_to_react(init_persona, 
                                          target_persona, retrieved)

    if react_mode == "1": 
      wait_until = ((target_persona.scratch.act_start_time 
        + datetime.timedelta(minutes=target_persona.scratch.act_duration - 1))
        .strftime("%B %d, %Y, %H:%M:%S"))
      return f"wait: {wait_until}"
    elif react_mode == "2":
      return False
      return "do other things"
    else:
      print("\033[0;33m-----in should_react-----gpt return no react mode, it's", react_mode, "\033[0m")
      return False #"keep" 

  # If the persona is chatting right now, default to no reaction 
  if persona.scratch.chatting_with: 
    print("\033[0;33m-----in should_react-----", persona.name, " chatting now so return false\033[0m")
    return False
  if "<waiting>" in persona.scratch.act_address: 
    print("\033[0;33m-----in should_react-----", persona.name, " waiting now so return false\033[0m")
    return False

  # Recall that retrieved takes the following form: 
  # dictionary {["curr_event"] = <ConceptNode>, 
  #             ["events"] = [<ConceptNode>, ...], 
  #             ["thoughts"] = [<ConceptNode>, ...]}
  curr_event = retrieved["curr_event"]

  if ":" not in curr_event.subject: 
    # this is a persona event. 
    print("\033[0;33m-----in should_react-----", persona.name, 
      f"Current Event: {curr_event.subject} {curr_event.predicate} {curr_event.object}" if curr_event else "None", "\033[0m")
    print("\033[0;33m-----in should_react-----", persona.name, " try to find whether to talk\033[0m")
    if lets_talk(persona, personas[curr_event.subject], retrieved):
      print("\033[0;33m-----in should_react-----", persona.name, " decide to talk with", curr_event.subject, "\033[0m")
      return f"chat with {curr_event.subject}"
    print("\033[0;33m-----in should_react-----", persona.name, " decide not to talk with", curr_event.subject, "\033[0m")
    print("\033[0;33m-----in should_react-----", persona.name, " try to find react mode\033[0m")
    react_mode = lets_react(persona, personas[curr_event.subject], 
                            retrieved)
    print("\033[0;33m-----in should_react-----", persona.name, " get react mode:", react_mode, "\033[0m")
    return react_mode
  return False


def _create_react(persona, inserted_act, inserted_act_dur,
                  act_address, act_event, chatting_with, chat, chatting_with_buffer,
                  chatting_end_time, 
                  act_pronunciatio, act_obj_description, act_obj_pronunciatio, 
                  act_obj_event, act_start_time=None): 
  p = persona 

  # 获取当前时间的分钟数（从午夜开始）
  today_min_pass = (int(p.scratch.curr_time.hour) * 60 + int(p.scratch.curr_time.minute))
  current_hour = int(p.scratch.curr_time.hour)
  
  # 使用f_daily_schedule来找到合适的开始时间
  def find_valid_start_hour():
    dur_sum = 0
    
    # 遍历f_daily_schedule找到当前时间对应的活动
    current_activity_index = None
    for i, (act, dur) in enumerate(p.scratch.f_daily_schedule):
      if dur_sum <= today_min_pass < dur_sum + dur:
        current_activity_index = i
        break
      dur_sum += dur
    
    if current_activity_index is None:
      # 如果没找到，使用当前小时
      return current_hour, 0
    
    # 从当前活动开始向前查找，寻找在整点开始的活动
    for i in range(current_activity_index, -1, -1):
      activity_start_time = 0
      for j in range(i):
        activity_start_time += p.scratch.f_daily_schedule[j][1]
      
      # 检查这个活动是否在整点开始
      if activity_start_time % 60 == 0:
        return int(activity_start_time / 60), i
    
    # 如果没找到在整点开始的活动，返回当前小时的开始
    return current_hour, current_activity_index

  # 找到合适的结束时间（必须对应活动边界）
  def find_valid_end_hour(min_end_hour):
    dur_sum = 0
    
    # 遍历所有活动，找到在min_end_hour之后的第一个活动边界
    for i, (act, dur) in enumerate(p.scratch.f_daily_schedule):
      activity_start_time = dur_sum
      activity_end_time = dur_sum + dur
      
      # 检查活动开始时间是否在整点且≥min_end_hour
      if activity_start_time % 60 == 0 and activity_start_time >= min_end_hour * 60:
        return int(activity_start_time / 60)
      
      # 检查活动结束时间是否在整点且≥min_end_hour
      if activity_end_time % 60 == 0 and activity_end_time >= min_end_hour * 60:
        return int(activity_end_time / 60)
      
      dur_sum += dur
    
    # 如果没找到合适的边界，返回一天结束或min_end_hour+1
    return min(24, min_end_hour + 1)

  start_hour, start_activity_index = find_valid_start_hour()
  
  # 确保从当前小时开始至少有2小时，然后找到对应的活动边界
  min_end_hour = current_hour + 2
  end_hour = find_valid_end_hour(min_end_hour)

  # 使用f_daily_schedule找到对应的索引范围
  dur_sum = 0
  start_index = None
  end_index = None
  
  for count, (act, dur) in enumerate(p.scratch.f_daily_schedule):
    # 检查是否到达start_hour对应的时间点
    if dur_sum >= start_hour * 60 and start_index is None:
      start_index = count
    
    # 检查是否到达end_hour对应的时间点  
    if dur_sum >= end_hour * 60 and end_index is None:
      end_index = count
      break
      
    dur_sum += dur

  # 如果没找到start_index，从0开始
  if start_index is None:
    start_index = 0
    
  # 如果没找到end_index，设置为列表长度
  if end_index is None:
    end_index = len(p.scratch.f_daily_schedule)

  # 检查所选范围内的最后一个事件是否是sleeping，如果是则调整end_index
  if end_index > start_index:
    # 从end_index-1开始向后检查，找到第一个sleeping事件
    for i in range(end_index - 1, start_index - 1, -1):
      if i < len(p.scratch.f_daily_schedule):
        act_name = p.scratch.f_daily_schedule[i][0]
        if "sleeping" in act_name.lower():
          # 找到sleeping事件，将end_index调整到这个事件之前
          end_index = i
          
          # 重新计算end_hour
          dur_sum = 0
          for j in range(end_index):
            dur_sum += p.scratch.f_daily_schedule[j][1]
          end_hour = int(dur_sum / 60)
          break

  ret = generate_new_decomp_schedule(p, inserted_act, inserted_act_dur, 
                                       start_hour, end_hour)
  p.scratch.f_daily_schedule[start_index:end_index] = ret
  p.scratch.add_new_action(act_address,
                           inserted_act_dur,
                           inserted_act,
                           act_pronunciatio,
                           act_event,
                           chatting_with,
                           chat,
                           chatting_with_buffer,
                           chatting_end_time,
                           act_obj_description,
                           act_obj_pronunciatio,
                           act_obj_event,
                           act_start_time)


def _chat_react(maze, persona, focused_event, reaction_mode, personas):
  # There are two personas -- the persona who is initiating the conversation
  # and the persona who is the target. We get the persona instances here. 
  init_persona = persona
  target_persona = personas[reaction_mode[9:].strip()]
  curr_personas = [init_persona, target_persona]

  # Actually creating the conversation here. 
  print("\033[0;33m-----in chat react----", init_persona.name , " start a chat with", target_persona.name, "\033[0m")
  convo, duration_min = generate_convo(maze, init_persona, target_persona)
  print("\033[0;33m-----in chat react----", init_persona.name , " finished a chat with", target_persona.name, "\033[0m")
  print("\033[0;33m-----in chat react----", init_persona.name , " start a conversation summary with", target_persona.name, "\033[0m")
  convo_summary = generate_convo_summary(init_persona, convo)
  print("\033[0;33m-----in chat react----", init_persona.name , " finish a conversation summary with", target_persona.name, "\033[0m")
  inserted_act = convo_summary
  inserted_act_dur = duration_min

  act_start_time = target_persona.scratch.act_start_time

  curr_time = target_persona.scratch.curr_time
  if curr_time.second != 0: 
    temp_curr_time = curr_time + datetime.timedelta(seconds=60 - curr_time.second)
    chatting_end_time = temp_curr_time + datetime.timedelta(minutes=inserted_act_dur)
  else: 
    chatting_end_time = curr_time + datetime.timedelta(minutes=inserted_act_dur)

  for role, p in [("init", init_persona), ("target", target_persona)]: 
    if role == "init": 
      act_address = f"<persona> {target_persona.name}"
      act_event = (p.name, "chat with", target_persona.name)
      chatting_with = target_persona.name
      chatting_with_buffer = {}
      chatting_with_buffer[target_persona.name] = 800
    elif role == "target": 
      act_address = f"<persona> {init_persona.name}"
      act_event = (p.name, "chat with", init_persona.name)
      chatting_with = init_persona.name
      chatting_with_buffer = {}
      chatting_with_buffer[init_persona.name] = 800

    act_pronunciatio = "💬" 
    act_obj_description = None
    act_obj_pronunciatio = None
    act_obj_event = (None, None, None)

    print("\033[0;33m-----in chat_react----", p.name , " start a create_react and decomp plan", target_persona.name, "\033[0m")
    # show original daily schedule
    print("\033[0;33m-----in chat_react----", p.name , " original f_daily_schedule\033[0m")
    show_f_daily_schedule_better(p)
    _create_react(p, inserted_act, inserted_act_dur,
      act_address, act_event, chatting_with, convo, chatting_with_buffer, chatting_end_time,
      act_pronunciatio, act_obj_description, act_obj_pronunciatio, 
      act_obj_event, act_start_time)
    print("\033[0;33m-----in chat_react----", p.name , " finish a create_react and decom plan", target_persona.name, "\033[0m")
    show_f_daily_schedule_better(p)
    print("\033[0;33m-----in chat_react----", p.name , " current time:", curr_time, "chatting end time:", chatting_end_time, "\033[0m")
    # 为每个角色创建聊天记忆节点
    keywords = set()
    # 使用当前角色的act_event，而不是外部的curr_event
    sub = act_event[0]
    obj = act_event[2]
    if ":" in sub: 
      sub = sub.split(":")[-1]
    if ":" in obj: 
      obj = obj.split(":")[-1]
    keywords.update([sub, obj])
    
    # 获取或创建嵌入
    if p.scratch.act_description in p.a_mem.embeddings: 
        chat_embedding = p.a_mem.embeddings[p.scratch.act_description]
    else: 
        chat_embedding = get_embedding(p.scratch.act_description)
    chat_embedding_pair = (p.scratch.act_description, chat_embedding)
    
    # 计算重要性分数
    chat_poignancy = generate_poig_score(p, "chat", p.scratch.act_description)
    
    print(f"\033[0;33m-----in chat_react------ {p.name} saving chat node. Current time: {p.scratch.curr_time} -----\033[0m")
    
    # 创建聊天节点并保存到记忆中
    chat_node = p.a_mem.add_chat(
        p.scratch.curr_time,  # 创建时间
        None,                 # 过期时间（无）
        act_event[0],         # 主语
        act_event[1],         # 谓语
        act_event[2],         # 宾语
        p.scratch.act_description,  # 描述
        keywords,             # 关键词
        chat_poignancy,       # 重要性
        chat_embedding_pair,  # 嵌入向量对
        convo                 # 实际对话内容
    )


def _wait_react(persona, reaction_mode):
  p = persona

  inserted_act = f'waiting to start {p.scratch.act_description.split("(")[-1][:-1]}'
  end_time = datetime.datetime.strptime(reaction_mode[6:].strip(), "%B %d, %Y, %H:%M:%S")
  inserted_act_dur = (end_time.minute + end_time.hour * 60) - (p.scratch.curr_time.minute + p.scratch.curr_time.hour * 60) + 1

  act_address = f"<waiting> {p.scratch.curr_tile[0]} {p.scratch.curr_tile[1]}"
  act_event = (p.name, "waiting to start", p.scratch.act_description.split("(")[-1][:-1])
  chatting_with = None
  chat = None
  chatting_with_buffer = None
  chatting_end_time = None

  act_pronunciatio = "⌛" 
  act_obj_description = None
  act_obj_pronunciatio = None
  act_obj_event = (None, None, None)

  print("\033[0;33m-----in wait_react----", p.name , " start a create_react and decomp plan", p.name, "\033[0m")
  _create_react(p, inserted_act, inserted_act_dur,
    act_address, act_event, chatting_with, chat, chatting_with_buffer, chatting_end_time,
    act_pronunciatio, act_obj_description, act_obj_pronunciatio, act_obj_event)
  print("\033[0;33m-----in wait_react----", p.name , " finish a create_react and decom plan", p.name, "\033[0m")


def plan(persona, maze, personas, new_day, retrieved): 
  """
  Main cognitive function of the chain. It takes the retrieved memory and 
  perception, as well as the maze and the first day state to conduct both 
  the long term and short term planning for the persona. 

  INPUT: 
    maze: Current <Maze> instance of the world. 
    personas: A dictionary that contains all persona names as keys, and the 
              Persona instance as values. 
    new_day: This can take one of the three values. 
      1) <Boolean> False -- It is not a "new day" cycle (if it is, we would
         need to call the long term planning sequence for the persona). 
      2) <String> "First day" -- It is literally the start of a simulation,
         so not only is it a new day, but also it is the first day. 
      2) <String> "New day" -- It is a new day. 
    retrieved: dictionary of dictionary. The first layer specifies an event,
               while the latter layer specifies the "curr_event", "events", 
               and "thoughts" that are relevant.
  OUTPUT 
    The target action address of the persona (persona.scratch.act_address).
  """ 
  # PART 1: Generate the hourly schedule. 
  if new_day: 
    print("\033[1;33m----in plan----", persona.name , " start a long term planning: \033[0m")
    _long_term_planning(persona, new_day)
    print("\033[1;33m----in plan----", persona.name , " finished long term planning: \033[0m")

  # first show the original daily schedule
  print("\033[0;33m------in plan------", persona.name , " original f_daily_schedule\033[0m")
  show_f_daily_schedule_better(persona)
  # PART 2: If the current action has expired, we want to create a new plan.
  if persona.scratch.act_check_finished(): 
    print("\033[1;33m----in plan----", persona.name , " start a new determine action: \033[0m")
    _determine_action(persona, maze)
    print("\033[1;33m----in plan----", persona.name , " finished a new determining action: \033[0m")
  else:
    print("\033[1;33m----in plan----", persona.name , " skip a new determine action since the old one is still active: ", persona.scratch.act_event, "\033[0m")

  # PART 3: If you perceived an event that needs to be responded to (saw 
  # another persona), and retrieved relevant information. 
  # Step 1: Retrieved may have multiple events represented in it. The first 
  #         job here is to determine which of the events we want to focus 
  #         on for the persona. 
  #         <focused_event> takes the form of a dictionary like this: 
  #         dictionary {["curr_event"] = <ConceptNode>, 
  #                     ["events"] = [<ConceptNode>, ...], 
  #                     ["thoughts"] = [<ConceptNode>, ...]}
  focused_event = False
  if retrieved.keys(): 
    print("\033[1;33m----in plan----", persona.name , " start a choose_retrieved about the pretrieved things just now.\033[0m")
    focused_event = _choose_retrieved(persona, retrieved)
    print("\033[1;33m----in plan----", persona.name, " finished choose_retrieved and get the focused_event ", 
      f"Event: {focused_event['curr_event'].subject} {focused_event['curr_event'].predicate} {focused_event['curr_event'].object}" if focused_event else "None", "\033[0m")
  
  # Step 2: Once we choose an event, we need to determine whether the
  #         persona will take any actions for the perceived event. There are
  #         three possible modes of reaction returned by _should_react. 
  #         a) "chat with {target_persona.name}"
  #         b) "react"
  #         c) False
  if focused_event: 
    print("\033[1;33m----in plan----", persona.name , " start a should_react: \033[0m")
    reaction_mode = _should_react(persona, focused_event, personas)
    print("\033[1;33m----in plan----", persona.name , " finished should_react and get the reaction_mode: ", reaction_mode, "\033[0m")
    if reaction_mode: 
      # If we do want to chat, then we generate conversation 
      if reaction_mode[:9] == "chat with":
        print("\033[1;33m----in plan----", persona.name , " start a chat_react: \033[0m")
        _chat_react(maze, persona, focused_event, reaction_mode, personas)
        print("\033[1;33m----in plan----", persona.name , " finished chat_react: \033[0m")
      elif reaction_mode[:4] == "wait": 
        print("\033[1;33m----in plan----", persona.name , " start a wait_react: \033[0m")
        _wait_react(persona, reaction_mode)
        print("\033[1;33m----in plan----", persona.name , " finished wait_react: \033[0m")
      # elif reaction_mode == "do other things": 
      #   _chat_react(persona, focused_event, reaction_mode, personas)

  # Step 3: Chat-related state clean up. 
  # If the persona is not chatting with anyone, we clean up any of the 
  # chat-related states here. 
  if persona.scratch.act_event[1] != "chat with":
    persona.scratch.chatting_with = None
    persona.scratch.chat = None
    persona.scratch.chatting_end_time = None
  # We want to make sure that the persona does not keep conversing with each
  # other in an infinite loop. So, chatting_with_buffer maintains a form of 
  # buffer that makes the persona wait from talking to the same target 
  # immediately after chatting once. We keep track of the buffer value here. 
  curr_persona_chat_buffer = persona.scratch.chatting_with_buffer
  for persona_name, buffer_count in curr_persona_chat_buffer.items():
    for persona_name, buffer_count in list(curr_persona_chat_buffer.items()):
			# skip decrementing whoever I'm chatting with right now
      if persona_name == persona.scratch.chatting_with:
        continue

			# decrement and clamp at zero   
      ###################################### IMPORTANT ###############################################
      new_count = max(buffer_count - 1, 0)
      curr_persona_chat_buffer[persona_name] = new_count

			# optionally clean up entries that have reached zero
      # if new_count == 0:
        # del persona.scratch.chatting_with_buffer[persona_name]

  return persona.scratch.act_address













































 
