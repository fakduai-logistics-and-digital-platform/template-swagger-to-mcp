[![MseeP.ai Security Assessment Badge](https://mseep.net/pr/watchakorn-18k-template-swagger-to-mcp-badge.png)](https://mseep.ai/app/watchakorn-18k-template-swagger-to-mcp)

# Swagger-to-MCP Template

Turn any existing OpenAPI/Swagger specification into a Model Context Protocol (MCP) server powered by [FastMCP](https://github.com/modelcontextprotocol/fastmcp). This repository is a minimal starting point for exposing an HTTP API to MCP-compatible clients such as Claude Code and Codex.

## What you get
- `main.py` that loads `swagger.yaml`, builds a reusable `httpx.AsyncClient`, and serves it through FastMCP.
- Dependency management via `pyproject.toml` (with `uv.lock` for reproducible installs).
- A place to drop your own OpenAPI 3.x / Swagger 2.0 spec (`swagger.yaml`).

## Local setup after cloning
1. **Clone & enter the project**
   ```bash
   git clone <repo-url>
   cd template-swagger-to-mcp
   ```
2. **Place your OpenAPI document** – copy or generate the file as `swagger.yaml` alongside `main.py`.
3. **Install dependencies**
   ```bash
   # Using uv (recommended)
   uv sync

   # or using pip
   python -m venv .venv
   source .venv/bin/activate
   pip install -e .
   ```
4. **Check the HTTP client configuration** – update `client = httpx.AsyncClient(base_url=...)` in `main.py` if your API lives somewhere other than `http://localhost:1323`, or add your own environment-variable handling.

## Running the MCP server locally
```bash
uv run python main.py
```
FastMCP serves over STDIO. Any MCP-aware client that invokes this command will proxy every operation defined in your OpenAPI document.

## Working straight from GitHub
MCP clients still need the code on your machine, but you can automate pulling the latest version from GitHub before launch.

```bash
# Run once to place the repo where your MCP clients expect it
mkdir -p ~/mcp-servers
cd ~/mcp-servers
if [ -d template-swagger-to-mcp ]; then
  cd template-swagger-to-mcp
  git pull
else
  git clone https://github.com/watchakorn-18k/template-swagger-to-mcp template-swagger-to-mcp
  cd template-swagger-to-mcp
fi
uv sync
```

You can reuse the same folder for both Claude Code and Codex configurations (see below). Whenever you want the newest version, run the `git pull` snippet above. If you create your own fork, replace `<owner>/<repo>` with the GitHub namespace for that fork.

## Connecting to Claude Code (Claude Desktop)
Claude Code reads MCP definitions from a JSON config file. After you have the project available locally (cloned or auto-pulled as shown above):

1. Locate the config file:
   - macOS: `~/Library/Application Support/Anthropic/claude_code_config.json`
   - Windows: `%APPDATA%/Anthropic/claude_code_config.json`
   - Linux: `~/.config/Anthropic/claude_code_config.json`
2. Add an entry under `"mcpServers"` that launches the script from your local path:
   ```json
   {
     "mcpServers": {
       "tempate-api": {
         "command": "uv",
         "args": [
           "run",
           "python",
           "main.py"
         ],
         "cwd": "/Users/<you>/mcp-servers/template-swagger-to-mcp",
         "env": {
           "PYTHONPATH": "."
         }
       }
     }
   }
   ```
   - Swap in the real absolute path you cloned to. If you prefer to activate a virtual environment before running, point the command to a wrapper script that does so.
3. Restart Claude Code. The new MCP server appears in the tools list; enable it and start issuing API calls from chats or the command palette.
  
Claude MCP CLI:
```bash
claude mcp add pinto-api-mcp -- uv --directory /Users/<ชื่อผู้ใช้>/pinto-api-mcp run main.py
```

> Tip: For authenticated APIs, add secrets via Claude Code's UI (Settings → Tools) or inject environment variables in the `env` block.

## Connecting to Codex CLI
Codex also supports MCP servers. Configure it by editing `~/.config/codex/config.json` (create it if necessary) and adding a matching entry:

```json
{
  "mcpServers": {
    "tempate-api": {
      "command": "uv",
      "args": [
        "run",
        "python",
        "main.py"
      ],
      "cwd": "/Users/<you>/mcp-servers/template-swagger-to-mcp"
    }
  }
}
```

Then start a Codex session:
```bash
codex chat --with tempate-api
```
Codex spawns the MCP server using the configured command and exposes each OpenAPI operation as a callable tool. If you want Codex to keep the repository fresh automatically, wrap the `command` in a shell script that performs `git pull` before launching `uv run python main.py`.

## Maintaining your bridge
- Update `swagger.yaml` whenever backend endpoints change; FastMCP regenerates tool definitions on the next launch.
- Introduce auth helpers, interceptors, or custom tools by expanding `main.py` before instantiating `FastMCP`.
- Keep dependencies locked with `uv lock --update` (or manage with standard `pip` workflows).

## Troubleshooting
- **Spec fails to load**: validate it with `npx @redocly/cli lint swagger.yaml` or another OpenAPI validator.
- **Connection errors**: ensure `base_url` points to a reachable server and that any required auth headers are configured.
- **MCP client cannot find the server**: double-check config file paths, `cwd` values, and restart the client after edits.

Happy building!
