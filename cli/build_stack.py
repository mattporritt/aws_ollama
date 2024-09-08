# ==============================================================================
#
# This file is part of aws_ollama.
#
# aws_ollama is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# aws_ollama is distributed WITHOUT ANY WARRANTY:
# without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this software. If not, see <http://www.gnu.org/licenses/>.
# ==============================================================================

# ==============================================================================
#
# @author Matthew Porritt
# @copyright  2024 onwards Matthew Porritt (matt.porritt@moodle.com)
# @license    http://www.gnu.org/copyleft/gpl.html GNU GPL v3 or later
# ==============================================================================

# Import necessary libraries.
import argparse
import os
from dotenv import load_dotenv  # For loading environment variables from a .env file
from datetime import datetime  # For generating a timestamp for keypair naming
from utils.stack import (deploy_stack, init_session)  # Import helper functions

# Load environment variables from .env file if it exists.
load_dotenv(verbose=True)

# Module-level variable for the CloudFormation template file path.
STACK_TEMPLATE_FILE = './templates/stack.yaml'

# ==============================================================================
# Function: get_stack_outputs
# Purpose: Queries an existing CloudFormation stack by its name and retrieves the stack's outputs.
# Inputs:
#   - session: A Boto3 session object.
#   - stack_name: The name of the CloudFormation stack.
# Outputs:
#   - A dictionary of stack outputs if the stack exists; otherwise, None.
# ==============================================================================
def get_stack_outputs(session, stack_name):
    cloudformation = session.client('cloudformation')
    try:
        response = cloudformation.describe_stacks(StackName=stack_name)
        stacks = response['Stacks']
        if stacks:
            outputs = {output['OutputKey']: output['OutputValue'] for output in stacks[0]['Outputs']}
            return outputs
    except cloudformation.exceptions.ClientError as e:
        print(f"Error querying stack: {e}")
        return None

# ==============================================================================
# Function: create_keypair
# Purpose: Creates an EC2 Key Pair, saves the private key locally, and returns the keypair name.
# Inputs:
#   - session: A Boto3 session object.
#   - keypair_name: The name of the EC2 Key Pair to create.
#   - save_path: The local path where the private key will be saved.
# Outputs:
#   - The key pair name and the path where the private key was saved.
# ==============================================================================
def create_keypair(session, keypair_name, save_path):
    ec2_client = session.client('ec2')
    try:
        response = ec2_client.create_key_pair(KeyName=keypair_name)
        private_key = response['KeyMaterial']

        # Save the private key locally in a .pem file.
        key_file_path = f"{save_path}/{keypair_name}.pem"
        with open(key_file_path, 'w') as key_file:
            key_file.write(private_key)

        # Set file permissions to read-only for the owner (SSH requirement).
        os.chmod(key_file_path, 0o400)

        print(f"Key pair {keypair_name} created and private key saved to {key_file_path}")
        return keypair_name, key_file_path
    except ec2_client.exceptions.ClientError as e:
        print(f"Error creating keypair: {e}")
        return None

# ==============================================================================
# Function: generate_keypair_name
# Purpose: Generates a default EC2 key pair name based on the stack name and current date.
# Inputs:
#   - stack_name: The name of the CloudFormation stack.
# Outputs:
#   - A generated key pair name combining the stack name and timestamp.
# ==============================================================================
def generate_keypair_name(stack_name):
    current_date = datetime.now().strftime('%Y%m%d%H')  # Include current date and hour
    return f"{stack_name}-{current_date}-keypair"

# ==============================================================================
# Function: main
# Purpose: The main function that orchestrates the stack creation process.
# Inputs:
#   - Command-line arguments for AWS credentials, region, stack details, key pair info, etc.
# Actions:
#   - Creates an EC2 key pair if not provided, deploys a CloudFormation stack, and prints
#     SSH and web access details after the stack creation.
# ==============================================================================
def main():
    # Parse command-line arguments.
    parser = argparse.ArgumentParser(description='Create an AWS CloudFormation Stack.')
    parser.add_argument('--access_key', help='AWS Access Key ID')
    parser.add_argument('--secret_key', help='AWS Secret Access Key')
    parser.add_argument('--region', required=True, help='AWS Region')
    parser.add_argument('--stack_name', required=True, help='Name of the CloudFormation Stack')
    parser.add_argument('--instance_type', required=True, help='Instance type for the EC2 instance')
    parser.add_argument('--hosted_zone_id', required=True, help='Hosted Zone ID for the website')
    parser.add_argument('--hosted_zone_name', required=True, help='Hosted Zone Name for the website')
    parser.add_argument('--basic_auth_username', required=True, help='Basic Auth username')
    parser.add_argument('--basic_auth_password', required=True, help='Basic Auth password')
    parser.add_argument('--keypair_name', help='The name for the EC2 Key Pair (optional)')
    parser.add_argument('--keypair_save_path', default='.', help='Path to save the private key file locally')

    args = parser.parse_args()

    # Use credentials from the .env file or command-line arguments.
    aws_access_key_id = args.access_key or os.getenv('AWS_ACCESS_KEY_ID')
    aws_secret_access_key = args.secret_key or os.getenv('AWS_SECRET_ACCESS_KEY')
    aws_region = args.region or os.getenv('AWS_REGION')

    # Ensure AWS credentials are provided.
    if not (aws_access_key_id and aws_secret_access_key):
        raise ValueError("AWS credentials must be provided either through CLI or .env file")

    # Initialize a Boto3 session for AWS API calls.
    session = init_session(aws_access_key_id, aws_secret_access_key, aws_region)

    # Generate the keypair name if it's not provided.
    keypair_name = args.keypair_name or generate_keypair_name(args.stack_name)

    # Create EC2 Key Pair and save it locally.
    created_keypair_name, created_keypair_path = create_keypair(session, keypair_name, args.keypair_save_path)
    if not created_keypair_name:
        raise RuntimeError("Key pair creation failed.")

    # Define parameters for the CloudFormation stack.
    template_parameters = [
        {'ParameterKey': 'Region', 'ParameterValue': args.region},
        {'ParameterKey': 'HostedZoneId', 'ParameterValue': args.hosted_zone_id},
        {'ParameterKey': 'HostedZoneName', 'ParameterValue': args.hosted_zone_name},
        {'ParameterKey': 'InstanceType', 'ParameterValue': args.instance_type},
        {'ParameterKey': 'KeyPairName', 'ParameterValue': created_keypair_name},
        {'ParameterKey': 'SubdomainName', 'ParameterValue': args.stack_name},  # Use stack name as subdomain.
        {'ParameterKey': 'BasicAuthUser', 'ParameterValue': args.basic_auth_username},
        {'ParameterKey': 'BasicAuthPassword', 'ParameterValue': args.basic_auth_password}
    ]

    # Deploy the CloudFormation stack using the template and parameters.
    stack_outputs = deploy_stack(
        session,
        args.stack_name,
        STACK_TEMPLATE_FILE,
        template_parameters
    )

    # If the stack outputs are available, generate and print the SSH command and web address.
    if stack_outputs:
        instance_ip = stack_outputs.get('PublicIP')
        if instance_ip:
            ssh_command = f"ssh -i {created_keypair_path} ubuntu@{instance_ip}"
            print(f"SSH command: {ssh_command}")
            print(f"Web address: https://{args.stack_name}.{args.hosted_zone_name}")


# Entry point for the script.
if __name__ == '__main__':
    main()
