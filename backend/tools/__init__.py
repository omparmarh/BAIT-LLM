from .web_tools import web_search
from .system_tools import open_app, take_screenshot, list_apps
from .file_tools import write_file, read_file, list_files
from .advanced_tools import run_python_code, get_system_info
from .media_tools import play_youtube_music

# Define the tools dictionary for the agent
TOOLS = {
    "web_search": web_search,
    "open_app": open_app,
    "take_screenshot": take_screenshot,
    "list_apps": list_apps,
    "write_file": write_file,
    "read_file": read_file,
    "list_files": list_files,
    "run_python_code": run_python_code,
    "get_system_info": get_system_info,
    "play_youtube_music": play_youtube_music
}
