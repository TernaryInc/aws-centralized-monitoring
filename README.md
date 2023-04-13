# aws-centralized-monitoring

## Table of Contents
- [Instructions](#instructions)
- [Support](#support)

## Instructions
### Why use this script?
The primary reason to use this script is to enable centralized, multi-account monitoring in AWS. You may choose to do this via the AWS console ([AWS documentation](https://aws.amazon.com/blogs/aws/new-amazon-cloudwatch-cross-account-observability/)), but the process involves multiple steps that can be prone to human error. Additionally, this process must be repeated in each AWS region you wish to collect metrics in. This script will automate the process and deploy the necessary resources in each region you specify (or all AWS default regions) for a quick and seamless onboarding to AWS Centralized CloudWatch Monitoring.

### Alternative ways to achieve multi-account monitoring (and why this is better)
There are multiple ways to achieve centralized monitoring in AWS. If you do not need to use the CloudWatch APIs, you can set up a
multi-account dashboard in the CloudWatch console, but you'll have to manually select and repeat this process for relevant metrics and resources. The advantage to using this script is that it will enable you to centralize, collect and report on any (standard) AWS metric for any resource you have access to.

### Ongoing maintenance
By leveraging CloudFormation StackSets and AWS Organizations you greatly reduce your ongoing burden to maintain centralized monitoring. As you add and delete accounts in your organization, new Stacks creating links to your centralized sink will automatically be created and destroyed on a per-region, per-account basis.

### Prerequisites:
- [`Python3`](https://www.python.org/downloads/) (We're using 3.11)
- `Pip3` (Comes standard with Python > 3.4)
- Optional, but highly recommended `VirtualEnv`
  - `pip3 install virtualenv`
- AWS CLI Credentials for your management account

### Setup your environment
- If you have `virtualenv` installed:
  - `source scripts/env_setup.sh`
- If you don't have `virtualenv`:
  - `pip3 install -r requirements.txt`

### Run the script
- `./main.py --sink-name SINK-NAME --regions "region1,region2,region3" --profile AWS-CLI-PROFILE --organization ORGANIZATION --organization-unit ORGANIZATION-UNIT --excluded-accounts "accountID1,accountID2,accountID3"`
```
usage: main.py [-h] --organization ORGANIZATION --organization-unit ORGANIZATION_UNIT [--sink-name SINK_NAME] [--profile PROFILE] [--regions REGIONS] [--excluded-accounts EXCLUDED_ACCOUNTS]

options:
  -h, --help            show this help message and exit
  --organization ORGANIZATION
                        Unique identifier for your AWS Organization
  --organization-unit ORGANIZATION_UNIT
                        AWS Organization Unit that you want to centralize monitoring for
  --sink-name SINK_NAME
                        Human-friendly AWS Metric Sink Name, defaults to "Centralized-Monitoring"
  --profile PROFILE     AWS CLI Config Profile Name for the Management Account, uses your default AWS profile if not specified
  --regions REGIONS     [Optional] List of comma-separated regions to create a sink and StackSet in. If not specified, a Sink/StackSet will be created in all default AWS regions
  --excluded-accounts EXCLUDED_ACCOUNTS
                        [Optional] List of comma-separated accounts to exclude from centralized monitoring (ex. --exclude "12345678910,09876543210"). Must exclude suspended accounts
```
- `organization`:
  - Navigate to [Organizations](https://us-east-1.console.aws.amazon.com/organizations/v2/home/accounts), click on Root, and get the string starting with o- from your organization ARN
  - arn:aws:organizations::01234567890:root/o-oooo1oo1oo/r-root -> o-oooo1oo1oo
- `organization-unit`:
  - We recommend root (arn:aws:organizations::01234567890:root/o-oooo1oo1oo/r-root -> r-root)
  - Can also be a sub-ou (arn:aws:organizations::01234567890:root/o-oooo1oo1oo/ou-root-ooooo1oo -> ou-root-ooooo1oo)

### Verify your resources are configured and your stack instances are created as intended

### Tear down your environment
- Only if using `virtualenv`: 
  - `source scripts/env_teardown.sh`

## Support

We've intended to build the subset of functionality that we need at Ternary into the AWS Centralized Monitoring scripts. Contributions are always welcome; see [Contributing](contributing.md).