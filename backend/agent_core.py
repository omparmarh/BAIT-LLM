import json
import os
import re
from typing import List, Dict, Any, Callable, AsyncIterator, AsyncGenerator

from .tools import TOOLS
from .memory_manager import BAITMemory
import requests

class BAITAgent:
    def __init__(self, api_base: str = "http://localhost:1234/v1", memory_db: str = "bait_memory.db"):
        self.api_base = api_base
        self.memory = BAITMemory(memory_db)
        self.tools = TOOLS
        self.max_iterations = 5
        self.system_prompt = f"""You are BAIT, a hyper-intelligent AI Agent. 
Think step-by-step. Use tools if needed.
If the user wants to play music or trending songs (especially in India), use the 'play_youtube_music' tool.
Output your response in the following JSON format:
{{
    "thought": "Your internal reasoning process",
    "action": "tool_name",
    "action_input": {{"param": "value"}},
    "final_answer": "Your final response to the user if no more tools are needed"
}}
Available tools:
{chr(10).join([f"- {name}: {func.__doc__}" for name, func in TOOLS.items()])}
"""

    async def _call_llm_stream(self, messages: List[Dict]) -> AsyncIterator[str]:
        try:
            payload = {
                "model": "local-model",
                "messages": messages,
                "temperature": 0.3,
                "stream": True
            }
            response = requests.post(
                f"{self.api_base}/chat/completions",
                json=payload,
                stream=True,
                timeout=90
            )
            
            if response.status_code != 200:
                yield json.dumps({"final_answer": f"Error: {response.status_code}"})
                return

            for line in response.iter_lines():
                if line:
                    line_str = line.decode('utf-8').replace('data: ', '').strip()
                    if line_str == '[DONE]': break
                    try:
                        data = json.loads(line_str)
                        content = data['choices'][0]['delta'].get('content', '')
                        if content:
                            yield content
                    except:
                        continue
        except Exception as e:
            yield json.dumps({"final_answer": f"Connection Error: {str(e)}"})

    async def run_stream(self, user_input: str, session_id: str = "default") -> AsyncGenerator[Dict, None]:
        history = self.memory.get_history(session_id)
        messages = [{"role": "system", "content": self.system_prompt}]
        for msg in history:
            messages.append(msg)
        messages.append({"role": "user", "content": user_input})

        for i in range(self.max_iterations):
            full_content = ""
            async for chunk in self._call_llm_stream(messages):
                full_content += chunk
                yield {"type": "text", "content": chunk}

            # Parse the full response for tools
            try:
                start = full_content.find('{')
                end = full_content.rfind('}') + 1
                if start != -1 and end != 0:
                    data = json.loads(full_content[start:end])
                else:
                    data = {"final_answer": full_content}
            except:
                data = {"final_answer": full_content}

            if "final_answer" in data and data["final_answer"]:
                self.memory.add_message(session_id, "user", user_input)
                self.memory.add_message(session_id, "assistant", data["final_answer"])
                yield {"type": "done", "content": data["final_answer"]}
                return

            action = data.get("action")
            action_input = data.get("action_input", {})

            if action in self.tools:
                yield {"type": "thought", "content": data.get("thought", "Executing tool...")}
                try:
                    observation = self.tools[action](**action_input)
                except Exception as e:
                    observation = f"Error: {str(e)}"
                
                yield {"type": "observation", "content": observation}
                messages.append({"role": "assistant", "content": full_content})
                messages.append({"role": "system", "content": f"Observation: {observation}"})
            else:
                yield {"type": "done", "content": data.get("final_answer", full_content)}
                return

    def run(self, user_input: str, session_id: str = "default") -> str:
        # Compatibility wrapper for synchronous call
        import asyncio
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        async def _run():
            resp = ""
            async for chunk in self.run_stream(user_input, session_id):
                if chunk['type'] == 'text':
                    resp += chunk['content']
                elif chunk['type'] == 'done':
                    resp = chunk['content']
            return resp
        
        return loop.run_until_complete(_run())

# Example tool definitions
def web_search(query: str):
    """Search the web for information."""
    return f"Results for {query}: Gujarat is a state in India..."

def create_file(filename: str, content: str):
    """Create a new file with the given content."""
    with open(filename, 'w') as f:
        f.write(content)
    return f"File {filename} created successfully."

if __name__ == "__main__":
    agent = BAITAgent(api_base="http://localhost:1234/v1")
    print(agent.run("Research Gujarat and save to gui.txt"))
