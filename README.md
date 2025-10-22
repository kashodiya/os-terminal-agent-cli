# OS Terminal Agent CLI

An intelligent CLI agent built with Strands library that can execute system commands, answer questions in natural language, and handle complex multi-step tasks with automatic planning.

🛡️ **Built-in Safety Guardrails**: Protects your system from dangerous commands with risk assessment and confirmation prompts.

## Installation

```bash
pip install -r requirements.txt
```

## Quick Start

```bash
# Ask a question in natural language
python cli_client.py ask "What files are in this directory?"

# Execute a direct command (with safety checks)
python cli_client.py execute "dir"

# Force execution of risky commands
python cli_client.py execute "del temp.txt" --force

# Disable all safety guardrails (USE WITH CAUTION)
python cli_client.py --unsafe execute "format c:"

# Start watch mode for continuous monitoring
python cli_client.py watch
```

## Commands

### `ask` - Natural Language Queries
Ask questions in plain English and get intelligent answers:

```bash
# System information queries
python cli_client.py ask "How much disk space is available?"
python cli_client.py ask "What processes are currently running?"
python cli_client.py ask "What's my current directory?"
python cli_client.py ask "Which file name starts with R?"

# AWS and cloud queries
python cli_client.py ask "Are we logged in to AWS?"
python cli_client.py ask "Do we have access to AWS CLI?"
python cli_client.py ask "List EC2 servers"

# Network and system configuration
python cli_client.py ask "What is the IP address of this computer?"
python cli_client.py ask "Explain the firewall config on this pc"
python cli_client.py ask "Is this machine running as a virtual machine?"

# Read question from file
python cli_client.py ask --file questions.txt
```

### `execute` - Direct Command Execution
Execute CLI commands with built-in safety checks and intelligent output summarization:

```bash
# Safe command execution with AI-powered output summary
python cli_client.py execute "dir"
python cli_client.py execute "git status" --working-dir C:\path\to\repo

# Show raw output without LLM summarization
python cli_client.py execute "systeminfo" --raw

# Force execution of commands requiring confirmation
python cli_client.py execute "del temp.txt" --force
```

### `task` - Complex Task Execution
Execute complex tasks with automatic planning:

```bash
python cli_client.py task "install nodejs and npm"
python cli_client.py task "git clone repo and build project"
python cli_client.py task "backup important files to external drive"
```

### `plan` - Task Planning
Create execution plans without running them:

```bash
python cli_client.py plan "deploy application to production"
python cli_client.py plan "set up development environment"
```

### `safety` - Safety Configuration
View or modify safety settings:

```bash
# View current safety configuration
python cli_client.py safety --show

# Reset to default safety settings
python cli_client.py safety --reset
```

### `watch` - File Monitoring Mode
Monitor `questions.txt` for changes and auto-process questions:

```bash
python cli_client.py watch
python cli_client.py watch --working-dir C:\path\to\monitor
```

**Watch Mode Usage:**
1. Add questions to `questions.txt`
2. Use `===` as delimiter between questions
3. Use `===!` as delimiter to enable **force mode** for risky commands
4. The agent processes the first question automatically when file changes
5. Questions are processed in order from top to bottom

**Force Mode in Watch Mode:**
- Use `===!` delimiter to bypass safety checks for the preceding question
- Equivalent to using `--force` flag in direct command execution
- Dangerous commands will execute without confirmation prompts
- Example:
  ```
  delete temp.txt file
  ===!
  ```

## Session Management

Maintain conversation memory across commands using sessions:

```bash
# Start a session with safety enabled (default)
python cli_client.py --session mysession ask "Are we logged in?"

# Continue the conversation
python cli_client.py --session mysession ask "What was my previous question?"
python cli_client.py --session mysession ask "Answer the first question again"

# Start unsafe session (disables all safety checks)
python cli_client.py --unsafe --session dangerzone execute "dangerous command"
```

## Global Options

- `--session, -s`: Session ID for conversation memory
- `--working-dir, -w`: Set working directory for commands
- `--file, -f`: Read input from file (for `ask` command)
- `--unsafe`: Disable safety guardrails (USE WITH EXTREME CAUTION)
- `--force`: Force execution of commands requiring confirmation
- `--raw`: Show raw command output without LLM summarization (for `execute` command)

## Features

- 🧠 **AI-Powered Intelligence**: Natural language understanding and command interpretation
- 📊 **Intelligent Output Summarization**: LLM-powered command output analysis and explanation
- 🛡️ **Safety Guardrails**: Multi-layer protection against dangerous commands
- 💾 **Session Memory**: Remembers context across multiple interactions
- 🔄 **Auto-Planning**: Breaks down complex tasks into executable steps
- 📁 **Working Directory Support**: Execute commands in specific directories
- 📝 **File Input**: Read questions from text files
- 👀 **Watch Mode**: Continuous monitoring and auto-processing
- ✅ **Error Handling**: Detailed success/failure reporting
- 🌐 **Cross-Platform**: Works on Windows, Linux, and macOS
- ☁️ **Cloud Integration**: Built-in support for AWS CLI operations
- ⚠️ **Risk Assessment**: Real-time command risk evaluation
- 🔒 **System Protection**: Blocks access to critical system directories

## Safety Features

### Risk Levels
- 🟢 **Safe**: Read-only operations (ls, dir, pwd, etc.)
- 🟡 **Low**: Standard commands with minimal risk
- 🟠 **Medium**: Commands that modify files or settings
- 🔴 **High**: Potentially destructive operations
- ⛔ **Critical**: System-destroying commands (blocked by default)

### Protected Elements
- **System Directories**: Windows, Program Files, /bin, /etc, etc.
- **Dangerous Commands**: del, rm, format, shutdown, reg, etc.
- **Destructive Flags**: -rf, /s /q, -recurse, -force
- **Critical Operations**: Disk formatting, registry editing, system shutdown

### Safety Modes
- **Safe Mode (Default)**: Full protection with confirmation prompts
- **Unsafe Mode**: All protections disabled (use `--unsafe` flag)
- **Force Mode**: Skip confirmations for individual commands (`--force`)

## Dependencies

- `strands-agents`: Core AI agent framework
- `click`: Command-line interface creation
- `boto3`: AWS SDK for Python (for cloud operations)