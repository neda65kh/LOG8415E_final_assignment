# LOG8415E_final_assignment
# README.md

## Project Overview

This project demonstrates a MySQL-based distributed system using the Proxy, Gatekeeper, and Trusted Host patterns. The system is deployed across multiple EC2 instances, with each instance fulfilling a specific role.

---

## How to Run

1. **Install Prerequisites**
   - Ensure Python 3.9 and AWS CLI are installed.
   - Install required Python libraries:
     ```bash
     pip install boto3 flask mysql-connector-python requests
     ```
   - Have an SSH key pair (`my-key-pair.pem`) for EC2 access.

2. **Run the `main.py` Script**
   - This script orchestrates the setup by sequentially executing all other scripts.
   - Execute the script:
     ```bash
     python main.py
     ```



---

## Project Structure

- `create_instances.py`: Sets up EC2 instances and networking.
- `configure_manager.py`: Configures the MySQL Manager instance.
- `configure_workers.py`: Configures Worker nodes.
- `configure_proxy.py`: Deploys the Proxy application.
- `configure_trusted_host.py`: Deploys the Trusted Host application.
- `configure_gatekeeper.py`: Deploys the Gatekeeper application.
- `main.py`: Runs all scripts in sequence.

---

## License

This project is licensed under the MIT License.
