# Start from the official Jenkins LTS image
FROM jenkins/jenkins:lts

# Switch to root to install packages
USER root

# Install Docker CLI and dependencies
RUN apt-get update && apt-get install -y \
    docker.io \
    git \
    curl \
    sudo \
    && rm -rf /var/lib/apt/lists/*

# Add Jenkins to the Docker group
RUN groupadd -g 999 docker || true && usermod -aG docker jenkins

# Install Jenkins plugins (e.g., GitHub plugin)
COPY plugins.txt /usr/share/jenkins/ref/plugins.txt
RUN jenkins-plugin-cli --plugin-file /usr/share/jenkins/ref/plugins.txt

# Preconfigure admin user
COPY security.groovy /usr/share/jenkins/ref/init.groovy.d/security.groovy

# Change back to the jenkins user
USER jenkins

# Expose ports
EXPOSE 8080 50000

# Jenkins home directory
VOLUME /var/jenkins_home
