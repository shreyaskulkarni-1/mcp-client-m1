import pdb
from mcp import ClientSession, StdioServerParameters, types
from mcp.client.stdio import stdio_client
import asyncio
import traceback
import json

import os
from dotenv import load_dotenv

from openai import OpenAI

load_dotenv('.env')
MODEL_NAME = os.getenv("MODEL_NAME", "llama3.2:3b")

# Load mcp server details from server.json file instead of hardcoding
server_params = None
try:
    with open('server.json', 'r') as f:
        server_config = json.load(f)
except FileNotFoundError:
    print("server.json not found, using default server parameters")
    server_config = {
      "servers": {
        "delphix-dct": {
          "command": "uvx",
          "args": ["--from", "git+https://github.com/delphix/dxi-mcp-server.git", "dct-mcp-server"],
          "env": {
            "DCT_API_KEY": "1.2Kyd90uq7RuxiA4PUT6l5rSdNvpygXQZNcXqV4Wmm8NOR5Jdcb6M9gjcJPwQCzld",
            "DCT_BASE_URL": "https://skdct.dlpxdc.co",
            "DCT_VERIFY_SSL": "false",
            "DCT_LOG_LEVEL": "INFO"
          }
        }
      }
    }

if server_config:
    print("Loaded server configuration from server.json:")
    print(json.dumps(server_config, indent=2))

server_params = StdioServerParameters(
    command=server_config['servers']['delphix-dct']['command'],
    args=server_config['servers']['delphix-dct']['args'],  # Optional command line arguments
    env=server_config['servers']['delphix-dct']['env'],
)

async def run(query, session, conversation_history=None):
    """
    Process a query with the MCP session and maintain conversation history.

    Args:
        query: The user's query
        session: The MCP session
        conversation_history: List of previous messages in the conversation

    Returns:
        The assistant's response
    """
    if conversation_history is None:
        conversation_history = []

    try:
        tools_result = await session.list_tools()
        openai_tools = [
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.inputSchema,
                },
            }
            for tool in tools_result.tools
        ]
        print("Available tools from MCP server:", json.dumps(openai_tools, indent=2))

        # Build messages array with conversation history
        messages = conversation_history.copy()  # Start with existing history
        messages.append({"role": "user", "content": query})  # Add new user query

        if MODEL_NAME == "llama3.2:3b":
            # For Ollama, we need to construct a special prompt
            explain_str = "You're a tool selector. Given the user's query and the list of available tools, your job is to determine which tool should be called to best answer the user's question. Consider the capabilities of each tool and how they can be used to gather information or perform actions that will help you respond to the user's query effectively."

            # Include conversation context for Ollama
            if len(conversation_history) > 0:
                explain_str += "\n\nPrevious conversation context:\n"
                for msg in conversation_history[-6:]:  # Include last 3 exchanges (6 messages)
                    explain_str += f"{msg['role']}: {msg['content']}\n"

            explain_str += "\nHere is the current user's query: "
            explain_str += query+"\n"
            explain_str += """
                        Go through the function description and arguments to return the optimal tool choice in the following JSON format:
                        {
                            "tool_name": "name-of-tool-to-call",
                            "arguments": {
                                "arg_name_1": "value1",
                                "arg_name_2": "value2"
                            }
                        }
                        """
            explain_str += "Here are the available tools:\n"
            explain_str += json.dumps(openai_tools)
            explain_str += "\n"

            messages = [
                {"role": "user", "content": explain_str}
            ]
            print("Message::", messages[0]['content'])
            client = OpenAI(
                    base_url="http://localhost:11434/v1",  # Change to your local LLM server URL
                    api_key="ollama",  # API key is not used for local models, but OpenAI client requires it
            )
        else:
            client = OpenAI()

        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=messages,
            tools=openai_tools,
            tool_choice="auto",
        )

        messages.append(response.choices[0].message)

        # Handle any tool calls
        if response.choices[0].message.tool_calls and MODEL_NAME != "llama3.2:3b":
            for tool_execution in response.choices[0].message.tool_calls:
                # Execute tool call
                print("Arguments for tool call:", tool_execution.function.arguments)
                result = await session.call_tool(
                    tool_execution.function.name,
                    arguments=json.loads(tool_execution.function.arguments),
                )

                # Add tool response to conversation
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_execution.id,
                        "content": result.content[0].text,
                    }
                )

            # Send tool results back to LLM for markdown formatting
            print("Formatting response with LLM...")
            format_response = client.chat.completions.create(
                model=MODEL_NAME,
                messages=messages + [
                    {
                        "role": "user",
                        "content": "Format the above tool results as clear, well-structured markdown. Include headers, bullet points, tables, and code blocks where appropriate. Make it easy to read."
                    }
                ],
            )
            final_response = format_response.choices[0].message.content
        else:
            final_response = response.choices[0].message.content

        # Update conversation history with the new exchange
        conversation_history.append({"role": "user", "content": query})
        conversation_history.append({"role": "assistant", "content": final_response})

        # Limit conversation history to last 20 messages (10 exchanges) to avoid token limits
        if len(conversation_history) > 20:
            conversation_history[:] = conversation_history[-20:]

        return final_response

    except Exception as e:
        print("An error occurred:")
        traceback.print_exc()

if __name__ == "__main__":
    from aiohttp import web

    # Global session storage
    mcp_session = None
    # Global conversation history (stores conversations by session_id)
    conversation_histories = {}

    async def handle_query(request):
        """Handle incoming HTTP POST requests with queries"""
        try:
            data = await request.json()
            query = data.get('query') or data.get('message')
            session_id = data.get('session_id', 'default')  # Support multiple conversation sessions
            clear_history = data.get('clear_history', False)

            if not query:
                return web.json_response(
                    {'error': 'No query provided. Send {"query": "your question"}'},
                    status=400
                )

            # Clear history if requested
            if clear_history:
                conversation_histories[session_id] = []
                return web.json_response({'response': 'Conversation history cleared', 'session_id': session_id})

            # Initialize conversation history for this session if not exists
            if session_id not in conversation_histories:
                conversation_histories[session_id] = []

            print(f"\n Received query (session: {session_id}): {query}")
            print(f" History length: {len(conversation_histories[session_id])} messages")

            # Process the query using the MCP session with conversation history
            result = await run(query, mcp_session, conversation_histories[session_id])

            print(f" Response: {result}\n")

            return web.json_response({'response': result, 'session_id': session_id})

        except json.JSONDecodeError:
            return web.json_response({'error': 'Invalid JSON'}, status=400)
        except Exception as e:
            print(f" Error processing request: {e}")
            traceback.print_exc()
            return web.json_response({'error': str(e)}, status=500)

    async def handle_health(request):
        """Health check endpoint"""
        return web.json_response({'status': 'ok', 'session_active': mcp_session is not None})

    async def init_app():
        """Initialize the web application and MCP session"""
        global mcp_session

        print(" Starting MCP Query Server...")
        print("=" * 50)

        # Initialize MCP session
        print(" Connecting to MCP server...")
        stdio_context = stdio_client(server_params)
        read, write = await stdio_context.__aenter__()

        session_context = ClientSession(read, write)
        mcp_session = await session_context.__aenter__()
        await mcp_session.initialize()

        print(" MCP session initialized")
        print("=" * 50)

        # Create web app
        app = web.Application()
        app.router.add_post('/query', handle_query)
        app.router.add_get('/health', handle_health)

        # Store contexts for cleanup
        app['stdio_context'] = stdio_context
        app['session_context'] = session_context

        return app

    async def cleanup(app):
        """Cleanup MCP session on shutdown"""
        print("\n Shutting down...")
        try:
            await app['session_context'].__aexit__(None, None, None)
            await app['stdio_context'].__aexit__(None, None, None)
            print(" MCP session closed")
        except Exception as e:
            print(f"  Error during cleanup: {e}")

    async def start_server():
        """Start the HTTP server"""
        app = await init_app()
        app.on_cleanup.append(cleanup)

        runner = web.AppRunner(app)
        await runner.setup()

        site = web.TCPSite(runner, '0.0.0.0', 8000)
        await site.start()

        print("\n Server running on http://localhost:8000")
        print(" Endpoints:")
        print("   POST /query - Send queries (JSON: {\"query\": \"your question\"})")
        print("   GET  /health - Health check")
        print("\n Example:")
        print('   curl -X POST http://localhost:8080/query \\')
        print('        -H "Content-Type: application/json" \\')
        print('        -d \'{"query": "list all vdbs"}\'')
        print("\n  Press Ctrl+C to stop")
        print("=" * 50 + "\n")

        # Keep the server running
        try:
            await asyncio.Event().wait()
        except KeyboardInterrupt:
            print("\n\n  Received shutdown signal")

    asyncio.run(start_server())
