#!/usr/bin/env python3
import click
import json
import time
import os
from cli_agent import CLIAgent

@click.group()
@click.option('--session', '-s', help='Session ID for conversation memory')
@click.option('--unsafe', is_flag=True, help='Disable safety guardrails (USE WITH CAUTION)')
@click.pass_context
def cli(ctx, session, unsafe):
    """CLI client for the Strands CLI Agent that can answer questions in English."""
    ctx.ensure_object(dict)
    ctx.obj['session'] = session
    ctx.obj['safe_mode'] = not unsafe
    
    if unsafe:
        click.echo("⚠️  WARNING: Safety guardrails disabled. Dangerous commands will not be blocked!")
        click.echo("⚠️  Use this mode only if you understand the risks.")
        click.echo()

@cli.command()
@click.argument('command')
@click.option('--working-dir', '-w', help='Working directory for the command')
@click.option('--force', is_flag=True, help='Force execution (skip safety confirmation)')
@click.option('--raw', is_flag=True, help='Show raw output without LLM summarization')
@click.pass_context
def execute(ctx, command, working_dir, force, raw):
    """Execute a single CLI command."""
    agent = CLIAgent(ctx.obj['session'], safe_mode=ctx.obj['safe_mode'])
    result = agent.execute_command(command, working_dir, force=force)
    
    if result['success']:
        click.echo(f"✅ Command executed successfully")
        if result['stdout'] or result['stderr']:
            if raw:
                # Show raw output
                if result['stdout']:
                    click.echo(f"Output:\n{result['stdout']}")
                if result['stderr']:
                    click.echo(f"Error:\n{result['stderr']}")
            else:
                # Get LLM summary
                summary = agent.summarize_command_output(command, result)
                click.echo("\n" + "="*50)
                click.echo(f"💬 Summary: {summary}")
                click.echo("\n💡 Use --raw flag to see the original command output")
    elif result.get('blocked'):
        click.echo(f"🛡️ Command blocked for safety: {result['stderr']}")
        click.echo(f"Risk level: {result.get('risk_level', 'unknown').upper()}")
        click.echo("Use --force to override (if you understand the risks)")
    elif result.get('requires_confirmation'):
        click.echo(f"❓ Command requires confirmation: {result['stderr']}")
        click.echo(f"Risk level: {result.get('risk_level', 'unknown').upper()}")
        click.echo("Use --force to execute anyway")
    else:
        click.echo(f"❌ Command failed with return code {result['return_code']}")
        if result['stderr']:
            click.echo(f"Error:\n{result['stderr']}")

@cli.command()
@click.argument('task')
@click.option('--working-dir', '-w', help='Working directory for the task')
@click.pass_context
def task(ctx, task, working_dir):
    """Execute a task (simple or complex with automatic planning)."""
    agent = CLIAgent(ctx.obj['session'], safe_mode=ctx.obj['safe_mode'])
    result = agent.execute_task(task, working_dir)
    
    click.echo(f"Task Type: {result['task_type']}")
    
    if result['task_type'] == 'complex':
        click.echo("📋 Execution Plan:")
        for i, step in enumerate(result['plan'], 1):
            click.echo(f"  {i}. {step}")
        click.echo()
    
    click.echo("📊 Results:")
    for i, res in enumerate(result['results'], 1):
        if 'command' in res:
            status = "✅" if res['success'] else "❌"
            click.echo(f"  {status} {res['command']}")
            if not res['success'] and res['stderr']:
                click.echo(f"    Error: {res['stderr'][:100]}...")
            elif res['stdout']:
                click.echo(f"    Output: {res['stdout'][:100]}...")
        else:
            click.echo(f"  📝 {res.get('step', f'Step {i}')}: {res.get('status', 'completed')}")

@cli.command()
@click.argument('question', required=False)
@click.option('--working-dir', '-w', help='Working directory for the command')
@click.option('--file', '-f', help='Read question from file')
@click.pass_context
def ask(ctx, question, working_dir, file):
    """Ask a question in natural English and get an answer."""
    if file:
        try:
            with open(file, 'r', encoding='utf-8') as f:
                question = f.read().strip()
        except Exception as e:
            click.echo(f"❌ Error reading file {file}: {e}")
            return
    
    if not question:
        click.echo("❌ Please provide a question either as argument or via --file option")
        return
    
    agent = CLIAgent(ctx.obj['session'], safe_mode=ctx.obj['safe_mode'])
    result = agent.answer_question(question, working_dir)
    
    if result['success']:
        click.echo(f"❓ Question: {result['question']}")
        click.echo(f"🔧 Command used: {result['command_used']}")
        click.echo()
        click.echo("="*50)
        click.echo(f"💬 Answer: {result['answer']}")
    else:
        click.echo(f"❌ {result['answer']}")

@cli.command()
@click.argument('task_description')
@click.pass_context
def plan(ctx, task_description):
    """Create a plan for a complex task without executing it."""
    agent = CLIAgent(ctx.obj['session'], safe_mode=ctx.obj['safe_mode'])
    steps = agent.create_task_plan(task_description)
    
    click.echo("📋 Task Plan:")
    for i, step in enumerate(steps, 1):
        click.echo(f"  {i}. {step}")

@cli.command()
@click.option('--show', is_flag=True, help='Show current safety configuration')
@click.option('--reset', is_flag=True, help='Reset to default safety configuration')
@click.pass_context
def safety(ctx, show, reset):
    """View or modify safety configuration."""
    config_file = 'safety_config.json'
    
    if reset:
        # Create default config
        default_config = {
            "safety_settings": {"default_mode": "safe"},
            "protected_paths": {"windows": ["C:\\Windows"], "unix": ["/bin"]},
            "dangerous_commands": {"critical": ["format c:"], "high_risk": ["del"], "medium_risk": ["reg"]},
            "safe_commands": ["dir", "ls", "pwd"],
            "destructive_flags": ["-rf", "/s /q"],
            "protected_extensions": [".exe", ".dll"]
        }
        with open(config_file, 'w') as f:
            json.dump(default_config, f, indent=2)
        click.echo("✅ Safety configuration reset to defaults")
        return
    
    if show or True:  # Default to show
        try:
            with open(config_file, 'r') as f:
                config = json.load(f)
            click.echo("🛡️ Current Safety Configuration:")
            click.echo(json.dumps(config, indent=2))
        except FileNotFoundError:
            click.echo("❌ Safety configuration file not found")
        except json.JSONDecodeError:
            click.echo("❌ Invalid safety configuration file")

@cli.command()
@click.option('--working-dir', '-w', help='Working directory for commands')
@click.pass_context
def watch(ctx, working_dir):
    """Watch questions.txt file for changes and process questions automatically."""
    filename = "questions.txt"
    agent = CLIAgent(ctx.obj['session'], safe_mode=ctx.obj['safe_mode'])
    last_modified = os.path.getmtime(filename) if os.path.exists(filename) else 0
    
    click.echo(f"👀 Watching {filename} for changes... (Press Ctrl+C to stop)")
    
    try:
        while True:
            if os.path.exists(filename):
                current_modified = os.path.getmtime(filename)
                if current_modified > last_modified:
                    last_modified = current_modified
                    
                    try:
                        with open(filename, 'r', encoding='utf-8') as f:
                            content = f.read()
                        
                        # Extract question and check for force mode delimiter
                        lines = content.split('\n')
                        question_lines = []
                        force_mode = False
                        
                        for line in lines:
                            if line.strip().startswith('===!'):
                                force_mode = True
                                break
                            elif line.strip().startswith('==='):
                                break
                            question_lines.append(line)
                        
                        question = '\n'.join(question_lines).strip()
                        
                        if question:
                            force_indicator = " 🔥 FORCE MODE" if force_mode else ""
                            click.echo(f"\n📝 New question detected{force_indicator}: {question[:50]}...")
                            result = agent.answer_question_with_force(question, working_dir) if force_mode else agent.answer_question(question, working_dir)
                            
                            if result['success']:
                                click.echo(f"❓ Question: {result['question']}")
                                click.echo(f"🔧 Command used: {result['command_used']}")
                                click.echo()
                                click.echo("="*50)
                                click.echo(f"💬 Answer: {result['answer']}")
                            else:
                                click.echo(f"❌ {result['answer']}")
                            click.echo("\n" + "="*50)
                        
                    except Exception as e:
                        click.echo(f"❌ Error reading {filename}: {e}")
            
            time.sleep(1)
            
    except KeyboardInterrupt:
        click.echo("\n👋 Stopped watching.")

if __name__ == '__main__':
    cli()