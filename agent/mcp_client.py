from typing import Optional, Any

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client
from mcp.types import CallToolResult, TextContent, GetPromptResult, ReadResourceResult, Resource, TextResourceContents, BlobResourceContents, Prompt
from pydantic import AnyUrl


class MCPClient:
    """Handles MCP server connection and tool execution"""

    def __init__(self, mcp_server_url: str) -> None:
        self.mcp_server_url = mcp_server_url
        self.session: Optional[ClientSession] = None
        self._streams_context = None
        self._session_context = None

from typing import Optional, Any

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client
from mcp.types import CallToolResult, TextContent, GetPromptResult, ReadResourceResult, Resource, TextResourceContents, BlobResourceContents, Prompt
from pydantic import AnyUrl


class MCPClient:
    """Handles MCP server connection and tool execution"""

    def __init__(self, mcp_server_url: str) -> None:
        self.mcp_server_url = mcp_server_url
        self.session: Optional[ClientSession] = None
        self._streams_context = None
        self._session_context = None

    async def __aenter__(self):
        try:
            # 1. Call `streamablehttp_client` method with `mcp_server_url` and assign to `self._streams_context`
            self._streams_context = streamablehttp_client(self.mcp_server_url)
            # 2. Call `await self._streams_context.__aenter__()` and assign to `read_stream, write_stream, _`
            read_stream, write_stream, _ = await self._streams_context.__aenter__()
            # 3. Create `ClientSession(read_stream, write_stream)` and assign to `self._session_context`
            self._session_context = ClientSession(read_stream, write_stream)
            # 4. Call `await self._session_context.__aenter__()` and assign it to `self.session`
            self.session = await self._session_context.__aenter__()
            # 5. Call `self.session.initialize()`, and print its result (to check capabilities of MCP server later)
            init_result = await self.session.initialize()
            print(f"Connected to MCP server with capabilities: {init_result.capabilities}\n")
            # 6. return self
            return self
        except ConnectionError as e:
            raise ConnectionError(f"Failed to connect to MCP server at {self.mcp_server_url}. "
                                f"Make sure the MCP server is running. Error: {e}")
        except Exception as e:
            raise RuntimeError(f"Failed to initialize MCP client at {self.mcp_server_url}. Error: {e}")

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session and self._session_context:
            await self._session_context.__aexit__(exc_type, exc_val, exc_tb)
        if self._streams_context:
            await self._streams_context.__aexit__(exc_type, exc_val, exc_tb)

    async def get_tools(self) -> list[dict[str, Any]]:
        """Get available tools from MCP server"""
        if not self.session:
            raise RuntimeError("MCP client not connected. Call connect() first.")
        # 1. Call `await self.session.list_tools()` and assign to `tools`
        tools = await self.session.list_tools()
        # 2. Return list with dicts with tool schemas. It should be provided according to DIAL specification
        #    https://dialx.ai/dial_api#operation/sendChatCompletionRequest (request -> tools)
        return [
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.inputSchema
                }
            }
            for tool in tools.tools
        ]

    async def call_tool(self, tool_name: str, tool_args: dict[str, Any]) -> Any:
        """Call a specific tool on the MCP server"""
        if not self.session:
            raise RuntimeError("MCP client not connected. Call connect() first.")

        # 1. Call `await self.session.call_tool(tool_name, tool_args)` and assign to `tool_result: CallToolResult` variable
        tool_result: CallToolResult = await self.session.call_tool(tool_name, tool_args)
        # 2. Get `content` with index `0` from `tool_result` and assign to `content` variable
        content = tool_result.contents[0]
        # 3. print(f"    ⚙️: {content}\n")
        print(f"    ⚙️: {content}\n")
        # 4. If `isinstance(content, TextContent)` -> return content.text
        #    else -> return content
        if isinstance(content, TextContent):
            return content.text
        else:
            return content

    async def get_resources(self) -> list[Resource]:
        """Get available resources from MCP server"""
        if not self.session:
            raise RuntimeError("MCP client not connected.")

        try:
            resources = await self.session.list_resources()
            return resources
        except Exception as e:
            print(f"Error fetching resources: {e}")
            return []

    async def get_resource(self, uri: AnyUrl) -> str:
        """Get specific resource content"""
        if not self.session:
            raise RuntimeError("MCP client not connected.")

        try:
            resource_result: ReadResourceResult = await self.session.read_resource(uri)
            content = resource_result.contents[0]
            if isinstance(content, TextResourceContents):
                return content.text
            elif isinstance(content, BlobResourceContents):
                return content.blob
            else:
                raise TypeError("Unsupported resource content type.")
        except Exception as e:
            print(f"Error fetching resource: {e}")

    async def get_prompts(self) -> list[Prompt]:
        """Get available prompts from MCP server"""
        if not self.session:
            raise RuntimeError("MCP client not connected.")
        try:
            prompts = await self.session.list_prompts()
            return prompts
        except Exception as e:
            print(f"Error fetching prompts: {e}")
            return []

    async def get_prompt(self, name: str) -> str:
        """Get specific prompt content"""
        if not self.session:
            raise RuntimeError("MCP client not connected.")
        prompt_result: GetPromptResult = await self.session.get_prompt(name)
        # 2. Create variable `combined_content` with empty string
        combined_content = ""
        # 3. Iterate through prompt result `messages` and:
        #       - if `message` has attribute 'content' and is instance of TextContent then concat `combined_content`
        #          with `message.content.text + "\n"`
        #       - if `message` has attribute 'content' and is instance of `str` then concat `combined_content` with
        #          with `message.content + "\n"`
        for message in prompt_result.messages:
            if hasattr(message, 'content'):
                content = message.content
                if isinstance(content, TextContent):
                    combined_content += content.text + "\n"
                elif isinstance(content, str):
                    combined_content += content + "\n"
        # 4. Return `combined_content`
        return combined_content