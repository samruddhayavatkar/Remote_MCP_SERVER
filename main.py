from fastmcp import FastMCP
import random
import json

# Create the FastMCP server instance
# This initializes an MCP (Model Context Protocol) server with a descriptive name
# The server will expose tools that can be called by Claude or other AI assistants
mcp = FastMCP("Simple Calculator Server")

# Tool: Add two numbers
# The @mcp.tool decorator registers this function as an MCP tool
# This makes it callable by Claude through the MCP protocol
@mcp.tool
def add(a: int, b: int) -> int:
    """Add two numbers together.
    
    Args:
        a: First number
        b: Second number
    
    Returns:
        The sum of a and b
    """
    return a + b

# Tool: Generate a random number
# This tool demonstrates how to create functions with default parameters
# Claude can call this with custom min/max values or use the defaults
@mcp.tool
def random_number(min_val: int = 1, max_val: int = 100) -> int:
    """Generate a random number within a range.
    
    Args:
        min_val: Minimum value (default: 1)
        max_val: Maximum value (default: 100)
    
    Returns:
        A random integer between min_val and max_val
    """
    return random.randint(min_val, max_val)

# Resource: Server information
# The @mcp.resource decorator registers this as an MCP resource
# Resources provide static or dynamic information that Claude can access
# The URI "info://server" is how Claude will reference this resource
@mcp.resource("info://server")
def server_info() -> str:
    """Get information about this server."""
    # Define server metadata as a dictionary
    info = {
        "name": "Simple Calculator Server",
        "version": "1.0.0",
        "description": "A basic MCP server with math tools",
        "tools": ["add", "random_number"],
        "author": "Your Name"
    }
    # Return the info as a formatted JSON string
    # indent=2 makes it human-readable with proper indentation
    return json.dumps(info, indent=2)

# Start the server
# This conditional ensures the server only runs when the script is executed directly
# (not when imported as a module)
if __name__ == "__main__":
    # Run the MCP server with HTTP transport
    # host="0.0.0.0" makes it accessible from any network interface
    # port=8000 is the port number where the server will listen
    mcp.run(transport="http", host="0.0.0.0", port=8000)  #this means we are using our transport streamable http as remote server 

    #if we just write mcp.run() then it means that we are using our transport as stdio means deploying it as a local server