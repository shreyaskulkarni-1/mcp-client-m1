"""
Gradio interface for MCP Chat
"""
import asyncio
import pdb

import gradio as gr
import requests
import json
from typing import List, Tuple


class GradioChatInterface:
    """Gradio chat interface for MCP client"""

    def __init__(self, api_url: str = "http://localhost:8000"):
        self.api_url = api_url
        self.chat_history = []

    def send_message(self, message: str, history: List[Tuple[str, str]]) -> List[Tuple[str, str]]:
        """
        Send message to Django backend and get response

        Args:
            message: User message
            history: Chat history from Gradio

        Returns:
            Updated chat history
        """
        try:
            # Add user message to history
            history.append((message, None))

            # Send to backend
            # pdb.set_trace()
            response = requests.post(
                f"{self.api_url}/query",
                json={"query": message},
                timeout=300  # 5 minute timeout for long-running operations
            )

            if response.status_code == 200:
                data = response.json()
                bot_response = data.get('response', 'No response from server')
            else:
                bot_response = f"Error: {response.status_code} - {response.text}"

            # Update last message with bot response
            history[-1] = (message, bot_response)

        except requests.exceptions.ConnectionError as ex:
            history[-1] = (message, "Error: Cannot connect to server. Make sure Django is running on http://localhost:8000")
        except requests.exceptions.Timeout:
            history[-1] = (message, "Error: Request timed out. The operation took too long.")
        except Exception as e:
            history[-1] = (message, f"Error: {str(e)}")

        return history

    def create_interface(self) -> gr.Blocks:
        """Create Gradio interface"""
        with gr.Blocks(title="MCP Chat Client") as interface:
            gr.Markdown("""
            # MCP Chat Client
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
                    send_btn = gr.Button("Send", scale=1, size="lg")

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

            gr.Markdown("""
            ### Tips:
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
        server_name="localhost",
        server_port=7860,
        share=False,
        show_error=True
    )

