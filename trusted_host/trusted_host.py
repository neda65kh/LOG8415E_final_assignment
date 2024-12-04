from flask import Flask, request, jsonify
import requests
import os
import json
import sys
app = Flask(__name__)



# Starting search directory (e.g., the script's directory)
script_dir = os.path.dirname(os.path.abspath(__file__))

# Search for the file recursively
file_name = "instance_details.json"
file_path = None

for root, dirs, files in os.walk(script_dir):
    if file_name in files:
        file_path = os.path.join(root, file_name)
        break

if file_path:
    # Debugging output
    # print(f"Found file at: {file_path}")

    # Read the JSON file
    with open(file_path, 'r') as file:
        instance_data = json.load(file)
    print("File loaded successfully.")
    proxy_private_ip=instance_data["proxy_instance"]["PrivateIP"]
    gatekeeper_private_ip=instance_data["gatekeeper_instance"]["PrivateIP"]
    
    print(json.dumps(instance_data, indent=4))
else:
    raise FileNotFoundError(f"{file_name} not found in {script_dir} or its subdirectories.")



# Proxy instance configuration
# proxy_host = "10.0.1.160"  # Update with the private IP of the proxy instance
proxy_port = 8000          # Port where the proxy application is running


@app.route('/write', methods=['POST'])
def write():
    data = request.get_json()
    try:
        response = requests.post(f"http://{proxy_private_ip}:{proxy_port}/write", json=data)
        return jsonify(response.json()), response.status_code
    except requests.RequestException as e:
        return jsonify({"error": str(e)}), 500

@app.route('/read/<strategy>', methods=['GET'])
def read(strategy):
    query = request.args.get("query", "")
    if not query:
        return jsonify({"error": "Query is required"}), 400

    if strategy not in ['direct', 'random', 'customized']:
        return jsonify({"error": "Invalid read strategy"}), 400

    try:
        response = requests.get(f"http://{proxy_private_ip}:{proxy_port}/read/{strategy}", params={"query": query})
        return jsonify(response.json()), response.status_code
    except requests.RequestException as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)
