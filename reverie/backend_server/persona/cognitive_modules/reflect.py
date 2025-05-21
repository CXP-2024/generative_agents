"""
Author: Joon Sung Park (joonspk@stanford.edu)

File: reflect.py
Description: This defines the "Reflect" module for generative agents. 
"""
import sys
sys.path.append('../../')

import datetime
import random

from numpy import dot
from numpy.linalg import norm

from global_methods import *
from persona.prompt_template.run_gpt_prompt import *
from persona.prompt_template.gpt_structure import *
from persona.cognitive_modules.retrieve import *

def generate_focal_points(persona, n=3): 
  if debug: print ("GNS FUNCTION: <generate_focal_points>")
  
  nodes = [[i.last_accessed, i]
            for i in persona.a_mem.seq_event + persona.a_mem.seq_thought
            if "idle" not in i.embedding_key]

  nodes = sorted(nodes, key=lambda x: x[0])
  nodes = [i for created, i in nodes]

  statements = ""
  for node in nodes[-1*persona.scratch.importance_ele_n:]: 
    statements += node.embedding_key + "\n"

  return run_gpt_prompt_focal_pt(persona, statements, n)[0]


def generate_insights_and_evidence(persona, nodes, n=5): 
  if debug: print ("GNS FUNCTION: <generate_insights_and_evidence>")

  statements = ""
  for count, node in enumerate(nodes): 
    statements += f'{str(count)}. {node.embedding_key}\n'

  ret = run_gpt_prompt_insight_and_guidance(persona, statements, n)[0]

  print (ret)
  try: 

    for thought, evi_raw in ret.items(): 
      evidence_node_id = [nodes[i].node_id for i in evi_raw]
      ret[thought] = evidence_node_id
    return ret
  except Exception as e:
    print("\033[1;31mtype of ret: ", ret, "\033[0m")
    print("\033[1;31mError in generate_insights_and_evidence: ", ret, "\033[0m")
    print("\033[1;31mError: ", e, "\033[0m")
    print("""\033[1;31mWill use the default ret: {"this is blank": "node_1"} """, type(ret), "\033[0m")
    return {"this is blank": "node_1"} 


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


def generate_poig_score(persona, event_type, description): 
  if debug: print ("GNS FUNCTION: <generate_poig_score>")

  if "is idle" in description: 
    return 1

  if event_type == "event" or event_type == "thought": 
    return run_gpt_prompt_event_poignancy(persona, description)[0]
  elif event_type == "chat": 
    return run_gpt_prompt_chat_poignancy(persona, 
                           persona.scratch.act_description)[0]



def generate_planning_thought_on_convo(persona, all_utt):
  if debug: print ("GNS FUNCTION: <generate_planning_thought_on_convo>")
  return run_gpt_prompt_planning_thought_on_convo(persona, all_utt)[0]


def generate_memo_on_convo(persona, all_utt):
  if debug: print ("GNS FUNCTION: <generate_memo_on_convo>")
  return run_gpt_prompt_memo_on_convo(persona, all_utt)[0]


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

def run_reflect(persona):
  """
  Run the actual reflection. We generate the focal points, retrieve any 
  relevant nodes, and generate thoughts and insights. 

  INPUT: 
    persona: Current Persona object
  Output: 
    None
  """
  # Reflection requires certain focal points. Generate that first. 
  print("\033[0;33m---in run_reflect---", persona.scratch.name, "start generate focal points --\033[0m")
  focal_points = generate_focal_points(persona, 3)
  print("\033[0;33m---in run_reflect---", persona.scratch.name, "finish generate focal points and get: \n", focal_points, "--\033[0m")
  # Retrieve the relevant Nodes object for each of the focal points. 
  # <retrieved> has keys of focal points, and values of the associated Nodes. 
  retrieved = new_retrieve(persona, focal_points)
  print_retrieved_items(persona.scratch.name, focal_points, retrieved)
  statements = ""
  for key, val in retrieved.items():
    for i in val: 
      statements += f"{i.created.strftime('%A %B %d -- %H:%M %p')}: {i.embedding_key}\n"
  print("\033[0;33m---in run_reflect---", persona.scratch.name, "finish retrieve and get: ", statements, "--\033[0m")

  # For each of the focal points, generate thoughts and save it in the 
  # agent's memory. 
  for focal_pt, nodes in retrieved.items(): 
    xx = [i.embedding_key for i in nodes]
    for xxx in xx: print (xxx)

    print("\033[0;33m---in run_reflect---", persona.scratch.name, "start generate insights and evidence --\033[0m")
    thoughts = generate_insights_and_evidence(persona, nodes, 5)
    print("\033[0;33m---in run_reflect---", persona.scratch.name, "finish generate insights and evidence and get thoughts: ", thoughts, "--\033[0m")
    for thought, evidence in thoughts.items(): 
      created = persona.scratch.curr_time
      expiration = persona.scratch.curr_time + datetime.timedelta(days=30)
      print("\033[0;33m---in run_reflect---", persona.scratch.name, "start get action event triple --\033[0m")
      s, p, o = generate_action_event_triple(thought, persona)
      print("\033[0;33m---in run_reflect---", persona.scratch.name, "finish get action event triple and get:", s, p, o, "--\033[0m")
      keywords = set([s, p, o])
      print("\033[0;33m---in run_reflect---", persona.scratch.name, "start generate poig score --\033[0m")
      thought_poignancy = generate_poig_score(persona, "thought", thought)
      print("\033[0;33m---in run_reflect---", persona.scratch.name, "finish generate poig score and get:", thought_poignancy, "--\033[0m")
      thought_embedding_pair = (thought, get_embedding(thought))

      print("\033[0;33m---in run_reflect---", persona.scratch.name, "add thought now. Current time:", persona.scratch.curr_time, "-----\033[0m")
      persona.a_mem.add_thought(created, expiration, s, p, o,
                                thought, keywords, thought_poignancy,
                                thought_embedding_pair, evidence)
      print("\033[0;33m---in run_reflect---", persona.scratch.name, "finish add a thought and evidence:", thought, evidence, "--\033[0m")


def reflection_trigger(persona): 
  """
  Given the current persona, determine whether the persona should run a 
  reflection. 
  
  Our current implementation checks for whether the sum of the new importance
  measure has reached the set (hyper-parameter) threshold.

  INPUT: 
    persona: Current Persona object
  Output: 
    True if we are running a new reflection. 
    False otherwise. 
  """
  print (persona.scratch.name, "persona.scratch.importance_trigger_curr::", persona.scratch.importance_trigger_curr)
  print ("persona.scratch.importance_trigger_max::", persona.scratch.importance_trigger_max)

  if (persona.scratch.importance_trigger_curr <= 0 and 
      [] != persona.a_mem.seq_event + persona.a_mem.seq_thought): 
    return True 
  print("\033[0;33m---in reflection_trigger---", persona.scratch.name, "decide not to run reflection --\033[0m")
  return False


def reset_reflection_counter(persona): 
  """
  We reset the counters used for the reflection trigger. 

  INPUT: 
    persona: Current Persona object
  Output: 
    None
  """
  persona_imt_max = persona.scratch.importance_trigger_max
  persona.scratch.importance_trigger_curr = persona_imt_max
  persona.scratch.importance_ele_n = 0
  
def extract_schedule_changes_from_thought(persona, planning_thought):
    """
    Analyzes a planning thought to extract ALL potential schedule changes.
    
    Returns a list of dicts with activities and durations if changes are identified,
    otherwise returns an empty list.
    """
    print(f"\033[0;33m---in extract_schedule_changes---", persona.scratch.name, "analyzing thought for multiple schedule changes --\033[0m")
    
    # Remove the prefix if it exists
    if planning_thought.startswith(f"For {persona.scratch.name}'s planning:"):
        planning_thought = planning_thought[len(f"For {persona.scratch.name}'s planning:"):]
    
    schedule_change_prompt = f"""
    The following is a planning thought from {persona.name}:
    
    "{planning_thought}"
    
    Based on this reflection, identify ALL suggested changes to {persona.name}'s schedule.
    Extract each activity that should be added or modified, and for approximately how many minutes.
		If the activity is not relevant to the current day, please ignore it. (for example, if go out for date tomorrow, do not include here; however if prepare for important Date tomorrow, include it)

    Answer in JSON format, without any ``` or ``` json tags code blocks or markdown formatting.
    Format the response as a list of schedule changes:
    [
      {{
        "change_needed": true,
        "activity": "first activity description",
        "duration": minutes_as_integer,
        "suggested_time": "morning/afternoon/evening/specific time",
        "priority": "high/medium/low"
      }},
      {{
        "change_needed": true,
        "activity": "second activity description",
        "duration": minutes_as_integer,
        "suggested_time": "morning/afternoon/evening/specific time",
        "priority": "high/medium/low"
      }}
    ]
    
    If no changes are needed, return an empty list: []
    """
    
    for i in range(3):
        try:
            response = ChatGPT_single_request(schedule_change_prompt)
            result = json.loads(response)
            
            # Check if the result is a list
            if isinstance(result, list):
                # Filter out any items where change_needed is False
                changes = [change for change in result if change.get("change_needed", True)]
                if changes:
                    print(f"\033[0;33m---in extract_schedule_changes---", persona.scratch.name, f"found {len(changes)} schedule changes --\033[0m")
                    return changes
                else:
                    print(f"\033[0;33m---in extract_schedule_changes---", persona.scratch.name, "no schedule changes needed --\033[0m")
                    return []
            else:
                # Try to handle the case where it returns a single object instead of a list
                if result.get("change_needed", False):
                    print(f"\033[0;33m---in extract_schedule_changes---", persona.scratch.name, "found a single schedule change --\033[0m")
                    return [result]
        except Exception as e:
            print(f"\033[1;31m---in extract_schedule_changes---Error parsing response: {e}, repeat: {i} --\033[0m")
    
    print(f"\033[1;31m---in extract_schedule_changes---Warning! failed to get response from GPT for", persona.scratch.name, "--\033[0m")
    return []

def generate_future_schedule(persona, schedule_changes):
    """
    Generates a completely new schedule for the rest of the day based on multiple requested changes.
    All changes are incorporated at once to avoid conflicts.
    
    Args:
        persona: The persona object
        schedule_changes: List of schedule changes extracted from planning thoughts
        
    Returns:
        A list of [activity, duration] pairs for the rest of the day
    """
    # Calculate current time in minutes from midnight
    curr_time_mins = (int(persona.scratch.curr_time.hour) * 60 + 
                     int(persona.scratch.curr_time.minute))
    
    # Round up to the nearest 5 minutes for clean scheduling
    if curr_time_mins % 5 != 0:
        curr_time_mins = curr_time_mins + (5 - (curr_time_mins % 5))
    
    # Find the starting index in the daily schedule for future activities
    future_start_index = None
    dur_sum = 0
    for i, (act, dur) in enumerate(persona.scratch.f_daily_schedule):
        if dur_sum <= curr_time_mins and dur_sum + dur > curr_time_mins:
            future_start_index = i
            break
        dur_sum += dur
    
    if future_start_index is None:
        print(f"\033[1;31m---in generate_future_schedule---Could not find current position in schedule for {persona.scratch.name}--\033[0m")
        return False
        
    # Extract the original future schedule
    future_schedule = persona.scratch.f_daily_schedule[future_start_index:]
    
    # Calculate the start time of the first future activity
    start_hour = int(dur_sum / 60)
    start_minute = dur_sum % 60
    start_time = f"{start_hour:02d}:{start_minute:02d}"
    
    # Calculate the end of the day
    end_hour = 24
    
    # Format the original schedule for the LLM
    original_schedule_formatted = []
    temp_dur_sum = dur_sum
    for act, dur in future_schedule:
        start_h = int(temp_dur_sum / 60)
        start_m = temp_dur_sum % 60
        end_h = int((temp_dur_sum + dur) / 60) 
        end_m = (temp_dur_sum + dur) % 60
        if start_h >= 24:
           break
        
        original_schedule_formatted.append(f"{start_h:02d}:{start_m:02d} ~ {end_h:02d}:{end_m:02d} -- {act}")
        temp_dur_sum += dur
    
    # Format the requested changes for the LLM
    changes_formatted = []
    for change in schedule_changes:
        changes_formatted.append(f"- {change['activity']} for {change['duration']} minutes " +
                               f"(suggested time: {change['suggested_time']}, priority: {change['priority']})")
    
    # Create the prompt for the LLM
    schedule_prompt = f"""
Revise {persona.scratch.name}'s schedule for the rest of today.

Current time: {persona.scratch.curr_time.strftime('%H:%M')}

Original plan (remaining day):
{chr(10).join(original_schedule_formatted)}

Requested changes:
{chr(10).join(changes_formatted)}

Please produce a revised schedule that:
- Your first entry must starts at {start_time}
- Must ends by 24:00
- Includes all high-priority changes
- Tries to accommodate medium- and low-priority changes
- Preserves as much of the original plan as possible
- Lists each activity with its duration in minutes

Return only a JSON array in this format, without any ``` or ``` json tags code blocks or markdown formatting.
[
  ["XX:XX-YY:YY", "Activity description 1", duration_in_minutes],
  ["YY:YY-ZZ:ZZ", "Activity description 2", duration_in_minutes],
  …
]

Ensure the sum of all durations equals the remaining minutes in the day.
    """

    
    # Get the new schedule from the LLM
    for repeat in range(3):
      try:
        response = ChatGPT_single_request(schedule_prompt)
        # Parse the JSON response
        new_schedule = json.loads(response)
        for i, item in enumerate(new_schedule):
           new_schedule[i] = [item[1], item[2]]
        print(f"\033[0;33m---in generate_future_schedule---", persona.scratch.name, f"new:\n{new_schedule} --\033[0m")
        
        # Validate the schedule
        total_duration = sum(item[1] for item in new_schedule)
        expected_duration = (24 * 60) - start_hour * 60 - start_minute
        
        if abs(total_duration - expected_duration) > 0:  # Allow small rounding errors
            print(f"\033[1;31m---in generate_future_schedule---Invalid schedule duration: {total_duration} vs expected {expected_duration}--\033[0m")
            # Adjust the last activity to make the total correct
            raise ValueError("Invalid schedule duration")
        

        return new_schedule
        
      except Exception as e:
        print(f"\033[1;31m---in generate_future_schedule---Error generating schedule: {e}, repeat: {repeat}--\033[0m")
        
    print(f"\033[1;31m---in generate_future_schedule---Failed to get a valid schedule for {persona.scratch.name}--\033[0m")
    return False

def modify_future_schedule(persona, planning_thought):
    """
    Analyzes planning thoughts and modifies the entire future schedule at once
    to incorporate all suggested changes, avoiding conflicts.
    
    Args:
        persona: The persona object
        planning_thought: The planning thought to analyze
        
    Returns:
        True if schedule was successfully modified, False otherwise
    """
    # Extract schedule changes from the planning thought
    schedule_changes = extract_schedule_changes_from_thought(persona, planning_thought)
    
    if not schedule_changes:
        print(f"\033[0;33m---in modify_future_schedule---", persona.scratch.name, "no schedule changes needed--\033[0m")
        return False
    
    print(f"\033[0;33m---in modify_future_schedule---", persona.scratch.name, f"found {len(schedule_changes)} schedule changes to implement--\033[0m")
    
    # Generate a new complete schedule for the future
    new_schedule = generate_future_schedule(persona, schedule_changes)
    
    if not new_schedule:
        print(f"\033[1;31m---in modify_future_schedule---Failed to generate new schedule for {persona.scratch.name}--\033[0m")
        return False
    
    # Calculate current time in minutes from midnight
    curr_time_mins = (int(persona.scratch.curr_time.hour) * 60 + 
                     int(persona.scratch.curr_time.minute))
    
    # Find the starting index in the daily schedule for future activities
    future_start_index = None
    dur_sum = 0
    for i, (act, dur) in enumerate(persona.scratch.f_daily_schedule):
        if dur_sum <= curr_time_mins and dur_sum + dur > curr_time_mins:
            future_start_index = i
            break
        dur_sum += dur
    
    if future_start_index is None:
        print(f"\033[1;31m---in modify_future_schedule---Could not find current position in schedule for {persona.scratch.name}--\033[0m")
        return False
    
    # Create a partial entry for the current activity that's being interrupted
    remaining_mins = dur_sum + persona.scratch.f_daily_schedule[future_start_index][1] - curr_time_mins
    if remaining_mins > 0:
        current_activity = persona.scratch.f_daily_schedule[future_start_index][0]
        modified_schedule = [[current_activity, remaining_mins]] + new_schedule
    else:
        modified_schedule = new_schedule
    
    # Replace the future schedule with the new schedule
    persona.scratch.f_daily_schedule = persona.scratch.f_daily_schedule[:future_start_index] + modified_schedule
    
    # Log the changes
    print(f"\033[0;32m---in modify_future_schedule---Successfully updated {persona.scratch.name}'s schedule with {len(schedule_changes)} changes--\033[0m")
    
    return True

def _matches_suggested_time(hour, suggested_time):
    """Helper function to determine if an hour matches a suggested time period."""
    if suggested_time.lower() == "morning":
        return 5 <= hour <= 11
    elif suggested_time.lower() == "afternoon":
        return 12 <= hour <= 17
    elif suggested_time.lower() == "evening":
        return 18 <= hour <= 22
    else:
        # Try to parse a specific time
        try:
            if ":" in suggested_time:
                suggested_hour = int(suggested_time.split(":")[0])
            else:
                suggested_hour = int(suggested_time)
            return abs(hour - suggested_hour) <= 2  # Within 2 hours
        except:
            return True  # If no clear preference, any time is fine

def reflect(persona):
  """
  The main reflection module for the persona. We first check if the trigger 
  conditions are met, and if so, run the reflection and reset any of the 
  relevant counters. 

  INPUT: 
    persona: Current Persona object
  Output: 
    None
  """
  if reflection_trigger(persona): 
    print("\033[0;33m---in reflect---", persona.scratch.name, "start run_reflect--\033[0m")
    run_reflect(persona)
    print("\033[0;33m---in reflect---", persona.scratch.name, "finish run_reflect --\033[0m")
    reset_reflection_counter(persona)



  # print (persona.scratch.name, "al;sdhfjlsad", persona.scratch.chatting_end_time)
  if persona.scratch.chatting_end_time: 
    print("\033[0;33m---in reflect---", persona.scratch.name, "start check if we are in a chat --\033[0m")
    print("current time + 5min:", persona.scratch.curr_time + datetime.timedelta(0,300))  ### IMPORTANT TIME
    print("chatting end time:", persona.scratch.chatting_end_time)
    # print("DEBUG", persona.scratch.curr_time + datetime.timedelta(0,10))
    if persona.scratch.curr_time + datetime.timedelta(0,300) >= persona.scratch.chatting_end_time: 
      # print ("KABOOOOOMMMMMMM")
      print("\033[0;33m---in reflect---", persona.scratch.name, "start reflect after a chat! --\033[0m")
      all_utt = ""
      if persona.scratch.chat: 
        for row in persona.scratch.chat:  
          all_utt += f"{row[0]}: {row[1]}\n"
      print("\033[0;33m---in reflect--- This is the conversation\n", all_utt, "--\033[0m")

      # planning_thought = generate_planning_thought_on_convo(persona, all_utt)
      # print ("init planning: aosdhfpaoisdh90m     ::", f"For {persona.scratch.name}'s planning: {planning_thought}")
      # planning_thought = generate_planning_thought_on_convo(target_persona, all_utt)
      # print ("target planning: aosdhfpaodish90m     ::", f"For {target_persona.scratch.name}'s planning: {planning_thought}")

      # memo_thought = generate_memo_on_convo(persona, all_utt)
      # print ("init memo: aosdhfpaoisdh90m     ::", f"For {persona.scratch.name} {memo_thought}")
      # memo_thought = generate_memo_on_convo(target_persona, all_utt)
      # print ("target memo: aosdhfpsaoish90m     ::", f"For {target_persona.scratch.name} {memo_thought}")
      

      # make sure you set the fillings as well

      # print (persona.a_mem.get_last_chat(persona.scratch.chatting_with).node_id)

      last_chat = persona.a_mem.get_last_chat(persona.scratch.chatting_with)
      try:
        evidence = [last_chat.node_id]
      except AttributeError:
        print("\033[1;31m---in reflect---Error", persona.scratch.name, "no chat history --\033[0m")
        evidence = []

      print("\033[0;33m---in reflect---", persona.scratch.name, "start planning thought on conversation --\033[0m")
      planning_thought = generate_planning_thought_on_convo(persona, all_utt)
      print("\033[0;33m---in reflect---", persona.scratch.name, "finish planning thought on conversation --\033[0m")
      planning_thought = f"For {persona.scratch.name}'s planning: {planning_thought}"

      created = persona.scratch.curr_time
      expiration = persona.scratch.curr_time + datetime.timedelta(days=30)
      print("\033[0;33m---in reflect---", persona.scratch.name, "start get action event triple --\033[0m")
      s, p, o = generate_action_event_triple(planning_thought, persona)
      print("\033[0;33m---in reflect---", persona.scratch.name, "finish get action event triple --\033[0m")
      keywords = set([s, p, o])
      print("\033[0;33m---in reflect---", persona.scratch.name, "start generate poig score --\033[0m")
      thought_poignancy = generate_poig_score(persona, "thought", planning_thought)
      print("\033[0;33m---in reflect---", persona.scratch.name, "finish generate poig score --\033[0m")
      thought_embedding_pair = (planning_thought, get_embedding(planning_thought))

      print("\033[0;33m---in reflect--- >>>> ", planning_thought, thought_poignancy, "as score. And save the plan_thought now: ", persona.scratch.curr_time, "--\033[0m")
      persona.a_mem.add_thought(created, expiration, s, p, o, 
                                planning_thought, keywords, thought_poignancy, 
                                thought_embedding_pair, evidence)
      
			# NEW: Try to modify future schedule based on the planning thought
      print("\033[0;33m---in reflect---", persona.scratch.name, "checking if planning thought suggests schedule changes --\033[0m")
      schedule_modified = modify_future_schedule(persona, planning_thought)
      if schedule_modified:
          print("\033[0;32m---in reflect---", persona.scratch.name, "schedule(s) successfully modified based on planning thought --\033[0m")
      else:
          print("\033[0;33m---in reflect---", persona.scratch.name, "no schedule changes needed or possible --\033[0m")


      print("\033[0;33m---in reflect---", persona.scratch.name, "start try to get memo on conversation --\033[0m")
      memo_thought = generate_memo_on_convo(persona, all_utt)
      print("\033[0;33m---in reflect---", persona.scratch.name, "finish get memo on conversation --\033[0m")
      memo_thought = f"{persona.scratch.name} {memo_thought}"

      created = persona.scratch.curr_time
      expiration = persona.scratch.curr_time + datetime.timedelta(days=30)
      print("\033[0;33m---in reflect---", persona.scratch.name, "start get action event triple --\033[0m")
      s, p, o = generate_action_event_triple(memo_thought, persona)
      print("\033[0;33m---in reflect---", persona.scratch.name, "finish get action event triple --\033[0m")
      keywords = set([s, p, o])
      thought_poignancy = generate_poig_score(persona, "thought", memo_thought)
      thought_embedding_pair = (memo_thought, get_embedding(memo_thought))

      print("\033[0;33m---in reflect--- >>>> ", memo_thought, thought_poignancy, "as score. And save the mem_thought now: ", persona.scratch.curr_time, "--\033[0m")
      persona.a_mem.add_thought(created, expiration, s, p, o, 
                                memo_thought, keywords, thought_poignancy, 
                                thought_embedding_pair, evidence)



























