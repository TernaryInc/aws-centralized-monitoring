import os

import boto3
from jinja2 import Environment, FileSystemLoader, select_autoescape


# Returns an instance of a client for a given service, in a given region, with a given profile
def get_client(profile, service, region):
    return boto3.Session(profile_name=profile, region_name=region).client(service)

policy = """{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":"*","Action":["oam:CreateLink","oam:UpdateLink"],"Resource":"*","Condition":{"ForAllValues:StringEquals":{"oam:ResourceTypes":"AWS::CloudWatch::Metric"},"ForAnyValue:StringEquals":{"aws:PrincipalOrgID":"%s"}}}]}"""

# Renders link-cfn-template.yaml as a string with user provided arguments
def render_template(monitoring_account_id, sink_arn):
    env = Environment(
        loader=FileSystemLoader(os.path.join(os.path.dirname(__file__),'../templates/')),
        autoescape=select_autoescape())
    template = env.get_template('link-cfn-template.yaml')
    return template.render(MonitoringAccountID=monitoring_account_id, SinkARN=sink_arn)

# Creates a sink in the provided region, and attaches the above policy to it
def create_sink(region, profile, sink_name, organization):
    # Get OAM client
    client = get_client(profile, 'oam', region)

    # Create an OAM sink in the specified region
    try:
        sink = client.create_sink(
            Name=sink_name
        )
    except Exception as e:
        raise Exception('creating sink') from e
    
    attach_policy_to_sink(region, profile, sink['Arn'], organization)
    
    return sink['Arn']

def check_for_existing_sink(region, profile):
    # Get OAM client
    client = get_client(profile, 'oam', region)

    # Get sink
    try:
        sinks = []
        paginator = client.get_paginator('list_sinks')
        for page in paginator.paginate():
            sinks.extend(page.get('Items', []))
        if len(sinks) == 0:
            return None
        return (sinks[0]['Arn'], sinks[0]['Name'])
    except Exception as e:
        raise Exception('get sink') from e

def attach_policy_to_sink(region, profile, sink_arn, organization):
    # Get OAM client
    client = get_client(profile, 'oam', region)

    # Put organization in the policy string
    formatted_policy = policy % organization

    # Attach policy to sink
    try:
        client.put_sink_policy(
            SinkIdentifier=sink_arn,
            Policy=formatted_policy
        )
    except Exception as e:
        raise Exception('adding policy to sink') from e

# Creates a stackset and stack instances that create links to the created sink
def create_stackset(region, profile, sink_arn, organization_unit, stack_set_name, excluded_accounts):
    # Get CFN Client
    client = get_client(profile, 'cloudformation', region)

    # Get account ID from caller identity
    try:
        account_id = get_client(profile, 'sts', region).get_caller_identity()['Account']
    except Exception as e:
        raise Exception('get account id') from e

    # Execute template
    try:
        rendered_template = render_template(monitoring_account_id=account_id, sink_arn=sink_arn)
    except Exception as e:
        raise('rendering template') from e
    
    # Create stackset
    try:
        stack_set = client.create_stack_set(
            StackSetName=stack_set_name,
            Description="Source Account Links To Enable Cross-Account Monitoring",
            TemplateBody=rendered_template,
            PermissionModel='SERVICE_MANAGED',
            AutoDeployment={
                'Enabled': True,
                'RetainStacksOnAccountRemoval': False
            }
        )
    except Exception as e:
        raise('creating stack set') from e

    # Set DeploymentTargets
    deployment_targets={
        'OrganizationalUnitIds': [
            organization_unit,
        ],
        'AccountFilterType': 'NONE'
    }
    if excluded_accounts is not None:
        deployment_targets['Accounts'] = excluded_accounts
        deployment_targets['AccountFilterType'] = 'DIFFERENCE'

    # Create stack instances
    client.create_stack_instances(
        StackSetName=stack_set['StackSetId'],
        DeploymentTargets=deployment_targets,
        Regions=[region],
        OperationPreferences={
            'RegionConcurrencyType': 'SEQUENTIAL',
            'MaxConcurrentCount': 1,
        }
    )
    return
