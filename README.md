# AWS Ollama
This project will set up a test EC2 instance running [Ollama](https://ollama.com/)
on AWS with a publicly accessible endpoint. It enables testing of large language models (LLMs)
and the Ollama API in a controlled environment.

**Note:** This project is intended for testing purposes only and is NOT suitable for production use.

## Install Models
The project will install the following models on the Ollama instance:
* mistral
* llama3.1:8b

## Prerequisites

### Domain Ownership
You will need a domain that you control for this setup. This project assumes the domain is already
registered and managed under Route 53. If you don’t already have a domain, you can acquire one
directly through AWS by following the guide below:

[Registering a domain with Route 53](https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/domain-register.html) 

### AWS Route 53 Hosted Zone
Before deploying the project, you must configure a hosted zone in Route 53. 
This hosted zone is necessary to manage the DNS records for your domain and any subdomains,
such as the one where the Ollama instance will be hosted.

This hosted zone setup is a one-time operation and is not automated by the project scripts.
To create a public hosted zone, follow this AWS guide:

[Creating a Public Hosted Zone in Route 53](https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/CreatingHostedZone.html) 

Once created, you will need the **Hosted Zone ID** and **domain name** for the deployment.

### Getting the Project Code
To start, clone the project code to your local environment:
```bash
git clone git@github.com:mattporritt/aws_ollama.git
```

### Dependency Installation
Next we need to make sure we have the required libraries locally:
```bash
cd aws_ollama
sudo pip3 install -r requirements.txt
```
This will ensure that the necessary libraries are installed, including boto3, python-dotenv, and other dependencies used to interact with AWS.


### Credential Setup
The project uses an .env file to manage credentials.
These are used for testing, development and setting up the project
environments. You will need to create one of these files by using the
provided template.

Copy the `.env-template` file in the root of the folder to `.env`.
Replace the values in the file with your real credentials.

You will need to have an AWS API user with administrator access and
generate a API Key ID and a API Secret Key for this user,
see: https://docs.aws.amazon.com/IAM/latest/UserGuide/id_users_create.html 
for information on how to do this.

## Deployment

### Build Stack

To build the stack run the following command (it assumes credentials in the
.env file):
```bash
python3 cli/build_stack.py \
--region ap-southeast-2 \
--stack_name test-ollama \
--instance_type t2.micro \
--hosted_zone_id Z06443053GNXEEQBFY3MD \
--hosted_zone_name yourdomain.com \
--keypair_name MyGeneratedKeyPair \
--keypair_save_path /path/to/save/key \
--basic_auth_username username \
--basic_auth_password password
```
The above command will create a CloudFormation stack with the name `test-ollama`.
These are the minimum required parameters to build the stack.

#### Command details
For a full list of parameters and their descriptions run:
```bash
python3 cli/build_stack.py --help
```
Command Details:
* **--region:** The AWS region to deploy the stack (e.g., ap-southeast-2 for Sydney).
* **--stack_name:** The name of the CloudFormation stack (e.g., test-ollama).
* **--instance_type:** The type of EC2 instance to launch (e.g., t2.micro).
* **--hosted_zone_id:** The Hosted Zone ID from Route 53.
* **--hosted_zone_name:** Your domain name (e.g., yourdomain.com).
* **--keypair_name:** The name of the EC2 key pair for SSH access (optional; if not provided, one will be generated).
* **--keypair_save_path:** The path where the generated key pair will be saved locally.
* **--basic_auth_username:** The username for basic authentication to protect access to Ollama.
* **--basic_auth_password:** The password for basic authentication.

The command will output various pieces of information including about
the created stack, including the command to SSH into the created instance.
The web address of the Ollama instance will also be output.

#### Build Output

After running the command, you will see output similar to the following, showing the key pair creation,
stack creation progress, and useful connection details:
```bash
Key pair test-ollama-2024090816-keypair created and private key saved to ./test-ollama-2024090816-keypair.pem
Creating stack 'test-ollama'...
Stack status: CREATE_IN_PROGRESS... waiting
Stack status: CREATE_IN_PROGRESS... waiting
Stack create_complete.
RegionOutput: ap-southeast-2
SSHKeyPairName: test-ollama-2024090816-keypair
InstanceId: i-00d72c22f9e08776d
PublicIP: 13.211.140.24
SSH command: ssh -i ./test-ollama-2024090816-keypair.pem ubuntu@13.211.140.24
Web address: https://test-ollama.yourdomain.com
```
**NOTE:** The stack creation process can take several minutes to complete, and some setup tasks may
continue on the EC2 instance after the stack is marked as complete.
Examining the creation log once ssh'd into the instance is recommended and will provide status of the final
set up steps.
```bash
tail -f /var/log/user-data.log
```

### Basic Authentication
The Ollama instance is protected by basic authentication.
The username and password are defined when the stack is built.

## Testing
The instance can be tested with the following command:
```bash
time curl -v -u username:password -X POST https://test-ollama.yourdomain.com/api/generate -d '{
  "model": "mistral",
  "prompt":"write 50 words on ww2",
  "stream": false,
  "system": "prefix all responses with the words: TEST TEST TEST"
 }'
```

## SSH Access
To SSH into the instance, use the command provided in the output:
```bash
ssh -i ./test-ollama-2024090816-keypair.pem ubuntu@13.211.140.24
```
Once connected, you can access the Ollama instance and install additional models or make changes as needed.
