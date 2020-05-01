from troposphere import GetAtt, Output, Parameter, Ref, Tags, Template, emr, iam
from troposphere.constants import M4_LARGE
from troposphere.ec2 import (
    VPC,
    InternetGateway,
    NetworkAcl,
    NetworkAclEntry,
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

    ref_stack_id = Ref("AWS::StackId")
    vpc = template.add_resource(
        VPC("VPC", CidrBlock="10.0.0.0/16", Tags=Tags(Application=ref_stack_id, Name="EMRSparkCluster"))
    )

    subnet = template.add_resource(
        Subnet(
            "Subnet",
            CidrBlock="10.0.0.0/24",
            VpcId=Ref(vpc),
            Tags=Tags(Application=ref_stack_id, Name="EMRSparkCluster"),
        )
    )

    internet_gateway = template.add_resource(
        InternetGateway("InternetGateway", Tags=Tags(Application=ref_stack_id, Name="EMRSparkCluster"))
    )
    attach_gateway = template.add_resource(
        VPCGatewayAttachment("AttachGateway", VpcId=Ref(vpc), InternetGatewayId=Ref(internet_gateway))
    )
    route_table = template.add_resource(
        RouteTable("RouteTable", VpcId=Ref(vpc), Tags=Tags(Application=ref_stack_id, Name="EMRSparkCluster"))
    )

    template.add_resource(
        Route(
            "Route",
            DependsOn=attach_gateway,
            GatewayId=Ref(internet_gateway),
            DestinationCidrBlock="0.0.0.0/0",
            RouteTableId=Ref(route_table),
        )
    )

    template.add_resource(
        SubnetRouteTableAssociation("SubnetRouteTableAssociation", SubnetId=Ref(subnet), RouteTableId=Ref(route_table),)
    )

    network_acl = template.add_resource(
        NetworkAcl("NetworkAcl", VpcId=Ref(vpc), Tags=Tags(Application=ref_stack_id, Name="EMRSparkCluster"),)
    )

    template.add_resource(
        NetworkAclEntry(
            "InboundSSHNetworkAclEntry",
            NetworkAclId=Ref(network_acl),
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
            NetworkAclId=Ref(network_acl),
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
            "OutBoundResponsePortsNetworkAclEntry",
            NetworkAclId=Ref(network_acl),
            RuleNumber="103",
            Protocol="6",
            PortRange=PortRange(To="65535", From="1024"),
            Egress="true",
            RuleAction="allow",
            CidrBlock="0.0.0.0/0",
        )
    )

    template.add_resource(
        NetworkAclEntry(
            "OutBoundHTTPPortsNetworkAclEntry",
            NetworkAclId=Ref(network_acl),
            RuleNumber="104",
            Protocol="6",
            PortRange=PortRange(To="80", From="80"),
            Egress="true",
            RuleAction="allow",
            CidrBlock="0.0.0.0/0",
        )
    )

    template.add_resource(
        NetworkAclEntry(
            "OutBoundHTTPSPortsNetworkAclEntry",
            NetworkAclId=Ref(network_acl),
            RuleNumber="105",
            Protocol="6",
            PortRange=PortRange(To="443", From="443"),
            Egress="true",
            RuleAction="allow",
            CidrBlock="0.0.0.0/0",
        )
    )

    template.add_resource(
        NetworkAclEntry(
            "OutBoundSSHPortsNetworkAclEntry",
            NetworkAclId=Ref(network_acl),
            RuleNumber="106",
            Protocol="6",
            PortRange=PortRange(To="22", From="22"),
            Egress="true",
            RuleAction="allow",
            CidrBlock="0.0.0.0/0",
        )
    )

    template.add_resource(
        SubnetNetworkAclAssociation("SubnetNetworkAclAssociation", SubnetId=Ref(subnet), NetworkAclId=Ref(network_acl))
    )

    emr_security_group = template.add_resource(
        SecurityGroup(
            "EMRSecurityGroup",
            GroupDescription="Enable SSH access via port 22",
            SecurityGroupIngress=[
                SecurityGroupRule(IpProtocol="tcp", FromPort="22", ToPort="22", CidrIp=Ref(sshlocation_param)),
            ],
            VpcId=Ref(vpc),
            Tags=Tags(Application=ref_stack_id, Name="EMRSparkCluster"),
        )
    )

    emr_service_role = template.add_resource(
        iam.Role(
            "EMRServiceRole",
            AssumeRolePolicyDocument={
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Principal": {"Service": ["elasticmapreduce.amazonaws.com"]},
                        "Action": ["sts:AssumeRole"],
                    }
                ]
            },
            ManagedPolicyArns=["arn:aws:iam::aws:policy/service-role/AmazonElasticMapReduceRole"],
        )
    )

    emr_job_flow_role = template.add_resource(
        iam.Role(
            "EMRJobFlowRole",
            AssumeRolePolicyDocument={
                "Statement": [
                    {"Effect": "Allow", "Principal": {"Service": ["ec2.amazonaws.com"]}, "Action": ["sts:AssumeRole"]}
                ]
            },
            ManagedPolicyArns=["arn:aws:iam::aws:policy/service-role/AmazonElasticMapReduceforEC2Role"],
        )
    )

    emr_instance_profile = template.add_resource(
        iam.InstanceProfile("EMRInstanceProfile", Roles=[Ref(emr_job_flow_role)])
    )

    cluster = template.add_resource(
        emr.Cluster(
            "EMRSparkCluster",
            Name="EMR Spark Cluster",
            ReleaseLabel="emr-6.0.0",
            JobFlowRole=Ref(emr_instance_profile),
            ServiceRole=Ref(emr_service_role),
            Instances=emr.JobFlowInstancesConfig(
                Ec2KeyName=Ref(keyname_param),
                Ec2SubnetId=Ref(subnet),
                EmrManagedMasterSecurityGroup=Ref(emr_security_group),
                EmrManagedSlaveSecurityGroup=Ref(emr_security_group),
                MasterInstanceGroup=emr.InstanceGroupConfigProperty(
                    Name="Master Instance", InstanceCount="1", InstanceType=M4_LARGE, Market="ON_DEMAND",
                ),
                CoreInstanceGroup=emr.InstanceGroupConfigProperty(
                    Name="Core Instance",
                    EbsConfiguration=emr.EbsConfiguration(
                        EbsBlockDeviceConfigs=[
                            emr.EbsBlockDeviceConfigs(
                                VolumeSpecification=emr.VolumeSpecification(SizeInGB="10", VolumeType="gp2"),
                                VolumesPerInstance="1",
                            )
                        ],
                        EbsOptimized="true",
                    ),
                    InstanceCount="1",
                    InstanceType=M4_LARGE,
                ),
            ),
            Applications=[emr.Application(Name="Spark")],
            VisibleToAllUsers="true",
            Tags=Tags(Name="EMR Sample Cluster"),
        )
    )

    template.add_output([Output("MasterPublicDNS", Value=GetAtt(cluster, "MasterPublicDNS"))])
    return template
