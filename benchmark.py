import requests
import time
import json
import os

# Path to the `instance_details.json` file
INSTANCE_DETAILS_PATH = "gatekeeper/instance_details.json"

def get_gatekeeper_ip():
    """Reads the Gatekeeper's IP address from the instance_details.json file."""
    if not os.path.exists(INSTANCE_DETAILS_PATH):
        raise FileNotFoundError(f"The file {INSTANCE_DETAILS_PATH} does not exist.")
    
    with open(INSTANCE_DETAILS_PATH, "r") as file:
        data = json.load(file)
    
    gatekeeper_info = data.get("gatekeeper_instance", {})
    gatekeeper_ip = gatekeeper_info.get("PublicIP")
    
    if not gatekeeper_ip:
        raise ValueError("Gatekeeper PublicIP not found in the instance_details.json file.")
    
    return gatekeeper_ip

# Number of requests to send
NUM_REQUESTS = 1000

def send_request(url, payload=None):
    """Send a request and measure its response time."""
    start_time = time.time()
    try:
        if payload:
            response = requests.post(url, json=payload)
        else:
            response = requests.get(url)
        response.raise_for_status()
        end_time = time.time()
        return end_time - start_time
    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")
        if hasattr(e.response, 'text'):
            print(f"Response content: {e.response.text}")
        return None

def benchmark_requests(gatekeeper_ip):
    """Send read and write requests and log the results."""
    read_times = []
    write_times = []
    
    # URLs for read and write operations
    READ_URL = f"http://{gatekeeper_ip}:8000/read"
    WRITE_URL = f"http://{gatekeeper_ip}:8000/write"
    
    # Sending read requests
    print(f"Sending {NUM_REQUESTS} read requests to {READ_URL}...")
    for i in range(NUM_REQUESTS):
        response_time = send_request(READ_URL)
        if response_time:
            read_times.append(response_time)
    
    # Sending write requests
    print(f"Sending {NUM_REQUESTS} write requests to {WRITE_URL}...")
    for i in range(NUM_REQUESTS):
        payload = {"key": f"key{i}", "value": f"value{i}"}
        response_time = send_request(WRITE_URL, payload=payload)
        if response_time:
            write_times.append(response_time)
    
    # Log the results
    if read_times:
        print(f"Read Requests: Avg={sum(read_times)/len(read_times):.2f}s, Total={len(read_times)}")
    else:
        print("No successful read requests.")

    if write_times:
        print(f"Write Requests: Avg={sum(write_times)/len(write_times):.2f}s, Total={len(write_times)}")
    else:
        print("No successful write requests.")
    
    return read_times, write_times

if __name__ == "__main__":
    try:
        # Retrieve the Gatekeeper IP address
        gatekeeper_ip = get_gatekeeper_ip()
        print(f"Gatekeeper Public IP: {gatekeeper_ip}")
        
        # Perform benchmarking
        read_times, write_times = benchmark_requests(gatekeeper_ip)
    except Exception as e:
        print(f"Error: {e}")
