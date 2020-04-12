from troposphere import FindInMap, GetAtt, Output, Parameter, Ref, Tags, Template
from troposphere.ec2 import (
    VPC,
    Instance,
    InternetGateway,
    NetworkAcl,
    NetworkAclEntry,
    NetworkInterfaceProperty,
    PortRange,
    Route,
    RouteTable,
    SecurityGroup,
    SecurityGroupRule,
    Subnet,
    SubnetNetworkAclAssociation,
    SubnetRouteTableAssociation,
    VPCGatewayAttachment,
)


def build(ssh_keypair_name):
    template = Template()
    template.set_version("2010-09-09")

    keyname_param = template.add_parameter(
        Parameter(
            "KeyName",
            ConstraintDescription="must be the name of an existing EC2 KeyPair.",
            Description="Name of an existing EC2 KeyPair to enable SSH access to \
    the instance",
            Type="AWS::EC2::KeyPair::KeyName",
            Default=ssh_keypair_name,
        )
    )

    sshlocation_param = template.add_parameter(
        Parameter(
            "SSHLocation",
            Description=" The IP address range that can be used to SSH to the EC2 \
    instances",
            Type="String",
            MinLength="9",
            MaxLength="18",
            Default="0.0.0.0/0",
            AllowedPattern=r"(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})/(\d{1,2})",
            ConstraintDescription=("must be a valid IP CIDR range of the form x.x.x.x/x."),
        )
    )

    instanceType_param = template.add_parameter(
        Parameter(
            "InstanceType",
            Type="String",
            Description="WebServer EC2 instance type",
            Default="t2.small",
            AllowedValues=[
                "t2.micro",
                "t2.small",
                "t2.medium",
                "m3.medium",
                "m3.large",
                "m3.xlarge",
                "m3.2xlarge",
                "c3.large",
                "c3.xlarge",
                "c3.2xlarge",
                "c3.4xlarge",
                "c3.8xlarge",
                "g2.2xlarge",
                "r3.large",
                "r3.xlarge",
                "r3.2xlarge",
                "r3.4xlarge",
                "r3.8xlarge",
                "i2.xlarge",
                "i2.2xlarge",
                "i2.4xlarge",
                "i2.8xlarge",
                "hi1.4xlarge",
                "hs1.8xlarge",
                "cr1.8xlarge",
                "cc2.8xlarge",
            ],
            ConstraintDescription="must be a valid EC2 instance type.",
        )
    )

    template.add_mapping(
        "AWSRegion2AMI",
        {
            "us-east-1": {"image": "ami-0d915a031cabac0e0"},
            "us-east-2": {"image": "ami-0b97435028ca44fcc"},
            "us-west-1": {"image": "ami-068d0753a46192935"},
            "us-west-2": {"image": "ami-0c457f229774da543"},
            "eu-west-1": {"image": "ami-046c6a0123bf94619"},
            "eu-west-2": {"image": "ami-0dbe8ba0cd21ea12b"},
            "eu-west-3": {"image": "ami-041bf9180061ce7ea"},
            "eu-central-1": {"image": "ami-0f8184e6f30cc0c33"},
            "eu-north-1": {"image": "ami-08dd1b893371bcaac"},
            "ap-south-1": {"image": "ami-0ff23052091536db2"},
            "ap-southeast-1": {"image": "ami-0527e82bae7c51958"},
            "ap-southeast-2": {"image": "ami-0bae8773e653a32ec"},
            "ap-northeast-1": {"image": "ami-060741a96307668be"},
            "ap-northeast-2": {"image": "ami-0d991ac4f545a6b34"},
            "sa-east-1": {"image": "ami-076f350d5a5ec448d"},
            "ca-central-1": {"image": "ami-0071deaa12b66d1bf"},
        },
    )

    ref_stack_id = Ref("AWS::StackId")
    vpc = template.add_resource(VPC("StreamSteamVPC", CidrBlock="10.0.0.0/16", Tags=Tags(Application=ref_stack_id)))

    subnet = template.add_resource(
        Subnet("Subnet", CidrBlock="10.0.0.0/24", VpcId=Ref(vpc), Tags=Tags(Application=ref_stack_id))
    )

    internetGateway = template.add_resource(InternetGateway("InternetGateway", Tags=Tags(Application=ref_stack_id)))

    template.add_resource(VPCGatewayAttachment("AttachGateway", VpcId=Ref(vpc), InternetGatewayId=Ref(internetGateway)))

    routeTable = template.add_resource(RouteTable("RouteTable", VpcId=Ref(vpc), Tags=Tags(Application=ref_stack_id)))

    template.add_resource(
        Route(
            "Route",
            DependsOn="AttachGateway",
            GatewayId=Ref("InternetGateway"),
            DestinationCidrBlock="0.0.0.0/0",
            RouteTableId=Ref(routeTable),
        )
    )

    template.add_resource(
        SubnetRouteTableAssociation("SubnetRouteTableAssociation", SubnetId=Ref(subnet), RouteTableId=Ref(routeTable),)
    )

    networkAcl = template.add_resource(NetworkAcl("NetworkAcl", VpcId=Ref(vpc), Tags=Tags(Application=ref_stack_id),))

    template.add_resource(
        NetworkAclEntry(
            "InboundHTTPNetworkAclEntry",
            NetworkAclId=Ref(networkAcl),
            RuleNumber="100",
            Protocol="6",
            PortRange=PortRange(To="80", From="80"),
            Egress="false",
            RuleAction="allow",
            CidrBlock="0.0.0.0/0",
        )
    )

    template.add_resource(
        NetworkAclEntry(
            "InboundSSHNetworkAclEntry",
            NetworkAclId=Ref(networkAcl),
            RuleNumber="101",
            Protocol="6",
            PortRange=PortRange(To="22", From="22"),
            Egress="false",
            RuleAction="allow",
            CidrBlock="0.0.0.0/0",
        )
    )

    template.add_resource(
        NetworkAclEntry(
            "InboundResponsePortsNetworkAclEntry",
            NetworkAclId=Ref(networkAcl),
            RuleNumber="102",
            Protocol="6",
            PortRange=PortRange(To="65535", From="1024"),
            Egress="false",
            RuleAction="allow",
            CidrBlock="0.0.0.0/0",
        )
    )

    template.add_resource(
        NetworkAclEntry(
            "OutBoundHTTPNetworkAclEntry",
            NetworkAclId=Ref(networkAcl),
            RuleNumber="100",
            Protocol="6",
            PortRange=PortRange(To="80", From="80"),
            Egress="true",
            RuleAction="allow",
            CidrBlock="0.0.0.0/0",
        )
    )

    template.add_resource(
        NetworkAclEntry(
            "OutBoundHTTPSNetworkAclEntry",
            NetworkAclId=Ref(networkAcl),
            RuleNumber="101",
            Protocol="6",
            PortRange=PortRange(To="443", From="443"),
            Egress="true",
            RuleAction="allow",
            CidrBlock="0.0.0.0/0",
        )
    )

    template.add_resource(
        NetworkAclEntry(
            "OutBoundResponsePortsNetworkAclEntry",
            NetworkAclId=Ref(networkAcl),
            RuleNumber="102",
            Protocol="6",
            PortRange=PortRange(To="65535", From="1024"),
            Egress="true",
            RuleAction="allow",
            CidrBlock="0.0.0.0/0",
        )
    )

    template.add_resource(
        SubnetNetworkAclAssociation("SubnetNetworkAclAssociation", SubnetId=Ref(subnet), NetworkAclId=Ref(networkAcl),)
    )

    instanceSecurityGroup = template.add_resource(
        SecurityGroup(
            "InstanceSecurityGroup",
            GroupDescription="Enable SSH access via port 22",
            SecurityGroupIngress=[
                SecurityGroupRule(IpProtocol="tcp", FromPort="22", ToPort="22", CidrIp=Ref(sshlocation_param)),
                SecurityGroupRule(IpProtocol="tcp", FromPort="80", ToPort="80", CidrIp="0.0.0.0/0"),
            ],
            VpcId=Ref(vpc),
        )
    )

    template.add_resource(
        Instance(
            "WebServerInstance",
            ImageId=FindInMap("AWSRegion2AMI", Ref("AWS::Region"), "image"),
            InstanceType=Ref(instanceType_param),
            KeyName=Ref(keyname_param),
            NetworkInterfaces=[
                NetworkInterfaceProperty(
                    GroupSet=[Ref(instanceSecurityGroup)],
                    AssociatePublicIpAddress="true",
                    DeviceIndex="0",
                    DeleteOnTermination="true",
                    SubnetId=Ref(subnet),
                )
            ],
            Tags=Tags(Application=ref_stack_id),
        )
    )

    template.add_output([Output("RedashServerIP", Value=GetAtt("WebServerInstance", "PublicIp"),)])

    return template
