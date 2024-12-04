from flask import Flask, request, jsonify
import requests
import os
import json



app = Flask(__name__)



##Read data########
script_dir = os.path.dirname(os.path.abspath(__file__))
file_name = "instance_details.json"
file_path = None
for root, dirs, files in os.walk(script_dir):
    if file_name in files:
        file_path = os.path.join(root, file_name)
        break

if file_path:
    # Debugging output
    print(f"Found file at: {file_path}")

    # Read the JSON file
    with open(file_path, 'r') as file:
        instance_data = json.load(file)
    trusted_host_ip=instance_data["trusted_instance"]["PrivateIP"]

  
else:
    raise FileNotFoundError(f"{file_name} not found in {script_dir} or its subdirectories.")








# Trusted Host configuration
# trusted_host = "10.0.1.140"  # Update with the private IP of the Trusted Host instance
trusted_port = 8000          # Port where the Trusted Host application is running

@app.route('/write', methods=['POST'])
def write():
    data = request.get_json()
    if not data or not data.get("query"):
        return jsonify({"error": "Query is required"}), 400

    try:
        response = requests.post(f"http://{trusted_host_ip}:{trusted_port}/write", json=data)
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
        response = requests.get(f"http://{trusted_host_ip}:{trusted_port}/read/{strategy}", params={"query": query})
        return jsonify(response.json()), response.status_code
    except requests.RequestException as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)
