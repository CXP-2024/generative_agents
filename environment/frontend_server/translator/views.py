"""
Author: Joon Sung Park (joonspk@stanford.edu)
File: views.py
"""
import os
import string
import random
import json
from os import listdir
import datetime
import sys
import io
from contextlib import redirect_stdout, redirect_stderr
from django.views.decorators.csrf import csrf_exempt
import datetime
from django.shortcuts import render, redirect, HttpResponseRedirect
from django.http import HttpResponse, JsonResponse

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from global_methods import *

from django.contrib.staticfiles.templatetags.staticfiles import static
from .models import *
sys.path.append(os.path.join(os.path.dirname(__file__), '../../../reverie/backend_server'))
from reverie import ReverieServer

def landing(request): 
  context = {}
  template = "landing/landing.html"
  return render(request, template, context)


def demo(request, sim_code, step, play_speed="2"): 
  move_file = f"compressed_storage/{sim_code}/master_movement.json"
  meta_file = f"compressed_storage/{sim_code}/meta.json"
  step = int(step)
  play_speed_opt = {
      "1": 0.1,   # 非常慢
      "2": 0.2,   # 慢
      "3": 0.5,     # 正常速度
      "4": 1,     # 稍快
      "5": 2,     # 中速
      "6": 4,     # 较快
      "7": 10,    # 快
      "8": 18,    # 很快
      "9": 24,    # 非常快
      "10": 32    # 最快
  }
  if play_speed not in play_speed_opt: play_speed = 2
  else: play_speed = play_speed_opt[play_speed]

  # Loading the basic meta information about the simulation.
  meta = dict() 
  with open (meta_file) as json_file: 
    meta = json.load(json_file)

  sec_per_step = meta["sec_per_step"]
  start_datetime = datetime.datetime.strptime(meta["start_date"] + " 00:00:00", 
                                              '%B %d, %Y %H:%M:%S')
  for i in range(step): 
    start_datetime += datetime.timedelta(seconds=sec_per_step)
  start_datetime = start_datetime.strftime("%Y-%m-%dT%H:%M:%S")

  # Loading the movement file
  raw_all_movement = dict()
  with open(move_file) as json_file: 
    raw_all_movement = json.load(json_file)
 
  # Loading all names of the personas
  persona_names = dict()
  persona_names = []
  persona_names_set = set()
  for p in list(raw_all_movement["0"].keys()): 
    persona_names += [{"original": p, 
                       "underscore": p.replace(" ", "_"), 
                       "initial": p[0] + p.split(" ")[-1][0]}]
    persona_names_set.add(p)

  # <all_movement> is the main movement variable that we are passing to the 
  # frontend. Whereas we use ajax scheme to communicate steps to the frontend
  # during the simulation stage, for this demo, we send all movement 
  # information in one step. 
  all_movement = dict()

  # Preparing the initial step. 
  # <init_prep> sets the locations and descriptions of all agents at the
  # beginning of the demo determined by <step>. 
  init_prep = dict() 
  for int_key in range(step+1): 
    key = str(int_key)
    val = raw_all_movement[key]
    for p in persona_names_set: 
      if p in val: 
        init_prep[p] = val[p]
  persona_init_pos = dict()
  for p in persona_names_set: 
    persona_init_pos[p.replace(" ","_")] = init_prep[p]["movement"]
  all_movement[step] = init_prep

  # Finish loading <all_movement>
  for int_key in range(step+1, len(raw_all_movement.keys())): 
    all_movement[int_key] = raw_all_movement[str(int_key)]

  context = {"sim_code": sim_code,
             "step": step,
             "persona_names": persona_names,
             "persona_init_pos": json.dumps(persona_init_pos), 
             "all_movement": json.dumps(all_movement), 
             "start_datetime": start_datetime,
             "sec_per_step": sec_per_step,
             "play_speed": play_speed,
             "mode": "demo"}
  template = "demo/demo.html"

  return render(request, template, context)


def UIST_Demo(request): 
  return demo(request, "March20_the_ville_n25_UIST_RUN-step-1-141", 2160, play_speed="3")


def home(request):
    f_curr_sim_code = "temp_storage/curr_sim_code.json"
    f_curr_step = "temp_storage/curr_step.json"

    if not check_if_file_exists(f_curr_step): 
        context = {}
        template = "home/error_start_backend.html"
        return render(request, template, context)

    with open(f_curr_sim_code) as json_file:  
        sim_code = json.load(json_file)["sim_code"]
    
    with open(f_curr_step) as json_file:  
        step = json.load(json_file)["step"]

    os.remove(f_curr_step)

    # 修改这部分 - 创建包含所需属性的对象列表
    persona_names = []
    persona_names_set = set()
    for i in find_filenames(f"storage/{sim_code}/personas", ""): 
        x = i.split("/")[-1].strip()
        if x[0] != ".": 
            # 创建包含demo版本所需属性的对象
            persona_obj = type('PersonaInfo', (), {
                'original': x,
                'underscore': x.replace(" ", "_"),
                'full_name': x,
                'initial': "".join([word[0] for word in x.split()])
            })()
            persona_names.append(persona_obj)
            persona_names_set.add(x)

    persona_init_pos = []
    file_count = []
    for i in find_filenames(f"storage/{sim_code}/environment", ".json"):
        x = i.split("/")[-1].strip()
        if x[0] != ".": 
            file_count += [int(x.split(".")[0])]
    
    curr_json = f'storage/{sim_code}/environment/{str(max(file_count))}.json'
    with open(curr_json) as json_file:  
        persona_init_pos_dict = json.load(json_file)
        for key, val in persona_init_pos_dict.items(): 
            if key in persona_names_set: 
                persona_init_pos += [[key, val["x"], val["y"]]]

    context = {"sim_code": sim_code,
               "step": step, 
               "persona_names": persona_names,
               "persona_init_pos": persona_init_pos,
               "mode": "simulate"}
    template = "home/home.html"
    return render(request, template, context)


def replay(request, sim_code, step): 
    sim_code = sim_code
    step = int(step)

    # 修改这部分 - 创建包含所需属性的对象列表
    persona_names = []
    persona_names_set = set()
    for i in find_filenames(f"storage/{sim_code}/personas", ""): 
        x = i.split("/")[-1].strip()
        if x[0] != ".": 
            # 创建包含demo版本所需属性的对象
            persona_obj = type('PersonaInfo', (), {
                'original': x,
                'underscore': x.replace(" ", "_"),
                'full_name': x,
                'initial': "".join([word[0] for word in x.split()])
            })()
            persona_names.append(persona_obj)
            persona_names_set.add(x)

    persona_init_pos = []
    file_count = []
    for i in find_filenames(f"storage/{sim_code}/environment", ".json"):
        x = i.split("/")[-1].strip()
        if x[0] != ".": 
            file_count += [int(x.split(".")[0])]
    
    curr_json = f'storage/{sim_code}/environment/{str(max(file_count))}.json'
    with open(curr_json) as json_file:  
        persona_init_pos_dict = json.load(json_file)
        for key, val in persona_init_pos_dict.items(): 
            if key in persona_names_set: 
                persona_init_pos += [[key, val["x"], val["y"]]]

    context = {"sim_code": sim_code,
               "step": step,
               "persona_names": persona_names,
               "persona_init_pos": persona_init_pos, 
               "mode": "replay"}
    template = "home/home.html"
    return render(request, template, context)


def replay_persona_state(request, sim_code, step, persona_name): 
  sim_code = sim_code
  step = int(step)

  persona_name_underscore = persona_name
  persona_name = " ".join(persona_name.split("_"))
  memory = f"storage/{sim_code}/personas/{persona_name}/bootstrap_memory"
  if not os.path.exists(memory): 
    memory = f"compressed_storage/{sim_code}/personas/{persona_name}/bootstrap_memory"

  with open(memory + "/scratch.json") as json_file:  
    scratch = json.load(json_file)

  with open(memory + "/spatial_memory.json") as json_file:  
    spatial = json.load(json_file)

  with open(memory + "/associative_memory/nodes.json") as json_file:  
    associative = json.load(json_file)

  a_mem_event = []
  a_mem_chat = []
  a_mem_thought = []

  for count in range(len(associative.keys()), 0, -1): 
    node_id = f"node_{str(count)}"
    node_details = associative[node_id]

    if node_details["type"] == "event":
      a_mem_event += [node_details]

    elif node_details["type"] == "chat":
      a_mem_chat += [node_details]

    elif node_details["type"] == "thought":
      a_mem_thought += [node_details]
  
  context = {"sim_code": sim_code,
             "step": step,
             "persona_name": persona_name, 
             "persona_name_underscore": persona_name_underscore, 
             "scratch": scratch,
             "spatial": spatial,
             "a_mem_event": a_mem_event,
             "a_mem_chat": a_mem_chat,
             "a_mem_thought": a_mem_thought}
  template = "persona_state/persona_state.html"
  return render(request, template, context)


def path_tester(request):
  context = {}
  template = "path_tester/path_tester.html"
  return render(request, template, context)


def process_environment(request): 
  """
  <FRONTEND to BACKEND> 
  This sends the frontend visual world information to the backend server. 
  It does this by writing the current environment representation to 
  "storage/environment.json" file. 

  ARGS:
    request: Django request
  RETURNS: 
    HttpResponse: string confirmation message. 
  """
  # f_curr_sim_code = "temp_storage/curr_sim_code.json"
  # with open(f_curr_sim_code) as json_file:  
  #   sim_code = json.load(json_file)["sim_code"]

  data = json.loads(request.body)
  step = data["step"]
  sim_code = data["sim_code"]
  environment = data["environment"]

  with open(f"storage/{sim_code}/environment/{step}.json", "w") as outfile:
    outfile.write(json.dumps(environment, indent=2))

  return HttpResponse("received")


def update_environment(request): 
  """
  <BACKEND to FRONTEND> 
  This sends the backend computation of the persona behavior to the frontend
  visual server. 
  It does this by reading the new movement information from 
  "storage/movement.json" file.

  ARGS:
    request: Django request
  RETURNS: 
    HttpResponse
  """
  # f_curr_sim_code = "temp_storage/curr_sim_code.json"
  # with open(f_curr_sim_code) as json_file:  
  #   sim_code = json.load(json_file)["sim_code"]

  data = json.loads(request.body)
  step = data["step"]
  sim_code = data["sim_code"]

  response_data = {"<step>": -1}
  if (check_if_file_exists(f"storage/{sim_code}/movement/{step}.json")):
    with open(f"storage/{sim_code}/movement/{step}.json") as json_file: 
      response_data = json.load(json_file)
      response_data["<step>"] = step

  return JsonResponse(response_data)


def path_tester_update(request): 
  """
  Processing the path and saving it to path_tester_env.json temp storage for 
  conducting the path tester. 

  ARGS:
    request: Django request
  RETURNS: 
    HttpResponse: string confirmation message. 
  """
  data = json.loads(request.body)
  camera = data["camera"]

  with open(f"temp_storage/path_tester_env.json", "w") as outfile:
    outfile.write(json.dumps(camera, indent=2))

  return HttpResponse("received")

def wait_and_read_command_output(command, sim_code, timeout=30):
    """等待并读取命令执行结果"""
    import time
    
    temp_storage = "temp_storage"
    output_file = f"{temp_storage}/command_output.json"
    
    start_time = time.time()
    while time.time() - start_time < timeout:
        if os.path.exists(output_file):
            try:
                with open(output_file, 'r') as f:
                    output_data = json.load(f)
                
                os.remove(output_file)
                
                if output_data.get('command') == command:
                    return {
                        'success': output_data.get('success', True),
                        'output': output_data.get('output', ''),
                        'command_type': 'general'
                    }
                
            except Exception as e:
                continue
        
        time.sleep(0.5)
    
    return {
        'success': False,
        'error': f'Command timeout after {timeout} seconds. Reverie backend may not be running.'
    }

@csrf_exempt
def execute_console_command(request):
    """执行控制台命令 - 支持对话交互"""
    print(f"📨 收到控制台命令请求: {request.method}")
    
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            command = data.get('command', '').strip()
            sim_code = data.get('sim_code')
            
            print(f"📋 命令: {command}")
            print(f"📋 模拟代码: {sim_code}")
            
            if not command:
                return JsonResponse({
                    'success': False,
                    'error': 'No command provided'
                })
            
            # 特殊处理：help命令
            if command.lower() == 'help':
                return JsonResponse({
                    'success': True,
                    'output': get_console_help_text(),
                    'command_type': 'help'
                })
            
            # 特殊处理：status命令
            if command.lower() in ['info', 'status']:
                status_output = get_status_from_files(sim_code)
                return JsonResponse({
                    'success': True,
                    'output': status_output,
                    'command_type': 'status'
                })
            
            # 检查命令类型
            conversation_commands = ['converse as', 'converse with', 'say ', 'end_conversation']
            long_running_commands = ['run', 'debug run']
            is_conversation = any(command.lower().startswith(cmd) for cmd in conversation_commands)
            is_long_running = any(command.lower().startswith(cmd) for cmd in long_running_commands)
            
            # 写入命令到文件
            command_result = write_command_to_file(command, sim_code)
            if not command_result['success']:
                return JsonResponse(command_result)
            
            # 根据命令类型调整等待时间
            if is_conversation:
                timeout = 60  # 对话命令等待1分钟
            elif is_long_running:
                timeout = 600  # 长时间命令等待10分钟
            else:
                timeout = 30  # 普通命令等待30秒
            
            # 等待结果
            output_result = wait_and_read_command_output(command, sim_code, timeout)
            
            # 如果是对话命令，添加特殊标记
            if is_conversation:
                output_result['command_type'] = 'conversation'
            
            return JsonResponse(output_result)
            
        except Exception as e:
            import traceback
            error_trace = traceback.format_exc()
            print(f"❌ 控制台命令执行错误: {e}")
            return JsonResponse({
                'success': False,
                'error': f'Error: {str(e)}',
                'traceback': error_trace
            })
    
    return JsonResponse({
        'success': False,
        'error': 'Invalid request method'
    })

def write_command_to_file(command, sim_code):
    """将命令写入文件，供reverie后端读取"""
    try:
        # 确保temp_storage目录存在
        temp_storage = "temp_storage"
        if not os.path.exists(temp_storage):
            os.makedirs(temp_storage)
        
        # 创建命令文件
        command_data = {
            "command": command,
            "sim_code": sim_code,
            "timestamp": datetime.datetime.now().isoformat(),
            "status": "pending"
        }
        
        command_file = f"{temp_storage}/frontend_command.json"
        with open(command_file, "w") as outfile:
            outfile.write(json.dumps(command_data, indent=2))
        
        # 创建一个信号文件，告诉后端有新命令
        signal_file = f"{temp_storage}/command_ready.signal"
        with open(signal_file, "w") as outfile:
            outfile.write("ready")
        
        print(f"✅ 命令已写入文件: {command}")
        return {'success': True}
        
    except Exception as e:
        print(f"❌ 写入命令文件失败: {e}")
        return {
            'success': False,
            'error': f'Failed to write command: {str(e)}'
        }

def get_status_from_files(sim_code):
    """从文件系统读取模拟状态"""
    try:
        sim_folder = f"storage/{sim_code}"
        if not os.path.exists(sim_folder):
            return f"❌ Simulation folder not found: {sim_code}\n💡 请确保您已经通过reverie.py创建了这个模拟"
        
        # 读取meta信息
        meta_file = f"{sim_folder}/reverie/meta.json"
        if os.path.exists(meta_file):
            with open(meta_file) as f:
                meta_data = json.load(f)
            
            # 检查当前步数文件
            temp_storage = "temp_storage"
            current_step = meta_data.get('step', 0)
            
            # 尝试读取当前步数
            curr_step_file = f"{temp_storage}/curr_step.json"
            if os.path.exists(curr_step_file):
                try:
                    with open(curr_step_file) as f:
                        step_data = json.load(f)
                    current_step = step_data.get('step', current_step)
                except:
                    pass
            
            # 检查reverie是否正在运行
            reverie_running = "❌ Not running"
            command_file = f"{temp_storage}/frontend_command.json"
            if os.path.exists(command_file):
                reverie_running = "🟡 May be running (command file exists)"
            
            status_info = f"""
🎮 Simulation Status (File-based):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🗂️ Simulation Code: {sim_code}
📊 Current Step: {current_step}
📅 Start Date: {meta_data.get('start_date', 'Unknown')}
👥 Personas: {len(meta_data.get('persona_names', []))}
🔧 Reverie Backend: {reverie_running}

📋 Available personas:
{chr(10).join([f"  • {name}" for name in meta_data.get('persona_names', [])])}

💡 To interact with simulation, make sure reverie.py is running
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
            return status_info
        else:
            return f"❌ Meta file not found for simulation: {sim_code}"
            
    except Exception as e:
        return f"❌ Error reading simulation info: {str(e)}"

def get_console_help_text():
    """返回控制台帮助文本"""
    return """
🎮 Reverie Console Commands (File-based Communication):

📊 Simulation Control:
  • status / info                 - Show simulation status from files
  • save                          - Save simulation progress
  • run <steps>                   - Run simulation for specified steps
  • debug run <steps>             - Run simulation in debug mode
  • print current time            - Show current simulation time

👥 Persona Management:
  • print all persona schedule    - Show all personas' schedules
  • print persona schedule <name> - Show specific persona's schedule
  • print persona associative memory (event) <name>   - Show event memory
  • print persona associative memory (thought) <name> - Show thought memory
  • print persona associative memory (chat) <name>    - Show chat memory

💬 Interaction:
  • converse with <persona>       - Start conversation with persona

Examples:
  status                                        # Check simulation status
  run 10                                       # Run 10 steps
  print persona schedule Isabella Rodriguez    # Check persona schedule
  save                                         # Save simulation

💡 Note: Commands are sent to reverie.py via files. Make sure reverie.py is running!
"""

import json
import os
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

@csrf_exempt
@require_http_methods(["POST"])
def create_pause_file(request):
    """直接创建暂停文件，不通过命令队列"""
    try:
        # 获取temp_storage路径
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
        temp_storage = os.path.join(project_root, "environment", "frontend_server", "temp_storage")
        
        # 确保目录存在
        os.makedirs(temp_storage, exist_ok=True)
        
        # 创建暂停文件
        pause_file = os.path.join(temp_storage, "simulation_pause.flag")
        
        with open(pause_file, 'w') as f:
            f.write('0')  # 写入暂停信号
        
        # 验证文件创建
        if os.path.exists(pause_file):
            print(f"✅ Pause file created successfully: {pause_file}")
            return JsonResponse({
                'success': True,
                'message': 'Pause file created successfully',
                'file_path': pause_file
            })
        else:
            print(f"❌ Failed to create pause file: {pause_file}")
            return JsonResponse({
                'success': False,
                'error': 'Failed to create pause file'
            })
            
    except Exception as e:
        print(f"❌ Error creating pause file: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        })

@csrf_exempt
@require_http_methods(["POST"])
def check_pause_status(request):
    """检查暂停状态，不通过命令队列"""
    try:
        # 获取temp_storage路径
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
        temp_storage = os.path.join(project_root, "environment", "frontend_server", "temp_storage")
        
        pause_file = os.path.join(temp_storage, "simulation_pause.flag")
        running_file = os.path.join(temp_storage, "simulation_running.flag")
        
        if not os.path.exists(pause_file) and not os.path.exists(running_file):
            status = "Pause file not found - simulation stopped"
        elif os.path.exists(pause_file):
            status = "Pause file exists - waiting for simulation to stop"
        elif os.path.exists(running_file):
            status = "Simulation is still running"
        else:
            status = "Unknown state"
            
        return JsonResponse({
            'success': True,
            'status': status,
            'pause_file_exists': os.path.exists(pause_file),
            'running_file_exists': os.path.exists(running_file)
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })