# Strands CLI Agent

A CLI agent built with Strands library that can execute any CLI command and handle complex multi-step tasks.

## Installation

```bash
pip install -r requirements.txt
```

## Usage

### Session Management
Use `--session` or `-s` to maintain conversation memory across commands:
```bash
python cli_client.py --session mysession ask "Are we logged in?"
python cli_client.py --session mysession ask "What was my previous question?"
```

### Execute Single Command
```bash
python cli_client.py execute "ls -la"
python cli_client.py execute "git status" --working-dir /path/to/repo
```

### Ask Questions in Natural English
```bash
python cli_client.py ask "What files are in this directory?"
python cli_client.py ask "How much disk space is available?"
python cli_client.py ask "What processes are currently running?"
python cli_client.py ask "What's my current directory?" --working-dir /path/to/check

# Read question from file
python cli_client.py ask --file question.txt
python cli_client.py ask --file question.txt --working-dir /path/to/check
```

### Execute Task (with automatic planning for complex tasks)
```bash
python cli_client.py task "install nodejs and npm"
python cli_client.py task "git clone repo and build project"
```

### Create Task Plan
```bash
python cli_client.py plan "deploy application to production"
```

### Watch Mode
```bash
python cli_client.py watch
python cli_client.py watch --working-dir /path/to/monitor
```

Watch mode monitors `questions.txt` file for changes. When the file is modified, it reads the question from the top until it encounters a line starting with `===` and processes it automatically.

## Features

- **Conversation Memory**: Remembers previous interactions within each session
- **Natural Language Queries**: Ask questions in plain English and get answers
- Execute any CLI command
- Automatic task complexity detection
- Multi-step task planning and execution
- Working directory support
- Detailed output and error handling
- AI-powered command interpretation and response formatting
- Session-based context for better follow-up questions