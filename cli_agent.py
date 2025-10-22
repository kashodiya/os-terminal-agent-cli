import subprocess
import json
import platform
import os
import pickle
from datetime import datetime
from typing import List, Dict, Any
import boto3
from strands import Agent, tool
from safety_guardrails import SafetyGuardrails

class CLIAgent(Agent):
    """Agent that can execute CLI commands and handle complex multi-step tasks."""
    
    def __init__(self, session_id: str = None, safe_mode: bool = True):
        # Initialize safety guardrails
        self.safety = SafetyGuardrails(safe_mode=safe_mode)
        self.safe_mode = safe_mode
        
        # Load and display system prompt
        system_prompt = self._load_system_prompt()
        print("🤖 CLI Agent System Prompt:")
        print("=" * 50)
        print(system_prompt)
        print("=" * 50)
        
        if safe_mode:
            print("🛡️  SAFETY MODE: ON - Dangerous commands will be blocked or require confirmation")
        else:
            print("⚠️  SAFETY MODE: OFF - All commands allowed (USE WITH CAUTION)")
        print("=" * 50)
        
        super().__init__(
            name="CLI Command Agent",
            description="An agent that can execute any CLI command and handle complex tasks by breaking them into steps",
            model="us.anthropic.claude-3-7-sonnet-20250219-v1:0",
            system_prompt=system_prompt
        )
        self.bedrock = boto3.client('bedrock-runtime', region_name='us-east-1')
        self.session_id = session_id or f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.memory_file = f".cli_memory_{self.session_id}.pkl"
        self.conversation_history = self._load_memory()
    
    def _load_system_prompt(self) -> str:
        """Load system prompt from SYSTEM-PROMPT.md file."""
        try:
            with open('SYSTEM-PROMPT.md', 'r', encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            return "You are a CLI Command Agent that helps execute system commands and answer questions."
    
    def _load_memory(self) -> List[Dict[str, Any]]:
        """Load conversation history from file."""
        if os.path.exists(self.memory_file):
            try:
                with open(self.memory_file, 'rb') as f:
                    return pickle.load(f)
            except:
                pass
        return []
    
    def _save_memory(self):
        """Save conversation history to file."""
        try:
            with open(self.memory_file, 'wb') as f:
                pickle.dump(self.conversation_history, f)
        except:
            pass
    
    def _add_to_memory(self, interaction_type: str, input_data: str, output_data: str, success: bool = True):
        """Add interaction to conversation memory."""
        self.conversation_history.append({
            'timestamp': datetime.now().isoformat(),
            'type': interaction_type,
            'input': input_data,
            'output': output_data,
            'success': success
        })
        # Keep only last 20 interactions
        if len(self.conversation_history) > 20:
            self.conversation_history = self.conversation_history[-20:]
        self._save_memory()
    
    def _get_context_prompt(self) -> str:
        """Generate context from recent conversation history."""
        if not self.conversation_history:
            return ""
        
        context_lines = ["Previous conversation context:"]
        for item in self.conversation_history[-5:]:  # Last 5 interactions
            context_lines.append(f"- {item['type']}: {item['input'][:100]} -> {item['output'][:100]}")
        
        return "\n".join(context_lines) + "\n\n"
        self.session_id = session_id or f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.memory_file = f".cli_memory_{self.session_id}.pkl"
        self.conversation_history = self._load_memory()
    
    @tool
    def execute_command(self, command: str, working_directory: str = None, force: bool = False) -> Dict[str, Any]:
        """Execute a CLI command and return the result.
        
        Args:
            command: The CLI command to execute
            working_directory: Optional working directory for the command
            force: Skip safety checks (use with extreme caution)
            
        Returns:
            Dictionary with command output, error, and return code
        """
        print(f"🔧 Tool: execute_command(command='{command}', working_directory={working_directory})")
        if working_directory:
            print(f"📁 Working directory: {working_directory}")
        
        # Safety validation (unless forced)
        if not force:
            validation = self.safety.validate_command(command, working_directory)
            
            # Display risk assessment
            risk_level = validation['risk_level']
            risk_icons = {'safe': '✅', 'low': '🟡', 'medium': '🟠', 'high': '🔴', 'critical': '⛔'}
            print(f"{risk_icons.get(risk_level, '❓')} Risk Level: {risk_level.upper()} - {validation['reason']}")
            
            # Display warnings
            for warning in validation['warnings']:
                print(f"⚠️  Warning: {warning}")
            
            # Block if not allowed
            if not validation['allowed']:
                error_msg = f"Command blocked: {validation['blocked_reason']}"
                print(f"❌ {error_msg}")
                
                # Suggest alternatives
                alternatives = self.safety.get_safe_alternatives(command)
                if alternatives:
                    print("💡 Suggested alternatives:")
                    for alt in alternatives:
                        print(f"  - {alt}")
                
                self._add_to_memory('command', command, error_msg, False)
                return {
                    "command": command,
                    "stdout": "",
                    "stderr": error_msg,
                    "return_code": -1,
                    "success": False,
                    "blocked": True,
                    "risk_level": risk_level
                }
            
            # Require confirmation for risky commands
            if validation['requires_confirmation']:
                print(f"❓ This command requires confirmation due to {risk_level} risk level.")
                
                # Show backup recommendation
                backup_rec = self.safety.create_backup_recommendation(command)
                if backup_rec:
                    print(f"💾 Backup recommendation: {backup_rec}")
                
                print("⚠️  Command execution paused. Use force=True to override or modify the command.")
                self._add_to_memory('command', command, "Execution paused - confirmation required", False)
                return {
                    "command": command,
                    "stdout": "",
                    "stderr": "Execution paused - confirmation required",
                    "return_code": -2,
                    "success": False,
                    "requires_confirmation": True,
                    "risk_level": risk_level
                }
            
        try:
            print("⚙️  Executing command...")
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                cwd=working_directory
            )
            
            print(f"📤 Command output:")
            if result.stdout:
                print(f"STDOUT:\n{result.stdout}")
            if result.stderr:
                print(f"STDERR:\n{result.stderr}")
            print(f"Return code: {result.returncode}")
            
            # Save to memory
            output_summary = result.stdout[:200] if result.stdout else result.stderr[:200]
            self._add_to_memory('command', command, output_summary, result.returncode == 0)
            
            return {
                "command": command,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "return_code": result.returncode,
                "success": result.returncode == 0
            }
        except Exception as e:
            print(f"❌ Exception during execution: {str(e)}")
            self._add_to_memory('command', command, str(e), False)
            return {
                "command": command,
                "stdout": "",
                "stderr": str(e),
                "return_code": -1,
                "success": False
            }
    
    @tool
    def answer_question(self, question: str, working_directory: str = None) -> Dict[str, Any]:
        """Answer a natural language question by determining the appropriate CLI command and executing it.
        
        Args:
            question: Natural language question in English
            working_directory: Optional working directory for the command
            
        Returns:
            Dictionary with the answer, command used, and execution result
        """
        print(f"🔧 Tool: answer_question(question='{question}', working_directory={working_directory})")
        # Detect operating system
        is_windows = platform.system().lower() == 'windows'
        
        if is_windows:
            examples = """
Examples for Windows:
- "What files are in this directory?" -> "dir"
- "What's my current location?" -> "cd"
- "What processes are running?" -> "tasklist"
- "How much disk space is available?" -> "wmic logicaldisk get size,freespace,caption"
- "What's in this file?" -> "type filename"
- "What's the system info?" -> "systeminfo"""
        else:
            examples = """
Examples for Unix/Linux:
- "What files are in this directory?" -> "ls -la"
- "What's my current location?" -> "pwd"
- "What processes are running?" -> "ps aux"
- "How much disk space is available?" -> "df -h"
- "What's in this file?" -> "cat filename"""
        
        context = self._get_context_prompt()
        prompt = f"""{context}Convert this English question to the most appropriate CLI command for {platform.system()}:

Question: {question}

Provide only the CLI command that would answer this question. Be specific and use commands available on {platform.system()}.
If multiple commands are needed, provide the most important one.
{examples}

Command:"""
        
        try:
            print(f"🤔 Thinking: Converting question '{question}' to appropriate command for {platform.system()}...")
            
            response = self.bedrock.invoke_model(
                modelId="us.anthropic.claude-3-7-sonnet-20250219-v1:0",
                body=json.dumps({
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": 200,
                    "messages": [{"role": "user", "content": prompt}]
                })
            )
            
            result = json.loads(response['body'].read())
            command = result['content'][0]['text'].strip()
            
            # Clean up the command (remove any extra text)
            command_lines = command.split('\n')
            command = command_lines[0].strip()
            
            print(f"💡 Selected command: {command}")
            print(f"⚡ Executing command...")
            
            # Execute the command
            exec_result = self.execute_command(command, working_directory)
            
            if exec_result['success']:
                print(f"✅ Command executed successfully")
            else:
                print(f"❌ Command failed with return code {exec_result['return_code']}")
                if exec_result['stderr']:
                    print(f"Error: {exec_result['stderr']}")
            
            print(f"🧠 Interpreting results...")
            
            # Generate human-readable answer
            context = self._get_context_prompt()
            answer_prompt = f"""{context}Based on this command output, provide a clear English answer to the original question.

Original Question: {question}
Command Used: {command}
Command Output: {exec_result['stdout']}
Command Error: {exec_result['stderr']}

Provide a concise, helpful answer in plain English:"""
            
            answer_response = self.bedrock.invoke_model(
                modelId="us.anthropic.claude-3-7-sonnet-20250219-v1:0",
                body=json.dumps({
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": 300,
                    "messages": [{"role": "user", "content": answer_prompt}]
                })
            )
            
            answer_result = json.loads(answer_response['body'].read())
            answer = answer_result['content'][0]['text'].strip()
            
            print(f"📝 Generated answer: {answer[:100]}{'...' if len(answer) > 100 else ''}")
            
            # Save to memory
            self._add_to_memory('question', question, answer, exec_result['success'])
            
            return {
                "question": question,
                "command_used": command,
                "answer": answer,
                "raw_output": exec_result,
                "success": exec_result['success']
            }
            
        except Exception as e:
            error_msg = f"Sorry, I couldn't process your question: {str(e)}"
            self._add_to_memory('question', question, error_msg, False)
            return {
                "question": question,
                "command_used": "unknown",
                "answer": error_msg,
                "raw_output": None,
                "success": False
            }
    
    def answer_question_with_force(self, question: str, working_directory: str = None) -> Dict[str, Any]:
        """Answer a question with force mode enabled for risky commands."""
        print(f"🔧 Tool: answer_question_with_force(question='{question}', working_directory={working_directory})")
        is_windows = platform.system().lower() == 'windows'
        
        if is_windows:
            examples = """
Examples for Windows:
- "What files are in this directory?" -> "dir"
- "What's my current location?" -> "cd"
- "What processes are running?" -> "tasklist"
- "How much disk space is available?" -> "wmic logicaldisk get size,freespace,caption"
- "What's in this file?" -> "type filename"
- "What's the system info?" -> "systeminfo"""
        else:
            examples = """
Examples for Unix/Linux:
- "What files are in this directory?" -> "ls -la"
- "What's my current location?" -> "pwd"
- "What processes are running?" -> "ps aux"
- "How much disk space is available?" -> "df -h"
- "What's in this file?" -> "cat filename"""
        
        context = self._get_context_prompt()
        prompt = f"""{context}Convert this English question to the most appropriate CLI command for {platform.system()}:

Question: {question}

Provide only the CLI command that would answer this question. Be specific and use commands available on {platform.system()}.
If multiple commands are needed, provide the most important one.
{examples}

Command:"""
        
        try:
            print(f"🤔 Thinking: Converting question '{question}' to appropriate command for {platform.system()}...")
            
            response = self.bedrock.invoke_model(
                modelId="us.anthropic.claude-3-7-sonnet-20250219-v1:0",
                body=json.dumps({
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": 200,
                    "messages": [{"role": "user", "content": prompt}]
                })
            )
            
            result = json.loads(response['body'].read())
            command = result['content'][0]['text'].strip()
            
            command_lines = command.split('\n')
            command = command_lines[0].strip()
            
            print(f"💡 Selected command: {command}")
            print(f"🔥 FORCE MODE: Executing command with safety bypassed...")
            
            exec_result = self.execute_command(command, working_directory, force=True)
            
            if exec_result['success']:
                print(f"✅ Command executed successfully")
            else:
                print(f"❌ Command failed with return code {exec_result['return_code']}")
                if exec_result['stderr']:
                    print(f"Error: {exec_result['stderr']}")
            
            print(f"🧠 Interpreting results...")
            
            context = self._get_context_prompt()
            answer_prompt = f"""{context}Based on this command output, provide a clear English answer to the original question.

Original Question: {question}
Command Used: {command}
Command Output: {exec_result['stdout']}
Command Error: {exec_result['stderr']}

Provide a concise, helpful answer in plain English:"""
            
            answer_response = self.bedrock.invoke_model(
                modelId="us.anthropic.claude-3-7-sonnet-20250219-v1:0",
                body=json.dumps({
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": 300,
                    "messages": [{"role": "user", "content": answer_prompt}]
                })
            )
            
            answer_result = json.loads(answer_response['body'].read())
            answer = answer_result['content'][0]['text'].strip()
            
            print(f"📝 Generated answer: {answer[:100]}{'...' if len(answer) > 100 else ''}")
            
            self._add_to_memory('question', question, answer, exec_result['success'])
            
            return {
                "question": question,
                "command_used": command,
                "answer": answer,
                "raw_output": exec_result,
                "success": exec_result['success']
            }
            
        except Exception as e:
            error_msg = f"Sorry, I couldn't process your question: {str(e)}"
            self._add_to_memory('question', question, error_msg, False)
            return {
                "question": question,
                "command_used": "unknown",
                "answer": error_msg,
                "raw_output": None,
                "success": False
            }
    
    @tool
    def create_task_plan(self, task_description: str) -> List[str]:
        """Create a step-by-step plan for complex tasks using Bedrock Claude model.
        
        Args:
            task_description: Description of the task to be completed
            
        Returns:
            List of steps to complete the task
        """
        print(f"🔧 Tool: create_task_plan(task_description='{task_description}')")
        prompt = f"""Create a detailed step-by-step plan for this task: {task_description}

Provide only the steps as a numbered list, one step per line. Be specific and actionable."""
        
        try:
            response = self.bedrock.invoke_model(
                modelId="us.anthropic.claude-3-7-sonnet-20250219-v1:0",
                body=json.dumps({
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": 1000,
                    "messages": [{"role": "user", "content": prompt}]
                })
            )
            
            result = json.loads(response['body'].read())
            plan_text = result['content'][0]['text']
            
            # Extract steps from the response
            steps = []
            for line in plan_text.split('\n'):
                line = line.strip()
                if line and (line[0].isdigit() or line.startswith('-') or line.startswith('*')):
                    # Remove numbering and clean up
                    step = line.split('.', 1)[-1].strip() if '.' in line else line.lstrip('-*').strip()
                    if step:
                        steps.append(step)
            
            return steps if steps else ["Execute the task", "Verify completion"]
            
        except Exception as e:
            # Fallback to simple planning
            return [f"Execute: {task_description}", "Verify completion"]
    
    def execute_task(self, task: str, working_dir: str = None) -> Dict[str, Any]:
        """Execute a task, creating a plan if it's complex."""
        print(f"🔧 Method: execute_task(task='{task}', working_dir={working_dir})")
        
        # Check if task seems complex
        complex_keywords = ["and", "then", "after", "install", "build", "deploy", "setup"]
        is_complex = any(keyword in task.lower() for keyword in complex_keywords) or len(task.split()) > 10
        
        if is_complex:
            plan = self.create_task_plan(task)
            results = []
            
            for i, step in enumerate(plan, 1):
                print(f"Step {i}: {step}")
                # Execute the original task as final step
                if i == len(plan):
                    result = self.execute_command(task, working_dir)
                    results.append(result)
                else:
                    results.append({"step": step, "status": "planned"})
            
            return {"plan": plan, "results": results, "task_type": "complex"}
        else:
            result = self.execute_command(task, working_dir)
            return {"results": [result], "task_type": "simple"}