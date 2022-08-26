#!/bin/bash

###################################################################
# Script Name     : create_stack.sh
# Description     : Executes the EC2ImageBuilderAmiShare.yaml
#                   CloudFormation templatre supplying the
#                   parameters defined in this script.
# Args            :
# Author          : Damian McDonald
###################################################################

### <START> check if AWS credential variables are correctly set
if [ -z "${AWS_ACCESS_KEY_ID}" ]
then
      echo "AWS credential variable AWS_ACCESS_KEY_ID is empty."
      echo "Please see the guide below for instructions on how to configure your AWS CLI environment."
      echo "https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-envvars.html"
fi

if [ -z "${AWS_SECRET_ACCESS_KEY}" ]
then
      echo "AWS credential variable AWS_SECRET_ACCESS_KEY is empty."
      echo "Please see the guide below for instructions on how to configure your AWS CLI environment."
      echo "https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-envvars.html"
fi

if [ -z "${AWS_DEFAULT_REGION}" ]
then
      echo "AWS credential variable AWS_DEFAULT_REGION is empty."
      echo "Please see the guide below for instructions on how to configure your AWS CLI environment."
      echo "https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-envvars.html"
fi
### </END> check if AWS credential variables are correctly set

# Parameters
VPC_ID="<<ADD_VPC_ID>>"
SUBNET_ID="<<ADD_SUBNET_ID>>"
# each of the variables below support multiple entries.
# Multiple entries should be separated by an escaped comma; 
# "eu-west-1\,eu-west-2"
AMI_PUBLISHING_REGION="<<ADD_PUBLISHING_REGIONS>>"
AMI_PUBLISHING_TARGETS="<<ADD_PUBLISHING_TARGETS>>"
AMI_SHARING_ACCOUNTS="<<ADD_SHARING_ACCOUNTS>>"

aws cloudformation create-stack \
    --stack-name Ec2ImageBuilderAmiShare \
    --template-body file://EC2ImageBuilderAmiShare.yaml \
    --parameters ParameterKey=VpcIdParameter,ParameterValue="${VPC_ID}" \
                 ParameterKey=SubnetIdParameter,ParameterValue="${SUBNET_ID}" \
                 ParameterKey=AmiPublishingRegionsParameter,ParameterValue="${AMI_PUBLISHING_REGION}" \
                 ParameterKey=AmiPublishingTargetIdsParameter,ParameterValue="${AMI_PUBLISHING_TARGETS}" \
                 ParameterKey=AmiSharingAccountIdsParameter,ParameterValue="${AMI_SHARING_ACCOUNTS}" \
    --capabilities CAPABILITY_NAMED_IAM