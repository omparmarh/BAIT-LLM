import subprocess
import os

def run_python_code(code: str):
    """Execute python code and return output."""
    try:
        temp_file = "/tmp/agent_exec.py"
        with open(temp_file, "w") as f:
            f.write(code)
        
        result = subprocess.run(["python3", temp_file], capture_output=True, text=True, timeout=10)
        return f"Output:\n{result.stdout}\nErrors:\n{result.stderr}"
    except Exception as e:
        return f"Execution error: {str(e)}"

def get_system_info():
    """Get basic system information (CPU, RAM)."""
    try:
        cpu = subprocess.check_output(["sysctl", "-n", "machdep.cpu.brand_string"]).decode().strip()
        mem = subprocess.check_output(["sysctl", "-n", "hw.memsize"]).decode().strip()
        ram_gb = int(mem) / (1024**3)
        return f"CPU: {cpu}, RAM: {ram_gb:.2f} GB"
    except Exception as e:
        return f"Error getting sys info: {str(e)}"
