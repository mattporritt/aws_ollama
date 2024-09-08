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

import boto3
import time
from botocore.exceptions import ClientError


def read_template_file(file_path):
    """
    Reads a file and returns its contents.

    :param file_path: Path to the file to read
    :return: Contents of the file
    """
    with open(file_path, 'r') as file:
        return file.read()

def deploy_cloudformation_stack(cloudformation_client, stack_name, template_body, parameters):
    """
    Deploys a CloudFormation stack. It creates a new stack or updates an existing one.

    :param cloudformation_client: Boto3 CloudFormation client object
    :param stack_name: Name of the stack to deploy
    :param template_body: CloudFormation template content
    :param parameters: Parameters for the CloudFormation template
    :return: Stack ID if successful, None otherwise
    """
    if does_stack_exist(cloudformation_client, stack_name):
        try:
            print(f"Updating stack '{stack_name}'...")
            response = cloudformation_client.update_stack(
                StackName=stack_name,
                TemplateBody=template_body,
                Parameters=parameters,
                Capabilities=['CAPABILITY_IAM', 'CAPABILITY_NAMED_IAM'],
            )
            return response['StackId']
        except ClientError as e:
            if e.response['Error']['Code'] == 'ValidationError' and 'No updates are to be performed' in str(e):
                print("No updates to perform.")
                return None
            print(f"Error updating stack: {e}")
            return None
    else:
        try:
            print(f"Creating stack '{stack_name}'...")
            response = cloudformation_client.create_stack(
                StackName=stack_name,
                TemplateBody=template_body,
                Parameters=parameters,
                Capabilities=['CAPABILITY_IAM', 'CAPABILITY_NAMED_IAM'],
            )
            return response['StackId']
        except ClientError as e:
            print(f"Error creating stack: {e}")
            return None

def wait_for_stack_completion(cloudformation_client, stack_id):
    """
    Waits for CloudFormation stack creation or update to complete, checking the stack's status periodically.

    :param cloudformation_client: Boto3 CloudFormation client object
    :param stack_id: ID of the stack to check.
    """
    while True:
        response = cloudformation_client.describe_stacks(StackName=stack_id)
        stack_status = response['Stacks'][0]['StackStatus']

        if stack_status in ['CREATE_COMPLETE', 'UPDATE_COMPLETE']:
            print(f"Stack {stack_status.lower()}.")
            break
        elif 'FAILED' in stack_status or stack_status in ['ROLLBACK_COMPLETE', 'UPDATE_ROLLBACK_COMPLETE']:
            print(f"Stack {stack_status.lower()}: operation failed.")
            break

        print(f"Stack status: {stack_status}... waiting")
        time.sleep(10)  # Wait for 10 seconds before checking again.


def does_stack_exist(cloudformation_client, stack_name):
    """
    Checks if a CloudFormation stack exists.

    :param cloudformation_client: Boto3 CloudFormation client object
    :param stack_name: Name of the stack to check
    :return: True if the stack exists, False otherwise
    """
    try:
        cloudformation_client.describe_stacks(StackName=stack_name)
        return True
    except ClientError as e:
        if e.response['Error']['Code'] == 'ValidationError':
            return False
        raise  # Re-raise the exception if it's not a ValidationError.


def get_stack_outputs(cloudformation_client, stack_name):
    """
    Retrieves the outputs of a CloudFormation stack.

    :param cloudformation_client: Boto3 CloudFormation client object
    :param stack_name: Name of the CloudFormation stack
    :return: Dictionary of output values
    """
    try:
        response = cloudformation_client.describe_stacks(StackName=stack_name)
        outputs = response['Stacks'][0]['Outputs']
        output_dict = {}
        for output in outputs:
            print(f"{output['OutputKey']}: {output['OutputValue']}")
            output_dict[output['OutputKey']] = output['OutputValue']

        return output_dict
    except ClientError as e:
        print(f"Error retrieving stack outputs: {e}")
        return None

def init_session(aws_access_key_id, aws_secret_access_key, region):
    """
    Initializes a Boto3 session using the provided credentials.

    :param aws_access_key_id:
    :param aws_secret_access_key:
    :param region:
    :return:
    """
    return boto3.Session(
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key,
        region_name=region
    )


def deploy_stack(session, stack_name, template_file, parameters):
    """
    Deploys a CloudFormation stack using the specified template and parameters.
    :param session: Boto3 session object
    :param stack_name: Name of the stack to deploy
    :param template_file: Cloudformation template file
    :param parameters: Parameters for the CloudFormation template
    :return:
    """
    cloudformation_client = session.client('cloudformation')
    template_body = read_template_file(template_file)
    stack_id = deploy_cloudformation_stack(cloudformation_client, stack_name, template_body, parameters)
    if stack_id:
        wait_for_stack_completion(cloudformation_client, stack_id)
        return get_stack_outputs(cloudformation_client, stack_name)
    return None
