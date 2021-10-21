import setuptools


with open("README.md") as fp:
    long_description = fp.read()


setuptools.setup(
    name="ec2_imagebuilder_ami_share",
    version="0.0.1",

    description="CloudFormation template and CDK stack that contains a CustomResource with Lambda function to allow the setting of the targetAccountIds attribute of the EC2 Image Builder AMI distribution settings which is not currently supported in CloudFormation or CDK.",
    long_description=long_description,
    long_description_content_type="text/markdown",

    author="Damian Francis McDonald",
    author_email="damiamcd@amazon.es",

    package_dir={"": "ec2_imagebuilder_ami_share"},
    packages=setuptools.find_packages(where="ec2_imagebuilder_ami_share"),

    install_requires=[
        "aws-cdk.core==1.123.0",
    ],

    python_requires=">=3.6",

    classifiers=[
        "Development Status :: 4 - Beta",

        "Intended Audience :: Developers",

        "Programming Language :: JavaScript",
        "Programming Language :: Python :: 3 :: Only",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",

        "Topic :: Software Development :: Code Generators",
        "Topic :: Utilities",

        "Typing :: Typed",
    ],
)
