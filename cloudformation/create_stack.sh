#!/bin/bash

# Parameters
VPC_ID="vpc-58db6321"
SUBNET_ID="subnet-c0f1348b"
AMI_PUBLISHING_REGION="eu-west-1\,eu-west-2"
AMI_PUBLISHING_TARGETS="582036921242"
AMI_SHARING_ACCOUNTS="582036921242\,774136563876"

aws cloudformation create-stack \
    --stack-name Ec2ImageBuilderAmiShare \
    --template-body file://EC2ImageBuilderAmiShare.yaml \
    --parameters ParameterKey=VpcIdParameter,ParameterValue="${VPC_ID}" \
                 ParameterKey=SubnetIdParameter,ParameterValue="${SUBNET_ID}" \
                 ParameterKey=AmiPublishingRegionsParameter,ParameterValue="${AMI_PUBLISHING_REGION}" \
                 ParameterKey=AmiPublishingTargetIdsParameter,ParameterValue="${AMI_PUBLISHING_TARGETS}" \
                 ParameterKey=AmiSharingAccountIdsParameter,ParameterValue="${AMI_SHARING_ACCOUNTS}" \
    --capabilities CAPABILITY_NAMED_IAM