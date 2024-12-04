import sys
import paramiko
import json
import os
import re
from scp import SCPClient
import tarfile
import time
# Define the folder and file path
# folder_path_manager = "sync_manager_worker"
# #ip of instances
# file_path_ips = os.path.join(folder_path_manager, "instance_details.json")

#get proxy ip
folder_path_trusted = "trusted_host"
file_path_trusted = os.path.join(folder_path_trusted, "instance_details.json")




def ssh_exec_command(ip_address, username, private_key_path, commands):
    """
    Executes a list of commands over SSH on the specified EC2 instance.

    Args:
    ip_address (str): The public IP address of the EC2 instance.
    username (str): The SSH username (e.g., 'ubuntu').
    private_key_path (str): Path to the private key (.pem) used for SSH.
    commands (list): List of shell commands to execute on the remote instance.

    Returns:
    None
    """
    key = paramiko.RSAKey.from_private_key_file(private_key_path)
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(hostname=ip_address, username=username, pkey=key)
    
    for command in commands:
        print(f"Running command on {ip_address}: {command}")
        stdin, stdout, stderr = client.exec_command(command, get_pty=True)
        stdout.channel.recv_exit_status()
        print(stdout.read().decode())
        print(stderr.read().decode())
    
    client.close()



def transfer_file(ip_address, username, private_key_path, local_filepath, remote_filepath):
    """
    Transfers a file from the local machine to the specified EC2 instance using SCP (via Paramiko),
    with progress reporting.
    """
    # Check if local file exists
    if not os.path.exists(local_filepath):
        print(f"Local file {local_filepath} does not exist.")
        return
    
    # Load the private key
    key = paramiko.RSAKey.from_private_key_file(private_key_path)
    
    # Establish SSH connection
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(hostname=ip_address, username=username, pkey=key)

    # Use SCPClient to transfer the file with progress callback
    print(f"Transferring {local_filepath} to {remote_filepath} on {ip_address}...")
    try:
        def progress(filename, size, sent):
            progress_percentage = (sent / size) * 100
            print(f"{filename}: {progress_percentage:.2f}% completed.")

        with SCPClient(client.get_transport(), progress=progress) as scp:
            scp.put(local_filepath, remote_filepath)
            print("File transfer completed successfully.")
    except Exception as e:
        print(f"Failed to transfer file: {e}")
    finally:
        # Close SSH connection
        client.close()
    print(f"Local file exists: {os.path.exists(local_filepath)}")
    print(f"Local file path: {local_filepath}")
    print(f"Remote file path: {remote_filepath}")


def wait_for_ssh(ip_address, username, private_key_path, retries=10, delay=30):
    """
    Tries to establish an SSH connection to a given EC2 instance multiple times until successful or retries run out.

    Args:
    ip_address (str): The public IP address of the EC2 instance.
    username (str): The SSH username (usually 'ubuntu').
    private_key_path (str): Path to the private key (.pem) used to authenticate the SSH connection.
    retries (int): Number of retries before failing (default is 10).
    delay (int): Delay between retries in seconds (default is 30 seconds).

    Returns:
    bool: True if SSH connection is successful, False if all retries fail.
    """
    key = paramiko.RSAKey.from_private_key_file(private_key_path)
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    for attempt in range(retries):
        try:
            print(f"Attempting SSH connection to {ip_address} (Attempt {attempt+1}/{retries})...")
            client.connect(hostname=ip_address, username=username, pkey=key, timeout=10)
            client.close()
            print(f"SSH connection to {ip_address} successful!")
            return True
        except paramiko.ssh_exception.NoValidConnectionsError as e:
            print(f"SSH connection failed: {e}")
        except paramiko.AuthenticationException as e:
            print(f"SSH Authentication failed: {e}")
        except paramiko.SSHException as e:
            print(f"General SSH error: {e}")
        except Exception as e:
            print(f"Unexpected error: {e}")
        
        print(f"Waiting {delay} seconds before retrying...")
        time.sleep(delay)
    
    print(f"Unable to establish SSH connection to {ip_address} after {retries} attempts.")
    return False


def create_tar_gz(folder_path, tar_file_name):
    with tarfile.open(tar_file_name, "w:gz") as tar:
        tar.add(folder_path, arcname=os.path.basename(folder_path))
    print(f"Archive created: {tar_file_name}")



def run_docker(ip_address, user_name, private_key_path, docker_name):
    # Installing docker
    commands = [
#         'sudo apt-get update -y',
#         # 'sudo apt-get install -y python3-pip python3-venv',
#         #Install prerequisite packages for Docker
#         'sudo apt-get install -y ca-certificates curl',
#         #Add Docker’s GPG key
#         'sudo install -m 0755 -d /etc/apt/keyrings',
#         'sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc',
#         'sudo chmod a+r /etc/apt/keyrings/docker.asc',
#         # Add the Docker repository
#         'echo \
#   "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu \
#   $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
#   sudo tee /etc/apt/sources.list.d/docker.list > /dev/null',
#         # Update the apt package index again to include Docker’s repo
#         'sudo apt-get update -y',
#         # Install Docker Engine, CLI, and required plugins
#         'sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin',
        'sudo docker run hello-world',
    ]
    ssh_exec_command(ip_address, username, private_key_path, commands)
    
    #Build docker image
    temp= docker_name.strip().replace('.tar.gz', '')
    commands = [
       f"tar -xvzf /home/ubuntu/{docker_name} -C /home/ubuntu",
       "ls",
       f"cd /home/ubuntu/{temp} && sudo docker build -t {temp} . && sudo docker run -d -p 8000:8000 {temp}",
       "sudo docker ps -a"
    ]
    ssh_exec_command(ip_address, user_name, private_key_path, commands) 






if __name__ == "__main__":
    #define varaibles
    #path of keypair

     # Ensure the binary details file exists and retrieve binary log info
    if os.path.exists(file_path_trusted):
        with open(file_path_trusted, 'r') as file:
            data = json.load(file)


        # Access proxy informations
        trusted_info = data.get("trusted_instance", {})
        trusted_host_public_ip = trusted_info.get("PublicIP", "Public IP not found")
        trusted_host_private_ip = trusted_info.get("PrivateIP", "Private IP not found")

        print(f"trusted host Public IP: {trusted_host_public_ip}")
        print(f"trusted host Private IP: {trusted_host_private_ip}")
    
    else:
        print(f"Error: File {file_path_trusted} does not exist.")
        sys.exit(1)
    #################################################
        # Define paths and parameters

    tar_file_name = "trusted_host.tar.gz"
    username = "ubuntu"  # Default EC2 username
    private_key_path = "./my-key-pair.pem"  # Path to your private key
    remote_filepath = "/home/ubuntu/trusted_host.tar.gz"

 
    
    #stable for connection
    if not wait_for_ssh(trusted_host_public_ip, username, private_key_path):
        print(f"Failed to establish SSH connection to {trusted_host_public_ip}")
        

    #Create the tar.gz archive
    create_tar_gz(folder_path_trusted, tar_file_name)
    # local_path = "./sync_manager_worker/instance_details.json"
    local_path = f"./{tar_file_name}"
    # Transfer the archive to the manager
    transfer_file(trusted_host_public_ip , username, private_key_path, local_path , remote_filepath)

    run_docker(trusted_host_public_ip , username, private_key_path, tar_file_name)
