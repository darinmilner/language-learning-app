def buildPythonEnvironment() {
    echo "Installing Python environment"
    sh """
        apt update
        apt install python3-pip -y
        python3 --version
        pip3 install -r requirements.txt
    """
}

def configureAWSProfile(String awsRegion) {
    echo "Install AWS CLI"

    sh 'pip install --upgrade awscli'

    echo "Configuring AWS Profile"

    withCredentials([usernamePassword(credentialsId: "amazon", usernameVariable: "ACCESSKEY", passwordVariable: "SECRETKEY")]) {
        sh 'aws configure set aws_access_key_id $ACCESSKEY --profile Default'
        sh 'aws configure set aws_secret_access_key $SECRETKEY --profile Default'
    }

    try {
        sh """
            aws configure set region ${awsRegion} --profile Default
            aws configure set output "json" --profile Default
        """

    } catch (Exception err) {
        echo "Error configuring AWS Profile $err"
        throw err
    }
}

return this