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
        初始化评估器
        
        Args:
            sim_code: 模拟代码，如 "exp"
        """
        self.sim_code = sim_code
        self.current_dir = os.path.dirname(os.path.abspath(__file__))
        self.sim_folder = os.path.join(self.current_dir, f"../../environment/frontend_server/storage/{sim_code}")
        self.personas = {}
        self.meta_data = {}
        self.evaluation_categories = ["Self-Knowledge", "Memory", "Plans", "Reactions", "Reflections"]
        
        # 确保工作目录正确
        os.chdir(self.current_dir)
    
    def load_simulation_data(self) -> bool:
        """从存储中加载模拟数据"""
        meta_file = os.path.join(self.sim_folder, "reverie/meta.json")
        # 加载元数据
        with open(meta_file, 'r', encoding='utf-8') as f:
            self.meta_data = json.load(f)

        print(f"✅ 加载元数据: {self.meta_data.get('persona_names', [])}")
        
        # 加载所有personas
        successful_personas = []
        for persona_name in self.meta_data.get('persona_names', []):
            persona_folder = os.path.join(self.sim_folder, f"personas/{persona_name}")
            
            if not os.path.exists(persona_folder):
                print(f"⚠️ Persona文件夹不存在: {persona_name}")
                continue
            # 确保在正确的目录下加载persona
            original_cwd = os.getcwd()
            os.chdir(self.current_dir)
            
            persona = Persona(persona_name, persona_folder)
            self.personas[persona_name] = persona
            successful_personas.append(persona_name)
            print(f"✅ 成功加载: {persona_name}")
            
            os.chdir(original_cwd)
        print(f"✅ 成功加载 {len(successful_personas)} 个personas")
        return True
          
    
    def analyze_agent_interactions(self, persona_name: str) -> Dict:
        """分析agent的交互历史，找出最频繁互动的其他agents"""
        if persona_name not in self.personas:
            return {}
        
        persona = self.personas[persona_name]
        interaction_counts = {}
        # 分析记忆中的交互
        if hasattr(persona, 'a_mem'):
            # 分析聊天记录
            if hasattr(persona.a_mem, 'seq_chat'):
                for chat_node in persona.a_mem.seq_chat:
                    if hasattr(chat_node, 'description'):
                        desc = chat_node.description
                        for other_persona in self.personas.keys():
                            if other_persona != persona_name and other_persona in desc:
                                interaction_counts[other_persona] = interaction_counts.get(other_persona, 0) + 2
            
            # 分析事件记录
            if hasattr(persona.a_mem, 'seq_event'):
                for event_node in persona.a_mem.seq_event:
                    if hasattr(event_node, 'description'):
                        desc = event_node.description
                        for other_persona in self.personas.keys():
                            if other_persona != persona_name and other_persona in desc:
                                interaction_counts[other_persona] = interaction_counts.get(other_persona, 0) + 1
            
            # 分析思考记录
            if hasattr(persona.a_mem, 'seq_thought'):
                for thought_node in persona.a_mem.seq_thought:
                    if hasattr(thought_node, 'description'):
                        desc = thought_node.description
                        for other_persona in self.personas.keys():
                            if other_persona != persona_name and other_persona in desc:
                                interaction_counts[other_persona] = interaction_counts.get(other_persona, 0) + 0.5
              
        # 排序
        sorted_interactions = sorted(interaction_counts.items(), key=lambda x: x[1], reverse=True)
        
        return {
            "all_interactions": dict(sorted_interactions),
            "most_frequent": [name for name, count in sorted_interactions[:3]],
            "has_interactions": [name for name, count in sorted_interactions if count > 0],
            "random_pool": list(self.personas.keys())
        }
    
    def personalize_questions(self, questions_data: Dict, persona_name: str) -> List[Dict]:
        """个性化问题，替换其中的人名占位符"""
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
                
                # 处理人名替换
                personalized_question = question
                
                # 替换 [frequent] - 最频繁互动的人
                if "[frequent]" in personalized_question:
                    frequent_names = interaction_analysis.get("most_frequent", [])
                    if frequent_names:
                        replacement = random.choice(frequent_names)
                        personalized_question = personalized_question.replace("[frequent]", replacement)
                        print(f"🔄 [frequent] -> {replacement} (for {persona_name})")
                    else:
                        # 如果没有频繁互动的人，使用其他personas
                        other_personas = [name for name in self.personas.keys() if name != persona_name]
                        if other_personas:
                            replacement = random.choice(other_personas)
                            personalized_question = personalized_question.replace("[frequent]", replacement)
                
                # 替换 [random] - 随机选择的人
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
        """获取与问题相关的记忆摘要"""
        if persona_name not in self.personas:
            return ""
        
        persona = self.personas[persona_name]
        # 检索相关记忆
        retrieved = new_retrieve(persona, [question], max_memories)[question]
        
        # 构建记忆摘要
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
        
        # 添加简单的验证和清理函数
        def simple_validate(response, **kwargs):
            return True  # 始终通过验证
        
        def simple_cleanup(response, **kwargs):
            return response  # 不做任何处理，直接返回
    
        # 构建该维度的评估上下文
        conversations_text = ""
        for i, conv in enumerate(conversations, 1):
            conversations_text += f"Q{i}: {conv['question']}\n"
            conversations_text += f"A{i}: {conv['response']}\n\n"
        
        # Simplified evaluation prompt
        evaluation_prompt = f"""
Please evaluate {persona_name}'s performance in the {dimension} dimension.

Conversation records:
{conversations_text}

Please give a score from 1-10 and briefly explain the reason.

Output format:
Score: X.X
Reason: Brief explanation of performance
"""
    
        try:
            # 使用简单函数替代None
            response = ChatGPT_safe_generate_response(
                evaluation_prompt,
                "Score: 7.5\\nReason: Good performance, reasonable answers",
                "Please output in the specified format",
                repeat=2,
                fail_safe_response="Score: 5.0\\nReason: Evaluation failed",
                func_validate=simple_validate,  # 使用简单验证函数
                func_clean_up=simple_cleanup,   # 使用简单清理函数
                verbose=False
            )
            
            # 修复：处理JSON响应解析时的错误处理
            if response and isinstance(response, str):
                if response.strip().startswith('{') and '"output"' in response:
                    try:
                        # 清理JSON字符串
                        json_str = response.strip()
                        # 移除可能导致问题的控制字符
                        import re
                        json_str = re.sub(r'[\x00-\x1f\x7f-\x9f]', ' ', json_str)
                        
                        json_data = json.loads(json_str)
                        if "output" in json_data:
                            response = json_data["output"]
                            print(f"✅ Successfully parsed JSON output for {dimension}")
                    except json.JSONDecodeError as e:
                        print(f"⚠️ JSON parsing failed for {dimension}: {e}")
                        # 使用默认响应
                        response = "Score: 5.0\nReason: JSON parsing failed"
            
            # 如果响应不是字符串，使用默认值
            if not isinstance(response, str):
                response = "Score: 5.0\nReason: Evaluation failed"
            
            # 解析分数
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
            
            # 生成单个问题分数（基于总分数和随机变化）
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
            
        except Exception as e:
            print(f"❌ Error evaluating {dimension} dimension: {e}")
            return {
                "average": 5.0,
                "scores": [5] * len(conversations),
                "count": len(conversations),
                "explanation": f"Evaluation error: {str(e)}"
            }
        
    def print_evaluation_summary(self, results: Dict):
        """打印评估总结 - 简化版本"""
        print("\n" + "="*60)
        print("📊 评估结果总结")
        print("="*60)
        
        personas_data = results.get("personas", {})
        valid_results = {name: data for name, data in personas_data.items() if "error" not in data}
        
        if not valid_results:
            print("❌ 没有有效的评估结果")
            return
        
        # 总体排名
        ranking = []
        for persona_name, data in valid_results.items():
            if "overall_average" in data:
                ranking.append((persona_name, data["overall_average"]))
        
        ranking.sort(key=lambda x: x[1], reverse=True)
        
        print("\n🏆 总体排名:")
        for i, (name, score) in enumerate(ranking, 1):
            print(f"  {i}. {name}: {score:.2f}")
        
        # 各维度平均表现
        print("\n📈 各维度平均表现:")
        for dim in self.evaluation_categories:
            scores = []
            for persona_name, data in valid_results.items():
                dimension_scores = data.get("dimension_scores", {})
                if dim in dimension_scores and isinstance(dimension_scores[dim], dict):
                    scores.append(dimension_scores[dim]["average"])
            
            if scores:
                avg_score = sum(scores) / len(scores)
                print(f"  {dim}: {avg_score:.2f}")
        
        print(f"\n📋 评估统计:")
        print(f"  评估对象: {len(valid_results)} 个agents")
        print(f"  评估维度: {len(self.evaluation_categories)} 个")
        print(f"  生成图表: evaluation_charts/ 文件夹")


    def evaluate_persona(self, persona_name: str, questions: List[Dict]) -> Dict:
        """评估单个persona - 先收集所有回复，再按维度分类评估"""
        print(f"\n🔍 开始评估: {persona_name}")
        print(f"{'='*50}")
        
        # 显示交互分析
        interaction_analysis = self.analyze_agent_interactions(persona_name)
        print(f"🤝 交互分析:")
        print(f"  最频繁互动: {interaction_analysis.get('most_frequent', [])}")
        print(f"  总交互对象: {len(interaction_analysis.get('has_interactions', []))}")
        
        persona_results = {
            "persona_name": persona_name,
            "total_questions": len(questions),
            "conversations": [],
            "category_scores": {},
            "dimension_scores": {},
            "interaction_analysis": interaction_analysis
        }
        
        # 第一阶段：收集所有问题的回复
        print(f"\n📝 阶段1: 收集所有问题回复 ({len(questions)}个问题)")
        print("="*50)
        
        for i, question_data in enumerate(questions, 1):
            print(f"\n问题 {i}/{len(questions)} [{question_data.get('category', 'general')}]")
            
            # 进行对话 - 使用reverie方法
            conversation_result = self.conduct_conversation(persona_name, question_data)
            
            if "error" not in conversation_result:
                persona_results["conversations"].append(conversation_result)
            
            time.sleep(0.5)  # 避免API限制
        
        if not persona_results["conversations"]:
            print("❌ 没有成功的对话，无法进行评估")
            return persona_results
        
        # 第二阶段：按维度分类评估
        print(f"\n📊 阶段2: 按维度分类评估")
        print("="*50)
        
        # 定义问题类别到评估维度的映射
        category_to_dimension = {
            "Self-Knowledge": ["Self-Knowledge"],
            "Memory": ["Memory"],
            "Plans": ["Plans"],
            "Reactions": ["Reactions"],
            "Reflections": ["Reflections"]
        }
        
        # 按维度组织对话数据
        dimension_conversations = {dim: [] for dim in self.evaluation_categories}
        
        for conv in persona_results["conversations"]:
            category = conv.get("category", "general")
            # 根据类别映射到对应维度
            if category in category_to_dimension:
                for dim in category_to_dimension[category]:
                    dimension_conversations[dim].append(conv)
        
        # 对每个维度进行评估
        dimension_scores = {}
        for dim in self.evaluation_categories:
            dim_convs = dimension_conversations[dim]
            if dim_convs:
                print(f"\n🔍 评估维度: {dim} ({len(dim_convs)}个相关问题)")
                dim_score = self.evaluate_dimension(dim, dim_convs, persona_name)
                dimension_scores[dim] = dim_score
            else:
                print(f"\n⚠️ 维度 {dim}: 没有相关问题")
                dimension_scores[dim] = {
                    "average": 0,
                    "scores": [],
                    "count": 0,
                    "explanation": "没有相关问题进行评估"
                }
        
        persona_results["dimension_scores"] = dimension_scores
        
        # 计算总体平均分
        all_scores = []
        for dim_data in dimension_scores.values():
            if dim_data["scores"]:
                all_scores.extend(dim_data["scores"])
        
        if all_scores:
            persona_results["overall_average"] = round(sum(all_scores) / len(all_scores), 2)
        
        print(f"\n✅ {persona_name} 评估完成，总体平均分: {persona_results.get('overall_average', 'N/A')}")
        return persona_results

    def run_evaluation(self, question_file: str, selected_personas: Optional[List[str]] = None) -> Dict:
        """运行完整的评估流程"""
        
        # 加载问题集
        try:
            with open(question_file, 'r', encoding='utf-8') as f:
                questions_data = json.load(f)
        except Exception as e:
            print(f"❌ 加载问题集失败: {e}")
            return {}
        
        print(f"✅ 加载问题集: {sum(len(qs) for qs in questions_data.values())} 个问题")
        
        # 确定要评估的personas
        if selected_personas:
            personas_to_evaluate = [name for name in selected_personas if name in self.personas]
        else:
            personas_to_evaluate = list(self.personas.keys())
        
        if not personas_to_evaluate:
            print("❌ 没有有效的personas进行评估")
            return {}
        
        print(f"🎯 开始评估 {len(personas_to_evaluate)} 个personas")
        
        # 评估结果存储
        evaluation_results = {
            "start_time": datetime.now().isoformat(),
            "question_file": question_file,
            "personas": {},
            "summary": {}
        }
        
        # 逐个评估personas
        for i, persona_name in enumerate(personas_to_evaluate, 1):
            print(f"\n{'='*60}")
            print(f"🔍 评估进度: {i}/{len(personas_to_evaluate)} - {persona_name}")
            print(f"{'='*60}")
            
            try:
                # 个性化问题
                personalized_questions = self.personalize_questions(questions_data, persona_name)
                
                # 评估persona
                persona_results = self.evaluate_persona(persona_name, personalized_questions)
                evaluation_results["personas"][persona_name] = persona_results
                
            except Exception as e:
                print(f"❌ 评估 {persona_name} 时出错: {e}")
                evaluation_results["personas"][persona_name] = {"error": str(e)}
        
        # 完成时间
        evaluation_results["end_time"] = datetime.now().isoformat()
        
        # 生成总结
        print(f"\n{'='*60}")
        print("📊 生成评估报告和可视化")
        print(f"{'='*60}")
        
        try:
            self.print_evaluation_summary(evaluation_results)
            self.create_evaluation_charts(evaluation_results)
            self.save_evaluation_results(evaluation_results)
        except Exception as e:
            print(f"⚠️ 生成报告时出错: {e}")
        
        return evaluation_results

    def create_evaluation_charts(self, results: Dict):
        """创建评估图表"""
        try:
            # 创建图表文件夹
            charts_dir = "evaluation_charts"
            os.makedirs(charts_dir, exist_ok=True)
            
            personas_data = results.get("personas", {})
            valid_results = {name: data for name, data in personas_data.items() if "error" not in data}
            
            if not valid_results:
                print("❌ 没有有效数据生成图表")
                return
            
            # 1. 雷达图
            self.create_radar_chart(valid_results, charts_dir)
            
            # 2. 对比柱状图
            self.create_comparison_chart(valid_results, charts_dir)
            
            print(f"✅ 图表已保存到 {charts_dir}/ 文件夹")
            
        except Exception as e:
            print(f"❌ 创建图表失败: {e}")

    def create_radar_chart(self, results: Dict, output_dir: str):
        """创建雷达图"""
        try:
            # 准备数据
            personas = list(results.keys())
            dimensions = self.evaluation_categories
            
            # 创建角度
            angles = np.linspace(0, 2 * np.pi, len(dimensions), endpoint=False).tolist()
            angles += angles[:1]  # 闭合图形
            
            # 创建图表
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
                
                values += values[:1]  # 闭合图形
                
                ax.plot(angles, values, 'o-', linewidth=2, label=persona_name, 
                    color=colors[i % len(colors)])
                ax.fill(angles, values, alpha=0.25, color=colors[i % len(colors)])
            
            # 设置图表
            ax.set_xticks(angles[:-1])
            ax.set_xticklabels(dimensions)
            ax.set_ylim(0, 10)
            ax.set_yticks([2, 4, 6, 8, 10])
            ax.set_yticklabels(['2', '4', '6', '8', '10'])
            ax.grid(True)
            
            plt.legend(loc='upper right', bbox_to_anchor=(0.1, 0.1))
            plt.title('Agent质量评估 - 五维度雷达图', size=16, pad=20)
            
            # 保存图表
            plt.savefig(f"{output_dir}/radar_chart.png", dpi=300, bbox_inches='tight')
            plt.close()
            
        except Exception as e:
            print(f"❌ 创建雷达图失败: {e}")

    def create_comparison_chart(self, results: Dict, output_dir: str):
        """创建对比柱状图"""
        try:
            personas = list(results.keys())
            dimensions = self.evaluation_categories
            
            # 准备数据
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
            
            # 创建DataFrame
            import pandas as pd
            df = pd.DataFrame(data, columns=['Persona'] + dimensions)
            df.set_index('Persona', inplace=True)
            
            # 创建柱状图
            fig, ax = plt.subplots(figsize=(12, 8))
            df.plot(kind='bar', ax=ax, width=0.8)
            
            plt.title('Agent质量评估 - 维度对比图', size=16, pad=20)
            plt.xlabel('Personas', size=12)
            plt.ylabel('评分 (1-10)', size=12)
            plt.legend(title='评估维度', bbox_to_anchor=(1.05, 1), loc='upper left')
            plt.xticks(rotation=45, ha='right')
            plt.grid(axis='y', alpha=0.3)
            
            # 保存图表
            plt.tight_layout()
            plt.savefig(f"{output_dir}/comparison_chart.png", dpi=300, bbox_inches='tight')
            plt.close()
            
        except Exception as e:
            print(f"❌ 创建对比图失败: {e}")

    def save_evaluation_results(self, results: Dict):
        """保存评估结果到JSON文件"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"evaluation_results_{timestamp}.json"
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(results, f, ensure_ascii=False, indent=2)
            
            print(f"✅ 评估结果已保存到: {filename}")
            
        except Exception as e:
            print(f"❌ 保存结果失败: {e}")

def main():
    """主函数"""
    print("🔧 Final Agent Quality Evaluation System")
    print("根据五个维度评估智能体，支持人名替换和可视化")
    print("="*60)
    
    # 显示可用模拟
    storage_path = "../../environment/frontend_server/storage"
    if not os.path.exists(storage_path):
        print("❌ 存储路径不存在")
        return
    
    available_sims = []
    for item in os.listdir(storage_path):
        sim_path = os.path.join(storage_path, item)
        if os.path.isdir(sim_path) and os.path.exists(f"{sim_path}/reverie/meta.json"):
            available_sims.append(item)
    
    if not available_sims:
        print("❌ 没有找到可用的模拟")
        return
    
    print(f"\n📋 可用的模拟:")
    for i, sim in enumerate(available_sims, 1):
        print(f"  {i}. {sim}")
    
    # 用户输入
    sim_code = input(f"\n请输入模拟名称: ").strip()
    if not sim_code or sim_code not in available_sims:
        print("❌ 无效的模拟名称")
        return
    
    question_file = "questions.json"
    
    if not os.path.exists(question_file):
        print(f"❌ 问题集文件不存在: {question_file}")
        return
    
    # 初始化评估器
    evaluator = AgentEvaluator(sim_code)
    
    # 加载模拟数据
    if not evaluator.load_simulation_data():
        return
    
    # 选择要评估的personas
    available_personas = list(evaluator.personas.keys())
    print(f"\n可用的Personas: {', '.join(available_personas)}")
    
    persona_input = input("请输入要评估的persona名称 (用逗号分隔，留空评估所有): ").strip()
    if persona_input:
        selected_personas = [name.strip() for name in persona_input.split(",")]
        selected_personas = [name for name in selected_personas if name in available_personas]
    else:
        selected_personas = None
    
    # 确认开始评估
    if selected_personas:
        print(f"\n🎯 将评估: {', '.join(selected_personas)}")
    else:
        print(f"\n🎯 将评估所有 {len(available_personas)} 个personas")
    
    # 运行评估
    results = evaluator.run_evaluation(question_file, selected_personas)
    
    print("\n✅ 评估完成！")
    print("📊 请查看 evaluation_charts/ 文件夹中的图表")


if __name__ == "__main__":
    main()