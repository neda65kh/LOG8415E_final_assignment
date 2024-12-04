import sys
import paramiko
import json
import os
import re
# Define the folder and file path
folder_path = "sync_manager_worker"
#ip of instances
file_path_ips = os.path.join(folder_path, "instance_details.json")
#binary informations
file_path_binary = os.path.join(folder_path, "binary_details.json")

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

def install_sakila(worker_ip):
    #Add Sakila data
    commands = [
        #install mysql
        'sudo apt update',
        'sudo apt install mysql-server -y',
        'sudo systemctl start mysql',
        'sudo systemctl enable mysql',
        'mysql --version',
        #configure my_sql
        "sudo sed -i 's/^bind-address.*/bind-address = 0.0.0.0/' /etc/mysql/mysql.conf.d/mysqld.cnf",
        "sudo systemctl restart mysql",
         # Create the replicate_user with a secure password
        "sudo mysql -e \"CREATE USER 'sakila_user'@'%' IDENTIFIED BY '1234';\"",
        # Grant privileges for database operations (adjust privileges as needed)
        "sudo mysql -e \"GRANT ALL PRIVILEGES ON *.* TO 'sakila_user'@'%';\"",
        # Apply the changes
        "sudo mysql -e \"FLUSH PRIVILEGES;\"",   
    ]
    #ssh connection
    ssh_exec_command(worker_ip,username , key_file, commands)
    commands = [
        # installing wget
        "sudo apt update",
        "sudo apt install wget -y",
        #get data of sakila
        "wget https://downloads.mysql.com/docs/sakila-db.tar.gz -O /tmp/sakila-db.tar.gz",
        "tar -xvzf /tmp/sakila-db.tar.gz -C /tmp",
        "sudo mysql -u sakila_user -p'1234' -e 'CREATE DATABASE sakila;'",
        "sudo mysql -u sakila_user -p'1234' sakila < /tmp/sakila-db/sakila-schema.sql",
        "sudo mysql -u sakila_user -p'1234' sakila < /tmp/sakila-db/sakila-data.sql",
        "sudo mysql -u sakila_user -p'1234' -e 'SHOW DATABASES;'"
    ]
    ssh_exec_command(worker_ip,username , key_file, commands)

def install_sysbench(worker_ip):
    commands = [
        "sudo apt-get update",
        "sudo apt-get install sysbench -y",
        #prepare database for Sysbench
        "sysbench /usr/share/sysbench/oltp_read_write.lua \
    --mysql-host=127.0.0.1 \
    --mysql-user=sakila_user \
    --mysql-password=1234 \
    --mysql-db=sakila \
    prepare",
    #test
    "sysbench /usr/share/sysbench/oltp_read_only.lua \
    --mysql-host=127.0.0.1 \
    --mysql-user=sakila_user \
    --mysql-password=1234 \
    --mysql-db=sakila \
    --time=60 \
    --threads=4 \
    run"
   
    ]
     #ssh connection
    ssh_exec_command(worker_ip,username , key_file, commands)


def sync_db(worker_ip,server_id):
    # Configure server-id and restart MySQL
    commands = [
        "sudo sed -i 's/^bind-address.*/bind-address = 0.0.0.0/' /etc/mysql/mysql.conf.d/mysqld.cnf",
        f"sudo sed -i '/^\\[mysqld\\]/a server-id = {server_id}' /etc/mysql/mysql.conf.d/mysqld.cnf",  # Ensure unique server-id
        "sudo sed -i '/^\\[mysqld\\]/a relay-log = /var/log/mysql/mysql-relay-bin' /etc/mysql/mysql.conf.d/mysqld.cnf",
        "sudo systemctl restart mysql",
    ]
    ssh_exec_command(worker_ip, username, key_file, commands)
     # Set up replication
    commands = [
        f"sudo mysql -u sakila_user -p'1234' -e \"CHANGE MASTER TO MASTER_HOST='{manager_private_ip}', MASTER_USER='sakila_user', MASTER_PASSWORD='1234', MASTER_LOG_FILE='{binary_file}', MASTER_LOG_POS={binary_position};\"",
        "sudo mysql -u sakila_user -p'1234' -e \"START SLAVE;\"",
        "sudo mysql -u sakila_user -p'1234' -e \"SHOW SLAVE STATUS\\G;\""
    ]
    ssh_exec_command(worker_ip, username, key_file, commands)

if __name__ == "__main__":
    #define varaibles
    #path of keypair
    key_file = "./my-key-pair.pem"
    username='ubuntu'

    ########################################################get ips
    # Ensure the JSON file exists and workers info is retrieved
    if os.path.exists(file_path_ips):
        with open(file_path_ips, 'r') as file:
            data = json.load(file)


        manager_info = data.get("mysql-manager", {})
        manager_private_ip = manager_info.get("PrivateIP", "Private IP not found")

        print(f"Manager Private IP: {manager_private_ip}")
        #data of workers
        worker1_info = data.get("mysql-worker-1", {})
        worker1_public_ip = worker1_info.get("PublicIP", "Public IP not found")
        worker1_private_ip = worker1_info.get("PrivateIP", "Private IP not found")


        worker2_info = data.get("mysql-worker-2", {})
        worker2_public_ip = worker2_info.get("PublicIP", "Public IP not found")
        worker2_private_ip = worker2_info.get("PrivateIP", "Private IP not found")
        print(f"Worker2 Public IP: {worker2_public_ip}")
        print(f"Worker2 Private IP: {worker2_public_ip}")
    else:
        print(f"Error: File {file_path_ips} does not exist.")
        sys.exit(1)

    # Ensure the binary details file exists and retrieve binary log info
    if os.path.exists(file_path_binary):
        with open(file_path_binary, 'r') as file:
            binary_data = json.load(file)

        # Access the 'File' and 'Position' fields
        binary_file = binary_data.get("File", "File not found")
        binary_position = binary_data.get("Position", "Position not found")

        print(f"Binary File: {binary_file}")
        print(f"Binary Position: {binary_position}")
    else:
        print(f"Error: File {file_path_binary} does not exist.")
        sys.exit(1)
    
    #install sakila
    install_sakila(worker1_public_ip)
    install_sakila(worker2_public_ip)
    
    #install sysbench 
    install_sysbench(worker1_public_ip)
    install_sysbench(worker2_public_ip)

    #sync databases
    sync_db(worker1_public_ip,2)
    sync_db(worker2_public_ip,3)
