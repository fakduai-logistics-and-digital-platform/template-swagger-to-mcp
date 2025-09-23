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


async def load_openapi_spec_from_url(url: str) -> dict:
    """Load and parse the OpenAPI spec from a URL."""
    async with httpx.AsyncClient() as temp_client:
        response = await temp_client.get(url)
        response.raise_for_status()
        return yaml.safe_load(response.text)


SPEC_PATH = Path(__file__).parent / "swagger.yaml"

# Configuration - set SWAGGER_URL to empty string to use local file
SWAGGER_URL = "http://localhost:1323/swagger.yaml"  # Set to "" to use local file
BASE_URL = "http://localhost:1323"

# JWT Token storage
JWT_TOKEN = ""

# Create an HTTP client for your API (the MCP server will reuse this instance)
client = httpx.AsyncClient(base_url=BASE_URL)

# Load OpenAPI spec based on configuration
if SWAGGER_URL == "":
    # Use local file
    try:
        openapi_spec = load_openapi_spec(SPEC_PATH)
        print(f"✅ Loaded OpenAPI spec from local file: {SPEC_PATH}")
    except Exception as e:
        print(f"❌ Failed to load local file: {e}")
        # Create minimal spec as fallback
        openapi_spec = {
            "openapi": "3.1.0",
            "info": {"title": "Pinto API", "version": "1.0"},
            "paths": {}
        }
else:
    # Try to load from URL first, fallback to local file
    try:
        import asyncio
        openapi_spec = asyncio.run(load_openapi_spec_from_url(SWAGGER_URL))
        print(f"✅ Loaded OpenAPI spec from URL: {SWAGGER_URL}")
    except Exception as e:
        print(f"⚠️  Failed to load from URL ({e}), falling back to local file")
        try:
            openapi_spec = load_openapi_spec(SPEC_PATH)
            print(f"✅ Loaded OpenAPI spec from local file: {SPEC_PATH}")
        except Exception as local_error:
            print(f"❌ Failed to load local file: {local_error}")
            # Create minimal spec as fallback
            openapi_spec = {
                "openapi": "3.1.0",
                "info": {"title": "Pinto API", "version": "1.0"},
                "paths": {}
            }

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
def set_base_url(base_url: str) -> Dict[str, Any]:
    """Set a new base URL for API calls."""
    global BASE_URL, client
    
    # Validate URL format
    if not base_url.startswith(('http://', 'https://')):
        return {"error": "Base URL must start with http:// or https://"}
    
    # Remove trailing slash if present
    base_url = base_url.rstrip('/')
    
    # Update global BASE_URL
    BASE_URL = base_url
    
    # Create new client with updated base URL
    client = httpx.AsyncClient(base_url=BASE_URL)
    
    return {
        "success": True,
        "message": f"Base URL updated to: {BASE_URL}",
        "base_url": BASE_URL
    }


@mcp.tool()
def set_jwt_token(token: str) -> Dict[str, Any]:
    """Set JWT token for authenticated API calls.
    
    Examples:
    - set_jwt_token("eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...")
    - set_jwt_token("") - clear token
    """
    global JWT_TOKEN
    
    JWT_TOKEN = token.strip()
    
    if JWT_TOKEN == "":
        return {
            "success": True,
            "message": "JWT token cleared",
            "has_token": False
        }
    else:
        # Basic validation - check if it looks like a JWT
        parts = JWT_TOKEN.split('.')
        if len(parts) != 3:
            return {"error": "Invalid JWT format. JWT should have 3 parts separated by dots."}
        
        return {
            "success": True,
            "message": "JWT token set successfully",
            "has_token": True,
            "token_preview": f"{JWT_TOKEN[:20]}..." if len(JWT_TOKEN) > 20 else JWT_TOKEN
        }


@mcp.tool()
def get_jwt_status() -> Dict[str, Any]:
    """Check current JWT token status."""
    if JWT_TOKEN == "":
        return {
            "has_token": False,
            "message": "No JWT token set"
        }
    else:
        return {
            "has_token": True,
            "message": "JWT token is set",
            "token_preview": f"{JWT_TOKEN[:20]}..." if len(JWT_TOKEN) > 20 else JWT_TOKEN
        }



@mcp.tool()
async def reload_openapi_spec(spec_source: str = "") -> Dict[str, Any]:
    """Reload OpenAPI spec from a URL or local file path.
    
    Examples:
    - reload_openapi_spec() - reload using current configuration (URL or local file)
    - reload_openapi_spec("https://api.pinto-app.com/swagger.yaml") - load from URL
    - reload_openapi_spec("swagger.yaml") - load from local file
    """
    global openapi_spec
    
    # If no spec_source provided, use current configuration
    if spec_source == "":
        spec_source = SWAGGER_URL if SWAGGER_URL != "" else "swagger.yaml"
    global openapi_spec
    
    try:
        if spec_source.startswith(('http://', 'https://')):
            # Load from URL
            async with httpx.AsyncClient() as temp_client:
                response = await temp_client.get(spec_source)
                response.raise_for_status()
                openapi_spec = yaml.safe_load(response.text)
        else:
            # Load from local file
            spec_path = Path(spec_source)
            if not spec_path.is_absolute():
                spec_path = Path(__file__).parent / spec_path
            
            if not spec_path.exists():
                return {"error": f"File not found: {spec_path}"}
            
            openapi_spec = load_openapi_spec(spec_path)
        
        return {
            "success": True,
            "message": f"OpenAPI spec loaded from: {spec_source}",
            "spec_info": {
                "title": openapi_spec.get("info", {}).get("title", ""),
                "version": openapi_spec.get("info", {}).get("version", ""),
                "total_paths": len(openapi_spec.get("paths", {}))
            }
        }
        
    except Exception as e:
        return {"error": f"Failed to load spec: {str(e)}"}


@mcp.tool()
def get_current_spec_info() -> Dict[str, Any]:
    """Get information about current OpenAPI spec and configuration."""
    info = openapi_spec.get("info", {})
    
    return {
        "current_base_url": BASE_URL,
        "spec_info": {
            "title": info.get("title", ""),
            "version": info.get("version", ""),
            "description": info.get("description", ""),
            "total_paths": len(openapi_spec.get("paths", {}))
        },
        "servers": openapi_spec.get("servers", [])
    }


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
        "base_url": BASE_URL,
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
    json_body: Dict[str, Any] = None,
    use_jwt: bool = True
) -> Dict[str, Any]:
    """Call an API endpoint and return the actual response.
    
    Parameters:
    - path: API endpoint path
    - method: HTTP method (GET, POST, PUT, DELETE, PATCH)
    - headers: Additional headers
    - query_params: Query parameters
    - json_body: JSON request body
    - use_jwt: Whether to include JWT token in Authorization header (default: True)
    """
    try:
        # Prepare headers
        request_headers = headers or {}
        
        # Add JWT token if available and requested
        if use_jwt and JWT_TOKEN:
            request_headers["Authorization"] = f"Bearer {JWT_TOKEN}"
        
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
            "success": response.is_success,
            "used_jwt": use_jwt and bool(JWT_TOKEN)
        }
        
    except Exception as e:
        return {
            "error": str(e),
            "path": path,
            "method": method.upper(),
            "success": False,
            "used_jwt": use_jwt and bool(JWT_TOKEN)
        }


@mcp.tool()
async def login_and_get_token(email: str, password: str) -> Dict[str, Any]:
    """Login with email/password and automatically set JWT token.
    
    This is a convenience function that calls the login API and stores the token.
    """
    try:
        # Call login endpoint
        login_response = await call_api_endpoint(
            path="/api/auth/login",
            method="POST",
            json_body={"email": email, "password": password},
            use_jwt=False  # Don't use JWT for login
        )
        
        if not login_response.get("success"):
            return {
                "success": False,
                "error": "Login failed",
                "login_response": login_response
            }
        
        # Extract token from response
        response_data = login_response.get("data", {})
        if isinstance(response_data, dict) and "data" in response_data:
            token = response_data["data"].get("token")
            if token:
                # Set the token
                token_result = set_jwt_token(token)
                return {
                    "success": True,
                    "message": "Login successful and token set",
                    "token_info": token_result,
                    "user_info": response_data["data"].get("user", {})
                }
        
        return {
            "success": False,
            "error": "Token not found in login response",
            "login_response": login_response
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Login error: {str(e)}"
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