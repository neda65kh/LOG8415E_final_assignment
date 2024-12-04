import boto3
from botocore.exceptions import ClientError
import os
import stat
import json
import shutil
import paramiko
import json

# AWS clients for EC2 operations
ec2 = boto3.resource('ec2', region_name='us-east-1')
ec2_client = boto3.client('ec2', region_name='us-east-1')

# ============================
# 1. KEY PAIR MANAGEMENT
# ============================
key_name = 'my-key-pair'
key_file = f"./{key_name}.pem"

try:
    ec2_client.describe_key_pairs(KeyNames=[key_name])
    print(f"Key Pair '{key_name}' exists.")
    os.chmod(key_file, stat.S_IRUSR)  # Ensure proper permissions
except ClientError as e:
    if 'InvalidKeyPair.NotFound' in str(e):
        key_pair = ec2_client.create_key_pair(KeyName=key_name)
        with open(key_file, 'w') as file:
            file.write(key_pair['KeyMaterial'])
        print(f"Key Pair created and saved as {key_name}.pem")
        os.chmod(key_file, stat.S_IRUSR)  # Ensure proper permissions
    else:
        raise e

# ============================
# 2. CREATE VPC AND INTERNET GATEWAY
# ============================
response = ec2_client.create_vpc(CidrBlock='10.0.0.0/16')
vpc_id = response['Vpc']['VpcId']
print(f"VPC created: {vpc_id}")

ec2_client.create_tags(Resources=[vpc_id], Tags=[{'Key': 'Name', 'Value': 'MyVPC'}])

# Create and attach an Internet Gateway
igw_response = ec2_client.create_internet_gateway()
internet_gateway_id = igw_response['InternetGateway']['InternetGatewayId']
print(f"Internet Gateway created: {internet_gateway_id}")

ec2_client.attach_internet_gateway(VpcId=vpc_id, InternetGatewayId=internet_gateway_id)
print(f"Internet Gateway {internet_gateway_id} attached to VPC {vpc_id}.")

# Create a route table and add a route to the Internet Gateway
route_table_response = ec2_client.create_route_table(VpcId=vpc_id)
route_table_id = route_table_response['RouteTable']['RouteTableId']
print(f"Route Table created: {route_table_id}")

# Corrected: Accessing RouteTableId properly from the response
route_table_id = route_table_response['RouteTable']['RouteTableId']
print(f"Route Table created: {route_table_id}")

ec2_client.create_route(
    RouteTableId=route_table_id,
    DestinationCidrBlock='0.0.0.0/0',
    GatewayId=internet_gateway_id
)
print(f"Route to Internet Gateway added to Route Table {route_table_id}.")

# ============================
# 3. CREATE SUBNET
# ============================
response = ec2_client.create_subnet(CidrBlock='10.0.1.0/24', VpcId=vpc_id)
subnet_id = response['Subnet']['SubnetId']
print(f"Subnet created: {subnet_id}")

# Enable auto-assign public IPs for the subnet
ec2_client.modify_subnet_attribute(
    SubnetId=subnet_id,
    MapPublicIpOnLaunch={"Value": True}
)
print("Public IP assignment enabled for the subnet.")

# Associate the route table with the subnet
ec2_client.associate_route_table(RouteTableId=route_table_id, SubnetId=subnet_id)
print(f"Route Table {route_table_id} associated with Subnet {subnet_id}.")

# Check subnet IP availability
subnet_info = ec2_client.describe_subnets(SubnetIds=[subnet_id])
available_ips = subnet_info['Subnets'][0]['AvailableIpAddressCount']

if available_ips == 0:
    raise Exception(f"Subnet {subnet_id} has no available IP addresses!")
else:
    print(f"Subnet {subnet_id} has {available_ips} available IPs.")

# ============================
# 4. CREATE SECURITY GROUP
# ============================
response = ec2_client.create_security_group(
    GroupName='MySecurityGroup',
    Description='Allow SSH and HTTP',
    VpcId=vpc_id
)
security_group_id = response['GroupId']
print(f"Security Group created: {security_group_id}")

ec2_client.authorize_security_group_ingress(
    GroupId=security_group_id,
    IpPermissions=[
        {'IpProtocol': 'tcp', 'FromPort': 22, 'ToPort': 22, 'IpRanges': [{'CidrIp': '0.0.0.0/0'}]},
        {'IpProtocol': 'tcp', 'FromPort': 3306, 'ToPort': 3306, 'IpRanges': [{'CidrIp': '0.0.0.0/0'}]},
        {'IpProtocol': 'tcp', 'FromPort': 8000, 'ToPort': 8000, 'IpRanges': [{'CidrIp': '0.0.0.0/0'}]}
    ]
)

# ============================
# 5. AMI 
# ============================
ami_id = 'ami-0e86e20dae9224db8'

# ============================
# 6.1 INSTANCE LAUNCH FUNCTION
# ============================
def launch_instance(name, instance_type):
    response = ec2_client.run_instances(
        ImageId=ami_id,
        MinCount=1,
        MaxCount=1,
        InstanceType=instance_type,
        KeyName='my-key-pair',
        SubnetId=subnet_id,
        SecurityGroupIds=[security_group_id],
        TagSpecifications=[{
            'ResourceType': 'instance',
            'Tags': [{'Key': 'Name', 'Value': name}]
        }],
        # UserData=mysql_user_data_script
    )
    instance_id = response['Instances'][0]['InstanceId']
    print(f"Instance '{name}' launched with ID: {instance_id}")
    return instance_id

def wait_for_instance(instance_id):
    print(f"Waiting for instance {instance_id} to reach 'running' state...")
    instance = ec2.Instance(instance_id)
    instance.wait_until_running()
    instance.load()  # Refresh instance state
    print(f"Instance {instance_id} is now running.")
    
    return {
        "InstanceID": instance.id,
        "PublicIP": instance.public_ip_address,
        "PrivateIP": instance.private_ip_address
    }


def wait_for_instance(instance_id):
    print(f"Waiting for instance {instance_id} to reach 'running' state...")
    instance = ec2.Instance(instance_id)
    instance.wait_until_running()
    instance.load()  # Refresh instance state
    print(f"Instance {instance_id} is now running.")
    return {
        "InstanceID": instance.id,
        "PublicIP": instance.public_ip_address,
        "PrivateIP": instance.private_ip_address
    }

def launch_instance(name, instance_type):
    # Docker installation commands
    user_data_script = '''#!/bin/bash
sudo apt-get update -y
sudo apt-get install -y ca-certificates curl
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt-get update -y
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo docker run hello-world
'''

    response = ec2_client.run_instances(
        ImageId=ami_id,
        MinCount=1,
        MaxCount=1,
        InstanceType=instance_type,
        KeyName='my-key-pair',
        SubnetId=subnet_id,
        SecurityGroupIds=[security_group_id],
        TagSpecifications=[{
            'ResourceType': 'instance',
            'Tags': [{'Key': 'Name', 'Value': name}]
        }],
        UserData=user_data_script  # Add the user data script for Docker installation
    )
    instance_id = response['Instances'][0]['InstanceId']
    print(f"Instance '{name}' launched with ID: {instance_id}")
    return instance_id

# ============================
# 8.1 LAUNCH AND getting IPs of instances
# ============================




def get_instance_ips(json_file_path):
    """
    Reads the instance details JSON file and retrieves the public IP addresses
    for mysql-manager, mysql-worker-1, and mysql-worker-2.

    Args:
    json_file_path (str): Path to the JSON file.

    Returns:
    dict: A dictionary containing the public IPs for manager and workers.
    """
    with open(json_file_path, 'r') as file:
        data = json.load(file)
    return {
        "mysql_manager": data.get("mysql-manager", {}).get("PublicIP"),
        "mysql_worker_1": data.get("mysql-worker-1", {}).get("PublicIP"),
        "mysql_worker_2": data.get("mysql-worker-2", {}).get("PublicIP")
    }




if __name__ == "__main__":
    instances = {}
    # instances={}

    mysql_manager = launch_instance('mysql-manager', 't2.micro')
    instances['mysql-manager'] = wait_for_instance(mysql_manager)

    mysql_worker1 = launch_instance('mysql-worker-1', 't2.micro')
    instances['mysql-worker-1'] = wait_for_instance(mysql_worker1)

    mysql_worker2 = launch_instance('mysql-worker-2', 't2.micro')
    instances['mysql-worker-2'] = wait_for_instance(mysql_worker2)


    # Define the folder and file path
    folder_path = "sync_manager_worker"
    file_path = os.path.join(folder_path, "instance_details.json")

    # Ensure the folder exists
    os.makedirs(folder_path, exist_ok=True)

    # Save instance details to JSON
    with open(file_path, 'w') as json_file:
        json.dump(instances, json_file, indent=4)




    print(f"Instance details(SQL) saved to {file_path}")

    print("All resources created, and instances are configured with default public IPs.")

    # Define instance names
    instance_names = ["proxy_instance", "trusted_instance", "gatekeeper_instance"]
    


    for name in instance_names:
        print(f"Launching instance: {name}")
        instance_id = launch_instance(name, "t2.large")
        
        # Wait for instance to reach running state and get IPs
        instance_details = wait_for_instance(instance_id)
        
        # Save instance details (ID, PublicIP, PrivateIP)
        instances[name] = instance_details

    # Save instance details to a JSON file for proxy_image
    folder_path = "proxy_image"
    file_path = os.path.join(folder_path, "instance_details.json")
    os.makedirs(folder_path, exist_ok=True)
    
    with open(file_path, 'w') as json_file:
        json.dump(instances, json_file, indent=4)

    #Save JSON file to trusted_host directoy
    folder_path = "trusted_host"
    file_path = os.path.join(folder_path, "instance_details.json")
    os.makedirs(folder_path, exist_ok=True)
    
    with open(file_path, 'w') as json_file:
        json.dump(instances, json_file, indent=4)

    #Save JSON file to gatekeeper directoy
    folder_path = "gatekeeper"
    file_path = os.path.join(folder_path, "instance_details.json")
    os.makedirs(folder_path, exist_ok=True)
    
    with open(file_path, 'w') as json_file:
        json.dump(instances, json_file, indent=4)

    print(f"Instance details saved to {file_path}")

     #Save JSON file to benchmarking directoy
    folder_path = "benchmarking"
    file_path = os.path.join(folder_path, "instance_details.json")
    os.makedirs(folder_path, exist_ok=True)
    
    with open(file_path, 'w') as json_file:
        json.dump(instances, json_file, indent=4)

    print(f"Instance details saved to {file_path}")
