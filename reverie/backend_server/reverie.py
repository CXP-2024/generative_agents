"""
Author: Joon Sung Park (joonspk@stanford.edu)

File: reverie.py
Description: This is the main program for running generative agent simulations
that defines the ReverieServer class. This class maintains and records all  
states related to the simulation. The primary mode of interaction for those  
running the simulation should be through the open_server function, which  
enables the simulator to input command-line prompts for running and saving  
the simulation, among other tasks.
 
Release note (June 14, 2023) -- Reverie implements the core simulation 
mechanism described in my paper entitled "Generative Agents: Interactive 
Simulacra of Human Behavior." If you are reading through these lines after 
having read the paper, you might notice that I use older terms to describe 
generative agents and their cognitive modules here. Most notably, I use the 
term "personas" to refer to generative agents, "associative memory" to refer 
to the memory stream, and "reverie" to refer to the overarching simulation 
framework.
"""
import json
import numpy
import datetime
import pickle
import time
import math
import os
import shutil
import traceback
import threading

from selenium import webdriver

from global_methods import *
from utils import *
from maze import *
from persona.persona import *

##############################################################################
#                                  REVERIE                                   #
##############################################################################

class ReverieServer: 
  def __init__(self, 
               fork_sim_code,
               sim_code):
    # FORKING FROM A PRIOR SIMULATION:
    # <fork_sim_code> indicates the simulation we are forking from. 
    # Interestingly, all simulations must be forked from some initial 
    # simulation, where the first simulation is "hand-crafted".
    self.fork_sim_code = fork_sim_code
    fork_folder = f"{fs_storage}/{self.fork_sim_code}"

    # <sim_code> indicates our current simulation. The first step here is to 
    # copy everything that's in <fork_sim_code>, but edit its 
    # reverie/meta/json's fork variable. 
    self.sim_code = sim_code
    sim_folder = f"{fs_storage}/{self.sim_code}"
    copyanything(fork_folder, sim_folder)

    with open(f"{sim_folder}/reverie/meta.json") as json_file:  
      reverie_meta = json.load(json_file)

    with open(f"{sim_folder}/reverie/meta.json", "w") as outfile: 
      reverie_meta["fork_sim_code"] = fork_sim_code
      outfile.write(json.dumps(reverie_meta, indent=2))

    # LOADING REVERIE'S GLOBAL VARIABLES
    # The start datetime of the Reverie: 
    # <start_datetime> is the datetime instance for the start datetime of 
    # the Reverie instance. Once it is set, this is not really meant to 
    # change. It takes a string date in the following example form: 
    # "June 25, 2022"
    # e.g., ...strptime(June 25, 2022, "%B %d, %Y")
    self.start_time = datetime.datetime.strptime(
                        f"{reverie_meta['start_date']}, 00:00:00",  
                        "%B %d, %Y, %H:%M:%S")
    # <curr_time> is the datetime instance that indicates the game's current
    # time. This gets incremented by <sec_per_step> amount everytime the world
    # progresses (that is, everytime curr_env_file is recieved). 
    self.curr_time = datetime.datetime.strptime(reverie_meta['curr_time'], 
                                                "%B %d, %Y, %H:%M:%S")
    # <sec_per_step> denotes the number of seconds in game time that each 
    # step moves foward. 
    self.sec_per_step = reverie_meta['sec_per_step']
    
    # <maze> is the main Maze instance. Note that we pass in the maze_name
    # (e.g., "double_studio") to instantiate Maze. 
    # e.g., Maze("double_studio")
    self.maze = Maze(reverie_meta['maze_name'])
    
    # <step> denotes the number of steps that our game has taken. A step here
    # literally translates to the number of moves our personas made in terms
    # of the number of tiles. 
    self.step = reverie_meta['step']

    # SETTING UP PERSONAS IN REVERIE
    # <personas> is a dictionary that takes the persona's full name as its 
    # keys, and the actual persona instance as its values.
    # This dictionary is meant to keep track of all personas who are part of
    # the Reverie instance. 
    # e.g., ["Isabella Rodriguez"] = Persona("Isabella Rodriguezs")
    self.personas = dict()
    # <personas_tile> is a dictionary that contains the tile location of
    # the personas (!-> NOT px tile, but the actual tile coordinate).
    # The tile take the form of a set, (row, col). 
    # e.g., ["Isabella Rodriguez"] = (58, 39)
    self.personas_tile = dict()
    
    # # <persona_convo_match> is a dictionary that describes which of the two
    # # personas are talking to each other. It takes a key of a persona's full
    # # name, and value of another persona's full name who is talking to the 
    # # original persona. 
    # # e.g., dict["Isabella Rodriguez"] = ["Maria Lopez"]
    # self.persona_convo_match = dict()
    # # <persona_convo> contains the actual content of the conversations. It
    # # takes as keys, a pair of persona names, and val of a string convo. 
    # # Note that the key pairs are *ordered alphabetically*. 
    # # e.g., dict[("Adam Abraham", "Zane Xu")] = "Adam: baba \n Zane:..."
    # self.persona_convo = dict()

    # Loading in all personas. 
    init_env_file = f"{sim_folder}/environment/{str(self.step)}.json"
    init_env = json.load(open(init_env_file))
    for persona_name in reverie_meta['persona_names']: 
      persona_folder = f"{sim_folder}/personas/{persona_name}"
      p_x = init_env[persona_name]["x"]
      p_y = init_env[persona_name]["y"]
      curr_persona = Persona(persona_name, persona_folder)

      self.personas[persona_name] = curr_persona
      self.personas_tile[persona_name] = (p_x, p_y)
      self.maze.tiles[p_y][p_x]["events"].add(curr_persona.scratch
                                              .get_curr_event_and_desc())

    # REVERIE SETTINGS PARAMETERS:  
    # <server_sleep> denotes the amount of time that our while loop rests each
    # cycle; this is to not kill our machine. 
    self.server_sleep = 0.1

    # SIGNALING THE FRONTEND SERVER: 
    # curr_sim_code.json contains the current simulation code, and
    # curr_step.json contains the current step of the simulation. These are 
    # used to communicate the code and step information to the frontend. 
    # Note that step file is removed as soon as the frontend opens up the 
    # simulation. 
    curr_sim_code = dict()
    curr_sim_code["sim_code"] = self.sim_code
    with open(f"{fs_temp_storage}/curr_sim_code.json", "w") as outfile: 
      outfile.write(json.dumps(curr_sim_code, indent=2))
    
    curr_step = dict()
    curr_step["step"] = self.step
    with open(f"{fs_temp_storage}/curr_step.json", "w") as outfile: 
      outfile.write(json.dumps(curr_step, indent=2))


  def save(self): 
    """
    Save all Reverie progress -- this includes Reverie's global state as well
    as all the personas.  

    INPUT
      None
    OUTPUT 
      None
      * Saves all relevant data to the designated memory directory
    """
    # <sim_folder> points to the current simulation folder.
    sim_folder = f"{fs_storage}/{self.sim_code}"

    # Save Reverie meta information.
    reverie_meta = dict() 
    reverie_meta["fork_sim_code"] = self.fork_sim_code
    reverie_meta["start_date"] = self.start_time.strftime("%B %d, %Y")
    reverie_meta["curr_time"] = self.curr_time.strftime("%B %d, %Y, %H:%M:%S")
    reverie_meta["sec_per_step"] = self.sec_per_step
    reverie_meta["maze_name"] = self.maze.maze_name
    reverie_meta["persona_names"] = list(self.personas.keys())
    reverie_meta["step"] = self.step
    reverie_meta_f = f"{sim_folder}/reverie/meta.json"
    with open(reverie_meta_f, "w") as outfile: 
      outfile.write(json.dumps(reverie_meta, indent=2))

    # Save the personas.
    for persona_name, persona in self.personas.items(): 
      save_folder = f"{sim_folder}/personas/{persona_name}/bootstrap_memory"
      persona.save(save_folder)


  def start_path_tester_server(self): 
    """
    Starts the path tester server. This is for generating the spatial memory
    that we need for bootstrapping a persona's state. 

    To use this, you need to open server and enter the path tester mode, and
    open the front-end side of the browser. 

    INPUT 
      None
    OUTPUT 
      None
      * Saves the spatial memory of the test agent to the path_tester_env.json
        of the temp storage. 
    """
    def print_tree(tree): 
      def _print_tree(tree, depth):
        dash = " >" * depth

        if type(tree) == type(list()): 
          if tree:
            print (dash, tree)
          return 

        for key, val in tree.items(): 
          if key: 
            print (dash, key)
          _print_tree(val, depth+1)
      
      _print_tree(tree, 0)

    # <curr_vision> is the vision radius of the test agent. Recommend 8 as 
    # our default. 
    curr_vision = 8
    # <s_mem> is our test spatial memory. 
    s_mem = dict()

    # The main while loop for the test agent. 
    while (True): 
      try: 
        curr_dict = {}
        tester_file = fs_temp_storage + "/path_tester_env.json"
        if check_if_file_exists(tester_file): 
          with open(tester_file) as json_file: 
            curr_dict = json.load(json_file)
            os.remove(tester_file)
          
          # Current camera location
          curr_sts = self.maze.sq_tile_size
          curr_camera = (int(math.ceil(curr_dict["x"]/curr_sts)), 
                         int(math.ceil(curr_dict["y"]/curr_sts))+1)
          curr_tile_det = self.maze.access_tile(curr_camera)

          # Initiating the s_mem
          world = curr_tile_det["world"]
          if curr_tile_det["world"] not in s_mem: 
            s_mem[world] = dict()

          # Iterating throughn the nearby tiles.
          nearby_tiles = self.maze.get_nearby_tiles(curr_camera, curr_vision)
          for i in nearby_tiles: 
            i_det = self.maze.access_tile(i)
            if (curr_tile_det["sector"] == i_det["sector"] 
                and curr_tile_det["arena"] == i_det["arena"]): 
              if i_det["sector"] != "": 
                if i_det["sector"] not in s_mem[world]: 
                  s_mem[world][i_det["sector"]] = dict()
              if i_det["arena"] != "": 
                if i_det["arena"] not in s_mem[world][i_det["sector"]]: 
                  s_mem[world][i_det["sector"]][i_det["arena"]] = list()
              if i_det["game_object"] != "": 
                if (i_det["game_object"] 
                    not in s_mem[world][i_det["sector"]][i_det["arena"]]):
                  s_mem[world][i_det["sector"]][i_det["arena"]] += [
                                                         i_det["game_object"]]

        # Incrementally outputting the s_mem and saving the json file. 
        print ("= " * 15)
        out_file = fs_temp_storage + "/path_tester_out.json"
        with open(out_file, "w") as outfile: 
          outfile.write(json.dumps(s_mem, indent=2))
        print_tree(s_mem)

      except:
        pass

      time.sleep(self.server_sleep * 10)


  # 在 ReverieServer 类中添加以下方法

# 修改 start_interactive_conversation 方法
  def start_interactive_conversation(self, persona_name, user_role="User", user_description=""):
    """
    Start an interactive conversation with a specified persona.
    
    INPUT:
      persona_name: Name of the persona to converse with
      user_role: The role/character the user is playing
      user_description: Brief description of the user's character
    """
    from persona.cognitive_modules.converse import (
        generate_summarize_ideas, 
        generate_next_line, 
        generate_inner_thought,
        generate_action_event_triple,
        generate_poig_score
    )
    from persona.cognitive_modules.retrieve import new_retrieve
    from persona.prompt_template.run_gpt_prompt import (
        run_gpt_generate_safety_score
    )
    from persona.prompt_template.gpt_structure import get_embedding
    
    persona = self.personas[persona_name]
    curr_convo = []
    interlocutor_desc = user_role
    
    # Create enhanced description for AI understanding
    if user_description:
        enhanced_interlocutor_desc = f"{user_role} ({user_description})"
    else:
        enhanced_interlocutor_desc = user_role
    
    print(f"\n=== Starting conversation between {persona_name} and {user_role} ===")
    if user_description:
        print(f"Playing as: {user_role} - {user_description}")
    print("Type 'end_convo' to finish the conversation")
    print("Note: This conversation will be saved to the agent's memory\n")
    
    # Add initial context if user is playing a character
    if user_role != "User" and user_description:
        context_prompt = f"You are now talking with {user_role}, who is {user_description}. Respond appropriately to this character."
        print(f"\033[0;36m[Context set: {persona_name} now knows they're talking with {enhanced_interlocutor_desc}]\033[0m\n")
    
    while True:
        try:
            line = input(f"{user_role}: ").strip()
            if not line:
                continue
                
            if line == "end_convo":
                break
            
            # Safety check. Disabled for now to allow free conversation.
            #safety_score = int(run_gpt_generate_safety_score(persona, line)[0])
            #if safety_score >= 8:
            #    print(f"\n{persona.scratch.name} is a computational agent, and as such, it may be inappropriate to attribute human agency to the agent in your communication.")
            #    continue
            
            # Retrieve relevant memories
            retrieved = new_retrieve(persona, [line], 50)[line]
            
            # Enhanced summarization with role context
            if user_role != "User":
                contextualized_line = f"{enhanced_interlocutor_desc} says: {line}"
                summarized_idea = generate_summarize_ideas(persona, retrieved, contextualized_line)
            else:
                summarized_idea = generate_summarize_ideas(persona, retrieved, line)
            
            # Add user input to conversation
            curr_convo.append([interlocutor_desc, line])
            
            # Generate agent response with enhanced context
            next_line = generate_next_line(persona, enhanced_interlocutor_desc, curr_convo, summarized_idea)
            curr_convo.append([persona.scratch.name, next_line])
            
            # Display response
            print(f"{persona.scratch.name}: {next_line}\n")
            
        except KeyboardInterrupt:
            print("\nConversation interrupted by user.")
            break
        except Exception as e:
            print(f"Error during conversation: {e}")
            continue
    
    # Save conversation if it has content
    if len(curr_convo) > 0:
        self.save_conversation_to_memory(persona, curr_convo, enhanced_interlocutor_desc)
        print(f"\nConversation between {persona_name} and {user_role} has been saved to {persona_name}'s memory.")
    else:
        print("\nNo conversation content to save.")

# 修改 generate_conversation_reflection 方法以支持角色感知
  def generate_conversation_reflection(self, persona, conversation, interlocutor_desc):
    """
    Generate a thoughtful reflection based on the complete conversation.
    """
    from persona.prompt_template.gpt_structure import ChatGPT_safe_generate_response
    
    # Format the conversation for reflection
    convo_text = ""
    for speaker, utterance in conversation:
        convo_text += f"{speaker}: {utterance}\n"
    
    # Enhanced reflection prompt with role awareness
    reflection_prompt = f"""
    {persona.scratch.name} just finished a conversation with {interlocutor_desc}. Here is the complete conversation:

    {convo_text}

    Based on this conversation, generate a thoughtful inner reflection from {persona.scratch.name}'s perspective. Consider:
    1. Who {interlocutor_desc} is and what their background/role might mean for this interaction
    2. What was discussed and any new information learned about {interlocutor_desc} or their profession/situation
    3. The emotional impact and social dynamics of this conversation
    4. How this interaction with {interlocutor_desc} relates to {persona.scratch.name}'s current situation, goals, or relationships
    5. Any insights, concerns, or future actions that might arise from meeting/talking with {interlocutor_desc}
    6. What {persona.scratch.name} thinks about {interlocutor_desc} as a person. Bad or good, what is their impression of them?

    The reflection should be 2-3 sentences long, written in first person, and capture the important information or mindset of this interaction with {interlocutor_desc} for {persona.scratch.name}.
    You should have your own objective and perspective as {persona.scratch.name}.
    """
    
    def __func_validate(gpt_response, prompt=""):
        if not gpt_response or len(gpt_response.strip()) < 20:
            return False
        if "just had a conversation" in gpt_response.lower() and len(gpt_response.strip()) < 50:
            return False
        return True
    
    def __func_clean_up(gpt_response, prompt=""):
        cleaned = gpt_response.strip()
        if not any(pronoun in cleaned.lower() for pronoun in ["i ", "my ", "me ", "myself"]):
            cleaned = f"I reflect on this conversation: {cleaned}"
        return cleaned
    
    # Role-specific example output
    if "singer" in interlocutor_desc.lower():
        example_output = f"Meeting {interlocutor_desc} was interesting - their passion for music reminds me of the creative energy on campus, and I'm curious about their musical background and what brought them here."
    elif "student" in interlocutor_desc.lower():
        example_output = f"It's nice to connect with {interlocutor_desc}, and I appreciate getting to know someone new in our community."
    else:
        example_output = f"My conversation with {interlocutor_desc} gave me some new perspectives to consider, and I found their viewpoint quite engaging."
    
    special_instruction = f"Generate a thoughtful, introspective reflection that shows {persona.scratch.name}'s genuine thoughts about meeting and talking with {interlocutor_desc}. Consider their role/profession in the reflection."
    
    reflection = ChatGPT_safe_generate_response(
        reflection_prompt,
        example_output,
        special_instruction,
        repeat=3,
        fail_safe_response=f"I had an interesting conversation with {interlocutor_desc} that gave me some new perspectives to think about.",
        func_validate=__func_validate,
        func_clean_up=__func_clean_up,
        verbose=False
    )
    
    return reflection if reflection else f"I had a meaningful conversation with {interlocutor_desc} that I'll need to think more about."


  def extract_conversation_topics(self, conversation):
    """
    Extract key topics from the conversation for further reflection.
    """
    topics = []
    for speaker, utterance in conversation:
        words = utterance.lower().split()
        meaningful_words = [word for word in words if len(word) > 4 and word not in 
                          ['about', 'think', 'really', 'would', 'could', 'should', 'there', 'where', 'which']]
        topics.extend(meaningful_words[:3])
    
    return list(set(topics))[:5]

  def save_conversation_to_memory(self, persona, conversation, interlocutor_desc):
    """
    Save the conversation to persona's memory as chat and thought nodes.
    """
    from persona.cognitive_modules.converse import (
        generate_action_event_triple,
        generate_poig_score,
        generate_inner_thought
    )
    from persona.prompt_template.gpt_structure import get_embedding
    from persona.prompt_template.run_gpt_prompt import run_gpt_prompt_summarize_conversation
    import datetime
    
    try:
        # Validate and format conversation data properly
        formatted_conversation = []
        convo_str = ""
        
        for item in conversation:
            if isinstance(item, list) and len(item) >= 2:
                speaker, utterance = str(item[0]), str(item[1])
                if speaker and utterance:
                    formatted_conversation.append([speaker, utterance])
                    convo_str += f"{speaker}: {utterance}\n"
        
        if not formatted_conversation:
            print("\033[0;31m✗ No valid conversation data to save\033[0m")
            return
        
        created = persona.scratch.curr_time
        expiration = persona.scratch.curr_time + datetime.timedelta(days=30)
        
        # 1. Save as chat node
        try:
            chat_summary_result = run_gpt_prompt_summarize_conversation(persona, formatted_conversation)
            if chat_summary_result and len(chat_summary_result) > 0:
                chat_summary = chat_summary_result[0]
            else:
                raise Exception("GPT summarization returned empty result")
        except Exception as gpt_error:
            topics = []
            for speaker, utterance in formatted_conversation:
                if len(utterance) > 10:
                    topics.append(utterance[:50] + "..." if len(utterance) > 50 else utterance)
            
            if topics:
                chat_summary = f"conversing about {'; '.join(topics[:3])}"
            else:
                chat_summary = f"conversing with {interlocutor_desc}"
        
        # Generate action event triple for chat
        s, p, o = generate_action_event_triple(chat_summary, persona)
        keywords = set([s, p, o])
        
        # Calculate poignancy score
        chat_poignancy = generate_poig_score(persona, "chat", chat_summary)
        
        # Create embedding
        chat_embedding_pair = (chat_summary, get_embedding(chat_summary))
        
        # Save chat to memory
        try:
            if hasattr(persona.a_mem, 'add_chat'):
                persona.a_mem.add_chat(created, expiration, s, p, o,
                                     chat_summary, keywords, chat_poignancy,
                                     chat_embedding_pair, convo_str)
            else:
                persona.a_mem.add_thought(created, expiration, s, p, o,
                                        chat_summary, keywords, chat_poignancy,
                                        chat_embedding_pair, convo_str)
            
            print(f"\033[0;32m✓ Chat summary saved: {chat_summary}\033[0m")
        except Exception as e:
            print(f"\033[0;31m✗ Error saving chat: {e}\033[0m")
        
        # 2. Generate and save comprehensive reflection
        try:
            reflection_content = self.generate_conversation_reflection(persona, formatted_conversation, interlocutor_desc)
            
            s_thought, p_thought, o_thought = generate_action_event_triple(reflection_content, persona)
            keywords_thought = set([s_thought, p_thought, o_thought])
            thought_poignancy = generate_poig_score(persona, "thought", reflection_content)
            thought_embedding_pair = (reflection_content, get_embedding(reflection_content))
            
            persona.a_mem.add_thought(created, expiration, s_thought, p_thought, o_thought,
                                    reflection_content, keywords_thought, thought_poignancy,
                                    thought_embedding_pair, None)
            
            print(f"\033[0;32m✓ Reflection saved: {reflection_content}\033[0m")
        except Exception as e:
            print(f"\033[0;31m✗ Error saving reflection: {e}\033[0m")
        
    except Exception as e:
        print(f"\033[0;31m✗ Error saving conversation to memory: {e}\033[0m")
        import traceback
        traceback.print_exc()      

  def start_server(self, int_counter, debug_mode=False): 
    """
    The main backend server of Reverie. 
    This function retrieves the environment file from the frontend to 
    understand the state of the world, calls on each personas to make 
    decisions based on the world state, and saves their moves at certain step
    intervals. 
    INPUT
      int_counter: Integer value for the number of steps left for us to take
                   in this iteration. 
      debug_mode: If True, runs without frontend interaction
    OUTPUT 
      None
    """
    # <sim_folder> points to the current simulation folder.
    sim_folder = f"{fs_storage}/{self.sim_code}"

    # When a persona arrives at a game object, we give a unique event
    # to that object. 
    # e.g., ('double studio[...]:bed', 'is', 'unmade', 'unmade')
    # Later on, before this cycle ends, we need to return that to its 
    # initial state, like this: 
    # e.g., ('double studio[...]:bed', None, None, None)
    # So we need to keep track of which event we added. 
    # <game_obj_cleanup> is used for that. 
    game_obj_cleanup = dict()

    # The main while loop of Reverie. 
    while (True): 
      # Done with this iteration if <int_counter> reaches 0. 
      if int_counter == 0: 
        break

      # <curr_env_file> file is the file that our frontend outputs. When the
      # frontend has done its job and moved the personas, then it will put a 
      # new environment file that matches our step count. That's when we run 
      # the content of this for loop. Otherwise, we just wait. 
      # curr_env_file = f"{sim_folder}/environment/{self.step}.json"
      # if check_if_file_exists(curr_env_file):
      #   # If we have an environment file, it means we have a new perception
      #   # input to our personas. So we first retrieve it.
      #   try: 
      #     # Try and save block for robustness of the while loop.
      #     with open(curr_env_file) as json_file:
      #       new_env = json.load(json_file)
      #       env_retrieved = True
      #   except: 
      #     pass
      # Skip file checking in debug mode# In debug mode, we don't need to wait for environment files
      env_retrieved = debug_mode
      new_env = {}
      
      # In debug mode, generate our own environment data based on current state
      if debug_mode:
          # Create environment data based on current persona positions
          for persona_name, position in self.personas_tile.items():
              new_env[persona_name] = {"x": position[0], "y": position[1]}
          
          # Save environment file for this step (for record keeping)
          env_path = f"{sim_folder}/environment"
          if not os.path.exists(env_path):
              os.makedirs(env_path)
          env_file = f"{sim_folder}/environment/{self.step}.json"
          with open(env_file, "w") as outfile:
              outfile.write(json.dumps(new_env, indent=2))
      # In normal mode, check for environment files from frontend
      else:
          curr_env_file = f"{sim_folder}/environment/{self.step}.json"
          if check_if_file_exists(curr_env_file):
              try: 
                  with open(curr_env_file) as json_file:
                      new_env = json.load(json_file)
                      env_retrieved = True
              except: 
                  pass

      if env_retrieved:
          # This is where we go through <game_obj_cleanup> to clean up all
          # object actions that were used in this cycle.
          for key, val in game_obj_cleanup.items(): 
            # We turn all object actions to their blank form (with None). 
            self.maze.turn_event_from_tile_idle(key, val)
          # Then we initialize game_obj_cleanup for this cycle. 
          game_obj_cleanup = dict()

          # Only process frontend environment data if not in debug mode
          if not debug_mode:
           for persona_name, persona in self.personas.items(): 
            # <curr_tile> is the tile that the persona was at previously. 
            curr_tile = self.personas_tile[persona_name]
            # <new_tile> is the tile that the persona will move to right now,
            # during this cycle. 
            new_tile = (new_env[persona_name]["x"], 
                        new_env[persona_name]["y"])

            # We actually move the persona on the backend tile map here. 
            self.personas_tile[persona_name] = new_tile
            self.maze.remove_subject_events_from_tile(persona.name, curr_tile)
            self.maze.add_event_from_tile(persona.scratch
                                         .get_curr_event_and_desc(), new_tile)

            # Now, the persona will travel to get to their destination. *Once*
            # the persona gets there, we activate the object action.
            if not persona.scratch.planned_path: 
              # We add that new object action event to the backend tile map. 
              # At its creation, it is stored in the persona's backend. 
              game_obj_cleanup[persona.scratch
                               .get_curr_obj_event_and_desc()] = new_tile
              self.maze.add_event_from_tile(persona.scratch
                                     .get_curr_obj_event_and_desc(), new_tile)
              # We also need to remove the temporary blank action for the 
              # object that is currently taking the action. 
              blank = (persona.scratch.get_curr_obj_event_and_desc()[0], 
                       None, None, None)
              self.maze.remove_event_from_tile(blank, new_tile)

          # Then we need to actually have each of the personas perceive and
          # move. The movement for each of the personas comes in the form of
          # x y coordinates where the persona will move towards. e.g., (50, 34)
          # This is where the core brains of the personas are invoked. 
          movements = {"persona": dict(), 
                       "meta": dict()}
          print("\n\n\n\033[3;7;36mStart Step: ", self.step, "\033[0m")
          print("\033[3;7;36mCurrent Time: ", self.curr_time, "\033[0m")

          for persona_name, persona in self.personas.items(): 
            # <next_tile> is a x,y coordinate. e.g., (58, 9)
            # <pronunciatio> is an emoji. e.g., "\ud83d\udca4"
            # <description> is a string description of the movement. e.g., 
            #   writing her next novel (editing her novel) 
            #   @ double studio:double studio:common room:sofa
            print(f"\n\033[1;7;35m>>>>>   In step {self.step}   >>>>> {persona_name} start a move --\033[0m")
            next_tile, pronunciatio, description = persona.move(
              self.maze, self.personas, self.personas_tile[persona_name], 
              self.curr_time)
            print(f"\033[1;7;35m>>>>>   In step {self.step}   >>>>> {persona_name} finished a move --\033[0m")

            movements["persona"][persona_name] = {}
            movements["persona"][persona_name]["movement"] = next_tile
            movements["persona"][persona_name]["pronunciatio"] = pronunciatio
            movements["persona"][persona_name]["description"] = description
            movements["persona"][persona_name]["chat"] = (persona
                                                          .scratch.chat)
            
						# in debug mode, update the persona's tile immediately
            if debug_mode:
                  curr_tile = self.personas_tile[persona_name]
                  self.personas_tile[persona_name] = next_tile
                  self.maze.remove_subject_events_from_tile(persona.name, curr_tile)
                  self.maze.add_event_from_tile(persona.scratch.get_curr_event_and_desc(), next_tile)

          # Include the meta information about the current stage in the 
          # movements dictionary. 
          movements["meta"]["curr_time"] = (self.curr_time 
                                             .strftime("%B %d, %Y, %H:%M:%S"))

          # We then write the personas' movements to a file that will be sent 
          # to the frontend server. always save the file in json format.
          # Example json output: 
          # {"persona": {"Maria Lopez": {"movement": [58, 9]}},
          #  "persona": {"Klaus Mueller": {"movement": [38, 12]}}, 
          #  "meta": {curr_time: <datetime>}}
          curr_move_path = f"{sim_folder}/movement"
          if not os.path.exists(curr_move_path):
            os.makedirs(curr_move_path)
          curr_move_file = f"{sim_folder}/movement/{self.step}.json"
          with open(curr_move_file, "w") as outfile: 
            outfile.write(json.dumps(movements, indent=2))

          # After this cycle, the world takes one step forward, and the 
          # current time moves by <sec_per_step> amount. 
          self.step += 1
          self.curr_time += datetime.timedelta(seconds=self.sec_per_step)
          
          # 自动保存机制 - 每10步保存一次
          if self.step % 10 == 0:
              print(f"\033[1;36m自动保存点 - 步数: {self.step}\033[0m")
              self.save()

          int_counter -= 1
          
      # Only wait between steps in non-debug mode
      if not debug_mode:
          time.sleep(self.server_sleep)


  def monitor_frontend_commands(self):
    """监听前端命令文件 - 后台线程运行"""
    import time
    import os
    import json
    
    print("🔍 Started monitoring frontend commands...")
    
    while True:
        try:
            # Check for command signal file
            signal_file = f"{fs_temp_storage}/command_ready.signal"
            command_file = f"{fs_temp_storage}/frontend_command.json"
            
            if os.path.exists(signal_file) and os.path.exists(command_file):
                # Read the command
                with open(command_file, 'r') as f:
                    command_data = json.load(f)
                
                command = command_data.get('command', '').strip()
                sim_code = command_data.get('sim_code')
                
                # Remove signal file
                os.remove(signal_file)
                
                # Execute the command
                if command:
                    print(f"📨 Received command from frontend: {command}")
                    self.execute_and_save_command(command)
                
        except Exception as e:
            print(f"❌ Error monitoring commands: {e}")
        
        time.sleep(0.5)  # Check every 500ms

  def execute_and_save_command(self, sim_command):
    """执行命令并保存结果到文件"""
    import io
    from contextlib import redirect_stdout
    
    success = True
    error_msg = ""
    captured_output = ""
    
    try:
        # 检查是否是需要保持原始输出的命令
        long_running_commands = ['run ', 'debug run ']
        is_long_running = any(sim_command.lower().startswith(cmd) for cmd in long_running_commands)
        
        if is_long_running:
            # 对于 run 命令，不重定向输出，保持原始的 stdout
            print(f"🚀 [Frontend Command] 开始执行: {sim_command}")
            
            if sim_command.lower().startswith("run "):
                try:
                    steps = int(sim_command.split()[-1])
                    print(f"📊 [Frontend Command] 启动 {steps} 步模拟...")
                    self.start_server(steps)
                    captured_output = f"✅ Successfully executed {steps} steps"
                    print(f"✅ [Frontend Command] 完成 {steps} 步模拟")
                except ValueError:
                    captured_output = "❌ Invalid step count. Usage: run <number>"
                    success = False
                    
            elif sim_command.lower().startswith("debug run "):
                try:
                    steps = int(sim_command.split()[-1])
                    print(f"🐛 [Frontend Command] 启动调试模式 {steps} 步...")
                    self.start_server(steps, debug_mode=True)
                    captured_output = f"✅ Debug executed {steps} steps"
                    print(f"🐛 [Frontend Command] 调试模式完成 {steps} 步")
                except ValueError:
                    captured_output = "❌ Invalid step count. Usage: debug run <number>"
                    success = False
        else:
            # 对于其他命令，使用重定向捕获输出
            output_buffer = io.StringIO()
            with redirect_stdout(output_buffer):
                if sim_command.lower() == "print current time":
                    print(f"Current time: {self.curr_time.strftime('%A %B %d, %Y, %H:%M:%S')}")
                elif sim_command.lower() == "save":
                    self.save()
                    print("✅ Simulation saved successfully!")
                elif "print all persona schedule" in sim_command.lower():
                    for persona_name, persona in self.personas.items():
                        print(f"\n👤 {persona_name}'s schedule:")
                        print(persona.scratch.get_str_daily_schedule_summary())
                        print("─" * 50)
                elif ("print persona schedule" in sim_command[:22].lower()): 
                    persona_name = " ".join(sim_command.split()[-2:])
                    if persona_name in self.personas:
                        print(f"👤 {persona_name}")
                        print(self.personas[persona_name].scratch.get_str_daily_schedule_summary())
                    else:
                        print(f"❌ Persona '{persona_name}' not found")
                elif ("print persona associative memory (event)" in sim_command.lower()):
                    persona_name = " ".join(sim_command.split()[-2:])
                    if persona_name in self.personas:
                        print(f"👤 {persona_name} - Event Memory:")
                        print(self.personas[persona_name].a_mem.get_str_seq_events())
                    else:
                        print(f"❌ Persona '{persona_name}' not found")
                elif ("print persona associative memory (thought)" in sim_command.lower()): 
                    persona_name = " ".join(sim_command.split()[-2:])
                    if persona_name in self.personas:
                        print(f"👤 {persona_name} - Thought Memory:")
                        print(self.personas[persona_name].a_mem.get_str_seq_thoughts())
                    else:
                        print(f"❌ Persona '{persona_name}' not found")
                elif ("print persona associative memory (chat)" in sim_command.lower()): 
                    persona_name = " ".join(sim_command.split()[-2:])
                    if persona_name in self.personas:
                        print(f"👤 {persona_name} - Chat Memory:")
                        print(self.personas[persona_name].a_mem.get_str_seq_chats())
                    else:
                        print(f"❌ Persona '{persona_name}' not found")
                elif ("converse with" in sim_command.lower()): 
                    persona_name = sim_command[len("converse with"):].strip()
                    if persona_name in self.personas:
                        print(f"💬 Conversation with {persona_name} is available in terminal mode")
                    else:
                        print(f"❌ Persona '{persona_name}' not found")
                else:
                    print(f"❌ Unknown command: '{sim_command}'")
                    success = False
            
            captured_output = output_buffer.getvalue()
            
    except Exception as e:
        success = False
        error_msg = str(e)
        captured_output = f"❌ Error: {error_msg}"
        print(f"❌ [Frontend Command] 执行错误: {e}")
        import traceback
        traceback.print_exc()
    
    # 保存结果到文件
    try:
        result_data = {
            'command': sim_command,
            'success': success,
            'output': captured_output,
            'error': error_msg if error_msg else None,
            'timestamp': datetime.datetime.now().isoformat()
        }
        
        output_file = f"{fs_temp_storage}/command_output.json"
        with open(output_file, 'w') as f:
            json.dump(result_data, f, indent=2)
            
        print(f"💾 [Frontend Command] 结果已保存到文件")
        
        # 删除命令文件，表示处理完成
        command_file = f"{fs_temp_storage}/frontend_command.json"
        if os.path.exists(command_file):
            os.remove(command_file)
        
    except Exception as e:
        print(f"❌ [Frontend Command] 保存结果失败: {e}")

# 修改open_server方法，只在开头添加3行启动文件监听
  def open_server(self): 
    """
    Open up an interactive terminal prompt that lets you run the simulation 
    step by step and probe agent state. 
    """
    print ("Note: The agents in this simulation package are computational")
    print ("constructs powered by generative agents architecture and LLM. We")
    print ("clarify that these agents lack human-like agency, consciousness,")
    print ("and independent decision-making.\n---")
    
    # 只添加这3行 - 启动文件监听
    print("🌐 File-based frontend communication enabled")
    file_monitor_thread = threading.Thread(target=self.monitor_frontend_commands, daemon=True)
    file_monitor_thread.start()

    # <sim_folder> points to the current simulation folder.
    sim_folder = f"{fs_storage}/{self.sim_code}"

    # 保持原有的while循环完全不变
    while True: 
      sim_command = input("Enter option: ")
      sim_command = sim_command.strip()
      ret_str = ""

      try: 
        if sim_command.lower() in ["f", "fin", "finish", "save and finish"]: 
          self.save()
          break

        elif sim_command.lower() == "exit": 
          shutil.rmtree(sim_folder) 
          break 

        elif sim_command.lower() == "save": 
          self.save()

        elif sim_command[:3].lower() == "run": 
          int_count = int(sim_command.split()[-1])
          self.start_server(int_count)
        
        elif sim_command[:9].lower() == "debug run":
          int_count = int(sim_command.split()[-1])
          self.start_server(int_count, debug_mode=True)

        elif ("print persona schedule" 
              in sim_command[:22].lower()): 
          # Print the decomposed schedule of the persona specified in the 
          # prompt.
          # Example: print persona schedule Isabella Rodriguez
          ret_str += (self.personas[" ".join(sim_command.split()[-2:])]
                      .scratch.get_str_daily_schedule_summary())

        elif ("print all persona schedule" 
              in sim_command[:26].lower()): 
          # Print the decomposed schedule of all personas in the world. 
          # Example: print all persona schedule
          for persona_name, persona in self.personas.items(): 
            ret_str += f"{persona_name}\n"
            ret_str += f"{persona.scratch.get_str_daily_schedule_summary()}\n"
            ret_str += f"---\n"

        elif ("print hourly org persona schedule" 
              in sim_command.lower()): 
          # Print the hourly schedule of the persona specified in the prompt.
          # This one shows the original, non-decomposed version of the 
          # schedule.
          # Ex: print persona schedule Isabella Rodriguez
          ret_str += (self.personas[" ".join(sim_command.split()[-2:])]
                      .scratch.get_str_daily_schedule_hourly_org_summary())

        elif ("print persona current tile" 
              in sim_command[:26].lower()): 
          # Print the x y tile coordinate of the persona specified in the 
          # prompt. 
          # Ex: print persona current tile Isabella Rodriguez
          ret_str += str(self.personas[" ".join(sim_command.split()[-2:])]
                      .scratch.curr_tile)

        elif ("print persona chatting with buffer" 
              in sim_command.lower()): 
          # Print the chatting with buffer of the persona specified in the 
          # prompt.
          # Ex: print persona chatting with buffer Isabella Rodriguez
          curr_persona = self.personas[" ".join(sim_command.split()[-2:])]
          for p_n, count in curr_persona.scratch.chatting_with_buffer.items(): 
            ret_str += f"{p_n}: {count}"

        elif ("print persona associative memory (event)" 
              in sim_command.lower()):
          # Print the associative memory (event) of the persona specified in
          # the prompt
          # Ex: print persona associative memory (event) Isabella Rodriguez
          ret_str += f'{self.personas[" ".join(sim_command.split()[-2:])]}\n'
          ret_str += (self.personas[" ".join(sim_command.split()[-2:])]
                                           .a_mem.get_str_seq_events())

        elif ("print persona associative memory (thought)" 
              in sim_command.lower()): 
          # Print the associative memory (thought) of the persona specified in
          # the prompt
          # Ex: print persona associative memory (thought) Isabella Rodriguez
          ret_str += f'{self.personas[" ".join(sim_command.split()[-2:])]}\n'
          ret_str += (self.personas[" ".join(sim_command.split()[-2:])]
                                           .a_mem.get_str_seq_thoughts())

        elif ("print persona associative memory (chat)" 
              in sim_command.lower()): 
          # Print the associative memory (chat) of the persona specified in
          # the prompt
          # Ex: print persona associative memory (chat) Isabella Rodriguez
          ret_str += f'{self.personas[" ".join(sim_command.split()[-2:])]}\n'
          ret_str += (self.personas[" ".join(sim_command.split()[-2:])]
                                           .a_mem.get_str_seq_chats())

        elif ("print current time" 
              in sim_command[:18].lower()): 
          # Print the current time of the world. 
          # Ex: print current time
          ret_str += f'{self.curr_time.strftime("%B %d, %Y, %H:%M:%S")}\n'
          ret_str += f'steps: {self.step}'

        elif ("print tile event" 
              in sim_command[:16].lower()): 
          # Print the tile events in the tile specified in the prompt 
          # Ex: print tile event 50, 30
          cooordinate = [int(i.strip()) for i in sim_command[16:].split(",")]
          for i in self.maze.access_tile(cooordinate)["events"]: 
            ret_str += f"{i}\n"

        elif ("print tile details" 
              in sim_command.lower()): 
          # Print the tile details of the tile specified in the prompt 
          # Ex: print tile event 50, 30
          cooordinate = [int(i.strip()) for i in sim_command[18:].split(",")]
          for key, val in self.maze.access_tile(cooordinate).items(): 
            ret_str += f"{key}: {val}\n"

        elif ("call -- analysis" 
              in sim_command.lower()): 
          # Starts a stateless chat session with the agent. It does not save 
          # anything to the agent's memory. 
          # Ex: call -- analysis Isabella Rodriguez
          persona_name = sim_command[len("call -- analysis"):].strip() 
          self.personas[persona_name].open_convo_session("analysis")
          
        elif ("insert -- thought" 
              in sim_command.lower()): 
          # Starts a stateless chat session with the agent. It does not save 
          # anything to the agent's memory. 
          # Ex: insert -- thought Isabella Rodriguez
          persona_name = sim_command[len("insert -- thought"):].strip() 
          self.personas[persona_name].open_convo_session("whisper")
        
        elif ("converse with" in sim_command.lower()): 
            # Start a conversation with the specified persona and save as chat/thought nodes
            persona_name = sim_command[len("converse with"):].strip()
            if persona_name not in self.personas:
                print(f"Persona '{persona_name}' not found.")
                print("Available personas:")
                for name in self.personas.keys():
                    print(f"  - {name}")
            else:
                # Ask user to define their role
                print("\n=== Role Definition ===")
                print("You can play as yourself (User) or define a specific character.")
                user_role_input = input("Enter your role/character (press Enter for 'User'): ").strip()
                user_role = user_role_input if user_role_input else "User"
                
                # If user defines a character, ask for brief description
                user_description = ""
                if user_role != "User":
                    user_description = input(f"Brief description of {user_role} (optional): ").strip()
                
                self.start_interactive_conversation(persona_name, user_role, user_description)

        # 在 open_server 方法的命令处理循环中添加快速角色设置
        elif ("converse as" in sim_command.lower()):
            # Quick role setup: "converse as Wei Xu with Isabella Rodriguez"
            command_parts = sim_command[len("converse as"):].strip().split(" with ")
            if len(command_parts) == 2:
                user_role = command_parts[0].strip()
                persona_name = command_parts[1].strip()
                
                if persona_name not in self.personas:
                    print(f"Persona '{persona_name}' not found.")
                    print("Available personas:")
                    for name in self.personas.keys():
                        print(f"  - {name}")
                else:
                    # Pre-defined role descriptions
                    role_descriptions = {
                        "Wei Xu": "a new campus singer who just arrived and is passionate about music",
                        "wei xu": "a new campus singer who just arrived and is passionate about music",
                        "Wei": "a new campus singer who just arrived and is passionate about music"
                    }
                    
                    user_description = role_descriptions.get(user_role, "")
                    if not user_description and user_role.lower() in role_descriptions:
                        user_description = role_descriptions[user_role.lower()]
                    
                    self.start_interactive_conversation(persona_name, user_role, user_description)
            else:
                print("Usage: converse as [role name] with [persona name]")
                print("Example: converse as Wei Xu with Isabella Rodriguez")

        elif ("call -- load history" 
              in sim_command.lower()): 
          curr_file = maze_assets_loc + "/" + sim_command[len("call -- load history"):].strip() 
          # call -- load history the_ville/agent_history_init_n3.csv

          rows = read_file_to_list(curr_file, header=True, strip_trail=True)[1]
          clean_whispers = []
          for row in rows: 
            agent_name = row[0].strip() 
            whispers = row[1].split(";")
            whispers = [whisper.strip() for whisper in whispers]
            for whisper in whispers: 
              clean_whispers += [[agent_name, whisper]]

          load_history_via_whisper(self.personas, clean_whispers)

        print (ret_str)

      except:
        traceback.print_exc()
        print ("Error.")
        pass


if __name__ == '__main__':
  # rs = ReverieServer("base_the_ville_isabella_maria_klaus", 
  #                    "July1_the_ville_isabella_maria_klaus-step-3-1")
  # rs = ReverieServer("July1_the_ville_isabella_maria_klaus-step-3-20", 
  #                    "July1_the_ville_isabella_maria_klaus-step-3-21")
  # rs.open_server()
  while(True):
    num = int(input("""Choose the forked simulation: \n1. base_the_ville_isabella_maria_klaus\n2. 4ps\n3. custom\n"""))
    if num == 1: 
      origin = "base_the_ville_isabella_maria_klaus"
      break
    if num == 2:
      origin = "4ps"
      break
    else:
      origin = input("Enter the name of the simulation to fork from: ").strip()
      break
      
  target = input("Enter the name of the new simulation: ").strip()

  rs = ReverieServer(origin, target)
  rs.open_server()

