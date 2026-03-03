"""
Gradio interface for MCP Chat
"""
import asyncio
import pdb

import gradio as gr
import requests
import json
from typing import List, Dict


class GradioChatInterface:
    """Gradio chat interface for MCP client"""

    def __init__(self, api_url: str = "http://localhost:8000"):
        self.api_url = api_url
        self.chat_history = []
        self.session_id = "default"  # Each user gets a session ID

    def send_message(self, message: str, history: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """
        Send message to backend and get response

        Args:
            message: User message
            history: Chat history from Gradio (list of message dicts)

        Returns:
            Updated chat history
        """
        try:
            # Add user message to history
            history.append({"role": "user", "content": message})

            # Send to backend with session_id
            response = requests.post(
                f"{self.api_url}/query",
                json={
                    "query": message,
                    "session_id": self.session_id
                },
                timeout=300  # 5 minute timeout for long-running operations
            )

            if response.status_code == 200:
                data = response.json()
                bot_response = data.get('response', 'No response from server')
            else:
                bot_response = f"Error: {response.status_code} - {response.text}"

            # Add bot response to history
            history.append({"role": "assistant", "content": bot_response})

        except requests.exceptions.ConnectionError as ex:
            history.append({"role": "assistant", "content": "Error: Cannot connect to server. Make sure the backend is running on http://localhost:8000"})
        except requests.exceptions.Timeout:
            history.append({"role": "assistant", "content": "Error: Request timed out. The operation took too long."})
        except Exception as e:
            history.append({"role": "assistant", "content": f"Error: {str(e)}"})

        return history

    def clear_history(self, history: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """Clear conversation history on both client and server"""
        try:
            # Clear server-side history
            response = requests.post(
                f"{self.api_url}/query",
                json={
                    "query": "",
                    "session_id": self.session_id,
                    "clear_history": True
                },
                timeout=10
            )
            print("History cleared on server")
        except Exception as e:
            print(f"Error clearing server history: {e}")

        # Clear client-side history
        return []

    def create_interface(self) -> gr.Blocks:
        """Create Gradio interface"""
        with gr.Blocks(title="MCP Chat Client") as interface:
            gr.Markdown("""
            # MCP Chat Client
            Chat with your MCP server. Conversation history is maintained automatically.
            """)

            with gr.Group():
                chatbot = gr.Chatbot(
                    label="Chat History",
                    height=400,
                    show_label=True
                )

                with gr.Row():
                    message_input = gr.Textbox(
                        label="Your Message",
                        placeholder="Enter your query...",
                        lines=2,
                        scale=4
                    )
                    with gr.Column(scale=1):
                        send_btn = gr.Button("Send", size="lg")
                        clear_btn = gr.Button("Clear History", size="sm", variant="secondary")

                send_btn.click(
                    self.send_message,
                    inputs=[message_input, chatbot],
                    outputs=chatbot
                ).then(
                    lambda: "",
                    outputs=message_input
                )

                # Allow pressing Enter to send
                message_input.submit(
                    self.send_message,
                    inputs=[message_input, chatbot],
                    outputs=chatbot
                ).then(
                    lambda: "",
                    outputs=message_input
                )

                # Clear history button
                clear_btn.click(
                    self.clear_history,
                    inputs=[chatbot],
                    outputs=chatbot
                )

            gr.Markdown("""
            ### Tips:
            - **Conversation history is maintained** - You can ask follow-up questions
            - Example: "List VDBs" → "Show me more details about the first one"
            - Click "Clear History" to start a new conversation
            - Be specific with your queries to help the LLM select the right tool
            - Tool execution may take time depending on the operation
            - Check the server logs for debugging information
            """)

        return interface


def create_gradio_app(api_url: str = "http://localhost:8000") -> gr.Blocks:
    """Factory function to create Gradio app"""
    interface = GradioChatInterface(api_url)
    return interface.create_interface()


if __name__ == "__main__":
    app = create_gradio_app()
    app.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False,
        show_error=True
    )

