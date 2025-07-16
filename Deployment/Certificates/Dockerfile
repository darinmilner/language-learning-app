# Dockerfile.jenkins-agent
FROM jenkins/agent:jdk11

# Install AWS SDK
ENV AWS_SDK_VERSION=1.12.678
RUN mkdir -p /opt/aws-sdk && \
    curl -s "https://sdk-for-java.amazonwebservices.com/aws-java-sdk-${AWS_SDK_VERSION}.zip" -o aws-sdk.zip && \
    unzip aws-sdk.zip -d /opt/aws-sdk && \
    rm aws-sdk.zip && \
    mv /opt/aws-sdk/aws-java-sdk-${AWS_SDK_VERSION} /opt/aws-sdk/latest

# Install certbot and AWS CLI for DNS validation
RUN apt-get update && \
    apt-get install -y certbot python3-pip && \
    pip3 install awscli && \
    rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /home/jenkins