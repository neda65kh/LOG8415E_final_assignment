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
        return end_time - start_time, response.json() if response.content else None
    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")
        if hasattr(e, 'response') and e.response:
            print(f"Response content: {e.response.text}")
        return None, None

def benchmark_requests(gatekeeper_ip):
    """Send read and write requests and log the results."""
    read_times = []
    write_times = []
    
    # URLs for read and write operations
    WRITE_URL = f"http://{gatekeeper_ip}:8000/write"
    READ_URL_DIRECT = f"http://{gatekeeper_ip}:8000/read/direct"
    READ_URL_RANDOM = f"http://{gatekeeper_ip}:8000/read/random"
    READ_URL_CUSTOMIZED = f"http://{gatekeeper_ip}:8000/read/customized"
    
    # Sending write requests
    print(f"Sending {NUM_REQUESTS} write requests to {WRITE_URL}...")
    for i in range(NUM_REQUESTS):
        payload = {
            "query": f"INSERT INTO actor (first_name, last_name, last_update) VALUES ('Name{i}', 'Surname{i}', NOW());"
        }
        response_time, response_data = send_request(WRITE_URL, payload=payload)
        if response_time:
            write_times.append(response_time)
            print(f"Write #{i + 1}: Time={response_time:.2f}s, Response={response_data}")
    
    # Sending read requests (direct)
    print(f"\nSending {NUM_REQUESTS} direct read requests to {READ_URL_DIRECT}...")
    for i in range(NUM_REQUESTS):
        query_param = {"query": f"SELECT * FROM actor WHERE first_name='Name{i}';"}
        response_time, response_data = send_request(f"{READ_URL_DIRECT}?query={query_param['query']}")
        if response_time:
            read_times.append(response_time)
            print(f"Read Direct #{i + 1}: Time={response_time:.2f}s, Response={response_data}")
    
    # Sending read requests (random)
    print(f"\nSending {NUM_REQUESTS} random read requests to {READ_URL_RANDOM}...")
    for i in range(NUM_REQUESTS):
        query_param = {"query": f"SELECT * FROM actor WHERE first_name='Name{i}';"}
        response_time, response_data = send_request(f"{READ_URL_RANDOM}?query={query_param['query']}")
        if response_time:
            read_times.append(response_time)
            print(f"Read Random #{i + 1}: Time={response_time:.2f}s, Response={response_data}")
    
    # Sending read requests (customized)
    print(f"\nSending {NUM_REQUESTS} customized read requests to {READ_URL_CUSTOMIZED}...")
    for i in range(NUM_REQUESTS):
        query_param = {"query": f"SELECT * FROM actor WHERE first_name='Name{i}';"}
        response_time, response_data = send_request(f"{READ_URL_CUSTOMIZED}?query={query_param['query']}")
        if response_time:
            read_times.append(response_time)
            print(f"Read Customized #{i + 1}: Time={response_time:.2f}s, Response={response_data}")
    
    # Log the results
    if write_times:
        avg_write = sum(write_times) / len(write_times)
        print(f"\nWrite Requests: Avg={avg_write:.2f}s, Total={len(write_times)}")
    else:
        print("No successful write requests.")

    if read_times:
        avg_read = sum(read_times) / len(read_times)
        print(f"Read Requests: Avg={avg_read:.2f}s, Total={len(read_times)}")
    else:
        print("No successful read requests.")
    
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