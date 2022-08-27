# ec2-imagebuilder-ami-share

CloudFormation template and CDK stack that contains a CustomResource with Lambda function to allow the setting of the `targetAccountIds` attribute of the EC2 Image Builder AMI distribution settings which is not currently supported in CloudFormation or CDK.

---

[EC2 Image Builder](https://aws.amazon.com/image-builder/) simplifies the building, testing, and deployment of Virtual Machine and container images for use on AWS or on-premises. Customers looking to create custom AMIs ([Amazon Machine Image](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/AMIs.html)) or container images can leverage EC2 Image Builder to significantly reduce the effort of keeping images up-to-date and secure through its simple graphical interface, built-in automation, and AWS-provided security settings. 

EC2 Image Builder includes [distribution settings](https://docs.aws.amazon.com/imagebuilder/latest/userguide/manage-distribution-settings.html) that allow for the *publishing* and *sharing* of AMIs. *Publishing* an AMI allows customers to define the AWS accounts and regions to which the generated AMI will be copied. *Sharing* an AMI allows customers to define the AWS accounts and regions to which the generated AMI will be shared. AWS accounts that have been nominated as targets for AMI sharing are able to launch EC2 instances based on those AMIs.

The AWS CLI fully supports [creating and updating distribution settings for AMIs](https://docs.aws.amazon.com/imagebuilder/latest/userguide/crud-ami-distribution-settings.html).

AWS CloudFormation offers the capability of defining [distribution settings for EC2 Image Builder](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-properties-imagebuilder-distributionconfiguration-distribution.html). However, at the time of writing this blog post, AWS CloudFormation does not provide the capability of defining the target accounts to which a generated AMI will be published. Specifically, the `targetAccountIds` attribute is not currently exposed through AWS CloudFormation.

This project describes how a [CloudFormation Custom Resource](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/template-custom-resources.html) can be leveraged to allow customers to access the full set of distribution settings for EC2 Image Builder, including the `targetAccountIds` attribute, as part of their CloudFormation templates or CDK ([Cloud Development Kit](https://aws.amazon.com/cdk/)) code base.

The project assumes the availability of at least 3 AWS accounts:

1. A *tooling* account where the CloudFormation template is deployed and the project resources are created.
2. A *publishing* account (or accounts) to which the generated AMI would be published.
3. A *sharing* account (or accounts) to whom the generated AMI would be shared.

The code will only deploy resources into the *tooling* account. The existence of the *publishing* and *sharing* accounts are required in order to set the respective EC2 Image Builder distribution configuration settings.

Additionally, the project assumes that the account into which the CloudFormation template is deployed has an AWS VPC with at least 1 subnet.

----

* [Solution architecture](#solution-architecture)
* [Deploying the CloudFormation project](#deploying-the-cloudformation-project)
* [Clean up the CloudFormation project](#clean-up-the-cloudformation-project)
* [Deploying the CDK project](#deploying-the-cdk-project)
* [Clean up the CDK project](#clean-up-the-cdk-project)
* [Executing unit tests](#executing-unit-tests)
* [Executing static code analysis tool](#executing-static-code-analysis-tool)
* [Security](#security)
* [License](#license)

# Solution architecture

The solution architecture discussed in this post is presented below:

![Solution architecture](docs/assets/solution_architecture.png)

1. A CloudFormation template, generated manually or via CDK, is deployed to the AWS CloudFormation service.
2. The provided CloudFormation template includes the definition of a custom resource. The custom resource is implement via a Lambda function which will use the [Python Boto3 library](https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/imagebuilder.html#imagebuilder.Client.update_distribution_configuration) to update the AMI distribution configuration of EC2 Image Builder, including setting the `targetAccountIds` attribute. The `targetAccountIds` attribute is currently not available to CloudFormation but it can be set with the Boto3 library.
3. The CloudFormation service will call the Lambda function defined in the custom resource, waiting for the result of the Lambda invocation.
4. Upon successful completion of the Lambda function, CloudFormation will resume the creation of the remaining resources of the stack.

# Deploying the CloudFormation project

Follow the steps below to deploy the CloudFormation template.

1. Download the [EC2ImageBuilderAmiShare.yaml](cloudformation/EC2ImageBuilderAmiShare.yaml) template file to your local machine.
2. Log into the AWS Console → navigate to the CloudFormation console.
3. Click on the *Create stack* button and choose *With new resources (standard)*.
4. In the *Create stack* screen, select the option to *Upload a template file*.
5. Choose the [EC2ImageBuilderAmiShare.yaml](cloudformation/EC2ImageBuilderAmiShare.yaml) template file.
6. Click *Next*.
7. In the *Specify stack details* screen, provide the following values:
    1. Stack name: **EC2ImageBuilderAmiShare**
    2. AmiPublishingRegionsParameter: *&lt;AWS region to which the AMI should be published, e.g. us-east-1&gt;*
    3. AmiPublishingTargetIdsParameter: *&lt;AWS account ids to which the AMI should be published&gt;*
    4. AmiSharingAccountIdsParameter: *&lt;AWS account ids to whom the AMI should be shared&gt;*
    5. SubnetIdParameter: *&lt;Select a desired subnet&gt;*
    6. VpcIdParameter: *&lt;Select a desired VPC&gt;*

![CloudFormation parameters](docs/assets/screenshots/01-cfn-parameters.png)

8. Click *Next*.
9. On the *Configure stack options* screen, click *Next* to accept defaults.
10. On the *Review EC2ImageBuilderAmiShare* screen, click the check box for **I acknowledge that AWS CloudFormation might create IAM resources with custom names.**
11. Click *Create stack*.
12. Confirm that the stack reaches the **CREATE_COMPLETE** state.

Verify the distribution settings of EC2 Image Builder.

1. Log into the AWS Console → navigate to the EC2 Image Builder console.
2. Click on the pipeline with name `ami-share-pipeline` to open the detailed pipeline view.
3. Click on the *Distribution settings* and review the *Distribution details*.
4. Confirm that the following values match the parameter values passed to the CloudFormation template:
    1. Region
    2. Target accounts for distribution
    3. Accounts with shared permissions

![EC2 Image Builder AMI distribution settings](docs/assets/screenshots/02-distribution-settings.png)

The CloudFormation template has successfully deployed the EC2 Image Builder and the *Target accounts for distribution* value has been correctly set through the use of a CustomResource Lambda function.

At this point the pipeline could be *Run* in order to generate, distribute and share the AMI.

Please note that in order to distribute the generated AMI to other AWS accounts it is necessary to [set up cross-account AMI distribution with Image Builder](https://docs.aws.amazon.com/imagebuilder/latest/userguide/cross-account-dist.html).

# Clean up the CloudFormation project

Project clean-up is a single step process:

1. Delete the *EC2ImageBuilderAmiShare* stack from CloudFormation.

Delete the *EC2ImageBuilderAmiShare* CloudFormation stack.

1. Log into the AWS Console → navigate to the *CloudFormation* console.
2. Navigate to *Stacks*.
3. Select the **EC2ImageBuilderAmiShare**.
4. Click the *Delete* button.

# Deploying the CDK project

The project code uses the Python flavour of the AWS CDK ([Cloud Development Kit](https://aws.amazon.com/cdk/)). In order to execute the code, please ensure that you have fulfilled the [AWS CDK Prerequisites for Python](https://docs.aws.amazon.com/cdk/latest/guide/work-with-cdk-python.html).

Additionally, the project assumes:

* configuration of [AWS CLI Environment Variables](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-envvars.html).
* the availability of a `bash` (or compatible) shell environment.

The project requires that the AWS account is [bootstrapped](https://docs.aws.amazon.com/de_de/cdk/latest/guide/bootstrapping.html) in order to allow the deployment of the CDK stack.

```bash
# navigate to project directory
cd ec2-imagebuilder-ami-share

# install and activate a Python Virtual Environment
python3 -m venv .venv
source .venv/bin/activate

# install dependant libraries
python -m pip install -r requirements.txt

# bootstrap the account to permit CDK deployments
cdk bootstrap
```

Upon successful completion of `cdk bootstrap`, the project is ready to be deployed.

Before deploying the project, some configuration parameters need to be be defined in the [cdk.json](cdk.json) file.

```
{
  "app": "python3 app.py",
  "context": {
    "@aws-cdk/aws-apigateway:usagePlanKeyOrderInsensitiveId": true,
    "@aws-cdk/core:enableStackNameDuplicates": "true",
    "aws-cdk:enableDiffNoFail": "true",
    "@aws-cdk/core:stackRelativeExports": "true",
    "@aws-cdk/aws-ecr-assets:dockerIgnoreSupport": true,
    "@aws-cdk/aws-secretsmanager:parseOwnedSecretName": true,
    "@aws-cdk/aws-kms:defaultKeyPolicies": true,
    "@aws-cdk/aws-s3:grantWriteWithoutAcl": true,
    "@aws-cdk/aws-ecs-patterns:removeDefaultDesiredCount": true,
    "@aws-cdk/aws-rds:lowercaseDbIdentifier": true,
    "@aws-cdk/aws-efs:defaultEncryptionAtRest": true,
    "@aws-cdk/aws-lambda:recognizeVersionProps": true,
    "@aws-cdk/aws-cloudfront:defaultSecurityPolicyTLSv1.2_2021": true
  },
  "projectSettings": {
    "vpc": {
      "vpc_id": "<<ADD_VPD_ID_HERE>>",
      "subnet_id": "<<ADD_SUBNET_ID_HERE>>"
    },
    "imagebuilder": {
      "baseImageArn": "amazon-linux-2-x86/2021.4.29",
      "ebsVolumeSize": 8,
      "instanceTypes": [
        "t2.medium"
      ],
      "version": "1.0.0",
      "imageBuilderEmailAddress": "email@domian.com",
      "extraTags": {
        "imagePipeline": "AMIBuilder"
      },
      "distributionList": [
        "account1",
        "account2"
      ],
      "amiPublishingRegions": [
        "<<ADD_AMI_PUBLISHING_REGION_HERE>>"
      ],
      "amiPublishingTargetIds": [
        "<<ADD_AMI_PUBLISHING_TARGET_ACCOUNT_IDS_HERE>>"
      ],
      "amiSharingIds": [
        "<<ADD_AMI_SHARING_ACCOUNT_IDS_HERE>>"
      ]
    }
  }
}
```

Add your environment specific values to the [cdk.json](cdk.json) file as follows:

* Replace placeholder `<<ADD_VPD_ID_HERE>>` with your Vpc Id.
* Replace placeholder `<<ADD_SUBNET_ID_HERE>>` with your Subnet Id. The subnet you select must be part of the Vpc you defined in the previous step.
* Replace placeholder `<<ADD_AMI_PUBLISHING_REGION_HERE>>` with the AWS regions to which you would like to publish the generated AMIs.
* Replace placeholder `<<ADD_AMI_PUBLISHING_TARGET_ACCOUNT_IDS_HERE>>` with the AWS account ids to whom you would like to publish the generated AMIs.
* Replace placeholder `<<ADD_AMI_SHARING_ACCOUNT_IDS_HERE>>` with the AWS account ids to whom you would like to share the generated AMIs.

With the placeholders replaced in the [cdk.json](cdk.json) file, the CDK stack can be deployed with the command below.

```
cdk deploy
```

Following a successful deployment, verify that two new stacks have been created within the *tooling* AWS account:

* `CDKToolkit`
* `EC2ImageBuilderAmiShare-main`

Log into the AWS Console → navigate to the CloudFormation console:

![CDK CloudFormation deployment](docs/assets/screenshots/03-cloudformation-deployed.png)

Verify the distribution settings of EC2 Image Builder.

1. Log into the AWS Console → navigate to the EC2 Image Builder console.
2. Click on the pipeline with name `ami-share-pipeline-main` to open the detailed pipeline view.
3. Click on the *Distribution settings* and review the *Distribution details*.
4. Confirm that the following values match the parameter values defined in the [cdk.json](cdk.json) file.
    1. Region
    2. Target accounts for distribution
    3. Accounts with shared permissions

![EC2 Image Builder AMI distribution settings](docs/assets/screenshots/02-distribution-settings.png)

The CDK stack has successfully deployed the EC2 Image Builder and the *Target accounts for distribution* value has been correctly set through the use of a CustomResource Lambda function.

At this point the pipeline could be *Run* in order to generate, distribute and share the AMI.

Please note that in order to distribute the generated AMI to other AWS accounts it is necessary to [set up cross-account AMI distribution with Image Builder](https://docs.aws.amazon.com/imagebuilder/latest/userguide/cross-account-dist.html).

# Clean up the CDK project

Project clean-up is a 2 step process:

1. Destroy the CDK stack.
2. Delete the *CDKToolkit* stack from CloudFormation.

Delete the stack deployed by CDK with the command below:

```
cdk destroy
```

![Destroy the CDK stack](docs/assets/screenshots/04-destroy-cdk-stack.png)

Delete the CDKToolkit CloudFormation stack.

1. Log into the AWS Console → navigate to the *CloudFormation* console.
2. Navigate to *Stacks*.
3. Select the **CDKToolkit**.
4. Click the *Delete* button.

# Executing unit tests

Unit tests for the project can be executed via the command below:

```bash
python3 -m venv .venv
source .venv/bin/activate
cdk synth && python -m pytest -v -c ./tests/pytest.ini
```

# Executing static code analysis tool

The solution includes [Checkov](https://github.com/bridgecrewio/checkov) which is a static code analysis tool for infrastructure as code (IaC).

The static code analysis tool for the project can be executed via the commands below:

```bash
python3 -m venv .venv
source .venv/bin/activate
rm -fr cdk.out && cdk synth && checkov --config-file checkov.yaml
```

**NOTE:** The Checkov tool has been configured to skip certain checks.

The Checkov configuration file, [checkov.yaml](checkov.yaml), contains a section named `skip-check`.

```
skip-check:
   - CKV_AWS_7     # Ensure rotation for customer created CMKs is enabled
   - CKV_AWS_23    # Ensure every security groups rule has a description
   - CKV_AWS_24    # Ensure no security groups allow ingress from 0.0.0.0:0 to port 22
   - CKV_AWS_25    # Ensure no security groups allow ingress from 0.0.0.0:0 to port 3389
   - CKV_AWS_26    # Ensure all data stored in the SNS topic is encrypted
   - CKV_AWS_33    # Ensure KMS key policy does not contain wildcard (*) principal
   - CKV_AWS_40    # Ensure IAM policies are attached only to groups or roles (Reducing access management complexity may in-turn reduce opportunity for a principal to inadvertently receive or retain excessive privileges.)
   - CKV_AWS_45    # Ensure no hard-coded secrets exist in lambda environment
   - CKV_AWS_60    # Ensure IAM role allows only specific services or principals to assume it
   - CKV_AWS_61    # Ensure IAM role allows only specific principals in account to assume it
   - CKV_AWS_107   # Ensure IAM policies does not allow credentials exposure
   - CKV_AWS_108   # Ensure IAM policies does not allow data exfiltration
   - CKV_AWS_109   # Ensure IAM policies does not allow permissions management without constraints
   - CKV_AWS_110   # Ensure IAM policies does not allow privilege escalation
   - CKV_AWS_111   # Ensure IAM policies does not allow write access without constraints
```

These checks represent best practices in AWS and should be enabled (or at the very least the security risk of not enabling the checks should be accepted and understood) for production systems. 

In the context of this solution, these specific checks have not been remediated in order to focus on the core elements of the solution.

# Security

See [CONTRIBUTING](CONTRIBUTING.md#security-issue-notifications) for more information.

# License

This library is licensed under the MIT-0 License. See the LICENSE file.