"""
Author: Joon Sung Park (joonspk@stanford.edu)

File: reflect.py
Description: This defines the "Reflect" module for generative agents. 
"""
import sys
sys.path.append('../../')

import datetime
import random
import re

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
    分析规划思想，提取所有潜在的日程变更。
    返回包含活动和持续时间的字典列表，如果没有变更则返回空列表。
    """
    print(f"\033[0;33m---in extract_schedule_changes---", persona.scratch.name, "analyzing thought for multiple schedule changes --\033[0m")
    
    # 如果存在前缀，则移除
    if planning_thought.startswith(f"For {persona.scratch.name}'s planning:"):
        planning_thought = planning_thought[len(f"For {persona.scratch.name}'s planning:"):]
    
    schedule_change_prompt = f"""
    The following is a planning thought from {persona.name}:
    
    "{planning_thought}"
    
    Based on this reflection, identify ALL suggested changes to {persona.name}'s schedule.
    Extract each activity that should be added or modified, with detailed descriptions of the activity.
    Include approximately how many minutes each activity should take.
    If the activity is not relevant to the current day, please ignore it.

    Answer in JSON format, without any ``` or ``` json tags code blocks or markdown formatting.
    Format the response as a list of schedule changes:
    [
      {{
        "change_needed": true,
        "activity": "detailed activity description (can include sub-activities and transitions)",
        "duration": minutes_as_integer,
        "suggested_time": "morning/afternoon/evening/specific time",
        "priority": "high/medium/low"
      }},
      {{
        "change_needed": true,
        "activity": "detailed activity description (can include sub-activities and transitions)",
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
            
            # 检查结果是否为列表
            if isinstance(result, list):
                # 过滤掉 change_needed 为 False 的项目
                changes = [change for change in result if change.get("change_needed", True)]
                if changes:
                    print(f"\033[0;33m---in extract_schedule_changes---", persona.scratch.name, f"found {len(changes)} schedule changes --\033[0m")
                    return changes
                else:
                    print(f"\033[0;33m---in extract_schedule_changes---", persona.scratch.name, "no schedule changes needed --\033[0m")
                    return []
            else:
                # 处理返回单个对象而非列表的情况
                if result.get("change_needed", False):
                    print(f"\033[0;33m---in extract_schedule_changes---", persona.scratch.name, "found a single schedule change --\033[0m")
                    return [result]
        except Exception as e:
            print(f"\033[1;31m---in extract_schedule_changes---Error parsing response: {e}, repeat: {i} --\033[0m")
    
    print(f"\033[1;31m---in extract_schedule_changes---Warning! failed to get response from GPT for", persona.scratch.name, "--\033[0m")
    return []

def generate_future_hourly_schedule(persona, schedule_changes):
    """
    基于多个请求的变更为一天的剩余时间生成一个全新的小时级别日程表。
    保持原始时间条目不变，在活动描述中添加新活动。
    
    Args:
        persona: Persona 对象
        schedule_changes: 从规划思想中提取的日程变更列表
        
    Returns:
        一个用于一天剩余时间的 [activity, duration_in_minutes] 对列表
    """
    # 计算从午夜开始的当前时间（以分钟为单位）
    curr_time_mins = (int(persona.scratch.curr_time.hour) * 60 + 
                     int(persona.scratch.curr_time.minute))
    
    # 找到每日日程中未来活动的起始索引
    future_start_index = None
    dur_sum = 0
    for i, (act, dur) in enumerate(persona.scratch.f_daily_schedule_hourly_org):
        if dur_sum <= curr_time_mins and dur_sum + dur > curr_time_mins:
            future_start_index = i
            break
        dur_sum += dur
    
    if future_start_index is None:
        print(f"\033[1;31m---in generate_future_hourly_schedule---Could not find current position in hourly schedule for {persona.scratch.name}--\033[0m")
        return False
        
    # 提取原始未来日程
    future_schedule = persona.scratch.f_daily_schedule_hourly_org[future_start_index:]
    
    # 计算第一个未来活动的开始时间
    start_hour = int(dur_sum / 60)
    start_minute = dur_sum % 60
    start_minutes_int = (start_hour * 60 + start_minute) % (24 * 60)
    start_time = f"{start_hour:02d}:{start_minute:02d}"
    
    # 为 LLM 格式化原始日程，包含完整的时间范围
    original_schedule_formatted = []
    temp_dur_sum = dur_sum
    
    # 保存原始时间范围，以便后续匹配
    original_time_ranges = []
    
    for act, dur in future_schedule:
        start_h = int(temp_dur_sum / 60)
        start_m = temp_dur_sum % 60
        temp_dur_sum += dur
        end_h = int(temp_dur_sum / 60) % 24
        end_m = temp_dur_sum % 60
        if start_h >= 24:
           break
        
        time_range = f"{start_h:02d}:{start_m:02d}-{end_h:02d}:{end_m:02d}"
        original_time_ranges.append((time_range, dur))
        original_schedule_formatted.append(f"{time_range} -- {act} -- {dur} minutes")
    
    # 为 LLM 格式化请求的变更
    changes_formatted = []
    for change in schedule_changes:
        changes_formatted.append(f"- {change['activity']} for {change['duration']} minutes " +
                               f"(suggested time: {change['suggested_time']}, priority: {change['priority']})")
    
    # 为 LLM 创建提示，明确不要改变时间范围，而是在描述中添加活动
    schedule_prompt = f"""
		Revise {persona.scratch.name}'s schedule for the rest of today.

		Current time: {persona.scratch.curr_time.strftime('%H:%M')}

		Original schedule (remaining day):
		{chr(10).join(original_schedule_formatted)}

		Requested changes:
		{chr(10).join(changes_formatted)}

		Instructions:
		1. KEEP ALL ORIGINAL TIME SLOTS EXACTLY AS THEY ARE - Do not modify any HH:MM-HH:MM time ranges
		2. Incorporate all requested changes by EMBEDDING them into existing time slots
		3. For activities within a time slot, use natural language like:
			 - "at around 2:30 PM will [activity]"
			 - "from approximately 3:00 to 4:30 will [activity]"
		4. For activities spanning multiple time slots:
			 - First slot: "original activity, and at [time] will begin [new activity]"
			 - Middle slots: "continuing [new activity]"
			 - Final slot: "finishing [new activity], then resume [original activity]"
		5. ONLY modify activity descriptions - never change time ranges or durations
		6. The first time slot is already in progress - make minimal changes to it if necessary (better not to change for this one!!!!)

		Example:
		Original: "09:00-11:00", "Working at cafe", "120"
		Change needed: "Meet Sam for coffee"
		Result: "09:00-11:00", "Working at cafe, and at around 10:30, meet with Sam for coffee", "120"

    IMPORTANT: 
    Your response must be valid JSON without markdown formatting or code blocks. Do not wrap the JSON in ```json or ``` tags.
		Return a JSON array with this exact structure:
		[
			["HH:MM-HH:MM", "Updated activity description", duration_in_minutes],
			["HH:MM-HH:MM", "Updated activity description", duration_in_minutes],
			...
		]
		"""

    # 从 LLM 获取新日程
    for repeat in range(3):
        try:
            response = ChatGPT_single_request(schedule_prompt)
            # 解析 JSON 响应
            full_schedule = json.loads(response)
            
            # 验证时间范围是否与原始时间范围匹配
            if len(full_schedule) != len(original_time_ranges):
                print(f"\033[1;31m---in generate_future_hourly_schedule---Mismatch in schedule length: {len(full_schedule)} vs expected {len(original_time_ranges)}--\033[0m")
                continue
                
            mismatch = False
            for i, (time_range, _, dur) in enumerate(full_schedule):
                orig_time_range, orig_dur = original_time_ranges[i]
                if time_range != orig_time_range or dur != orig_dur:
                    print(f"\033[1;31m---in generate_future_hourly_schedule---Mismatch in time range or duration: {time_range}/{dur} vs expected {orig_time_range}/{orig_dur}--\033[0m")
                    mismatch = True
                    break
                    
            if mismatch:
                continue
                
            # 从响应中提取活动描述和持续时间（保持原始时间范围和持续时间）
            new_schedule = [[item[1], item[2]] for item in full_schedule]
            
            # 打印完整日程（包含时间范围）以便调试
            # print(f"\033[0;33m---in generate_future_hourly_schedule---", persona.scratch.name, f"new detailed schedule with time ranges:\033[0m")
            # for time_range, activity, duration in full_schedule:
            #     print(f"\033[0;33m  [\"{time_range}\", \"{activity}\", {duration}],\033[0m")
            
            # 返回只包含活动描述和持续时间的日程
            print(f"\033[0;33m---in generate_future_hourly_schedule---", persona.scratch.name, f"returning processed schedule (without time ranges)\033[0m")
            return new_schedule
            
        except Exception as e:
            print(f"\033[1;31m---in generate_future_hourly_schedule---Error generating schedule: {e}, repeat: {repeat}--\033[0m")
    
    print(f"\033[1;31m---in generate_future_hourly_schedule---Failed to get a valid schedule for {persona.scratch.name}--\033[0m")
    return False

def modify_future_schedule(persona, planning_thought):
    """
    分析规划思想并一次性修改整个未来的小时级别日程，以结合所有建议的变更，避免冲突。
    修改f_daily_schedule_hourly_org而不是f_daily_schedule，以便让decomposition机制正常运行。
    
    Args:
        persona: Persona 对象
        planning_thought: 要分析的规划思想
        
    Returns:
        如果日程成功修改则返回True，否则返回False
    """
    # 从规划思想中提取日程变更
    schedule_changes = extract_schedule_changes_from_thought(persona, planning_thought)
    
    if not schedule_changes:
        print(f"\033[0;33m---in modify_future_schedule---", persona.scratch.name, "no schedule changes needed--\033[0m")
        return False
    
    print(f"\033[0;33m---in modify_future_schedule---", persona.scratch.name, f"found {len(schedule_changes)} schedule changes to implement--\033[0m")
    
    # 为未来生成一个全新的完整日程
    new_hourly_schedule = generate_future_hourly_schedule(persona, schedule_changes)
    
    if not new_hourly_schedule:
        print(f"\033[1;31m---in modify_future_schedule---Failed to generate new hourly schedule for {persona.scratch.name}--\033[0m")
        return False
    
    # 计算从午夜开始的当前时间（以分钟为单位）
    curr_time_mins = (int(persona.scratch.curr_time.hour) * 60 + 
                     int(persona.scratch.curr_time.minute))
    
    # 找到小时日程中未来活动的起始索引
    future_start_index = None
    dur_sum = 0
    for i, (act, dur) in enumerate(persona.scratch.f_daily_schedule_hourly_org):
        if dur_sum <= curr_time_mins and dur_sum + dur > curr_time_mins:
            future_start_index = i
            break
        dur_sum += dur
    
    if future_start_index is None:
        print(f"\033[1;31m---in modify_future_schedule---Could not find current position in hourly schedule for {persona.scratch.name}--\033[0m")
        return False
    
    # 为当前被中断的活动创建一个部分条目
    remaining_mins = dur_sum + persona.scratch.f_daily_schedule_hourly_org[future_start_index][1] - curr_time_mins
    if remaining_mins > 0:
        current_activity = persona.scratch.f_daily_schedule_hourly_org[future_start_index][0]
        modified_schedule = [[current_activity, remaining_mins]] + new_hourly_schedule
    else:
        modified_schedule = new_hourly_schedule
    
    # 在修改小时日程之前先保存原始详细日程到当前时间点
    print(f"\033[0;33m---in modify_future_schedule---Preserving detailed schedule up to current time--\033[0m")
    
    # 用新日程替换未来的小时日程
    persona.scratch.f_daily_schedule_hourly_org = persona.scratch.f_daily_schedule_hourly_org[:future_start_index] + modified_schedule
    
    # 显示更新后的小时日程
    print(f"\033[0;33m---in modify_future_schedule---Updated hourly schedule for {persona.scratch.name}:--\033[0m")
    for i, (activity, duration) in enumerate(persona.scratch.f_daily_schedule_hourly_org):
        print(f"\033[0;32m  {i}: [{activity}, {duration}]--\033[0m")
    # 显示 f_daily_schedule
    print(f"\033[0;33m---in modify_future_schedule---Show f_daily_schedule for {persona.scratch.name} (This should be updated after next decomp): --\033[0m")
    for i, (activity, duration) in enumerate(persona.scratch.f_daily_schedule):
        print(f"\033[0;32m  {i}: [{activity}, {duration}]--\033[0m")
    
    # 记录变更
    print(f"\033[0;33m---in modify_future_schedule---Successfully updated {persona.scratch.name}'s hourly schedule with {len(schedule_changes)} changes--\033[0m")
    
    # 将重要的约定添加到commitments中
    today_date = persona.scratch.curr_time.strftime('%Y-%m-%d')
    if today_date not in persona.scratch.commitments:
        persona.scratch.commitments[today_date] = []
    
    for change in schedule_changes:
        if change.get('priority') == 'high':
            # 计算近似时间
            suggested_time = change.get('suggested_time', '')
            time_estimate = _estimate_time_from_suggestion(suggested_time, persona.scratch.curr_time)
            
            commitment = {
                "time": time_estimate,
                "duration": change.get('duration', 30),  # 转换为分钟
                "description": change['activity'],
                "with": _extract_person_from_activity(change['activity']),
                "location": _extract_location_from_activity(change['activity'])
            }
            
            # 避免重复添加相同的承诺
            if not any(c['description'] == commitment['description'] for c in persona.scratch.commitments[today_date]):
                persona.scratch.commitments[today_date].append(commitment)
                print(f"\033[0;33m---in modify_future_schedule---Added commitment: {commitment}--\033[0m")
    
    return True

def _estimate_time_from_suggestion(suggested_time, current_time):
    """辅助函数，从时间建议中估计具体时间"""
    # 首先检查是否有"around XX:XX"或"at XX:XX"等模式
    time_pattern = r'(?:around|at|about|approximately|by|near|close to)\s+(\d{1,2})[:\.]?(\d{2})?\s*(am|pm|AM|PM)?'
    matches = re.findall(time_pattern, suggested_time)
    
    if matches:
        hours, minutes, period = matches[0]
        hours = int(hours)
        minutes = int(minutes) if minutes else 0
        
        # 处理am/pm格式
        if period and period.lower() == 'pm' and hours < 12:
            hours += 12
        elif period and period.lower() == 'am' and hours == 12:
            hours = 0
            
        return f"{hours:02d}:{minutes:02d}"
        
    # 然后检查标准时间格式
    if ":" in suggested_time:
        return suggested_time
    
    # 检查时间段描述
    if suggested_time.lower() == "morning":
        if current_time.hour < 10:
            return f"{current_time.hour + 1}:00"
        else:
            return "10:00"
    elif suggested_time.lower() == "afternoon":
        if current_time.hour < 14:
            return "14:00"
        else:
            return f"{current_time.hour + 1}:00"
    elif suggested_time.lower() == "evening":
        if current_time.hour < 18:
            return "18:00"
        else:
            return f"{current_time.hour + 1}:00"
    elif suggested_time.lower() == "night":
        return "20:00"
    else:
        # 尝试解析纯数字（小时）
        try:
            hour = int(suggested_time)
            if 0 <= hour < 24:
                return f"{hour}:00"
        except:
            pass

    # 如果无法解析，则默认为当前时间后一小时
    next_hour = (current_time.hour + 1) % 24
    return f"{next_hour}:00"

def _extract_person_from_activity(activity):
    """从活动描述中提取可能的人名"""
    # 扩展人名列表以覆盖更多角色
    common_names = [
        "Isabella", "Maria", "Arthur", "Klaus", "John", "Jane", "Sam", "Mei", 
        "Rodriguez", "Lopez", "Burton", "Chen", "Smith", "Johnson", "Williams", 
        "Brown", "Jones", "Miller", "Davis", "Garcia", "Wilson"
    ]
    
    # 首先尝试找出"meet with X"或"talk to X"等模式
    meet_pattern = r"(?:meet|talk|speak|chat|discuss|see|visit|hang out)(?:\s+\w+){0,3}\s+(?:with|to)\s+(\w+)(?:\s+\w+)?"
    matches = re.findall(meet_pattern, activity, re.IGNORECASE)
    
    if matches:
        for name in matches:
            if name in common_names:
                return name
    
    # 如果上面的模式没找到，检查常见名字
    for name in common_names:
        if re.search(r'\b' + name + r'\b', activity):
            return name
            
    return ""

def _extract_location_from_activity(activity):
    """从活动描述中提取可能的位置"""
    # 扩展位置列表以覆盖更多地点
    common_locations = [
        "Cafe", "Park", "Home", "College", "School", "Library", "Playground", 
        "Studio", "Gym", "Restaurant", "Office", "Market", "Store", "Shop", 
        "Mall", "Theater", "Cinema", "Museum", "Gallery", "Garden", "Hobbs", 
        "Oak Hill", "jumping pit", "downtown"
    ]
    
    # 首先尝试找出"at X"或"to X"等模式
    location_pattern = r"(?:at|to|in|visit|go to|arrive at|be at|head to)\s+(?:the\s+)?([A-Z][a-z]+ ?(?:[A-Z][a-z]+)?)"
    matches = re.findall(location_pattern, activity)
    
    if matches:
        for loc in matches:
            if any(l.lower() in loc.lower() for l in common_locations):
                return loc
    
    # 如果上面的模式没找到，检查常见位置
    for location in common_locations:
        if re.search(r'\b' + location + r'\b', activity, re.IGNORECASE):
            return location
            
    return ""

def _matches_suggested_time(hour, suggested_time):
    """辅助函数，确定一个小时是否匹配建议的时间段。"""
    if suggested_time.lower() == "morning":
        return 5 <= hour <= 11
    elif suggested_time.lower() == "afternoon":
        return 12 <= hour <= 17
    elif suggested_time.lower() == "evening":
        return 18 <= hour <= 22
    else:
        # 尝试解析具体时间
        try:
            if ":" in suggested_time:
                suggested_hour = int(suggested_time.split(":")[0])
            else:
                suggested_hour = int(suggested_time)
            return abs(hour - suggested_hour) <= 2  # 在2小时内
        except:
            return True  # 如果没有明确的偏好，任何时间都可以

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



























