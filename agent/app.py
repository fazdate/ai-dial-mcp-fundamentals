import asyncio
import os

from mcp import Resource
from mcp.types import Prompt

from agent.mcp_client import MCPClient
from agent.dial_client import DialClient
from agent.models.message import Message, Role
from agent.prompts import SYSTEM_PROMPT


# https://remote.mcpservers.org/fetch/mcp
# Pay attention that `fetch` doesn't have resources and prompts

async def main():
    async with MCPClient(mcp_server_url="http://localhost:8005/mcp") as mcp_client:
        # 2. Get Available MCP Resources and print them
        resources: list[Resource] = await mcp_client.session.list_resources()
        for resource in resources:
            print(resource)
        # 3. Get Available MCP Tools, assign to `tools` variable, print tool as well
        tools = await mcp_client.get_tools()
        for tool in tools:
            print(f"Tool Name: {tool['function']['name']}, Description: {tool['function']['description']}")
        # 4. Create DialClient
        dial_client = DialClient(
            api_key=os.getenv("DIAL_API_KEY"),
            endpoint="https://ai-proxy.lab.epam.com",
            tools=tools,
            mcp_client=mcp_client
        )
        # 5. Create list with messages and add there SYSTEM_PROMPT with instructions to LLM
        messages: list[Message] = [
            Message(
                role=Role.SYSTEM,
                content=SYSTEM_PROMPT
            )
        ]
        # 6. Add to messages Prompts from MCP server as User messages
        prompts: list[Prompt] = await mcp_client.session.list_prompts()
        for prompt in prompts.prompts:
            print(prompt)
            content = await mcp_client.session.get_prompt(prompt.name)
            print(content)
            messages.append(
                Message(
                    role=Role.USER,
                    content=f"## Prompt provided by MCP server:\n{prompt.description}\n{content}"
                )
            )
        # 7. Create console chat (infinite loop + ability to exit from chat + preserve message history after the call to dial client)
        while True:
            user_input = input("You: ")
            if user_input.lower() in {"exit", "quit"}:
                print("Exiting chat.")
                break

            messages.append(
                Message(
                    role=Role.USER,
                    content=user_input
                )
            )

            ai_message: Message = await dial_client.get_completion(messages)
            print(f"AI: {ai_message.content}")

            messages.append(ai_message)


if __name__ == "__main__":
    asyncio.run(main())