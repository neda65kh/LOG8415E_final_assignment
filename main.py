import subprocess
import sys

def run_scripts(script_paths):
    """
    Run multiple Python scripts sequentially, displaying output in real-time.

    Args:
    script_paths (list): List of paths to Python scripts to run.
    """
    for script in script_paths:
        try:
            print(f"Running script: {script}")
            # Run the script and allow real-time output to show in the console
            result = subprocess.run(["python3", script], check=True, stdout=sys.stdout, stderr=sys.stderr)
            print(f"Completed script: {script}\n")
        except subprocess.CalledProcessError as e:
            print(f"Error occurred while running {script}: {e}\n")

if __name__ == "__main__":
    # List of scripts to run
    scripts = [
       #1. create all  instances 
       "create_instances.py",

       #2.cofigure manger server
       "configure_manager.py",

       #3.cofigure workers
       "configure_workers.py",

       #4. proxy configuration
        "configure_proxy.py",
    
       #5.trusted_host configuration
        "configure_trusted_host.py",

        #6. gatekeeper configuration
        "configure_gatekeeper.py"

        #7. benchmarking
        # "benchmarking.py"

       

    
    ]

    run_scripts(scripts)
