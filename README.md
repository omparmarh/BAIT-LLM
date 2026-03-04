# 🤖 BAIT-LLM — Hyper-Intelligent AI Desktop Assistant

**BAIT** (Brain-powered AI Terminal) is a powerful, fully-local AI assistant that runs on your own machine using LLM Studio. It combines a FastAPI backend with a React + Electron frontend to deliver a feature-rich, voice-enabled, agent-driven experience — completely offline.

---

## ✨ Features

| Feature | Description |
|--------|-------------|
| 🧠 **AI Agent Core** | Tool-calling agent with memory, reasoning, and multi-step task execution |
| 🎙️ **Voice I/O** | Speech-to-text input + hyper-human Edge TTS voice output |
| 💬 **Chat Interface** | Streaming chat UI with conversation history |
| 🌐 **Web Research** | Live web search via DuckDuckGo & Wikipedia |
| 📁 **File Manager** | Create, edit, open files via natural language commands |
| 🖥️ **Desktop Control** | Open/close apps, take screenshots, control system |
| 🎭 **AI Avatar** | Animated lip-sync avatar with emotion detection |
| 📝 **Live Notes** | Real-time note-taking panel |
| 📹 **Video Chat** | WebSocket-based video session support |
| 🧬 **Memory System** | Persistent conversation memory across sessions |
| 🔊 **Mood Detection** | Emotionally-aware AI responses |
| 🎬 **Browser Panel** | Built-in browser view within the app |

---

## 🏗️ Tech Stack

### Backend
- **Python** + **FastAPI** — REST API & WebSocket server
- **OpenAI-compatible API** — works with LM Studio (local LLMs)
- **Edge TTS** — Microsoft neural voice synthesis
- **SQLite** — persistent memory & history storage
- **BeautifulSoup** — web scraping for research
- **PyAutoGUI / psutil** — desktop automation & system stats

### Frontend
- **React 18** + **Vite** — fast, modern UI
- **Electron** — desktop app wrapper
- **Three.js / React Three Fiber** — 3D avatar rendering
- **Framer Motion** — smooth animations
- **WaveSurfer.js** — audio visualization

---

## 📁 Project Structure

```
BAIT_LLM/
├── api_server.py          # Main FastAPI server
├── database.py            # Database helpers
├── requirements.txt       # Python dependencies
├── package.json           # Node dependencies
├── vite.config.js         # Vite config
├── index.html             # App entry point
│
├── backend/               # Python backend modules
│   ├── agent_core.py      # Tool-calling AI agent
│   ├── memory_manager.py  # Persistent memory
│   ├── history_manager.py # Conversation history
│   ├── vector_store.py    # Semantic memory
│   ├── api_routes.py      # Extra API routes
│   └── tools/             # Agent tools
│       ├── web_tools.py
│       ├── file_tools.py
│       ├── media_tools.py
│       ├── system_tools.py
│       └── advanced_tools.py
│
├── src/                   # React frontend
│   ├── components/        # UI components
│   ├── pages/             # App pages
│   ├── hooks/             # Custom React hooks
│   ├── context/           # Theme & global state
│   ├── utils/             # API & config helpers
│   └── styles/            # Global CSS & themes
│
└── public/                # Electron main process
    ├── main.js
    └── preload.js
```

---

## 🚀 Getting Started

### Prerequisites
- Python 3.10+
- Node.js 18+
- [LM Studio](https://lmstudio.ai/) running locally on `http://localhost:1234`

---

### 1. Clone the Repository

```bash
git clone https://github.com/omparmarh/BAIT-LLM.git
cd BAIT-LLM
```

### 2. Set Up Python Backend

```bash
# Create virtual environment
python -m venv venv

# Activate it
# macOS/Linux:
source venv/bin/activate
# Windows:
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Configure Environment

Create a `.env` file in the root directory:

```env
LLM_API_BASE=http://localhost:1234/v1
LLM_API_KEY=lm-studio
```

> Make sure LM Studio is running with a model loaded before starting the backend.

### 4. Start the Backend

```bash
uvicorn api_server:app --host 0.0.0.0 --port 8000 --reload
```

### 5. Set Up & Start the Frontend

```bash
npm install
npm run dev        # Web UI at http://localhost:5173
# OR
npm start          # Launches Electron desktop app
```

---

## 🖥️ Platform Support

| Platform | Status |
|----------|--------|
| macOS | ✅ Fully supported |
| Windows | ✅ Fully supported |
| Linux | ⚠️ Partial support |

---

## 🔧 Quick Launch Scripts

| Script | Platform | Description |
|--------|----------|-------------|
| `BAIT_LAUNCHER.command` | macOS | One-click launcher |
| `START_BAIT.bat` | Windows | Quick start |
| `START_BAIT_ULTIMATE.bat` | Windows | Full-featured start |
| `install.sh` | macOS/Linux | Auto-install script |

---

## 📖 Documentation

- [`API_DOCS.md`](API_DOCS.md) — REST API reference
- [`SETUP_GUIDE.md`](SETUP_GUIDE.md) — Detailed setup instructions
- [`TESTING_GUIDE.md`](TESTING_GUIDE.md) — Testing & debugging guide
- [`README_MAC.md`](README_MAC.md) — macOS-specific setup

---

## 🤝 Contributing

Pull requests are welcome! For major changes, please open an issue first to discuss what you'd like to change.

---

## 📄 License

This project is open source. See [LICENSE](LICENSE) for details.

---

<p align="center">Built with ❤️ by <a href="https://github.com/omparmarh">omparmarh</a></p>
