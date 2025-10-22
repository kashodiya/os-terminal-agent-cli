#!/usr/bin/env python3
import click
import json
import time
import os
from cli_agent import CLIAgent

@click.group()
@click.option('--session', '-s', help='Session ID for conversation memory')
@click.pass_context
def cli(ctx, session):
    """CLI client for the Strands CLI Agent that can answer questions in English."""
    ctx.ensure_object(dict)
    ctx.obj['session'] = session

@cli.command()
@click.argument('command')
@click.option('--working-dir', '-w', help='Working directory for the command')
@click.pass_context
def execute(ctx, command, working_dir):
    """Execute a single CLI command."""
    agent = CLIAgent(ctx.obj['session'])
    result = agent.execute_command(command, working_dir)
    
    if result['success']:
        click.echo(f"✅ Command executed successfully")
        if result['stdout']:
            click.echo(f"Output:\n{result['stdout']}")
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
    agent = CLIAgent(ctx.obj['session'])
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
            if res['stdout']:
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
    
    agent = CLIAgent(ctx.obj['session'])
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
    agent = CLIAgent(ctx.obj['session'])
    steps = agent.create_task_plan(task_description)
    
    click.echo("📋 Task Plan:")
    for i, step in enumerate(steps, 1):
        click.echo(f"  {i}. {step}")

@cli.command()
@click.option('--working-dir', '-w', help='Working directory for commands')
@click.pass_context
def watch(ctx, working_dir):
    """Watch questions.txt file for changes and process questions automatically."""
    filename = "questions.txt"
    agent = CLIAgent(ctx.obj['session'])
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
                        
                        # Extract question until "===" delimiter
                        lines = content.split('\n')
                        question_lines = []
                        for line in lines:
                            if line.strip().startswith('==='):
                                break
                            question_lines.append(line)
                        
                        question = '\n'.join(question_lines).strip()
                        
                        if question:
                            click.echo(f"\n📝 New question detected: {question[:50]}...")
                            result = agent.answer_question(question, working_dir)
                            
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