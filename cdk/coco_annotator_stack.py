from aws_cdk import core as cdk

# For consistency with other languages, `cdk` is the preferred import name for
# the CDK's core module.  The following line also imports it as `core` for use
# with examples from the CDK Developer's Guide, which are in the process of
# being updated to use `cdk`.  You may delete this import if you don't need it.
from aws_cdk import core
from aws_cdk import aws_s3 as s3
from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_iam as iam


class CocoAnnotatorStack(cdk.Stack):

    def __init__(self, scope: cdk.Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # S3 bucket
        bucket = s3.Bucket(self, "coco-annotator-bucket", bucket_name="coco-annotator-stack-bucket")

        # Networking
        vpc = ec2.Vpc(self, "coco-annotator-vpc")
        security_group = ec2.SecurityGroup(self, "coco-annotator-sg",
            vpc=vpc,
            description="Allow ssh access to ec2 instances, allow internet access",
            allow_all_outbound=True
        )
        security_group.add_ingress_rule(ec2.Peer.any_ipv4(), ec2.Port.tcp(22), "allow ssh access from the world")
        security_group.add_ingress_rule(ec2.Peer.any_ipv4(), ec2.Port.tcp(80), "allows HTTP access from Internet")
        security_group.add_ingress_rule(ec2.Peer.any_ipv4(), ec2.Port.tcp(443), "allows HTTPS access from Internet")

        # Machine OS
        amzn_linux = ec2.MachineImage.latest_amazon_linux()

        # Instance
        instance = ec2.Instance(self, "Instance",
                # Showing the most complex setup, if you have simpler requirements
                # you can use `CloudFormationInit.fromElements()`.
                init=ec2.CloudFormationInit.from_config_sets(
                config_sets={
                    # Applies the configs below in this order
                    "default": ["yumPreinstall", "config"]
                },
                configs={
                    "yum_preinstall": ec2.InitConfig([
                        # Install an Amazon Linux package using yum
                        ec2.InitPackage.yum("git"),
                        ec2.InitPackage.yum("docker"),
                        ec2.InitPackage.yum("py-pip"),
                        ec2.InitPackage.yum("python3-dev"),
                        ec2.InitPackage.yum("libffi-dev"),
                        ec2.InitPackage.yum("openssl-dev"),
                        ec2.InitPackage.yum("gcc"),
                        ec2.InitPackage.yum("libc-dev"),
                        ec2.InitPackage.yum("rust"),
                        ec2.InitPackage.yum("cargo"),
                        ec2.InitPackage.yum("make"),
                        ec2.InitPackage.python("docker-compose"),
                    ]),
                    "config": ec2.InitConfig([
                        ec2.InitSource.from_git_hub("coco-annotator", "developmentseed", "coco-annotator")
                    ])
                }
            ),
            init_options=ec2.ApplyCloudFormationInitOptions(
                config_sets=["default"],
                timeout=cdk.Duration.minutes(30),
            ),
            instance_type=ec2.InstanceType.of(
                ec2.InstanceClass.BURSTABLE2,
                ec2.InstanceSize.MEDIUM
            ),
            machine_image = amzn_linux, 
            vpc = vpc,
            vpc_subnets=vpc.public_subnets[0],
            key_name="rodrigo-coco-annotator"
        )

        role = iam.Role(self, "coco-annotator-role",
            assumed_by=iam.AccountRootPrincipal()
        )
        volume = ec2.Volume(self, "Volume",
            availability_zone=core.Stack.of(self).availability_zones[0],
            size=cdk.Size.gibibytes(30),
            volume_name="coco-annotator-volume"
        )
        volume.grant_attach_volume(role, [instance])



                
