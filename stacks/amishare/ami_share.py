from aws_cdk import (
    core,
    aws_imagebuilder as imagebuilder,
    aws_iam as iam,
    aws_sns as sns,
    aws_ec2 as ec2,
    aws_ssm as ssm,
    aws_kms as kms,
    aws_lambda,
    custom_resources
)

from utils.CdkUtils import CdkUtils


class AmiShareStack(core.Stack):

    def __init__(self, scope: core.Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        config = CdkUtils.get_project_settings()

        # Retrieve VPC information via lookup
        ami_share_vpc = ec2.Vpc.from_lookup(self, "VPC",
            vpc_id = config['vpc']['vpc_id']
        )

        # create a KMS key to encrypt project contents
        ami_share_kms_key = kms.Key(
            self, 
            f"ami-share-kms-key-{CdkUtils.stack_tag}",
            admins=[iam.AccountPrincipal(account_id=core.Aws.ACCOUNT_ID)],
            enable_key_rotation=True,
            enabled=True,
            description="KMS key used with EC2 Imagebuilder Ami Share project",
            removal_policy=core.RemovalPolicy.DESTROY,
            alias=f"ami-share-kms-key-alias-{CdkUtils.stack_tag}"
        )

        ami_share_kms_key.grant_encrypt_decrypt(iam.ServicePrincipal(service=f'imagebuilder.{core.Aws.URL_SUFFIX}'))

        # below role is assumed by the ImageBuilder ec2 instance
        ami_share_image_role = iam.Role(self, f"ami-share-image-role-{CdkUtils.stack_tag}", assumed_by=iam.ServicePrincipal("ec2.amazonaws.com"))
        ami_share_image_role.add_managed_policy(iam.ManagedPolicy.from_aws_managed_policy_name("AmazonSSMManagedInstanceCore"))
        ami_share_image_role.add_managed_policy(iam.ManagedPolicy.from_aws_managed_policy_name("EC2InstanceProfileForImageBuilder"))
        ami_share_kms_key.grant_encrypt_decrypt(ami_share_image_role)
        ami_share_kms_key.grant(ami_share_image_role, "kms:Describe*")
        ami_share_image_role.add_to_policy(iam.PolicyStatement(
            actions=[
                "logs:CreateLogStream",
                "logs:CreateLogGroup",
                "logs:PutLogEvents"
            ],
            resources=[
                core.Arn.format(components=core.ArnComponents(
                    service="logs",
                    resource="log-group",
                    resource_name="aws/imagebuilder/*"
                ), stack=self)
            ],
        ))

        # create an instance profile to attach the role
        instance_profile = iam.CfnInstanceProfile(
            self, f"ami-share-imagebuilder-instance-profile-{CdkUtils.stack_tag}",
            instance_profile_name=f"ami-share-imagebuilder-instance-profile-{CdkUtils.stack_tag}",
            roles=[ami_share_image_role.role_name]
        )

        ssm.StringListParameter(
            self, f"ami-share-distribution-list-{CdkUtils.stack_tag}",
            parameter_name=f'/{CdkUtils.stack_tag}-AmiSharePipeline/DistributionList',
            string_list_value=config["imagebuilder"]['distributionList']
        )

        sns_topic = sns.Topic(
            self, f"ami-share-imagebuilder-topic-{CdkUtils.stack_tag}",
            topic_name=f"ami-share-imagebuilder-topic-{CdkUtils.stack_tag}",
            master_key=ami_share_kms_key
        )

        sns.Subscription(
            self, f"ami-share-imagebuilder-subscription-{CdkUtils.stack_tag}",
            topic=sns_topic,
            endpoint=config["imagebuilder"]["imageBuilderEmailAddress"],
            protocol=sns.SubscriptionProtocol.EMAIL
        )

        sns_topic.grant_publish(ami_share_image_role)
        ami_share_kms_key.grant_encrypt_decrypt(iam.ServicePrincipal(service=f'sns.{core.Aws.URL_SUFFIX}'))

        # SG for the image build
        ami_share_imagebuilder_sg = ec2.SecurityGroup(
            self, f"ami-share-imagebuilder-sg-{CdkUtils.stack_tag}",
            vpc=ami_share_vpc,
            allow_all_outbound=True,
            description="Security group for the EC2 Image Builder Pipeline: " + self.stack_name + "-Pipeline",
            security_group_name=f"ami-share-imagebuilder-sg-{CdkUtils.stack_tag}"
        )

        # create infrastructure configuration to supply instance type
        infra_config = imagebuilder.CfnInfrastructureConfiguration(
            self, f"ami-share-infra-config-{CdkUtils.stack_tag}",
            name=f"ami-share-infra-config-{CdkUtils.stack_tag}",
            instance_types=config["imagebuilder"]["instanceTypes"],
            instance_profile_name=instance_profile.instance_profile_name,
            subnet_id=config['vpc']['subnet_id'],
            security_group_ids=[ami_share_imagebuilder_sg.security_group_id],
            resource_tags={
                "project": "ec2-imagebuilder-ami-share"
            },
            terminate_instance_on_failure=True,
            sns_topic_arn=sns_topic.topic_arn
        )
        # infrastructure need to wait for instance profile to complete before beginning deployment.
        infra_config.add_depends_on(instance_profile)

         # recipe that installs the Ami Share components together with a Amazon Linux 2 base image
        ami_share_recipe = imagebuilder.CfnImageRecipe(
            self, f"ami-share-image-recipe-{CdkUtils.stack_tag}",
            name=f"ami-share-image-recipe-{CdkUtils.stack_tag}",
            version=config["imagebuilder"]["version"],
            components=[
                {
                    "componentArn": core.Arn.format(components=core.ArnComponents(
                        service="imagebuilder",
                        resource="component",
                        resource_name="aws-cli-version-2-linux/x.x.x",
                        account="aws"
                    ), stack=self)
                }
            ],
            parent_image=f"arn:aws:imagebuilder:{self.region}:aws:image/{config['imagebuilder']['baseImageArn']}",
            block_device_mappings=[
                imagebuilder.CfnImageRecipe.InstanceBlockDeviceMappingProperty(
                    device_name="/dev/xvda",
                    ebs=imagebuilder.CfnImageRecipe.EbsInstanceBlockDeviceSpecificationProperty(
                        delete_on_termination=True,
                        # Encryption is disabled, because the export VM doesn't support encrypted ebs
                        encrypted=False,
                        volume_size=config["imagebuilder"]["ebsVolumeSize"],
                        volume_type="gp2"
                    )
                )],
            description=f"Recipe to build and validate AmiShareImageRecipe-{CdkUtils.stack_tag}",
            tags={
                "project": "ec2-imagebuilder-ami-share"
            },
            working_directory="/imagebuilder"
        )      

        # Distribution configuration for AMIs
        ami_share_distribution_config = imagebuilder.CfnDistributionConfiguration(
            self, f'ami-share-distribution-config-{CdkUtils.stack_tag}',
            name=f'ami-share-distribution-config-{CdkUtils.stack_tag}',
            distributions=[
                imagebuilder.CfnDistributionConfiguration.DistributionProperty(
                    region=self.region,
                    ami_distribution_configuration={
                        'Name': core.Fn.sub(f'AmiShare-{CdkUtils.stack_tag}-ImageRecipe-{{{{ imagebuilder:buildDate }}}}'),
                        'AmiTags': {
                            "project": "ec2-imagebuilder-ami-share",
                            'Pipeline': f"AmiSharePipeline-{CdkUtils.stack_tag}"
                        }
                    }
                )
            ]
        )

        # build the imagebuilder pipeline
        ami_share_pipeline = imagebuilder.CfnImagePipeline(
            self, f"ami-share-pipeline-{CdkUtils.stack_tag}",
            name=f"ami-share-pipeline-{CdkUtils.stack_tag}",
            image_recipe_arn=ami_share_recipe.attr_arn,
            infrastructure_configuration_arn=infra_config.attr_arn,
            tags={
                "project": "ec2-imagebuilder-ami-share"
            },
            description=f"Image Pipeline for: AmiSharePipeline-{CdkUtils.stack_tag}",
            enhanced_image_metadata_enabled=True,
            image_tests_configuration=imagebuilder.CfnImagePipeline.ImageTestsConfigurationProperty(
                image_tests_enabled=True,
                timeout_minutes=90
            ),
            distribution_configuration_arn=ami_share_distribution_config.attr_arn,
            status="ENABLED"
        )
        ami_share_pipeline.add_depends_on(infra_config)

        # Create ami distribution lambda function - this is required because 
        # EC2 ImageBuilder AMI distribution setting targetAccountIds
        # is not supported by CloudFormation (as of September 2021).
        # see https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-imagebuilder-distributionconfiguration.html
        
        # Create a role for the amidistribution lambda function
        amidistribution_lambda_role = iam.Role(
            scope=self,
            id=f"amidistributionLambdaRole-{CdkUtils.stack_tag}",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "service-role/AWSLambdaBasicExecutionRole"
                )
            ]
        )
        amidistribution_lambda_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                resources=[ami_share_distribution_config.attr_arn],
                actions=[
                    "imagebuilder:UpdateDistributionConfiguration"
                ]
            )
        )
        amidistribution_lambda_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                resources=[f"arn:aws:ssm:{core.Aws.REGION}:{core.Aws.ACCOUNT_ID}:parameter/{CdkUtils.stack_tag}-AmiSharing/*"],
                actions=[
                        "ssm:GetParameter",
                        "ssm:GetParameters",
                        "ssm:GetParametersByPath"
                ]
            )
        )

        # create the lambda that will use boto3 to set the 'targetAccountIds'
        # ami distribution setting currently not supported in Cloudformation
        ami_distribution_lambda = aws_lambda.Function(
            scope=self,
            id=f"amiDistributionLambda-{CdkUtils.stack_tag}",
            code=aws_lambda.Code.asset("stacks/amishare/resources/amidistribution"),
            handler="ami_distribution.lambda_handler",
            runtime=aws_lambda.Runtime.PYTHON_3_6,
            role=amidistribution_lambda_role
        )

        # Provider that invokes the ami distribution lambda function
        ami_distribution_provider = custom_resources.Provider(
            self, 
            f'AmiDistributionCustomResourceProvider-{CdkUtils.stack_tag}',
            on_event_handler=ami_distribution_lambda
        )

        # Create a SSM Parameters for AMI Publishing and Sharing Ids
        # so as not to hardcode the account id values in the Lambda
        ssm_ami_publishing_target_ids = ssm.StringListParameter(
            self, f"AmiPublishingTargetIds-{CdkUtils.stack_tag}",
            parameter_name=f'/{CdkUtils.stack_tag}-AmiSharing/AmiPublishingTargetIds',
            string_list_value=config['imagebuilder']['amiPublishingTargetIds']
        )

        ssm_ami_sharing_ids = ssm.StringListParameter(
            self, f"AmiSharingAccountIds-{CdkUtils.stack_tag}",
            parameter_name=f'/{CdkUtils.stack_tag}-AmiSharing/AmiSharingAccountIds',
            string_list_value=config['imagebuilder']['amiSharingIds']
        )

        # The custom resource that uses the ami distribution provider to supply values
        ami_distribution_custom_resource = core.CustomResource(
            self, 
            f'AmiDistributionCustomResource-{CdkUtils.stack_tag}',
            service_token=ami_distribution_provider.service_token,
            properties = {
                'CdkStackName': CdkUtils.stack_tag,
                'AwsDistributionRegions': config['imagebuilder']['amiPublishingRegions'],
                'ImageBuilderName': f'AmiDistributionConfig-{CdkUtils.stack_tag}',
                'AmiDistributionName': f"AmiShare-{CdkUtils.stack_tag}" + "-{{ imagebuilder:buildDate }}",
                'AmiDistributionArn': ami_share_distribution_config.attr_arn,
                'PublishingAccountIds': ssm_ami_publishing_target_ids.parameter_name,
                'SharingAccountIds': ssm_ami_sharing_ids.parameter_name
            }
        )

        ami_distribution_custom_resource.node.add_dependency(ami_share_distribution_config)

        # The result obtained from the output of custom resource
        ami_distriubtion_arn = core.CustomResource.get_att_string(ami_distribution_custom_resource, attribute_name='AmiDistributionArn')

        ##################################################
        ## <START> CDK Outputs
        ##################################################

        core.CfnOutput(
            self,
            id=f"export-ami-share-sns-topic-arn-{CdkUtils.stack_tag}",
            export_name=f"AmiShare-SnsTopicArn-{CdkUtils.stack_tag}", 
            value=sns_topic.topic_arn,
            description="Ami Share Sns Topic"
        )
        
        core.CfnOutput(
            self,
            id=f"export-ami-share-kms-key-arn-{CdkUtils.stack_tag}",
            export_name=f"AmiShare-KmsKeyArn-{CdkUtils.stack_tag}", 
            value=ami_share_kms_key.key_arn,
            description="Ami Share KMS Key ARN"
        )

        core.CfnOutput(
            self,
            id=f"export-ami-share-pipeline-arn-{CdkUtils.stack_tag}",
            export_name=f"AmiShare-PipelineArn-{CdkUtils.stack_tag}",
            value=ami_share_pipeline.attr_arn,
            description="Ami Share Pipeline Arn"
        )

        ##################################################
        ## </END> CDK Outputs
        ##################################################