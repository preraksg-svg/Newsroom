import time
import requests
import subprocess
import os
import sys

PORT = 8000
BACKEND_URL = f"http://127.0.0.1:{PORT}/api/news"

def check_backend():
    try:
        r = requests.get(BACKEND_URL, timeout=5)
        return r.status_code == 200
    except Exception:
        return False

def check_process_running(script_name):
    try:
        # Check command line arguments using WMIC
        cmd = f'wmic process where "CommandLine like \'%{script_name}%\'" get ProcessId'
        output = subprocess.check_output(cmd, shell=True).decode('utf-8', errors='ignore')
        lines = [line.strip() for line in output.split('\n') if line.strip()]
        pids = []
        for line in lines[1:]:
            if line.isdigit() and int(line) != os.getpid():
                pids.append(int(line))
        return len(pids) > 0
    except Exception:
        # Default to True to avoid restart loops if wmic query fails
        return True

def kill_port_owner(port):
    try:
        cmd = f'netstat -ano | findstr :{port}'
        output = subprocess.check_output(cmd, shell=True).decode('utf-8', errors='ignore')
        for line in output.split('\n'):
            if "LISTENING" in line:
                parts = line.strip().split()
                if parts:
                    pid = parts[-1]
                    print(f"[WATCHDOG] Killing process {pid} owning port {port}")
                    subprocess.run(f"taskkill /f /pid {pid}", shell=True)
    except Exception as e:
        print(f"[WATCHDOG] Error killing port {port} owner: {e}")

def main():
    print("[WATCHDOG] Self-Healing Watchdog online (100% 24x7 active check)")
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    while True:
        try:
            # 1. Check backend
            if not check_backend():
                print("[WATCHDOG] Backend server is DOWN or unresponsive. Restoring...")
                kill_port_owner(PORT)
                backend_cmd = f'start "Zapway Backend" cmd /c "cd /d {project_root} && python -m backend.main"'
                subprocess.run(backend_cmd, shell=True)
                time.sleep(5)
            else:
                print("[WATCHDOG] Backend server is healthy.")

            # 2. Check workers
            if not check_process_running("run_workers.py"):
                print("[WATCHDOG] Worker engine (run_workers.py) is DOWN. Restoring...")
                workers_cmd = f'start "Zapway Workers" cmd /c "cd /d {project_root} && python run_workers.py"'
                subprocess.run(workers_cmd, shell=True)
                time.sleep(5)
            else:
                print("[WATCHDOG] Worker engine is healthy.")

        except Exception as e:
            print(f"[WATCHDOG] Error in watchdog check loop: {e}")

        time.sleep(30)

if __name__ == "__main__":
    main()
