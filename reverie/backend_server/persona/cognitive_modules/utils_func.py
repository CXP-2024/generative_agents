import json
import re

from persona.prompt_template.run_gpt_prompt import *
from persona.prompt_template.gpt_structure import *
from global_methods import *

## Utility function to show the daily schedule in a readable format
def show_f_daily_schedule_better(persona):
    """
    Display a persona's daily schedule in a readable format showing time ranges,
    activity descriptions, and durations.
    
    Format: ["HH:MM-HH:MM", "activity description", duration_in_minutes]
    
    Args:
        persona: The persona whose schedule we want to display
    """
    if not persona.scratch.f_daily_schedule:
        print("\033[1;33mNo daily schedule available.\033[0m")
        return
    
    print(f"\033[1;36m{persona.scratch.name}'s Daily Schedule:\033[0m")
    
    # Calculate and format the schedule with time ranges
    curr_min_sum = 0
    formatted_schedule = []
    
    for activity, duration in persona.scratch.f_daily_schedule:
        # Calculate start time
        start_hour = int(curr_min_sum / 60) % 24
        start_min = curr_min_sum % 60
        
        # Add duration to get end time
        curr_min_sum += duration
        end_hour = int(curr_min_sum / 60) % 24
        end_min = curr_min_sum % 60
        
        # Format as HH:MM-HH:MM
        time_range = f"{start_hour:02d}:{start_min:02d}-{end_hour:02d}:{end_min:02d}"
        
        # Add to formatted list
        formatted_schedule.append([time_range, activity, duration])
    
    # Display the formatted schedule
    for time_range, activity, duration in formatted_schedule:
        print(f"\033[1;36m  [\"{time_range}\", \"{activity}\", {duration}], \033[0m")

def show_f_daily_schedule_hourly_better(persona):
    """
    Display a persona's daily schedule in a readable format showing time ranges,
    activity descriptions, and durations.
    
    Format: ["HH:MM-HH:MM", "activity description", duration_in_minutes]
    
    Args:
        persona: The persona whose schedule we want to display
    """
    if not persona.scratch.f_daily_schedule_hourly_org:
        print("\033[1;33mNo daily schedule available.\033[0m")
        return
    
    print(f"\033[1;36m{persona.scratch.name}'s Hourly Daily Schedule:\033[0m")
    
    # Calculate and format the schedule with time ranges
    curr_min_sum = 0
    formatted_schedule = []

    for activity, duration in persona.scratch.f_daily_schedule_hourly_org:
        # Calculate start time
        start_hour = int(curr_min_sum / 60) % 24
        start_min = curr_min_sum % 60
        
        # Add duration to get end time
        curr_min_sum += duration
        end_hour = int(curr_min_sum / 60) % 24
        end_min = curr_min_sum % 60
        
        # Format as HH:MM-HH:MM
        time_range = f"{start_hour:02d}:{start_min:02d}-{end_hour:02d}:{end_min:02d}"
        
        # Add to formatted list
        formatted_schedule.append([time_range, activity, duration])
    
    # Display the formatted schedule
    for time_range, activity, duration in formatted_schedule:
        print(f"\033[1;36m  [\"{time_range}\", \"{activity}\", {duration}], \033[0m")


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
	You are analyzing a planning thought from {persona.scratch.name} to identify concrete schedule changes needed for today.

	Planning thought: "{planning_thought}"

	Current time: {persona.scratch.curr_time.strftime('%H:%M')}

	Task: Extract all specific activities that need to be scheduled today. Only include changes that:
	1. Are concrete, actionable activities (not just thoughts or wishes)
	2. Have a clear time requirement or urgency
	3. Are relevant for today's schedule
	4. Can realistically be completed

	For each identified change, provide:
	- Detailed activity description including who/what/where if mentioned
	- Realistic duration in minutes
	- Preferred time period or specific time if indicated
	- Priority level based on urgency/importance in the thought

	Guidelines:
	- Maximum 3 changes total to avoid over-scheduling
	- Prioritize activities with specific time mentions or high urgency
	- Ignore vague future plans or general thoughts
	- If no concrete changes are identified, return empty list

	Response format (valid JSON only, without any markdown ``` code blocks):
	[
		{{
		  "change_needed": true,
		  "activity": "specific activity description with context",
		  "duration": integer_minutes,
		  "suggested_time": "HH:MM format or morning/afternoon/evening",
		  "priority": "high/medium/low",
		}},
		{{
      "change_needed": true,
      "activity": "detailed activity description (can include sub-activities and transitions)",
      "duration": minutes_as_integer,
      "suggested_time": "HH:MM format or morning/afternoon/evening",
      "priority": "high/medium/low"
    }}
	]

	If no schedule changes are needed, return: []
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
    同时修改f_daily_schedule_hourly_org和f_daily_schedule中未decompose的部分，
    以确保日程变更能够正确实现。
    
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
    
    # ===== 步骤1: 保存原始的hourly日程 =====
    original_hourly_schedule = persona.scratch.f_daily_schedule_hourly_org.copy()
    
    # ===== 步骤2: 找出小时制日程中当前所在的小时块索引 =====
    hourly_future_start_index = None
    hourly_dur_sum = 0
    
    for i, (act, dur) in enumerate(original_hourly_schedule):
        if hourly_dur_sum <= curr_time_mins and hourly_dur_sum + dur > curr_time_mins:
            hourly_future_start_index = i
            break
        hourly_dur_sum += dur
    
    if hourly_future_start_index is None:
        print(f"\033[1;31m---in modify_future_schedule---Could not find current position in hourly schedule for {persona.scratch.name}--\033[0m")
        return False
    
    # ===== 步骤3: 更新f_daily_schedule_hourly_org =====
    # 保持过去的活动不变，直接替换从当前时间点开始的所有活动
    new_f_daily_schedule_hourly_org = original_hourly_schedule[:hourly_future_start_index]
    
    # 添加新的活动描述，但保持原始时间长度不变
    for i in range(hourly_future_start_index, len(original_hourly_schedule)):
        idx_in_new = i - hourly_future_start_index  # 在new_hourly_schedule中的对应索引
        
        if idx_in_new < len(new_hourly_schedule):
            # 使用新生成的描述，但保持原有时长不变
            activity_desc = new_hourly_schedule[idx_in_new][0]
            original_duration = original_hourly_schedule[i][1]
            new_f_daily_schedule_hourly_org.append([activity_desc, original_duration])
        else:
            # 超出新日程范围，保留原活动不变
            print(f"\033[0;33m---in modify_future_schedule---", persona.scratch.name, f"keeping original activity: {original_hourly_schedule[i][0]}--\033[0m")
            new_f_daily_schedule_hourly_org.append(original_hourly_schedule[i])
    
    # 更新f_daily_schedule_hourly_org
    persona.scratch.f_daily_schedule_hourly_org = new_f_daily_schedule_hourly_org
    
    # 显示更新后的小时日程
    print(f"\033[0;33m---in modify_future_schedule---Updated hourly schedule for {persona.scratch.name}:--\033[0m")
    show_f_daily_schedule_hourly_better(persona)
    
    print(f"\033[0;33m---in modify_future_schedule---Updated hourly schedule (keeping hour-based time structure), now handling daily schedule, Original:--\033[0m")
    # show original_f_daily_schedule
    show_f_daily_schedule_better(persona)
    
    # ===== 步骤4: 简化的f_daily_schedule更新方法 =====
    # 找到当前活动在daily_schedule中的位置
    daily_future_start_index = None
    daily_dur_sum = 0
    
    for i, (act, dur) in enumerate(persona.scratch.f_daily_schedule):
        if daily_dur_sum <= curr_time_mins and daily_dur_sum + dur > curr_time_mins:
            daily_future_start_index = i
            break
        daily_dur_sum += dur
    
    if daily_future_start_index is None:
        print(f"\033[1;31m---in modify_future_schedule---Could not find current position in daily schedule for {persona.scratch.name}--\033[0m")
        return True  # 已更新hourly_schedule，所以返回True
    
    # ===== 步骤5: 直接构建新的daily schedule =====
    # 5.1 保留过去的活动
    new_daily_schedule = persona.scratch.f_daily_schedule[: daily_future_start_index+1]
    
    # 5.2 寻找第一个匹配的未来活动
    for i in range(daily_future_start_index + 1, len(persona.scratch.f_daily_schedule)):
        act = persona.scratch.f_daily_schedule[i][0]
        
        # 计算当前活动在f_daily_schedule中的开始时间
        current_activity_start_time = 0
        for j in range(i):
            current_activity_start_time += persona.scratch.f_daily_schedule[j][1]
        current_activity_hour = int(current_activity_start_time / 60)
        
        # 获取当前时间的小时数
        current_time_hour = int(persona.scratch.curr_time.hour)
        
        # 尝试在original_hourly_schedule中找到匹配
        match_found = False
        for h_idx, (h_act, _) in enumerate(original_hourly_schedule):
            if act == h_act:
                # 计算hourly_schedule中这个活动的开始时间
                hourly_activity_start_time = 0
                for k in range(h_idx):
                    hourly_activity_start_time += original_hourly_schedule[k][1]
                hourly_activity_hour = int(hourly_activity_start_time / 60)
                
                # 检查时间条件：hourly活动的开始时间必须 >= 当前时间的hour值
                if hourly_activity_hour >= current_time_hour:
                    print(f"\033[0;33m---in modify_future_schedule---", persona.scratch.name, f"found matching activity: {h_act} at hour {hourly_activity_hour} (current hour: {current_time_hour})--\033[0m")
                    match_found = True
                    
                    # 找到匹配点，直接替换从这里开始的所有未来活动
                    next_hourly_idx = h_idx
                    
                    # 从matching_hourly_idx位置开始，将所有后续活动添加到new_daily_schedule
                    for j in range(next_hourly_idx, len(new_f_daily_schedule_hourly_org)):
                        h_act = new_f_daily_schedule_hourly_org[j][0]
                        h_dur = new_f_daily_schedule_hourly_org[j][1]
                        new_daily_schedule.append([h_act, h_dur])
                    
                    break
                else:
                    print(f"\033[0;33m---in modify_future_schedule---", persona.scratch.name, f"activity {h_act} found but at wrong time: hour {hourly_activity_hour} < current hour {current_time_hour}, continuing search--\033[0m")
        
        if match_found:
            # 已找到匹配并添加了所有后续活动，退出循环
            break
        else:
            # 如果没有找到匹配，则保留当前活动
            new_daily_schedule.append([act, persona.scratch.f_daily_schedule[i][1]])
    
    # 如果没找到匹配，则保留当前活动之后的所有原始活动
    if len(new_daily_schedule) <= daily_future_start_index + 1:
        print(f"\033[0;33m---in modify_future_schedule---No matching future activities found, keeping original schedule--\033[0m")
        new_daily_schedule.extend(persona.scratch.f_daily_schedule[daily_future_start_index + 1:])
        
    # 更新f_daily_schedule
    persona.scratch.f_daily_schedule = new_daily_schedule
    
    # ===== 步骤6: 验证更新后的时间总和是否匹配 =====
    hourly_total_duration = sum(dur for _, dur in persona.scratch.f_daily_schedule_hourly_org)
    daily_total_duration = sum(dur for _, dur in persona.scratch.f_daily_schedule)
    
    if hourly_total_duration != daily_total_duration:
        print(f"\033[1;31m---in modify_future_schedule---Warning: Duration mismatch after update! " +
              f"hourly_total={hourly_total_duration}, daily_total={daily_total_duration}--\033[0m")
        
        # 可选：尝试调整最后一个活动的时间以匹配总时长
        if new_daily_schedule and hourly_total_duration > 0:
            time_diff = hourly_total_duration - daily_total_duration
            if time_diff > 0:
                last_act, last_dur = new_daily_schedule[-1]
                new_daily_schedule[-1] = [last_act, last_dur + time_diff]
                print(f"\033[0;33m---in modify_future_schedule---Adjusted last activity duration to match total time--\033[0m")
                # 重新更新f_daily_schedule
                persona.scratch.f_daily_schedule = new_daily_schedule
    
    # 显示更新后的日常日程
    print(f"\033[0;33m---in modify_future_schedule---Updated daily schedule for {persona.scratch.name}:--\033[0m")
    show_f_daily_schedule_better(persona)
    
    # 记录变更
    print(f"\033[0;32m---in modify_future_schedule---Successfully updated {persona.scratch.name}'s schedules with {len(schedule_changes)} changes--\033[0m")
    
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
                "duration": change.get('duration', 60),
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