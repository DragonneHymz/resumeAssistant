# Resume Assistant MCP Server

An MCP (Model Context Protocol) server that helps AI agents assist users with resume management, optimization, and generation.

## Features

- **Resume Storage**: Store resume data using the [JSON Resume](https://jsonresume.org) open standard
- **PDF Import**: Parse existing PDF resumes to extract structured data
- **ATS Optimization**: Enterprise-level scoring with multi-option selection and regeneration
- **PDF Generation**: Create professional resumes with 3 template options (Modern, Classic, Executive)

## Installation

### Using Conda (Recommended)

```bash
# Create and activate environment
conda create -n ResumeAssistant python=3.11 -y
conda activate ResumeAssistant

# Install the package
pip install -e .

# Download spaCy English model for NLP
python -m spacy download en_core_web_lg
```

### Using pip

```bash
pip install -e .
python -m spacy download en_core_web_lg
```

## Running the Server

```bash
# If using conda
conda activate ResumeAssistant

# Run the MCP server
resume-assistant
```

---

## How MCP Works: Local vs Hosted

### Local Mode (Default) - Client Runs the Server

**You do NOT need to run or host the server separately.** When you configure a client like Claude Desktop or Antigravity with a `command`, the client:

1. **Spawns the server process** automatically when needed
2. **Communicates via stdio** (standard input/output)
3. **Manages the lifecycle** (starts/stops with the client)

You just need the package installed and provide the path to the executable.

```json
{
  "mcpServers": {
    "resume-assistant": {
      "command": "/path/to/anaconda3/envs/ResumeAssistant/bin/resume-assistant"
    }
  }
}
```

### Hosted Mode (Remote) - Server Runs Separately

For shared/remote access, you run the server yourself with SSE transport, and clients connect to it:

```bash
# On the server
resume-assistant --transport sse --host 0.0.0.0 --port 8080
```

```json
{
  "mcpServers": {
    "resume-assistant": {
      "transport": "sse",
      "url": "http://your-server:8080/sse"
    }
  }
}
```

### When to Use Each

| Scenario | Mode | Configuration Type |
|----------|------|-------------------|
| Personal use on your machine | Local | `"command": "/path/to/exe"` |
| Claude Desktop / Antigravity | Local | `"command": "/path/to/exe"` |
| VS Code / GitHub Copilot | Local | `"command": "/path/to/exe"` |
| Shared team server | Hosted | `"url": "http://..."` |
| Cloud deployment | Hosted | `"url": "http://..."` |
| Multiple machines, one server | Hosted | `"url": "http://..."` |

---

## Connecting to MCP Clients (Local Mode)

> **Note**: In local mode, clients run the server for you. Just provide the command path.

### Claude Desktop

Add to `~/.config/claude/claude_desktop_config.json` (Mac/Linux) or `%APPDATA%\Claude\claude_desktop_config.json` (Windows):

```json
{
  "mcpServers": {
    "resume-assistant": {
      "command": "/path/to/anaconda3/envs/ResumeAssistant/bin/resume-assistant"
    }
  }
}
```

> **Note**: Use the full path to the executable in your conda environment. Find it with: `which resume-assistant` (after activating the environment).

---

### VS Code / GitHub Copilot

#### Option 1: Workspace Configuration

Create `.vscode/mcp.json` in your project:

```json
{
  "servers": {
    "resume-assistant": {
      "command": "/path/to/anaconda3/envs/ResumeAssistant/bin/resume-assistant"
    }
  }
}
```

#### Option 2: User Settings

Add to your VS Code `settings.json`:

```json
{
  "chat.mcp.enabled": true,
  "mcp.servers": {
    "resume-assistant": {
      "command": "/path/to/anaconda3/envs/ResumeAssistant/bin/resume-assistant"
    }
  }
}
```

#### Enable MCP Discovery

To auto-discover MCP servers from Claude Desktop:

```json
{
  "chat.mcp.enabled": true,
  "chat.mcp.discovery.enabled": true
}
```

---

### Antigravity (Google DeepMind)

Add to your Antigravity MCP configuration:

```json
{
  "mcpServers": {
    "resume-assistant": {
      "command": "/path/to/anaconda3/envs/ResumeAssistant/bin/resume-assistant"
    }
  }
}
```

---

### Cursor

Add to Cursor's MCP settings (Settings → MCP Servers):

```json
{
  "resume-assistant": {
    "command": "/path/to/anaconda3/envs/ResumeAssistant/bin/resume-assistant"
  }
}
```

---

### Cline (VS Code Extension)

Add to Cline's MCP configuration in VS Code settings:

```json
{
  "cline.mcp.servers": {
    "resume-assistant": {
      "command": "/path/to/anaconda3/envs/ResumeAssistant/bin/resume-assistant"
    }
  }
}
```

---

### Generic MCP Client

For any MCP-compatible client, the server runs via:

```bash
# Command to run
/path/to/anaconda3/envs/ResumeAssistant/bin/resume-assistant

# Or if conda env is activated
resume-assistant
```

**Transport**: stdio (standard input/output)

---

## Finding Your Executable Path

```bash
# Activate your environment first
conda activate ResumeAssistant

# Find the full path
which resume-assistant
# Example output: /Users/username/anaconda3/envs/ResumeAssistant/bin/resume-assistant
```

---

## Hosting Options

### Local (Default)

Run directly on your machine using stdio transport:

```bash
conda activate ResumeAssistant
resume-assistant
```

This is the simplest option for personal use with desktop clients.

---

### Docker

#### Dockerfile

Create `Dockerfile` in the project root:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for WeasyPrint
RUN apt-get update && apt-get install -y \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf2.0-0 \
    libffi-dev \
    shared-mime-info \
    && rm -rf /var/lib/apt/lists/*

# Copy project files
COPY pyproject.toml .
COPY src/ src/

# Install package and spaCy model
RUN pip install --no-cache-dir -e . && \
    python -m spacy download en_core_web_lg

# Create data directories
RUN mkdir -p /app/data/resumes /app/output

# Expose for SSE transport (if needed)
EXPOSE 8080

# Default: run with stdio transport
CMD ["resume-assistant"]
```

#### Build and Run

```bash
# Build the image
docker build -t resume-assistant .

# Run with stdio (for local MCP clients)
docker run -it --rm \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/output:/app/output \
  resume-assistant

# Run with SSE transport for remote access
docker run -d --rm \
  -p 8080:8080 \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/output:/app/output \
  resume-assistant \
  resume-assistant --transport sse --port 8080
```

#### Docker Compose

Create `docker-compose.yml`:

```yaml
version: '3.8'
services:
  resume-assistant:
    build: .
    ports:
      - "8080:8080"
    volumes:
      - ./data:/app/data
      - ./output:/app/output
    command: resume-assistant --transport sse --port 8080
```

```bash
docker-compose up -d
```

---

### Remote Server (SSE Transport)

For hosting on a remote server accessible by multiple clients:

```bash
# Install on server
pip install -e .
python -m spacy download en_core_web_lg

# Run with SSE transport
resume-assistant --transport sse --host 0.0.0.0 --port 8080
```

#### Connect Remote Clients

```json
{
  "mcpServers": {
    "resume-assistant": {
      "transport": "sse",
      "url": "http://your-server:8080/sse"
    }
  }
}
```

---

### Cloud Deployment

#### AWS / GCP / Azure VM

1. Provision a VM (Ubuntu 22.04 recommended)
2. Install Python 3.11+ and dependencies
3. Clone repo and install: `pip install -e .`
4. Download spaCy model: `python -m spacy download en_core_web_lg`
5. Run with systemd (see below)

#### Systemd Service

Create `/etc/systemd/system/resume-assistant.service`:

```ini
[Unit]
Description=Resume Assistant MCP Server
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/resumeAssistant
ExecStart=/home/ubuntu/.local/bin/resume-assistant --transport sse --host 0.0.0.0 --port 8080
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable resume-assistant
sudo systemctl start resume-assistant
```

#### Railway / Render / Fly.io

These platforms support Docker deployments. Use the Dockerfile above and configure:
- **Port**: 8080
- **Command**: `resume-assistant --transport sse --port 8080`
- **Health check**: `/health` (if implemented)

---

### Transport Options

| Transport | Use Case | Config |
|-----------|----------|--------|
| **stdio** | Local desktop clients | Default, no extra config |
| **sse** | Remote/shared access | `--transport sse --port 8080` |

---

## Available Tools

The server provides 22+ agent skills including:

| Category | Tools |
|----------|-------|
| Import/Storage | `import_resume_from_pdf`, `store_resume`, `get_resume`, `export_json_resume` |
| Editing | `add_work_experience`, `add_education`, `add_skill`, `add_project`, `add_certification` |
| ATS Optimization | `score_resume`, `generate_bullet_options`, `regenerate_options`, `start_interactive_optimization` |
| Generation | `generate_pdf`, `tailor_resume`, `list_templates` |

## Development

```bash
# Install with dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Lint
ruff check .
```

## License

MIT
