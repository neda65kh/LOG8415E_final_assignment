

import sys
import paramiko
import json
import os
import re
# Define the folder and file path
folder_path = "sync_manager_worker"
file_path = os.path.join(folder_path, "instance_details.json")


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




def install_sakila():
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
    ssh_exec_command(manager_public_ip,username , key_file, commands)
    commands = [
            #installing wget
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
    ssh_exec_command(manager_public_ip,username , key_file, commands)

def install_sysbench():
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
    ssh_exec_command(manager_public_ip,username , key_file, commands)


def ssh_exec_command_configure_manger(ip_address, username, private_key_path, commands):
    """
    Executes a list of commands over SSH and saves 'File' and 'Position' values
    from the output of the last command into a JSON file.

    Args:
        ip_address (str): The public IP address of the EC2 instance.
        username (str): The SSH username (usually 'ubuntu').
        private_key_path (str): Path to the private key (.pem) used to authenticate the SSH connection.
        commands (list): A list of shell commands (str) to be executed on the remote EC2 instance.

    Returns:
        None
    """
    folder_path = "sync_manager_worker"
    file_path = os.path.join(folder_path, "binary_details.json")

    key = paramiko.RSAKey.from_private_key_file(private_key_path)
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(hostname=ip_address, username=username, pkey=key)

    file_position_output = None

    try:
        # Execute all commands
        for i, command in enumerate(commands):
            print(f"Executing command: {command}")
            stdin, stdout, stderr = client.exec_command(command, get_pty=True)
            stdout.channel.recv_exit_status()
            output = stdout.read().decode().strip()
            error = stderr.read().decode().strip()

            if error:
                print(f"Error for command '{command}': {error}")

            print(f"Output for command '{command}': {output}")

            # Parse output of the last command for 'File' and 'Position'
            if i == len(commands) - 1:
                lines = output.splitlines()

                # Remove warning and separator lines
                filtered_lines = [
                    line for line in lines if not line.startswith("mysql:") and not line.startswith("+")
                ]

                # Ensure valid output
                if len(filtered_lines) >= 2:  # Header and at least one data row
                    header = filtered_lines[0].strip()
                    data = filtered_lines[1].strip()
                    print("Parsed Header:", header)
                    print("Parsed Data:", data)
                    if "File" in header and "Position" in header:
                        columns = re.split(r'\s+', header)
                        values = re.split(r'\s+', data)
                        file_index = columns.index("File")
                        position_index = columns.index("Position")
                        file_position_output = {
                            "File": values[file_index],
                            "Position": int(values[position_index])
                        }

                        # Save to JSON file
                        os.makedirs(folder_path, exist_ok=True)  # Ensure folder exists
                        with open(file_path, 'w') as json_file:
                            json.dump(file_position_output, json_file, indent=4)
                        print(f"Binary log details saved to {file_path}")
    finally:
        client.close()

    return file_position_output

def selecet_master_db():
    # Step 1: Update MySQL configuration


    commands = [
        # Ensure MySQL listens on all interfaces
        "sudo sed -i 's/^bind-address.*/bind-address = 0.0.0.0/' /etc/mysql/mysql.conf.d/mysqld.cnf",
        "sudo sed -i '/^\\[mysqld\\]/a server-id = 1' /etc/mysql/mysql.conf.d/mysqld.cnf",
        "sudo sed -i '/^\\[mysqld\\]/a log_bin = /var/log/mysql/mysql-bin.log' /etc/mysql/mysql.conf.d/mysqld.cnf",
        "sudo sed -i '/^\\[mysqld\\]/a binlog_do_db = sakila' /etc/mysql/mysql.conf.d/mysqld.cnf",
        "sudo systemctl restart mysql",  # Restart MySQL to apply changes
    ]
     #ssh connection
    ssh_exec_command(manager_public_ip,username , key_file, commands)

    # Step 2: configure  replication user
    commands = [
 #####
    "sudo mysql -u sakila_user -p'1234' -e \"CREATE USER 'sakila_user'@'%' IDENTIFIED BY '1234';\"",
    "sudo mysql -u sakila_user -p'1234' -e \"ALTER USER 'sakila_user'@'%' IDENTIFIED WITH 'mysql_native_password' BY '1234';\"",
    "sudo mysql -u sakila_user -p'1234' -e \"GRANT REPLICATION SLAVE ON *.* TO 'sakila_user'@'%';\"",
    "sudo mysql -u sakila_user -p'1234' -e \"FLUSH PRIVILEGES;\"",
    "sudo mysql -u sakila_user -p'1234' -e \"SHOW MASTER STATUS;\""
 #####
    # "sudo mysql -u sakila_user -p'1234' -e \"ALTER USER 'sakila_user'@'%' IDENTIFIED WITH 'mysql_native_password' BY '1234';\"",
    # "sudo mysql -u sakila_user -p'1234' -e \"GRANT REPLICATION SLAVE ON *.* TO 'sakila_user'@'%';\"",
    # "sudo mysql -u sakila_user -p'1234' -e \"FLUSH PRIVILEGES;\"",
    # "sudo mysql -u sakila_user -p'1234' -e \"SHOW MASTER STATUS;\""
    ]
    #Step 3: Retrieve the binary log file and position
    ssh_exec_command_configure_manger(manager_public_ip,username , key_file, commands)



if __name__ == "__main__":
    #define varaibles
    #path of keypair
    key_file = "./my-key-pair.pem"
    username='ubuntu'
    # Ensure the JSON file exists and manager info is retrieved
    if os.path.exists(file_path):
        with open(file_path, 'r') as file:
            data = json.load(file)

        manager_info = data.get("mysql-manager", {})
        manager_public_ip = manager_info.get("PublicIP", "Public IP not found")
        manager_private_ip = manager_info.get("PrivateIP", "Private IP not found")

        print(f"Manager Public IP: {manager_public_ip}")
        print(f"Manager Private IP: {manager_private_ip}")
    else:
        print(f"Error: File {file_path} does not exist.")
        sys.exit(1)


    # Call the desired functions sequentially
    print("Installing Sakila database...")
    install_sakila()  # Install Sakila database

    print("Installing Sysbench...")
    install_sysbench()  # Install Sysbench

    print("Configuring manager as master database...")
    selecet_master_db()  # Configure manager as master database

    print("Manager configuration completed successfully.")