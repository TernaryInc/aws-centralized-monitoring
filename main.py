#!/usr/bin/env python3
import argparse

import link_sink_utils.util as util

# Set up parser to accept CLI flags
parser = argparse.ArgumentParser(add_help=True)
parser.add_argument('--organization', help="Unique identifier for your AWS Organization", type=str, required=True)
parser.add_argument('--organization-unit', help="AWS Organization Unit that you want to centralize monitoring for", type=str, required=True)
parser.add_argument('--sink-name', help="Human-friendly AWS Metric Sink Name, defaults to \"Centralized-Monitoring\"", type=str, required=False, default="Centralized-Monitoring")
parser.add_argument('--profile', help="AWS CLI Config Profile Name for the Management Account, uses your default AWS profile if not specified", type=str, required=False, default=None)
parser.add_argument('--regions', help="[Optional] List of comma-separated regions to create a sink and StackSet in. If not specified, a Sink/StackSet will be created in all default AWS regions", type=str, required=False)
parser.add_argument('--excluded-accounts', help="[Optional] List of comma-separated accounts to exclude from centralized monitoring (ex. --exclude \"12345678910,09876543210\"). Must exclude suspended accounts", type=str, required=False, default=None)

# AWS Default regions
aws_default_regions = ["us-east-2", "us-east-1", "us-west-1", "us-west-2",
		"ap-south-1", "ap-northeast-3", "ap-northeast-2", "ap-southeast-1", "ap-southeast-2",
		"ap-northeast-1", "ca-central-1", "eu-central-1", "eu-west-1", "eu-west-2", "eu-west-3",
		"eu-north-1", "sa-east-1"]


def monitoring_onboarding():
    # Fetch/validate CLI args
    args = parser.parse_args()
    arg_dict = vars(args)

    # Read in existing regions from log.txt
    existing_regions = []
    try:
        with open('log.txt', 'r') as f:
            log_lines = f.readlines()
            for line in log_lines:
                existing_regions.append(line.strip())
    except FileNotFoundError:
        # Create empty log.txt file if it doesn't exist
        with open('log.txt', 'w') as f:
            pass
        existing_regions = []
    
    
    organization = arg_dict['organization']

    organization_unit = arg_dict['organization_unit']

    if arg_dict['regions'] is not None:
        regions = arg_dict['regions'].split(',')
    else:
        regions = aws_default_regions

    profile = arg_dict['profile']

    excluded_accounts = None
    if arg_dict['excluded_accounts'] is not None:
        excluded_accounts = arg_dict['excluded_accounts'].split(',')

    # declare sink_name and sink_arn as None to get correct scoping
    sink_name = None
    sink_arn = None

    print("========== STARTING ==========")
    # iterate over regions, creating sinks and stacksets
    for region in regions:
        if region in existing_regions:
            print(f'already processed {region}, skipping...')
            continue
        
        # strip any accidental spaces
        region = region.strip(" ")

        print(f'checking if sink exists in {region}')
        try:
            sink_arn, sink_name = util.check_for_existing_sink(region=region, profile=profile)
        except Exception as err:
            raise Exception('checking if sink exists in %s' % region) from err
        
        if sink_name is None:
            sink_name = arg_dict['sink_name']

        # If sink does not exist, create it with the name provided
        if sink_arn is None:
            print(f'creating sink in {region}')
            try:
                sink_arn = util.create_sink(region=region, profile=profile, sink_name=sink_name, organization=organization)
            except Exception as err:
                raise Exception('creating sink in %s' % region) from err
            print(f'successfully created sink in {region}')
        else:
            print(f'sink {sink_name} already exists in {region}')
            print(f'attaching policy to sink {sink_name} in {region}')
            try:
                util.attach_policy_to_sink(region=region, profile=profile, sink_arn=sink_arn, organization=organization)
            except Exception as err:
                raise Exception('attaching policy to sink in %s' % region) from err
            print(f'successfully attached policy to sink in {region}')

        

        print(f'creating stackset and stacks in {region}')

        # Check if stackset already exists
        stack_set_id = util.check_for_existing_stackset(region=region, profile=profile, stack_set_name=sink_name)
        if stack_set_id is not None:
            print(f'stackset {sink_name} already exists in {region}')
        else:
            # Create stackset and stacks
            try:
                util.create_stackset(region=region, profile=profile, sink_arn=sink_arn, organization_unit=organization_unit, stack_set_name=sink_name, excluded_accounts=excluded_accounts)
            except Exception as err:
                raise Exception('creating stackset in %s' % region) from err
            print(f'successfully created stackset and stacks in {region}')

        # Add region to log.txt
        with open('log.txt', 'a') as f:
            f.write(f'{region}\n')

    print("========== COMPLETED ==========")
    return

if __name__ == "__main__":  
    monitoring_onboarding()
