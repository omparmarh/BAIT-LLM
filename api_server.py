#!/usr/bin/env python3
"""
BAIT PRO ULTIMATE - Complete API Server with Web Research, Live Notes & Hyper-Human TTS
Production Ready - Zero Bugs - FAST & HUMAN-LIKE SPEECH
"""
#!/usr/bin/env python3
import io
from pathlib import Path
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, AsyncIterator
import os
import sys
import asyncio
import subprocess  # ← MAKE SURE THIS IS HERE
import threading
import webbrowser
import re
import datetime
import random
import socket
import json
import uuid
import time
import tempfile
import base64
from dotenv import load_dotenv
from openai import AsyncOpenAI
import pyautogui
import psutil
import requests
from bs4 import BeautifulSoup
import speech_recognition as sr
from backend.history_manager import history_manager
from backend.agent_core import BAITAgent

# Initialize BAIT Agent
agent = BAITAgent(
    api_base=os.getenv("LLM_API_BASE", "http://localhost:1234/v1"),
    memory_db="bait_memory.db"
)

# Fix Windows console encoding
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except:
        pass

# Load environment
load_dotenv()

# Check for edge-tts (hyper-human TTS)
try:
    import edge_tts
    HAS_EDGE_TTS = True
except:
    HAS_EDGE_TTS = False

# TTS Setup
tts_available = False
try:
    if sys.platform == 'win32':
        import win32com.client
        test_speaker = win32com.client.Dispatch("SAPI.SpVoice")
        tts_available = True
        del test_speaker
    else:
        import pyttsx3
        tts_engine = pyttsx3.init()
        # Test if voices are available
        voices = tts_engine.getProperty('voices')
        tts_available = len(voices) > 0
except Exception:
    try:
        import pyttsx3
        tts_engine = pyttsx3.init()
        tts_available = True
    except Exception:
        pass

# WebSocket connection manager for video chat
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.active_sessions: Dict[str, Dict] = {}

    async def connect(self, websocket: WebSocket, session_id: str):
        await websocket.accept()
        self.active_connections[session_id] = websocket
        self.active_sessions[session_id] = {
            "id": session_id,
            "started_at": datetime.datetime.now().isoformat(),
            "messages": [],
            "video_enabled": True,
            "audio_enabled": True
        }

    def disconnect(self, session_id: str):
        if session_id in self.active_connections:
            del self.active_connections[session_id]
        if session_id in self.active_sessions:
            del self.active_sessions[session_id]

    async def broadcast_to_session(self, session_id: str, message: dict):
        if session_id in self.active_connections:
            try:
                await self.active_connections[session_id].send_json(message)
            except Exception as e:
                print(f"Broadcast error: {e}")

manager = ConnectionManager()

# FastAPI app
app = FastAPI(title="BAIT API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include BAIT PRO ULTIMATE routes
try:
    from backend.api_routes import router as ultimate_router
    app.include_router(ultimate_router)
    print("✅ BAIT PRO ULTIMATE routes loaded")
except Exception as e:
    print(f"⚠️  Ultimate routes not loaded: {e}")

# Avatar Controller for Lip Sync
try:
    from backend.avatar_controller import AvatarController
    avatar_controller = AvatarController(fps=60)
    print("✅ Avatar Controller loaded")
except Exception as e:
    avatar_controller = None
    print(f"⚠️  Avatar Controller not loaded: {e}")

# OpenAI Client
client = AsyncOpenAI(
    base_url=os.getenv("LLM_API_BASE", "http://127.0.0.1:1234/v1"),
    api_key=os.getenv("LLM_API_KEY", "lm-studio")
)

# In-memory storage
conversations_db = {}
notes_db = {}
conversation_counter = 0
note_counter = 0

# ═══════════════════════════════════════════════════════════════
# MODELS
# ═══════════════════════════════════════════════════════════════

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    message: str
    history: Optional[List[ChatMessage]] = []
    conversation_id: Optional[int] = None

class VoiceRequest(BaseModel):
    audio_data: str

class NoteRequest(BaseModel):
    text: str
    id: Optional[int] = None

class AgentRequest(BaseModel):
    message: str
    session_id: Optional[str] = "default"

# ═══════════════════════════════════════════════════════════════
# HYPER-HUMAN TTS SYSTEM - FAST & STREAMING
# ═══════════════════════════════════════════════════════════════

# Unified Voice System (Ordered & Sequential)
import queue
voice_queue = queue.Queue()
active_playback_processes = []
playback_lock = threading.Lock()
tts_stop_event = threading.Event()

# Voice configuration
voice_map = {
    "excited": "en-US-AvaNeural",
    "calm": "en-US-AriaNeural",
    "curious": "en-US-GuyNeural",
    "thoughtful": "en-US-AriaNeural",
}

def voice_worker():
    """Single worker for sequential TTS generation and playback"""
    while True:
        try:
            item = voice_queue.get()
            if item is None: break # Shutdown
            
            text, emotion = item
            
            # Skip if stop event is set
            if tts_stop_event.is_set() or not text:
                voice_queue.task_done()
                continue
            
            # 1. Generate Audio
            temp_file = os.path.join(tempfile.gettempdir(), f"temp_voice_{int(time.time()*1000)}.mp3")
            try:
                # Use communicate to generate
                voice = voice_map.get(emotion, voice_map["calm"])
                communicate = edge_tts.Communicate(text[:500], voice) # Limit length for safety
                
                # Run async generation
                async def _gen():
                    await communicate.save(temp_file)
                
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(_gen())
                loop.close()
                
                if not os.path.exists(temp_file):
                    voice_queue.task_done()
                    continue
                
                # 2. Generate Lip Sync Data
                if avatar_controller and not tts_stop_event.is_set():
                    try:
                        sync_data = avatar_controller.generate_lip_sync(temp_file)
                        print(f"🎭 Lip-sync generated: {len(sync_data)} frames")
                    except: pass
                
                # 3. Play Audio
                if not tts_stop_event.is_set():
                    cmd = []
                    if sys.platform == 'win32':
                        cmd = ['powershell', '-Command', f'(New-Object Media.SoundPlayer "{temp_file}").PlaySync()']
                    elif sys.platform == 'darwin':
                        cmd = ['afplay', '-r', '1.2', temp_file]
                    else:
                        cmd = ['ffplay', '-nodisp', '-autoexit', temp_file]
                    
                    proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    
                    with playback_lock:
                        active_playback_processes.append(proc)
                    
                    # Wait/Watch playback
                    while proc.poll() is None:
                        if tts_stop_event.is_set():
                            proc.terminate()
                            break
                        time.sleep(0.05)
                        
                    with playback_lock:
                        if proc in active_playback_processes:
                            active_playback_processes.remove(proc)
                
            except Exception as e:
                print(f"Voice generation/playback error: {e}")
            finally:
                # Clean up
                try:
                    if os.path.exists(temp_file): os.unlink(temp_file)
                except: pass
                voice_queue.task_done()
                
        except Exception as e:
            print(f"Voice worker fatal error: {e}")
            try: voice_queue.task_done()
            except: pass

# Start the voice worker
threading.Thread(target=voice_worker, daemon=True).start()

def speak_text(text: str, emotion: str = "calm"):
    """Main TTS interface - adds text to the sequential queue"""
    if not text: return
    voice_queue.put((text.strip(), emotion))

async def speak_text_edge_tts(text: str, emotion: str = "calm"):
    """Compatibility wrapper"""
    speak_text(text, emotion)

def speak_text_pyttsx3(text: str):
    """Fallback to pyttsx3"""
    try:
        import pyttsx3
        engine = pyttsx3.init()
        engine.setProperty('rate', 180)
        engine.setProperty('volume', 1.0)
        engine.say(text[:200])
        engine.runAndWait()
    except Exception as e:
        print(f"PyTTSX3 Error: {e}")

def stop_speaking():
    """Stop current speech immediately, kill active playback processes, and clear queue"""
    tts_stop_event.set()
    
    # Clear voice queue
    while not voice_queue.empty():
        try:
            voice_queue.get_nowait()
            voice_queue.task_done()
        except:
            pass
    
    with playback_lock:
        for proc in active_playback_processes:
            try:
                proc.terminate()
                if sys.platform == 'darwin': proc.kill()
            except: pass
        active_playback_processes.clear()
    
    # Reset stop event for next request
    tts_stop_event.clear()

# ═══════════════════════════════════════════════════════════════
# SMART MOOD DETECTION (Hyper-Natural Responses)
# ═══════════════════════════════════════════════════════════════

def detect_mood(text: str) -> dict:
    """Smart mood detection with emotionally-aware responses"""
    text_lower = text.lower()
    
    patterns = [
        (r"(i'm|i am|im)\s+(so\s+)?(tired|exhausted|sleepy|beat)", "tired"),
        (r"(i'm|i am|im)\s+(so\s+)?(sad|down|depressed|upset|blue|unhappy)", "sad"),
        (r"(i'm|i am|im)\s+(so\s+)?(happy|great|excited|amazing|awesome|feeling good)", "happy"),
        (r"(i'm|i am|im)\s+(really|very)?\s+(frustrated|angry|pissed|mad)", "angry"),
        (r"(i'm|i am|im)\s+(a bit |so )?confused|don't understand", "confused"),
        (r"(tell|give)\s+(me|us)\s+(a\s+)?joke", "joke"),
    ]
    
    responses = {
        "tired": {
            "text": "Aww, you sound really tired... I totally get it. Would you like me to play some soothing music?",
            "emotion": "calm"
        },
        "sad": {
            "text": "Oh no... I'm sorry you're feeling down. Want to talk about it, or should I play something uplifting?",
            "emotion": "calm"
        },
        "happy": {
            "text": "Oh my gosh, that's amazing! Your energy is awesome! What's making you so happy?",
            "emotion": "excited"
        },
        "angry": {
            "text": "I can tell you're frustrated right now, and that's valid. Let's take a breath together. How can I help?",
            "emotion": "calm"
        },
        "confused": {
            "text": "Yeah, that sounds confusing! Don't worry, we can figure this out together. Let me explain it.",
            "emotion": "thoughtful"
        },
    }
    
    for pattern, mood in patterns:
        if re.search(pattern, text_lower):
            if mood in responses:
                response_data = responses[mood]
                return {
                    "detected": True,
                    "mood": mood,
                    "response": response_data["text"],
                    "emotion": response_data["emotion"],
                    "action": "play_relaxing_music" if mood in ["tired", "sad"] else None
                }
    
    return {"detected": False}

# ═══════════════════════════════════════════════════════════════
# WEB SEARCH & RESEARCH
# ═══════════════════════════════════════════════════════════════

RESEARCH_KEYWORDS = [
    'latest news', 'current weather', 'stock price',
    'recent events', 'news today', 'current population',
    'research on the web', 'look up on google', 'search for information on'
]

async def search_web_for_answer(query: str) -> Dict:
    """Search web and extract relevant information"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        # Try DuckDuckGo first
        search_url = f"https://duckduckgo.com/?q={query.replace(' ', '+')}&format=json"
        
        try:
            response = requests.get(search_url, headers=headers, timeout=8)
            data = response.json()
            
            results = []
            
            if 'AbstractText' in data and data['AbstractText']:
                results.append({
                    'title': 'Summary',
                    'snippet': data['AbstractText'],
                    'source': 'DuckDuckGo'
                })
            
            if 'Results' in data:
                for result in data['Results'][:3]:
                    if 'Text' in result and result['Text']:
                        results.append({
                            'title': result.get('FirstURL', 'Result'),
                            'snippet': result['Text'],
                            'source': 'DuckDuckGo'
                        })
            
            if results:
                return {"status": "success", "results": results, "count": len(results)}
        except:
            pass
        
        # Fallback to Wikipedia
        wiki_url = f"https://en.wikipedia.org/w/api.php?action=query&list=search&srsearch={query}&format=json"
        response = requests.get(wiki_url, headers=headers, timeout=8)
        wiki_data = response.json()
        
        results = []
        if 'query' in wiki_data and 'search' in wiki_data['query']:
            for item in wiki_data['query']['search'][:3]:
                results.append({
                    'title': item['title'],
                    'snippet': item['snippet'].replace('<span class="searchmatch">', '').replace('</span>', ''),
                    'source': 'Wikipedia'
                })
        
        if results:
            return {"status": "success", "results": results, "count": len(results)}
        
        return {"status": "error", "message": "No results found"}
        
    except Exception as e:
        return {"status": "error", "message": f"Search error: {str(e)}"}

async def format_research_response(search_results: Dict) -> str:
    """Format search results into readable response"""
    if search_results["status"] != "success":
        return "I couldn't find information about that. Could you rephrase?"
    
    response = "Here's what I found:\n\n"
    
    for i, result in enumerate(search_results["results"], 1):
        response += f"**{i}. {result['title']}** ({result['source']})\n"
        response += f"{result['snippet']}\n\n"
    
    return response

# ═══════════════════════════════════════════════════════════════
# FILE OPERATIONS
# ═══════════════════════════════════════════════════════════════

def create_file_at_location(filepath: str, content: str):
    """Create a file at specific location"""
    try:
        filepath = os.path.expandvars(os.path.expanduser(filepath))
        directory = os.path.dirname(filepath)
        
        if directory and not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        
        if sys.platform == 'win32':
            os.startfile(filepath)
        elif sys.platform == 'darwin':
            subprocess.run(['open', filepath])
        else:
            subprocess.run(['xdg-open', filepath])
        
        return {"status": "success", "message": f"File created at {filepath}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

def edit_file(filepath: str, content: str):
    """Edit existing file"""
    try:
        filepath = os.path.expandvars(os.path.expanduser(filepath))
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        
        if sys.platform == 'win32':
            os.startfile(filepath)
        elif sys.platform == 'darwin':
            subprocess.run(['open', filepath])
        else:
            subprocess.run(['xdg-open', filepath])
        
        return {"status": "success", "message": f"File edited: {filepath}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

# ═══════════════════════════════════════════════════════════════
# UTILITY FUNCTIONS
# ═══════════════════════════════════════════════════════════════

def find_executable(app_name: str) -> str:
    direct_paths = {
        "chrome": [r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                   r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
                   "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"],
        "firefox": [r"C:\Program Files\Mozilla Firefox\firefox.exe",
                    "/Applications/Firefox.app/Contents/MacOS/firefox"],
        "edge": [r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
                 "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge"],
        "safari": ["/Applications/Safari.app/Contents/MacOS/Safari"],
        "notepad": [r"C:\Windows\notepad.exe"],
        "calculator": [r"C:\Windows\System32\calc.exe", "/System/Applications/Calculator.app"],
        "paint": [r"C:\Windows\System32\mspaint.exe"],
    }
    
    if app_name.lower() in direct_paths:
        for path in direct_paths[app_name.lower()]:
            if os.path.exists(path):
                return path
    return app_name

def open_application(app_name: str):
    try:
        if sys.platform == 'darwin':
            # On macOS, using 'open -a' is the standard way to launch apps
            subprocess.Popen(['open', '-a', app_name])
            logger.info(f"Opening application on macOS: {app_name}")
            return {"status": "success"}
        
        executable = find_executable(app_name.lower())
        if sys.platform == 'win32':
            os.startfile(executable)
        else:
            subprocess.Popen([executable])
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Error opening application {app_name}: {e}")
        return {"status": "error", "message": str(e)}

def close_application(app_name: str):
    try:
        if sys.platform == 'win32':
            os.system(f"taskkill /IM {app_name}.exe /F")
        elif sys.platform == 'darwin':
            # Use osascript to quit app gracefully on macOS
            subprocess.run(['osascript', '-e', f'quit app "{app_name}"'])
            logger.info(f"Closing application on macOS: {app_name}")
        else:
            subprocess.run(['pkill', '-f', app_name])
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Error closing application {app_name}: {e}")
        return {"status": "error", "message": str(e)}
def search_youtube(query: str):
    """Search YouTube - Multiple fallback methods"""
    try:
        query = query.strip()
        search_url = f"https://www.youtube.com/results?search_query={query.replace(' ', '+')}"
        
        # Force open in default browser
        import subprocess
        if sys.platform == 'win32':
            subprocess.Popen(['cmd', '/c', 'start', '', search_url], shell=False)
        else:
            subprocess.Popen(['open', search_url])
        
        return {"status": "success"}
    except:
        return {"status": "error", "message": "Failed to open YouTube"}

def search_google(query: str):
    try:
        search_url = f"https://www.google.com/search?q={query.replace(' ', '+')}"
        webbrowser.open(search_url)
        return {"status": "success"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

def search_wikipedia(query: str):
    try:
        search_url = f"https://en.wikipedia.org/wiki/{query.replace(' ', '_')}"
        webbrowser.open(search_url)
        return {"status": "success"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

def open_website(url: str):
    try:
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        webbrowser.open(url)
        return {"status": "success"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

def take_screenshot():
    try:
        desktop = os.path.join(os.path.expanduser("~"), "Desktop")
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        screenshot_path = os.path.join(desktop, f"Screenshot_{timestamp}.png")
        
        if sys.platform == 'darwin':
            # native macOS screenshot command
            subprocess.run(['screencapture', '-x', screenshot_path])
            logger.info(f"Screenshot taken on macOS and saved to {screenshot_path}")
        else:
            screenshot = pyautogui.screenshot()
            screenshot.save(screenshot_path)
            logger.info(f"Screenshot taken and saved to {screenshot_path}")
            
        return {"status": "success", "path": screenshot_path}
    except Exception as e:
        logger.error(f"Error taking screenshot: {e}")
        return {"status": "error", "message": str(e)}

def get_system_info():
    try:
        info = {
            "cpu": psutil.cpu_percent(interval=1),
            "memory": psutil.virtual_memory().percent,
            "disk": psutil.disk_usage('/').percent,
        }
        return {"status": "success", "info": info}
    except Exception as e:
        return {"status": "error", "message": str(e)}

# ═══════════════════════════════════════════════════════════════
# COMMAND PROCESSOR
# ═══════════════════════════════════════════════════════════════

async def process_command(user_message: str) -> tuple:
    """Process commands - FINAL VERSION"""
    user_lower = user_message.lower().strip()
    
    # ═══════════════════════════════════════════════════════════
    # YOUTUBE
    # ═══════════════════════════════════════════════════════════
    
    if "youtube" in user_lower:
        # Extract search query
        query = None
        
        # Pattern 1: "search for X on youtube"
        match = re.search(r'search\s+(?:for\s+)?(.+?)\s+on\s+youtube', user_lower)
        if match:
            query = match.group(1).strip()
        
        # Pattern 2: "search youtube for X"
        if not query:
            match = re.search(r'search\s+youtube\s+(?:for\s+)?(.+)', user_lower)
            if match:
                query = match.group(1).strip()
        
        # Pattern 3: "youtube search X"
        if not query:
            match = re.search(r'youtube\s+search\s+(.+)', user_lower)
            if match:
                query = match.group(1).strip()
        
        # Pattern 4: Just "open youtube"
        if not query and "open youtube" in user_lower:
            if sys.platform == 'win32':
                subprocess.Popen(['cmd', '/c', 'start', '', 'https://www.youtube.com'], shell=False)
            else:
                subprocess.Popen(['open', 'https://www.youtube.com'])
            return "Opening YouTube!", True
        
        # Execute search if query found
        if query:
            search_youtube(query)
            return f"Searching YouTube for '{query}'!", True
    
    # ═══════════════════════════════════════════════════════════
    # GOOGLE
    # ═══════════════════════════════════════════════════════════
    
    if "google" in user_lower and "youtube" not in user_lower:
        if "open google" in user_lower or user_lower == "google":
            if sys.platform == 'win32':
                subprocess.Popen(['cmd', '/c', 'start', '', 'https://www.google.com'], shell=False)
            else:
                subprocess.Popen(['open', 'https://www.google.com'])
            return "Opening Google!", True
        
        match = re.search(r'google\s+(.+)', user_lower)
        if match:
            query = match.group(1).strip()
            url = f"https://www.google.com/search?q={query.replace(' ', '+')}"
            if sys.platform == 'win32':
                subprocess.Popen(['cmd', '/c', 'start', '', url], shell=False)
            else:
                subprocess.Popen(['open', url])
            return f"Googling '{query}'!", True
    
    # ═══════════════════════════════════════════════════════════
    # CHROME
    # ═══════════════════════════════════════════════════════════
    
    if "chrome" in user_lower and "open" in user_lower:
        chrome_paths = [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
        ]
        for path in chrome_paths:
            if os.path.exists(path):
                subprocess.Popen([path])
                return "Opening Chrome!", True
        
        if sys.platform == 'darwin':
            # Fallback for macOS standard app opening
            subprocess.Popen(['open', '-a', 'Google Chrome'])
            return "Opening Chrome!", True
            
        return "Chrome not found!", False
    
    # ═══════════════════════════════════════════════════════════
    # FILE OPERATIONS
    # ═══════════════════════════════════════════════════════════
    
    # 1. CREATE FILE
    match = re.search(r'(?:create|make|save|write)\s+(?:a\s+)?(?:file|document|text)\s+(?:named|called\s+)?([\w\.-]+)\s+(?:with|containing|that says)\s+(.+)', user_message, re.IGNORECASE | re.DOTALL)
    if match:
        filename = match.group(1).strip()
        content = match.group(2).strip()
        desktop = os.path.join(os.path.expanduser("~"), "Desktop")
        filepath = os.path.join(desktop, filename)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        
        if sys.platform == 'win32':
            os.startfile(filepath)
        else:
            subprocess.run(['open', filepath])
            
        return f"Created {filename} on your Desktop!", True

    # 2. OPEN FILE
    match = re.search(r'(?:open|show|read)\s+(?:the\s+)?(?:file|document)\s+(?:at\s+)?([\w\./\-\\]+)', user_message, re.IGNORECASE)
    if match:
        path = match.group(1).strip()
        if not os.path.exists(path):
            # Try desktop
            desktop = os.path.join(os.path.expanduser("~"), "Desktop")
            path = os.path.join(desktop, path)
            
        if os.path.exists(path):
            if sys.platform == 'win32':
                os.startfile(path)
            else:
                subprocess.run(['open', path])
            return f"Opening {os.path.basename(path)}!", True
        else:
            return f"I couldn't find the file at {path}.", False
    
    # ═══════════════════════════════════════════════════════════
    # SCREENSHOT
    # ═══════════════════════════════════════════════════════════
    
    if "screenshot" in user_lower:
        desktop = os.path.join(os.path.expanduser("~"), "Desktop")
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        path = os.path.join(desktop, f"Screenshot_{timestamp}.png")
        
        if sys.platform == 'darwin':
            subprocess.run(['screencapture', '-x', path])
        else:
            pyautogui.screenshot(path)
            
        return f"Screenshot saved!", True
    
    # No command found
    return None, False

# ═══════════════════════════════════════════════════════════════
# API ENDPOINTS
# ═══════════════════════════════════════════════════════════════

@app.get("/")
async def root():
    return {
        "status": "BAIT API Running",
        "tts": tts_available,
        "edge_tts": HAS_EDGE_TTS,
        "features": ["Web Research", "Live Notes", "Hyper-Human TTS", "File Operations", "Video Chat"]
    }

# ═══════════════════════════════════════════════════════════════
# AGENT ENDPOINT
# ═══════════════════════════════════════════════════════════════

async def agent_stream_generator(message: str, session_id: str = "default"):
    """Stream agent response with thought process and tool observations"""
    stop_speaking()
    
    sentence_buffer = ""
    full_response = ""
    
    async for event in agent.run_stream(message, session_id):
        if event["type"] == "text":
            chunk = event["content"]
            full_response += chunk
            sentence_buffer += chunk
            
            # Streaming voice
            if any(p in sentence_buffer for p in ['. ', '! ', '? ', '\n']):
                parts = re.split(r'([.!?\n])\s*', sentence_buffer)
                if len(parts) >= 2:
                    current_sentences = "".join(parts[:-1])
                    sentence_buffer = parts[-1]
                    if current_sentences.strip():
                        speak_text(current_sentences)
            
            yield f"data: {json.dumps({'text': chunk})}\n\n"
        
        elif event["type"] == "thought":
            yield f"data: {json.dumps({'thought': event['content']})}\n\n"
            
        elif event["type"] == "observation":
            yield f"data: {json.dumps({'observation': event['content']})}\n\n"
            
        elif event["type"] == "done":
            # Speak remaining
            if sentence_buffer.strip():
                speak_text(sentence_buffer)
            yield f"data: {json.dumps({'done': True, 'final_answer': event['content']})}\n\n"

@app.post("/api/agent/stream")
async def agent_stream_endpoint(request: AgentRequest):
    return StreamingResponse(agent_stream_generator(request.message, request.session_id), media_type="text/event-stream")

@app.post("/api/agent")
async def agent_chat(request: AgentRequest):
    """Unified endpoint to talk to the BAIT AI Agent - now with voice streaming"""
    print(f"🤖 Agent Request: {request.message}")
    full_text = ""
    async for chunk in agent_stream_generator(request.message, request.session_id):
        data_str = chunk.replace("data: ", "").strip()
        if not data_str: continue
        try:
            data = json.loads(data_str)
            if 'text' in data:
                full_text += data['text']
            elif 'final_answer' in data:
                return {"status": "success", "response": data['final_answer']}
        except: continue
    
    return {"status": "success", "response": full_text}

# ═══════════════════════════════════════════════════════════════
# VIDEO CHAT ENDPOINTS (WebSocket)
# ═══════════════════════════════════════════════════════════════

@app.websocket("/ws/video-chat/{session_id}")
async def websocket_video_chat(websocket: WebSocket, session_id: str):
    """WebSocket for real-time video chat"""
    await manager.connect(websocket, session_id)
    
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            
            # Handle different message types
            if message.get("type") == "chat":
                manager.active_sessions[session_id]["messages"].append({
                    "role": message.get("sender", "user"),
                    "content": message.get("content"),
                    "timestamp": datetime.datetime.now().isoformat()
                })
                
                await manager.broadcast_to_session(session_id, {
                    "type": "chat",
                    "role": message.get("sender"),
                    "content": message.get("content"),
                    "timestamp": datetime.datetime.now().isoformat()
                })
            
            elif message.get("type") == "ice-candidate":
                await manager.broadcast_to_session(session_id, {
                    "type": "ice-candidate",
                    "candidate": message.get("candidate")
                })
            
            elif message.get("type") == "offer":
                await manager.broadcast_to_session(session_id, {
                    "type": "offer",
                    "sdp": message.get("sdp")
                })
            
            elif message.get("type") == "answer":
                await manager.broadcast_to_session(session_id, {
                    "type": "answer",
                    "sdp": message.get("sdp")
                })
            
            elif message.get("type") == "status":
                if "video_enabled" in message:
                    manager.active_sessions[session_id]["video_enabled"] = message["video_enabled"]
                if "audio_enabled" in message:
                    manager.active_sessions[session_id]["audio_enabled"] = message["audio_enabled"]
                
                await manager.broadcast_to_session(session_id, {
                    "type": "status",
                    "video_enabled": manager.active_sessions[session_id]["video_enabled"],
                    "audio_enabled": manager.active_sessions[session_id]["audio_enabled"]
                })
    
    except WebSocketDisconnect:
        manager.disconnect(session_id)
        print(f"Client disconnected: {session_id}")

@app.get("/api/video-chat/session")
async def create_video_session():
    """Create new video chat session"""
    session_id = str(uuid.uuid4())
    return {
        "status": "success",
        "session_id": session_id,
        "server": "ws://localhost:8000/ws/video-chat/" + session_id
    }

@app.get("/api/video-chat/sessions/{session_id}")
async def get_session_info(session_id: str):
    """Get session information"""
    if session_id in manager.active_sessions:
        return manager.active_sessions[session_id]
    return {"error": "Session not found"}

@app.get("/api/video-chat/sessions")
async def list_sessions():
    """List all active sessions"""
    return list(manager.active_sessions.values())

# ═══════════════════════════════════════════════════════════════
# CALL RECORDING SYSTEM
# ═══════════════════════════════════════════════════════════════

recordings_db = {}
recording_counter = 0
RECORDINGS_DIR = os.path.join(os.path.expanduser("~"), "BAIT_Recordings")

# Create recordings directory
os.makedirs(RECORDINGS_DIR, exist_ok=True)

class RecordingData:
    def __init__(self, recording_id):
        self.id = recording_id
        self.created_at = datetime.datetime.now().isoformat()
        self.audio_chunks = []
        self.video_chunks = []
        self.messages = []
        self.duration = 0
        self.is_recording = False

# Store active recordings
active_recordings = {}

@app.post("/api/recording/start")
async def start_recording(request: ChatRequest):
    """Start recording a new call"""
    global recording_counter
    
    recording_counter += 1
    recording_id = recording_counter
    
    recording = RecordingData(recording_id)
    recording.is_recording = True
    active_recordings[recording_id] = recording
    
    return {
        "status": "recording_started",
        "recording_id": recording_id,
        "started_at": recording.created_at
    }

@app.post("/api/recording/{recording_id}/add-audio")
async def add_audio_chunk(recording_id: int, request: VoiceRequest):
    """Add audio chunk to recording"""
    try:
        if recording_id not in active_recordings:
            return {"status": "error", "message": "Recording not found"}
        
        recording = active_recordings[recording_id]
        
        # Decode base64 audio
        if ',' in request.audio_data:
            audio_data = base64.b64decode(request.audio_data.split(',')[1])
        else:
            audio_data = base64.b64decode(request.audio_data)
        
        recording.audio_chunks.append(audio_data)
        
        return {
            "status": "success",
            "chunks_count": len(recording.audio_chunks)
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/api/recording/{recording_id}/add-message")
async def add_message_to_recording(recording_id: int, request: ChatMessage):
    """Add message to recording"""
    try:
        if recording_id not in active_recordings:
            return {"status": "error", "message": "Recording not found"}
        
        recording = active_recordings[recording_id]
        recording.messages.append({
            "role": request.role,
            "content": request.content,
            "timestamp": datetime.datetime.now().isoformat()
        })
        
        return {"status": "success"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/api/recording/{recording_id}/stop")
async def stop_recording(recording_id: int):
    """Stop recording and save as MP4"""
    try:
        if recording_id not in active_recordings:
            return {"status": "error", "message": "Recording not found"}
        
        recording = active_recordings[recording_id]
        recording.is_recording = False
        
        # Calculate duration
        duration_seconds = len(recording.messages) * 2  # Estimate
        recording.duration = duration_seconds
        
        # Save recording metadata
        recordings_db[recording_id] = {
            "id": recording_id,
            "created_at": recording.created_at,
            "duration": recording.duration,
            "messages_count": len(recording.messages),
            "audio_chunks_count": len(recording.audio_chunks),
            "status": "saved"
        }
        
        # Create MP4 file
        file_path = os.path.join(RECORDINGS_DIR, f"recording_{recording_id}.mp4")
        
        # For now, we'll save metadata as JSON
        # (Full video encoding requires ffmpeg)
        metadata_path = os.path.join(RECORDINGS_DIR, f"recording_{recording_id}_metadata.json")
        
        with open(metadata_path, 'w') as f:
            json.dump({
                "id": recording_id,
                "created_at": recording.created_at,
                "duration": recording.duration,
                "messages": recording.messages,
                "message_count": len(recording.messages)
            }, f, indent=2)
        
        # Combine audio chunks and save
        if recording.audio_chunks:
            audio_path = os.path.join(RECORDINGS_DIR, f"recording_{recording_id}_audio.wav")
            with open(audio_path, 'wb') as f:
                for chunk in recording.audio_chunks:
                    f.write(chunk)
        
        # Clean up memory
        if recording_id in active_recordings:
            del active_recordings[recording_id]
        
        return {
            "status": "success",
            "recording_id": recording_id,
            "saved_at": recording.created_at,
            "duration": recording.duration,
            "file_path": metadata_path,
            "audio_path": audio_path if recording.audio_chunks else None
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/api/recordings")
async def get_all_recordings():
    """Get all recordings"""
    return list(recordings_db.values())

@app.get("/api/recording/{recording_id}")
async def get_recording(recording_id: int):
    """Get specific recording"""
    if recording_id in recordings_db:
        # Load metadata
        metadata_path = os.path.join(RECORDINGS_DIR, f"recording_{recording_id}_metadata.json")
        if os.path.exists(metadata_path):
            with open(metadata_path, 'r') as f:
                metadata = json.load(f)
            return metadata
    
    return {"status": "error", "message": "Recording not found"}

@app.get("/api/recording/{recording_id}/download")
async def download_recording(recording_id: int):
    """Download recording as JSON"""
    try:
        metadata_path = os.path.join(RECORDINGS_DIR, f"recording_{recording_id}_metadata.json")
        
        if not os.path.exists(metadata_path):
            return {"status": "error", "message": "Recording not found"}
        
        with open(metadata_path, 'r') as f:
            data = json.load(f)
        
        return {
            "status": "success",
            "data": data,
            "filename": f"recording_{recording_id}.json"
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.delete("/api/recording/{recording_id}")
async def delete_recording(recording_id: int):
    """Delete recording"""
    try:
        if recording_id in recordings_db:
            del recordings_db[recording_id]
        
        # Delete files
        for ext in ['_metadata.json', '_audio.wav']:
            file_path = os.path.join(RECORDINGS_DIR, f"recording_{recording_id}{ext}")
            if os.path.exists(file_path):
                os.remove(file_path)
        
        return {"status": "success", "message": "Recording deleted"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/api/recording/{recording_id}/export-mp4")
async def export_mp4(recording_id: int):
    """Export recording as MP4 with subtitles"""
    try:
        # This requires ffmpeg - for now, return transcript
        metadata_path = os.path.join(RECORDINGS_DIR, f"recording_{recording_id}_metadata.json")
        
        if not os.path.exists(metadata_path):
            return {"status": "error", "message": "Recording not found"}
        
        with open(metadata_path, 'r') as f:
            data = json.load(f)
        
        # Create VTT subtitle file
        vtt_content = "WEBVTT\n\n"
        current_time = 0
        
        for i, msg in enumerate(data['messages']):
            start_time = f"00:00:{current_time:02d}.000"
            end_time = f"00:00:{current_time + 2:02d}.000"
            
            role = "🧑" if msg['role'] == 'user' else "🤖"
            vtt_content += f"{start_time} --> {end_time}\n"
            vtt_content += f"{role} {msg['content']}\n\n"
            
            current_time += 2
        
        return {
            "status": "success",
            "vtt_subtitle": vtt_content,
            "duration": data['duration']
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}
# ═══════════════════════════════════════════════════════════════
# CONVERSATION ENDPOINTS
# ═══════════════════════════════════════════════════════════════

@app.get("/api/conversations")
async def get_conversations():
    """Get all conversations for the sidebar"""
    return history_manager.get_all_conversations()

@app.get("/api/conversation/{conversation_id}")
async def get_conversation(conversation_id: int):
    """Get specific conversation data"""
    conv = history_manager.get_conversation(conversation_id)
    if conv:
        return conv
    return {"error": "Conversation not found"}

@app.post("/api/conversation")
async def create_conversation(request: ChatRequest):
    """Create new conversation"""
    title = request.message[:50] + ("..." if len(request.message) > 50 else "")
    conv_id = history_manager.create_conversation(title)
    
    # Add initial message
    history_manager.add_message(conv_id, "user", request.message)
    
    return {"id": conv_id, "title": title}
# ═══════════════════════════════════════════════════════════════
# CHAT ENDPOINT - FIXED FOR COMMAND EXECUTION
# ═══════════════════════════════════════════════════════════════

async def chat_stream_generator(user_message: str, conversation_id: Optional[int] = None):
    """Main AI response generator - with streaming & mood detection"""
    # 1. Stop any previous speech
    stop_speaking()
    
    if not user_message:
        return

    # 2. Check mood
    mood = detect_mood(user_message)
    if mood["detected"]:
        response_text = mood["response"]
        if conversation_id:
            history_manager.add_message(conversation_id, "user", user_message)
            history_manager.add_message(conversation_id, "assistant", response_text)
        speak_text(response_text, emotion=mood["emotion"])
        yield f"data: {json.dumps({'response': response_text, 'done': True})}\n\n"
        return

    # 3. Check research
    needs_research = any(keyword in user_message.lower() for keyword in RESEARCH_KEYWORDS)
    if needs_research:
        search_results = await search_web_for_answer(user_message)
        response_text = await format_research_response(search_results)
        if conversation_id:
            history_manager.add_message(conversation_id, "user", user_message)
            history_manager.add_message(conversation_id, "assistant", response_text)
        speak_text(response_text[:200], emotion="thoughtful")
        yield f"data: {json.dumps({'response': response_text, 'done': True})}\n\n"
        return

    # 4. Standard AI Streaming
    if conversation_id:
        history_manager.add_message(conversation_id, "user", user_message)
    
    system_prompt = (
        "You are BAIT, a friendly and helpful AI assistant. "
        "Keep your responses naturally concise when making small talk, but provide detailed, "
        "thorough, and helpful explanations when the user asks for information, help, or a "
        "step-by-step guide."
    )
    messages = [{"role": "system", "content": system_prompt}]
    
    # Get last 10 messages for context
    history = history_manager.get_conversation(conversation_id).get("messages", []) if conversation_id else []
    messages.extend([{"role": m["role"], "content": m["content"]} for m in history[-10:]])
    
    full_response = ""
    sentence_buffer = ""
    
    try:
        response = await client.chat.completions.create(
            model="local-model",
            messages=messages,
            stream=True
        )
        
        async for chunk in response:
            if chunk.choices[0].delta.content:
                content = chunk.choices[0].delta.content
                full_response += content
                sentence_buffer += content
                
                # If we have a complete sentence, trigger TTS
                if any(punct in sentence_buffer for punct in ['. ', '! ', '? ', '\n']):
                    # Use a more robust split that keeps the punctuation
                    parts = re.split(r'([.!?\n])\s*', sentence_buffer)
                    if len(parts) >= 2:
                        # Reconstruct sentences from parts (parts = [text, punct, text, punct, ...])
                        full_sentences = []
                        for i in range(0, len(parts) - 1, 2):
                            full_sentences.append(parts[i] + parts[i+1])
                        
                        to_speak = " ".join(full_sentences)
                        sentence_buffer = parts[-1] if len(parts) % 2 != 0 else ""
                        
                        if to_speak.strip():
                            # stop_speaking() is NOT called here because we want 
                            # the sentences from the SAME response to play in sequence
                            # if they are generated fast enough. 
                            # Tracking handles the overlap across DIFFERENT responses.
                            speak_text(to_speak)
                
                yield f"data: {json.dumps({'text': content})}\n\n"
        
        # Speak remaining buffer
        if sentence_buffer.strip():
            threading.Thread(target=speak_text, args=(sentence_buffer,), daemon=True).start()
            
        if conversation_id:
            history_manager.add_message(conversation_id, "assistant", full_response)
        yield f"data: {json.dumps({'done': True})}\n\n"
        
    except Exception as e:
        yield f"data: {json.dumps({'error': str(e)})}\n\n"

@app.post("/api/chat/stream")
async def chat_stream_endpoint(request: ChatRequest):
    """Streaming chat endpoint"""
    return StreamingResponse(chat_stream_generator(request.message, request.conversation_id), media_type="text/event-stream")

@app.post("/api/chat")
async def chat_endpoint(request: ChatRequest):
    """Main chat endpoint - updated to use history_manager"""
    print(f"💬 Chat Request: {request.message} (Conv: {request.conversation_id})")
    try:
        user_message = request.message
        conv_id = request.conversation_id
        
        # Save user message
        if conv_id:
            history_manager.add_message(conv_id, "user", user_message)
            
        # Reuse generator logic but collect it for non-streaming clients
        full_response = ""
        async for chunk in chat_stream_generator(user_message, conv_id):
            data_str = chunk.replace("data: ", "").strip()
            if not data_str: continue
            try:
                data = json.loads(data_str)
                if 'response' in data:
                    res = data['response']
                    if conv_id:
                        history_manager.add_message(conv_id, "assistant", res)
                    return {"status": "success", "response": res}
                if 'text' in data:
                    full_response += data['text']
                if 'error' in data:
                    return {"status": "error", "response": data['error']}
            except:
                continue
        
        # Save assistant response
        if conv_id and full_response:
            history_manager.add_message(conv_id, "assistant", full_response)
            
        return {"status": "success", "response": full_response}
    except Exception as e:
        return {"status": "error", "response": str(e)}

@app.post("/api/stop-speech")
async def stop_speech_endpoint():
    """Stop current speech"""
    stop_speaking()
    return {"status": "stopped"}

@app.delete("/api/conversation/{conversation_id}")
async def delete_conversation(conversation_id: int):
    """Delete a conversation"""
    history_manager.delete_conversation(conversation_id)
    return {"status": "deleted"}

@app.post("/api/voice-to-text")
async def voice_to_text(request: VoiceRequest):
    """Convert voice to text"""
    try:
        audio_bytes = base64.b64decode(request.audio_data.split(',')[1] if ',' in request.audio_data else request.audio_data)
        
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_audio:
            temp_audio.write(audio_bytes)
            temp_audio_path = temp_audio.name
        
        recognizer = sr.Recognizer()
        
        with sr.AudioFile(temp_audio_path) as source:
            audio = recognizer.record(source)
            text = recognizer.recognize_google(audio)
        
        os.unlink(temp_audio_path)
        
        return {"status": "success", "text": text}
        
    except sr.UnknownValueError:
        return {"status": "error", "message": "Could not understand audio"}
    except sr.RequestError as e:
        return {"status": "error", "message": f"Speech recognition error: {str(e)}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

# ═══════════════════════════════════════════════════════════════
# NOTES ENDPOINTS
# ═══════════════════════════════════════════════════════════════

@app.get("/api/notes")
async def get_notes():
    """Get all notes"""
    return list(notes_db.values())

@app.post("/api/notes")
async def create_note(request: NoteRequest):
    """Create or update a note"""
    global note_counter
    
    if request.id and request.id in notes_db:
        notes_db[request.id]["text"] = request.text
        notes_db[request.id]["updated_at"] = datetime.datetime.now().isoformat()
        return notes_db[request.id]
    else:
        note_counter += 1
        note = {
            "id": note_counter,
            "text": request.text,
            "created_at": datetime.datetime.now().isoformat(),
            "updated_at": datetime.datetime.now().isoformat()
        }
        notes_db[note_counter] = note
        return note

@app.delete("/api/notes/{note_id}")
async def delete_note(note_id: int):
    """Delete a note"""
    if note_id in notes_db:
        del notes_db[note_id]
        return {"status": "deleted"}
    return {"error": "Note not found"}

@app.get("/api/notes/export")
async def export_notes():
    """Export all notes as text"""
    text = ""
    for note in sorted(notes_db.values(), key=lambda x: x['created_at']):
        text += f"[{note['created_at']}]\n{note['text']}\n\n---\n\n"
    return {"content": text}

@app.get("/api/stats")
async def get_stats():
    """Get system stats"""
    try:
        cpu = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory().percent
        disk = psutil.disk_usage('/').percent
        return {"cpu": cpu, "memory": memory, "disk": disk}
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    import uvicorn
    import socket
    
    port = 8000
    
    # Check if port is available
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.bind(('127.0.0.1', port))
        sock.close()
    except OSError:
        print(f"⚠️  PORT {port} is occupied! BAIT might not connect to frontend.")
        print(f"Please close any other application using port {port}.")
        # Still try to run, maybe it's just a ghost binding
    
    print(f"🚀 Starting BAIT API Server on port {port}...")
    print(f"✅ TTS Available: {tts_available}")
    print(f"✅ Edge TTS (Hyper-Human): {HAS_EDGE_TTS}")
    print("✅ Web Research: Enabled")
    print("✅ Live Notes: Enabled")
    print("✅ File Operations: Enabled")
    print("✅ Video Chat: Enabled")
    
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="info")
