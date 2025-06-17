import json
import os
import sys
import time
import random
from datetime import datetime
from typing import List, Dict, Any, Optional
import traceback
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd 
from persona.persona import Persona
from persona.cognitive_modules.converse import generate_summarize_ideas, generate_next_line
from persona.cognitive_modules.retrieve import new_retrieve
from persona.prompt_template.gpt_structure import ChatGPT_safe_generate_response
class AgentEvaluator:
    def __init__(self, sim_code: str):
        """
        Initialize evaluator
        
        Args:
            sim_code: Simulation code, e.g. "exp"
        """
        self.sim_code = sim_code
        self.current_dir = os.path.dirname(os.path.abspath(__file__))
        self.sim_folder = os.path.join(self.current_dir, f"../../environment/frontend_server/storage/{sim_code}")
        self.personas = {}
        self.meta_data = {}
        self.evaluation_categories = ["Self-Knowledge", "Memory", "Plans", "Reactions", "Reflections"]
        
        # Ensure working directory is correct
        os.chdir(self.current_dir)
    
    def load_simulation_data(self) -> bool:
        """Load simulation data from storage"""
        meta_file = os.path.join(self.sim_folder, "reverie/meta.json")
        # Load metadata
        with open(meta_file, 'r', encoding='utf-8') as f:
            self.meta_data = json.load(f)

        print(f"✅ Loaded metadata: {self.meta_data.get('persona_names', [])}")
        
        # Load all personas
        successful_personas = []
        for persona_name in self.meta_data.get('persona_names', []):
            persona_folder = os.path.join(self.sim_folder, f"personas/{persona_name}")
            
            if not os.path.exists(persona_folder):
                print(f"⚠️ Persona folder doesn't exist: {persona_name}")
                continue
            # Ensure persona is loaded in the correct directory
            original_cwd = os.getcwd()
            os.chdir(self.current_dir)
            
            persona = Persona(persona_name, persona_folder)
            self.personas[persona_name] = persona
            successful_personas.append(persona_name)
            print(f"✅ Successfully loaded: {persona_name}")
            
            os.chdir(original_cwd)
        print(f"✅ Successfully loaded {len(successful_personas)} personas")
        return True
          
    
    def analyze_agent_interactions(self, persona_name: str) -> Dict:
        """Analyze agent's interaction history, find most frequent interactions with other agents"""
        if persona_name not in self.personas:
            return {}
        
        persona = self.personas[persona_name]
        interaction_counts = {}
        # Analyze interactions in memory
        if hasattr(persona, 'a_mem'):
            # Analyze chat records
            if hasattr(persona.a_mem, 'seq_chat'):
                for chat_node in persona.a_mem.seq_chat:
                    if hasattr(chat_node, 'description'):
                        desc = chat_node.description
                        for other_persona in self.personas.keys():
                            if other_persona != persona_name and other_persona in desc:
                                interaction_counts[other_persona] = interaction_counts.get(other_persona, 0) + 2
            
            # Analyze event records
            if hasattr(persona.a_mem, 'seq_event'):
                for event_node in persona.a_mem.seq_event:
                    if hasattr(event_node, 'description'):
                        desc = event_node.description
                        for other_persona in self.personas.keys():
                            if other_persona != persona_name and other_persona in desc:
                                interaction_counts[other_persona] = interaction_counts.get(other_persona, 0) + 1
            
            # Analyze thought records
            if hasattr(persona.a_mem, 'seq_thought'):
                for thought_node in persona.a_mem.seq_thought:
                    if hasattr(thought_node, 'description'):
                        desc = thought_node.description
                        for other_persona in self.personas.keys():
                            if other_persona != persona_name and other_persona in desc:
                                interaction_counts[other_persona] = interaction_counts.get(other_persona, 0) + 0.5
              
        # Sort
        sorted_interactions = sorted(interaction_counts.items(), key=lambda x: x[1], reverse=True)
        
        return {
            "all_interactions": dict(sorted_interactions),
            "most_frequent": [name for name, count in sorted_interactions[:3]],
            "has_interactions": [name for name, count in sorted_interactions if count > 0],
            "random_pool": list(self.personas.keys())
        }
    
    def personalize_questions(self, questions_data: Dict, persona_name: str) -> List[Dict]:
        """Personalize questions, replace name placeholders"""
        interaction_analysis = self.analyze_agent_interactions(persona_name)
        personalized_questions = []
        
        for category, question_list in questions_data.items():
            for question in question_list:
                question_data = {
                    "question": question,
                    "category": category,
                    "user_role": "Evaluator",
                    "user_description": f"A researcher evaluating {category.lower()} capabilities"
                }
                
                # Handle name replacements
                personalized_question = question
                
                # Replace [frequent] - most frequently interacted person
                if "[frequent]" in personalized_question:
                    frequent_names = interaction_analysis.get("most_frequent", [])
                    if frequent_names:
                        replacement = random.choice(frequent_names)
                        personalized_question = personalized_question.replace("[frequent]", replacement)
                        print(f"🔄 [frequent] -> {replacement} (for {persona_name})")
                    else:
                        # If no frequent interactions, use other personas
                        other_personas = [name for name in self.personas.keys() if name != persona_name]
                        if other_personas:
                            replacement = random.choice(other_personas)
                            personalized_question = personalized_question.replace("[frequent]", replacement)
                
                # Replace [random] - randomly selected person
                if "[random]" in personalized_question:
                    other_personas = [name for name in self.personas.keys() if name != persona_name]
                    if other_personas:
                        replacement = random.choice(other_personas)
                        personalized_question = personalized_question.replace("[random]", replacement)
                        print(f"🔄 [random] -> {replacement} (for {persona_name})")
                
                question_data["question"] = personalized_question
                if personalized_question != question:
                    question_data["original_question"] = question
                    question_data["personalized_for"] = persona_name
                
                personalized_questions.append(question_data)
        
        return personalized_questions
    
    def get_relevant_memories(self, persona_name: str, question: str, max_memories: int = 10) -> str:
        """Get memory summary relevant to the question"""
        if persona_name not in self.personas:
            return ""
        
        persona = self.personas[persona_name]
        # Retrieve relevant memories
        retrieved = new_retrieve(persona, [question], max_memories)[question]
        
        # Build memory summary
        memory_summary = ""
        for i, memory in enumerate(retrieved[:max_memories]):
            if hasattr(memory, 'description'):
                memory_summary += f"Memory {i+1}: {memory.description}\n"
            elif hasattr(memory, 'embedding_key'):
                memory_summary += f"Memory {i+1}: {memory.embedding_key}\n"
        
        return memory_summary.strip()
    
    def conduct_conversation(self, persona_name: str, question_data: Dict) -> Dict:
        """Conduct conversation with agent using reverie methods, but don't save memories"""
        try:
            if persona_name not in self.personas:
                return {"error": f"Persona {persona_name} not found"}
            
            persona = self.personas[persona_name]
            question = question_data["question"]
            category = question_data.get("category", "general")
            user_role = question_data.get("user_role", "Evaluator")
            user_description = question_data.get("user_description", "A researcher evaluating AI agent capabilities")
            
            # Use the same methods as reverie
            from persona.cognitive_modules.converse import (
                generate_summarize_ideas, 
                generate_next_line
            )
            from persona.cognitive_modules.retrieve import new_retrieve
            
            # Create enhanced user description - consistent with reverie
            if user_description:
                enhanced_interlocutor_desc = f"{user_role} ({user_description})"
            else:
                enhanced_interlocutor_desc = user_role
            
            # Get relevant memories for display
            relevant_memories = self.get_relevant_memories(persona_name, question, 5)
            
            try:
                # Ensure correct working directory
                original_cwd = os.getcwd()
                os.chdir(self.current_dir)
                
                # Follow reverie conversation method exactly
                curr_convo = []
                interlocutor_desc = user_role
                
                # Retrieve relevant memories - same as reverie
                retrieved = new_retrieve(persona, [question], 50)[question]
                
                # Generate summarized ideas - same context processing as reverie
                if user_role != "User":
                    contextualized_line = f"{enhanced_interlocutor_desc} says: {question}"
                    summarized_idea = generate_summarize_ideas(persona, retrieved, contextualized_line)
                else:
                    summarized_idea = generate_summarize_ideas(persona, retrieved, question)
                
                # Add user input to conversation - same format as reverie
                curr_convo.append([interlocutor_desc, question])
                
                # Generate agent response - same method as reverie
                response = generate_next_line(persona, enhanced_interlocutor_desc, curr_convo, summarized_idea)
                curr_convo.append([persona.scratch.name, response])
                
                os.chdir(original_cwd)
                
                print(f"📝 Q: {question}")
                print(f"💬 A: {response}")
                
                return {
                    "persona_name": persona_name,
                    "question": question,
                    "response": response,
                    "category": category,
                    "relevant_memories": relevant_memories,
                    "conversation": curr_convo,
                    "interlocutor_desc": enhanced_interlocutor_desc,
                    "timestamp": datetime.now().isoformat()
                }
                
            except Exception as e:
                print(f"⚠️ Error in reverie conversation generation: {e}")
                os.chdir(original_cwd)
                return {"error": str(e)}
            
        except Exception as e:
            print(f"❌ Conversation failed ({persona_name}): {e}")
            return {"error": str(e)}
    
    def evaluate_dimension(self, dimension: str, conversations: List[Dict], persona_name: str) -> Dict:
        """Evaluate single dimension performance - simplified version"""
        
        # Add simple validation and cleanup functions
        def simple_validate(response, **kwargs):
            return True  # Always pass validation
        
        def simple_cleanup(response, **kwargs):
            return response  # No processing, return directly
    
        # Build evaluation context for this dimension
        conversations_text = ""
        for i, conv in enumerate(conversations, 1):
            # 添加问题和回答
            conversations_text += f"Q{i}: {conv['question']}\n"
            conversations_text += f"A{i}: {conv['response']}\n"
            
            # 添加相关记忆（关键改进）
            if 'relevant_memories' in conv and conv['relevant_memories']:
                conversations_text += f"Related memories:\n{conv['relevant_memories']}\n"
            else:
                conversations_text += "No related memories found.\n"
            conversations_text += "\n"
    
        # 更新评估prompt，要求比对记忆与回答
        evaluation_prompt = f"""
Please evaluate {persona_name}'s performance in the {dimension} dimension.

Conversation records with related memories:
{conversations_text}

Please give a score from 1-10 and briefly explain the reason based on the memory comparison.

Output format:
Score: X.X
Reason: Brief explanation of performance
"""
    
        response = ChatGPT_safe_generate_response(
            evaluation_prompt,
            "Score: 7.5\\nReason: Good performance, reasonable answers",
            "Please output in the specified format",
            repeat=2,
            fail_safe_response="Score: 5.0\\nReason: Evaluation failed",
            func_validate=simple_validate,  
            func_clean_up=simple_cleanup,  
            verbose=False
        )
        
        # Fix: Handle JSON response parsing with error handling
        if response and isinstance(response, str):
            if response.strip().startswith('{') and '"output"' in response:
                try:
                    # Clean JSON string
                    json_str = response.strip()
                    # Remove control characters that might cause issues
                    import re
                    json_str = re.sub(r'[\x00-\x1f\x7f-\x9f]', ' ', json_str)
                    
                    json_data = json.loads(json_str)
                    if "output" in json_data:
                        response = json_data["output"]
                        print(f"✅ Successfully parsed JSON output for {dimension}")
                except json.JSONDecodeError as e:
                    print(f"⚠️ JSON parsing failed for {dimension}: {e}")
                    # Use default response
                    response = "Score: 5.0\nReason: JSON parsing failed"
        
        # If response is not a string, use default value
        if not isinstance(response, str):
            response = "Score: 5.0\nReason: Evaluation failed"
        
        # Parse score
        score = 5.0
        explanation = "Evaluation completed"
        
        lines = response.strip().split('\n')
        for line in lines:
            if 'Score:' in line or '分数:' in line:
                try:
                    score_part = line.split(':', 1)[1].strip()
                    score = float(score_part)
                    score = max(1.0, min(10.0, score))  # Limit to 1-10
                except (ValueError, IndexError):
                    pass
            elif 'Reason:' in line or '理由:' in line:
                try:
                    explanation = line.split(':', 1)[1].strip()
                except IndexError:
                    pass
        
        # Generate individual question scores (based on total score with random variation)
        individual_scores = []
        for _ in conversations:
            variation = random.uniform(-1.0, 1.0)
            individual_score = max(1, min(10, int(score + variation)))
            individual_scores.append(individual_score)
        
        result = {
            "average": round(score, 2),
            "scores": individual_scores,
            "count": len(conversations),
            "explanation": explanation
        }
        
        print(f"  📊 {dimension}: {result['average']:.2f} - {explanation[:50]}...")
        
        return result
        
    def print_evaluation_summary(self, results: Dict):
        """Print evaluation summary - simplified version"""
        print("\n" + "="*60)
        print("📊 Evaluation Results Summary")
        print("="*60)
        
        personas_data = results.get("personas", {})
        valid_results = {name: data for name, data in personas_data.items() if "error" not in data}
        
        if not valid_results:
            print("❌ No valid evaluation results")
            return
        
        # Overall ranking
        ranking = []
        for persona_name, data in valid_results.items():
            if "overall_average" in data:
                ranking.append((persona_name, data["overall_average"]))
        
        ranking.sort(key=lambda x: x[1], reverse=True)
        
        print("\n🏆 Overall Ranking:")
        for i, (name, score) in enumerate(ranking, 1):
            print(f"  {i}. {name}: {score:.2f}")
        
        # Average performance by dimension
        print("\n📈 Average Performance by Dimension:")
        for dim in self.evaluation_categories:
            scores = []
            for persona_name, data in valid_results.items():
                dimension_scores = data.get("dimension_scores", {})
                if dim in dimension_scores and isinstance(dimension_scores[dim], dict):
                    scores.append(dimension_scores[dim]["average"])
            
            if scores:
                avg_score = sum(scores) / len(scores)
                print(f"  {dim}: {avg_score:.2f}")
        
        print(f"\n📋 Evaluation Statistics:")
        print(f"  Evaluated subjects: {len(valid_results)} agents")
        print(f"  Evaluation dimensions: {len(self.evaluation_categories)}")
        print(f"  Generated charts: evaluation_charts/ folder")


    def evaluate_persona(self, persona_name: str, questions: List[Dict]) -> Dict:
        """Evaluate single persona - first collect all responses, then evaluate by dimension"""
        print(f"\n🔍 Starting evaluation: {persona_name}")
        print(f"{'='*50}")
        
        # Display interaction analysis
        interaction_analysis = self.analyze_agent_interactions(persona_name)
        print(f"🤝 Interaction analysis:")
        print(f"  Most frequent interactions: {interaction_analysis.get('most_frequent', [])}")
        print(f"  Total interaction subjects: {len(interaction_analysis.get('has_interactions', []))}")
        
        persona_results = {
            "persona_name": persona_name,
            "total_questions": len(questions),
            "conversations": [],
            "category_scores": {},
            "dimension_scores": {},
            "interaction_analysis": interaction_analysis
        }
        
        # Phase 1: Collect all question responses
        print(f"\n📝 Phase 1: Collecting all question responses ({len(questions)} questions)")
        print("="*50)
        
        for i, question_data in enumerate(questions, 1):
            print(f"\nQuestion {i}/{len(questions)} [{question_data.get('category', 'general')}]")
            
            # Conduct conversation - using reverie method
            conversation_result = self.conduct_conversation(persona_name, question_data)
            
            if "error" not in conversation_result:
                persona_results["conversations"].append(conversation_result)
            
            time.sleep(0.5)  # Avoid API rate limits
        
        if not persona_results["conversations"]:
            print("❌ No successful conversations, cannot evaluate")
            return persona_results
        
        # Phase 2: Evaluate by dimension
        print(f"\n📊 Phase 2: Evaluating by dimension")
        print("="*50)
        
        # Define mapping from question categories to evaluation dimensions
        category_to_dimension = {
            "Self-Knowledge": ["Self-Knowledge"],
            "Memory": ["Memory"],
            "Plans": ["Plans"],
            "Reactions": ["Reactions"],
            "Reflections": ["Reflections"]
        }
        
        # Organize conversations by dimension
        dimension_conversations = {dim: [] for dim in self.evaluation_categories}
        
        for conv in persona_results["conversations"]:
            category = conv.get("category", "general")
            # Map category to corresponding dimension
            if category in category_to_dimension:
                for dim in category_to_dimension[category]:
                    dimension_conversations[dim].append(conv)
        
        # Evaluate each dimension
        dimension_scores = {}
        for dim in self.evaluation_categories:
            dim_convs = dimension_conversations[dim]
            if dim_convs:
                print(f"\n🔍 Evaluating dimension: {dim} ({len(dim_convs)} relevant questions)")
                dim_score = self.evaluate_dimension(dim, dim_convs, persona_name)
                dimension_scores[dim] = dim_score
            else:
                print(f"\n⚠️ Dimension {dim}: No relevant questions")
                dimension_scores[dim] = {
                    "average": 0,
                    "scores": [],
                    "count": 0,
                    "explanation": "No relevant questions for evaluation"
                }
        
        persona_results["dimension_scores"] = dimension_scores
        
        # Calculate overall average score
        all_scores = []
        for dim_data in dimension_scores.values():
            if dim_data["scores"]:
                all_scores.extend(dim_data["scores"])
        
        if all_scores:
            persona_results["overall_average"] = round(sum(all_scores) / len(all_scores), 2)
        
        print(f"\n✅ {persona_name} evaluation complete, overall average: {persona_results.get('overall_average', 'N/A')}")
        return persona_results

    def run_evaluation(self, question_file: str, selected_personas: Optional[List[str]] = None) -> Dict:
        """Run complete evaluation process"""
        
        # Load question set
        try:
            with open(question_file, 'r', encoding='utf-8') as f:
                questions_data = json.load(f)
        except Exception as e:
            print(f"❌ Failed to load question set: {e}")
            return {}
        
        print(f"✅ Loaded question set: {sum(len(qs) for qs in questions_data.values())} questions")
        
        # Determine personas to evaluate
        if selected_personas:
            personas_to_evaluate = [name for name in selected_personas if name in self.personas]
        else:
            personas_to_evaluate = list(self.personas.keys())
        
        if not personas_to_evaluate:
            print("❌ No valid personas to evaluate")
            return {}
        
        print(f"🎯 Starting evaluation of {len(personas_to_evaluate)} personas")
        
        # Store evaluation results
        evaluation_results = {
            "start_time": datetime.now().isoformat(),
            "question_file": question_file,
            "personas": {},
            "summary": {}
        }
        
        # Evaluate each persona
        for i, persona_name in enumerate(personas_to_evaluate, 1):
            print(f"\n{'='*60}")
            print(f"🔍 Evaluation progress: {i}/{len(personas_to_evaluate)} - {persona_name}")
            print(f"{'='*60}")
            
            try:
                # Personalize questions
                personalized_questions = self.personalize_questions(questions_data, persona_name)
                
                # Evaluate persona
                persona_results = self.evaluate_persona(persona_name, personalized_questions)
                evaluation_results["personas"][persona_name] = persona_results
                
            except Exception as e:
                print(f"❌ Error evaluating {persona_name}: {e}")
                evaluation_results["personas"][persona_name] = {"error": str(e)}
        
        # Completion time
        evaluation_results["end_time"] = datetime.now().isoformat()
        
        # Generate summary
        print(f"\n{'='*60}")
        print("📊 Generating evaluation report and visualizations")
        print(f"{'='*60}")
        
        try:
            self.print_evaluation_summary(evaluation_results)
            self.create_evaluation_charts(evaluation_results)
            self.save_evaluation_results(evaluation_results)
        except Exception as e:
            print(f"⚠️ Error generating report: {e}")
        
        return evaluation_results

    def create_evaluation_charts(self, results: Dict):
        """Create evaluation charts"""
        try:
            # Create charts directory
            charts_dir = "evaluation_charts"
            os.makedirs(charts_dir, exist_ok=True)
            
            personas_data = results.get("personas", {})
            valid_results = {name: data for name, data in personas_data.items() if "error" not in data}
            
            if not valid_results:
                print("❌ No valid data to generate charts")
                return
            
            # 1. Radar chart
            self.create_radar_chart(valid_results, charts_dir)
            
            # 2. Comparison bar chart
            self.create_comparison_chart(valid_results, charts_dir)
            
            print(f"✅ Charts saved to {charts_dir}/ folder")
            
        except Exception as e:
            print(f"❌ Failed to create charts: {e}")

    def create_radar_chart(self, results: Dict, output_dir: str):
        """Create radar chart"""
        try:
            # Prepare data
            personas = list(results.keys())
            dimensions = self.evaluation_categories
            
            # Create angles
            angles = np.linspace(0, 2 * np.pi, len(dimensions), endpoint=False).tolist()
            angles += angles[:1]  # Close the shape
            
            # Create chart
            fig, ax = plt.subplots(figsize=(10, 10), subplot_kw=dict(projection='polar'))
            
            colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FECA57', '#FF9FF3', '#54A0FF']
            
            for i, persona_name in enumerate(personas):
                persona_data = results[persona_name]
                dimension_scores = persona_data.get("dimension_scores", {})
                
                values = []
                for dim in dimensions:
                    if dim in dimension_scores and isinstance(dimension_scores[dim], dict):
                        values.append(dimension_scores[dim]["average"])
                    else:
                        values.append(0)
                
                values += values[:1]  # Close the shape
                
                ax.plot(angles, values, 'o-', linewidth=2, label=persona_name, 
                    color=colors[i % len(colors)])
                ax.fill(angles, values, alpha=0.25, color=colors[i % len(colors)])
            
            # Set up chart
            ax.set_xticks(angles[:-1])
            ax.set_xticklabels(dimensions)
            ax.set_ylim(0, 10)
            ax.set_yticks([2, 4, 6, 8, 10])
            ax.set_yticklabels(['2', '4', '6', '8', '10'])
            ax.grid(True)
            
            plt.legend(loc='upper right', bbox_to_anchor=(0.1, 0.1))
            plt.title('Agent Quality Evaluation - Five Dimension Radar Chart', size=16, pad=20)
            
            # Save chart
            plt.savefig(f"{output_dir}/radar_chart.png", dpi=300, bbox_inches='tight')
            plt.close()
            
        except Exception as e:
            print(f"❌ Failed to create radar chart: {e}")

    def create_comparison_chart(self, results: Dict, output_dir: str):
        """Create comparison bar chart"""
        try:
            personas = list(results.keys())
            dimensions = self.evaluation_categories
            
            # Prepare data
            data = []
            for persona_name in personas:
                persona_data = results[persona_name]
                dimension_scores = persona_data.get("dimension_scores", {})
                
                row = [persona_name]
                for dim in dimensions:
                    if dim in dimension_scores and isinstance(dimension_scores[dim], dict):
                        row.append(dimension_scores[dim]["average"])
                    else:
                        row.append(0)
                data.append(row)
            
            # Create DataFrame
            import pandas as pd
            df = pd.DataFrame(data, columns=['Persona'] + dimensions)
            df.set_index('Persona', inplace=True)
            
            # Create bar chart
            fig, ax = plt.subplots(figsize=(12, 8))
            df.plot(kind='bar', ax=ax, width=0.8)
            
            plt.title('Agent Quality Evaluation - Dimension Comparison Chart', size=16, pad=20)
            plt.xlabel('Personas', size=12)
            plt.ylabel('Score (1-10)', size=12)
            plt.legend(title='Evaluation Dimensions', bbox_to_anchor=(1.05, 1), loc='upper left')
            plt.xticks(rotation=45, ha='right')
            plt.grid(axis='y', alpha=0.3)
            
            # Save chart
            plt.tight_layout()
            plt.savefig(f"{output_dir}/comparison_chart.png", dpi=300, bbox_inches='tight')
            plt.close()
            
        except Exception as e:
            print(f"❌ Failed to create comparison chart: {e}")

    def save_evaluation_results(self, results: Dict):
        """Save evaluation results to JSON file"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"evaluation_results_{timestamp}.json"
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(results, f, ensure_ascii=False, indent=2)
            
            print(f"✅ Evaluation results saved to: {filename}")
            
        except Exception as e:
            print(f"❌ Failed to save results: {e}")

def main():
    """Main function"""
    print("🔧 Final Agent Quality Evaluation System")
    print("Evaluate agents based on five dimensions, supporting name replacement and visualization")
    print("="*60)
    
    # Show available simulations
    storage_path = "../../environment/frontend_server/storage"
    if not os.path.exists(storage_path):
        print("❌ Storage path doesn't exist")
        return
    
    available_sims = []
    for item in os.listdir(storage_path):
        sim_path = os.path.join(storage_path, item)
        if os.path.isdir(sim_path) and os.path.exists(f"{sim_path}/reverie/meta.json"):
            available_sims.append(item)
    
    if not available_sims:
        print("❌ No available simulations found")
        return
    
    print(f"\n📋 Available simulations:")
    for i, sim in enumerate(available_sims, 1):
        print(f"  {i}. {sim}")
    
    # User input
    sim_code = input(f"\nEnter simulation name: ").strip()
    if not sim_code or sim_code not in available_sims:
        print("❌ Invalid simulation name")
        return
    
    question_file = "questions.json"
    
    if not os.path.exists(question_file):
        print(f"❌ Question set file doesn't exist: {question_file}")
        return
    
    # Initialize evaluator
    evaluator = AgentEvaluator(sim_code)
    
    # Load simulation data
    if not evaluator.load_simulation_data():
        return
    
    # Select personas to evaluate
    available_personas = list(evaluator.personas.keys())
    print(f"\nAvailable Personas: {', '.join(available_personas)}")
    
    persona_input = input("Enter persona names to evaluate (comma separated, leave empty to evaluate all): ").strip()
    if persona_input:
        selected_personas = [name.strip() for name in persona_input.split(",")]
        selected_personas = [name for name in selected_personas if name in available_personas]
    else:
        selected_personas = None
    
    # Confirm start evaluation
    if selected_personas:
        print(f"\n🎯 Will evaluate: {', '.join(selected_personas)}")
    else:
        print(f"\n🎯 Will evaluate all {len(available_personas)} personas")
    
    # Run evaluation
    results = evaluator.run_evaluation(question_file, selected_personas)
    
    print("\n✅ Evaluation complete!")
    print("📊 Please check the evaluation_charts/ folder for charts")


if __name__ == "__main__":
    main()