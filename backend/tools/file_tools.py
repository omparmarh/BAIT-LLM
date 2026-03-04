import os
from pathlib import Path

def write_file(filename: str, content: str):
    """Write or overwrite a file with specific content."""
    try:
        with open(filename, 'w') as f:
            f.write(content)
        return f"Successfully wrote to {filename}."
    except Exception as e:
        return f"Error writing file: {str(e)}"

def read_file(filename: str):
    """Read the content of a file."""
    try:
        with open(filename, 'r') as f:
            return f.read()
    except Exception as e:
        return f"Error reading file: {str(e)}"

def list_files(directory: str = "."):
    """List files in a directory."""
    try:
        files = os.listdir(directory)
        return ", ".join(files)
    except Exception as e:
        return f"Error listing files: {str(e)}"
