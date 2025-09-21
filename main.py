from __future__ import annotations

from pathlib import Path

import httpx
import yaml
from fastmcp import FastMCP


def load_openapi_spec(spec_path: Path) -> dict:
    """Read and parse the OpenAPI spec from a YAML file."""
    with spec_path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


SPEC_PATH = Path(__file__).parent / "swagger.yaml"

# HTTP Client endpoint
client = httpx.AsyncClient(base_url="http://localhost:1818")

# Load your OpenAPI spec from swagger.yaml
openapi_spec = load_openapi_spec(SPEC_PATH)

# Create the MCP server
mcp = FastMCP.from_openapi(
    openapi_spec=openapi_spec,
    client=client,
    name="Template API MCP",
)


if __name__ == "__main__":
    mcp.run(transport="stdio")
