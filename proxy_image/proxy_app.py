from flask import Flask, request, jsonify
import random
import subprocess
import mysql.connector
from mysql.connector import Error
import json
import os

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
    print(f"Found file at: {file_path}")

    # Read the JSON file
    with open(file_path, 'r') as file:
        instance_data = json.load(file)
    print("File loaded successfully.")
    print(json.dumps(instance_data, indent=4))
else:
    raise FileNotFoundError(f"{file_name} not found in {script_dir} or its subdirectories.")
# Database credentials
skill_user = "sakila_user"
password = "1234"

# Extract manager and worker nodes from the JSON data
manager_node = {
    "host": instance_data["mysql-manager"]["PrivateIP"],
    "user": skill_user,
    "password": password,
    "database": "sakila"
}

worker_nodes = [
    {
        "host": instance_data["mysql-worker-1"]["PrivateIP"],
        "user": skill_user,
        "password": password,
        "database": "sakila"
    },
    {
        "host": instance_data["mysql-worker-2"]["PrivateIP"],
        "user": skill_user,
        "password": password,
        "database": "sakila"
    }
]

def execute_query(node, query, is_write=False):
    try:
        print(f"Connecting to {node['host']} with query: {query}")
        connection = mysql.connector.connect(
            host=node["host"],
            user=node["user"],
            password=node["password"],
            database=node["database"]
        )
        cursor = connection.cursor()
        cursor.execute(query)
        
        if is_write:
            connection.commit()
            print("Write operation committed successfully.")
            return {"status": "success", "message": "Write operation completed"}
        else:
            results = cursor.fetchall()
            print(f"Query results: {results}")
            return {"status": "success", "data": results}
    except Error as e:
        print(f"Database Connection Error: {e}")
        return {"status": "error", "message": str(e)}
    finally:
        if 'connection' in locals() and connection.is_connected():
            cursor.close()
            connection.close()

# Ping a node to get latency
def ping_node(host):
    try:
        response = subprocess.run(["ping", "-c", "1", host], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if response.returncode == 0:
            output = response.stdout.decode()
            latency = float(output.split("time=")[1].split(" ms")[0])
            return latency
        return float("inf")
    except Exception as e:
        print(f"Error pinging {host}: {e}")
        return float("inf")

@app.route('/write', methods=['POST'])
def write_request():
    data = request.get_json()
    query = data.get("query", "")
    if not query:
        return jsonify({"error": "Query is required"}), 400

    # Forward write requests to manager
    result = execute_query(manager_node, query, is_write=True)

    if result["status"] == "error":
        return jsonify({"error": f"Failed to execute query on manager: {result['message']}"}), 500

    return jsonify({"message": result["message"]})


@app.route('/read/direct', methods=['GET'])
def read_direct():
    query = request.args.get("query", "")
    if not query:
        return jsonify({"error": "Query is required"}), 400

    # Directly forward to manager
    result = execute_query(manager_node, query)
    if result is None:
        return jsonify({"error": "Failed to execute query on manager"}), 500

    return jsonify({"result": result})

@app.route('/read/random', methods=['GET'])
def read_random():
    query = request.args.get("query", "")
    if not query:
        return jsonify({"error": "Query is required"}), 400

    # Randomly select a worker
    worker = random.choice(worker_nodes)
    result = execute_query(worker, query)
    if result is None:
        return jsonify({"error": "Failed to execute query on worker"}), 500

    return jsonify({"result": result})

@app.route('/read/customized', methods=['GET'])
def read_customized():
    query = request.args.get("query", "")
    if not query:
        return jsonify({"error": "Query is required"}), 400

    # Select worker with the lowest latency
    latencies = {worker["host"]: ping_node(worker["host"]) for worker in worker_nodes}
    best_worker = min(latencies, key=latencies.get)
    selected_worker = next(worker for worker in worker_nodes if worker["host"] == best_worker)

    result = execute_query(selected_worker, query)
    if result is None:
        return jsonify({"error": "Failed to execute query on worker"}), 500

    return jsonify({"result": result, "worker": best_worker, "latency": latencies[best_worker]})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)
