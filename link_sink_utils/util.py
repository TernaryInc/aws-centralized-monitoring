import boto3, os
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
    except Exception:
        raise Exception('creating sink')
    
    # Put organization in the policy string
    formatted_policy = policy % organization

    # Attach policy to sink
    try:
        client.put_sink_policy(
            SinkIdentifier=sink['Arn'],
            Policy=formatted_policy
        )
    except Exception:
        raise Exception('adding policy to sink')
    
    return sink['Arn']

# Creates a stackset and stack instances that create links to the created sink
def create_stackset(region, profile, sink_arn, organization_unit, stack_set_name, excluded_accounts):
    # Get CFN Client
    client = get_client(profile, 'cloudformation', region)

    # Get account ID from caller identity
    try:
        account_id = get_client(profile, 'sts', region).get_caller_identity()['Account']
    except Exception:
        raise Exception('get account id')

    # Execute template
    try:
        rendered_template = render_template(monitoring_account_id=account_id, sink_arn=sink_arn)
    except Exception:
        raise('rendering template')
    
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
    except Exception:
        raise('creating stack set')

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