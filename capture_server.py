import subprocess
import time
import sys

# Start the server and redirect output
with open('server_debug.log', 'w') as f:
    process = subprocess.Popen(
        ['python', 'manage.py', 'runserver', '8001', '--noreload'],
        stdout=f,
        stderr=subprocess.STDOUT,
        cwd='c:/Users/User/Desktop/Registre_cancer/registre_cancer_n/Backend_registre_cancer'
    )
    print(f"Server started with PID {process.pid}. Waiting for 10 seconds...")
    time.sleep(10) # Enough time for startup and maybe a test request if I could trigger it
    # process.terminate() # Keep it running for now? No, better terminate to read log
    process.kill()

print("Server stopped. Log captured in server_debug.log")
