import asyncio
from fastapi import WebSocket, WebSocketDisconnect
from typing import List
from anthropic.types.beta import BetaMessageParam

from .agentic_loop import APIProvider, sampling_loop
from ..core.config import settings

class WebSocketAgentHandler:

    MODEL = "claude-sonnet-4-20250514"
    TOOL_VERSION = "computer_use_20250124"

    def __init__(self, websocket: WebSocket, session_id: str, db_service, api_provider: APIProvider, sampling_loop, messages_for_api: List[BetaMessageParam]):
        self.websocket = websocket
        self.session_id = session_id
        self.db_service = db_service
        self.api_provider = api_provider
        self.sampling_loop = sampling_loop
        self.messages_for_api = messages_for_api
        self.connected = True

    async def send_message(self, message: dict):
        if not self.connected:
            return
        try:
            await self.websocket.send_json(message)
        except Exception as e:
            print(f"[WebSocket Error] Failed to send: {e}")
            self.connected = False

    def output_callback(self, block):
        if block["type"] == "thinking":
            thinking_text = block.get("text", "") or block.get("thinking", "")
            if thinking_text:
                asyncio.create_task(self.send_message({
                    "type": "thinking",
                    "message": thinking_text
                }))
        elif block["type"] == "text":
            # Only stream to client; persistence happens after sampling completes
            asyncio.create_task(self.send_message({
                "type": "agent_message",
                "message": block["text"]
            }))
        elif block["type"] == "image":
            if block.get("source") and block["source"].get("type") == "base64":
                asyncio.create_task(self.send_message({
                    "type": "image",
                    "data": block["source"]["data"]
                }))
        elif block["type"] == "tool_use":
            print(f"[*] Tool requested: {block.get('name', '')} (id={block.get('id', '')})")
        else:
            asyncio.create_task(self.send_message({
                "type": "output",
                "content": block
            }))

    def tool_output_callback(self, tool_result, tool_use_id):
        if tool_result.output:
            asyncio.create_task(self.send_message({
                "type": "agent_message",
                "message": tool_result.output
            }))
        if tool_result.base64_image:
            asyncio.create_task(self.send_message({
                "type": "image",
                "data": tool_result.base64_image
            }))
        if tool_result.error:
            asyncio.create_task(self.send_message({
                "type": "agent_message",
                "message": f"Error: {tool_result.error}"
            }))

    def api_response_callback(self, req, res, err):
        if err:
            print(f"[API Error] {err}")
            asyncio.create_task(self.send_message({
                "type": "agent_message",
                "message": f"API Error: {err}"
            }))

    async def handle(self):
        try:
            while self.connected:
                try:
                    # First try to receive as JSON
                    data = await self.websocket.receive_json()
                    user_message = data.get("message", "")
                    if not user_message:
                        continue

                    print(f"[*] Received message: {user_message}")
                    self.db_service.add_message(self.session_id, "user", [{"type": "text", "text": user_message}])
                    self.messages_for_api.append({
                        "role": "user",
                        "content": [{"type": "text", "text": user_message}]
                    })

                    original_count = len(self.messages_for_api)

                    try:
                        if not settings.ANTHROPIC_API_KEY:
                            await self.send_message({
                                "type": "agent_message",
                                "message": "Error: ANTHROPIC_API_KEY is not configured. Please set the environment variable."
                            })
                            continue

                        await self.sampling_loop(
                            model=self.MODEL,
                            provider=self.api_provider,
                            system_prompt_suffix="",
                            messages=self.messages_for_api,
                            output_callback=self.output_callback,
                            tool_output_callback=self.tool_output_callback,
                            api_response_callback=self.api_response_callback,
                            api_key=settings.ANTHROPIC_API_KEY,
                            only_n_most_recent_images=None,
                            max_tokens=4096,
                            tool_version=self.TOOL_VERSION,
                            thinking_budget=None,
                            token_efficient_tools_beta=False
                        )
                    except Exception as e:
                        print(f"[Error] Sampling loop failed: {e}")
                        await self.send_message({
                            "type": "agent_message",
                            "message": f"Error: {str(e)}"
                        })

                    if len(self.messages_for_api) > original_count:
                        for i in range(original_count, len(self.messages_for_api)):
                            msg = self.messages_for_api[i]
                            role = msg.get("role")
                            content = msg.get("content", [])
                            if role == "assistant":
                                try:
                                    self.db_service.add_message(self.session_id, "assistant", content)
                                except Exception as e:
                                    print(f"[DB] Failed to persist assistant message: {e}")
                            elif role == "user":
                                # Handle tool results or extra user blocks that sampling_loop may have appended
                                if content and isinstance(content, list):
                                    if len(content) == 1 and content[0].get("type") == "tool_result":
                                        tool_result_content = content[0].get("content", [])
                                        if tool_result_content:
                                            self.db_service.add_message(self.session_id, "user", tool_result_content)
                                    else:
                                        self.db_service.add_message(self.session_id, "user", content)

                except ValueError as e:
                    try:
                        text_data = await self.websocket.receive_text()
                    except:
                        pass
                    continue
                except WebSocketDisconnect:
                    print(f"[-] WebSocket disconnected: {self.session_id}")
                    self.connected = False
                    break
                except Exception as e:
                    print(f"[Error] Error processing message: {e}")
                    # Check if this is a connection close error
                    if "Cannot call 'receive'" in str(e) or "NO_STATUS_RCVD" in str(e) or "1005" in str(e):
                        print(f"[Info] WebSocket connection closed by client: {self.session_id}")
                        self.connected = False
                        break
                    else:
                        # For other errors, continue processing
                        continue

        except WebSocketDisconnect:
            print(f"[-] WebSocket disconnected: {self.session_id}")
            self.connected = False
        except Exception as e:
            print(f"[Error] WebSocket error: {e}")
            self.connected = False
            try:
                await self.send_message({
                    "type": "agent_message",
                    "message": f"Connection error: {str(e)}"
                })
            except:
                pass
