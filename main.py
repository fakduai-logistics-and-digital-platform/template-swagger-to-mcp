from __future__ import annotations

from pathlib import Path
from typing import List, Dict, Any

import httpx
import yaml
from fastmcp import FastMCP

BASE_URL = "http://localhost:1323"


def load_openapi_spec(spec_path: Path) -> dict:
    """Read and parse the OpenAPI spec from a YAML file."""
    with spec_path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


SPEC_PATH = Path(__file__).parent / "swagger.yaml"

# Create an HTTP client for your API (the MCP server will reuse this instance)
client = httpx.AsyncClient(base_url=BASE_URL)

# Load your OpenAPI spec from swagger.yaml
openapi_spec = load_openapi_spec(SPEC_PATH)

# Create the MCP server
mcp = FastMCP.from_openapi(
    openapi_spec=openapi_spec,
    client=client,
    name="Template API MCP",
)


@mcp.tool()
def list_api_paths() -> List[Dict[str, Any]]:
    """List all available API paths with their methods and descriptions."""
    paths_info = []
    
    for path, methods in openapi_spec.get("paths", {}).items():
        for method, details in methods.items():
            if method.upper() in ["GET", "POST", "PUT", "DELETE", "PATCH"]:
                path_info = {
                    "path": path,
                    "method": method.upper(),
                    "summary": details.get("summary", ""),
                    "description": details.get("description", ""),
                    "tags": details.get("tags", []),
                    "full_url": f"{BASE_URL}{path}"
                }
                paths_info.append(path_info)
    
    return paths_info


@mcp.tool()
def get_api_path_details(path: str) -> Dict[str, Any]:
    """Get detailed information about a specific API path including parameters and responses."""
    if path not in openapi_spec.get("paths", {}):
        return {"error": f"Path '{path}' not found in API spec"}
    
    path_details = openapi_spec["paths"][path]
    result = {
        "path": path,
        "full_url": f"{BASE_URL}{path}",
        "methods": {}
    }
    
    for method, details in path_details.items():
        if method.upper() in ["GET", "POST", "PUT", "DELETE", "PATCH"]:
            result["methods"][method.upper()] = {
                "summary": details.get("summary", ""),
                "description": details.get("description", ""),
                "tags": details.get("tags", []),
                "parameters": details.get("parameters", []),
                "requestBody": details.get("requestBody", {}),
                "responses": list(details.get("responses", {}).keys())
            }
    
    return result


if __name__ == "__main__":
    mcp.run(transport="stdio")

@mcp.tool()
def search_api_paths(query: str) -> List[Dict[str, Any]]:
    """Search API paths by keyword in path, summary, or tags."""
    matching_paths = []
    query_lower = query.lower()
    
    for path, methods in openapi_spec.get("paths", {}).items():
        for method, details in methods.items():
            if method.upper() in ["GET", "POST", "PUT", "DELETE", "PATCH"]:
                # Search in path, summary, description, and tags
                search_text = " ".join([
                    path,
                    details.get("summary", ""),
                    details.get("description", ""),
                    " ".join(details.get("tags", []))
                ]).lower()
                
                if query_lower in search_text:
                    path_info = {
                        "path": path,
                        "method": method.upper(),
                        "summary": details.get("summary", ""),
                        "tags": details.get("tags", []),
                        "full_url": f"{BASE_URL}{path}"
                    }
                    matching_paths.append(path_info)
    
    return matching_paths


@mcp.tool()
def get_api_base_info() -> Dict[str, Any]:
    """Get basic information about the API including base URL and available tags."""
    info = openapi_spec.get("info", {})
    servers = openapi_spec.get("servers", [])
    
    # Collect all unique tags
    all_tags = set()
    for path, methods in openapi_spec.get("paths", {}).items():
        for method, details in methods.items():
            if method.upper() in ["GET", "POST", "PUT", "DELETE", "PATCH"]:
                all_tags.update(details.get("tags", []))
    
    return {
        "title": info.get("title", ""),
        "version": info.get("version", ""),
        "description": info.get("description", ""),
        "base_url": "{BASE_URL}",
        "servers": servers,
        "available_tags": sorted(list(all_tags)),
        "total_paths": len(openapi_spec.get("paths", {}))
    }