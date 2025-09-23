from __future__ import annotations

from pathlib import Path
from typing import List, Dict, Any

import httpx
import yaml
from fastmcp import FastMCP


def load_openapi_spec(spec_path: Path) -> dict:
    """Read and parse the OpenAPI spec from a YAML file."""
    with spec_path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


SPEC_PATH = Path(__file__).parent / "swagger.yaml"

# Create an HTTP client for your API (the MCP server will reuse this instance)
client = httpx.AsyncClient(base_url="http://localhost:1323")

# Load your OpenAPI spec from swagger.yaml
openapi_spec = load_openapi_spec(SPEC_PATH)

# Create the MCP server
mcp = FastMCP.from_openapi(
    openapi_spec=openapi_spec,
    client=client,
    name="Pinto API MCP",
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
                    "full_url": f"http://localhost:1323{path}"
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
        "full_url": f"http://localhost:1323{path}",
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
                        "full_url": f"http://localhost:1323{path}"
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
        "base_url": "http://localhost:1323",
        "servers": servers,
        "available_tags": sorted(list(all_tags)),
        "total_paths": len(openapi_spec.get("paths", {}))
    }


@mcp.tool()
async def call_api_endpoint(
    path: str, 
    method: str = "GET", 
    headers: Dict[str, str] = None, 
    query_params: Dict[str, Any] = None,
    json_body: Dict[str, Any] = None
) -> Dict[str, Any]:
    """Call an API endpoint and return the actual response."""
    try:
        # Prepare headers
        request_headers = headers or {}
        
        # Prepare the request
        request_kwargs = {
            "method": method.upper(),
            "url": path,
            "headers": request_headers,
        }
        
        # Add query parameters if provided
        if query_params:
            request_kwargs["params"] = query_params
            
        # Add JSON body if provided
        if json_body:
            request_kwargs["json"] = json_body
            
        # Make the API call
        response = await client.request(**request_kwargs)
        
        # Try to parse JSON response
        try:
            response_data = response.json()
        except:
            response_data = response.text
            
        return {
            "status_code": response.status_code,
            "headers": dict(response.headers),
            "data": response_data,
            "url": str(response.url),
            "method": method.upper(),
            "success": response.is_success
        }
        
    except Exception as e:
        return {
            "error": str(e),
            "path": path,
            "method": method.upper(),
            "success": False
        }


@mcp.tool()
def get_response_examples(path: str, method: str = "GET") -> Dict[str, Any]:
    """Get example responses for a specific API endpoint from the swagger spec."""
    if path not in openapi_spec.get("paths", {}):
        return {"error": f"Path '{path}' not found in API spec"}
    
    path_spec = openapi_spec["paths"][path]
    method_lower = method.lower()
    
    if method_lower not in path_spec:
        return {"error": f"Method '{method}' not found for path '{path}'"}
    
    method_spec = path_spec[method_lower]
    responses = method_spec.get("responses", {})
    
    examples = {}
    for status_code, response_spec in responses.items():
        content = response_spec.get("content", {})
        for content_type, content_spec in content.items():
            if "examples" in content_spec:
                examples[f"{status_code}_{content_type}"] = content_spec["examples"]
            elif "example" in content_spec:
                examples[f"{status_code}_{content_type}"] = content_spec["example"]
    
    return {
        "path": path,
        "method": method.upper(),
        "examples": examples,
        "response_codes": list(responses.keys())
    }


@mcp.tool()
def get_response_structure(path: str, method: str = "GET") -> Dict[str, Any]:
    """Get detailed response structure including schema, examples, and descriptions for a specific API endpoint."""
    if path not in openapi_spec.get("paths", {}):
        return {"error": f"Path '{path}' not found in API spec"}
    
    path_spec = openapi_spec["paths"][path]
    method_lower = method.lower()
    
    if method_lower not in path_spec:
        return {"error": f"Method '{method}' not found for path '{path}'"}
    
    method_spec = path_spec[method_lower]
    responses = method_spec.get("responses", {})
    
    response_details = {}
    
    for status_code, response_spec in responses.items():
        response_info = {
            "status_code": status_code,
            "description": response_spec.get("description", ""),
            "content": {}
        }
        
        content = response_spec.get("content", {})
        for content_type, content_spec in content.items():
            content_info = {
                "content_type": content_type,
                "schema": content_spec.get("schema", {}),
                "examples": {},
                "example": content_spec.get("example")
            }
            
            # Get examples
            if "examples" in content_spec:
                content_info["examples"] = content_spec["examples"]
            
            response_info["content"][content_type] = content_info
        
        response_details[status_code] = response_info
    
    return {
        "path": path,
        "method": method.upper(),
        "summary": method_spec.get("summary", ""),
        "description": method_spec.get("description", ""),
        "parameters": method_spec.get("parameters", []),
        "security": method_spec.get("security", []),
        "responses": response_details
    }


if __name__ == "__main__":
    mcp.run(transport="stdio")