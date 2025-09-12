// vars/terraformUtils.groovy

def installTerraform(version = '1.1.7') {
    echo "Installing Terraform ${version}"
    sh """
        wget https://releases.hashicorp.com/terraform/${version}/terraform_${version}_linux_amd64.zip
        unzip terraform_${version}_linux_amd64.zip
        sudo mv terraform /usr/local/bin/
        rm terraform_${version}_linux_amd64.zip
        terraform version
    """
}

def installAwsCli(version = '2.4.0') {
    echo "Installing AWS CLI ${version}"
    sh """
        curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64-${version}.zip" -o "awscliv2.zip"
        unzip awscliv2.zip
        sudo ./aws/install --update
        rm -rf awscliv2.zip aws/
        aws --version
    """
}

def buildLambdaLayers() {
    echo "Building Lambda layers"
    sh """
        chmod +x scripts/layers.sh
        ./scripts/layers.sh
    """
}

def terraformInit(directory = 'terraform') {
    echo "Initializing Terraform in ${directory}"
    dir(directory) {
        sh 'terraform init'
    }
}

def terraformPlan(directory = 'terraform', extraArgs = '') {
    echo "Running Terraform plan in ${directory}"
    dir(directory) {
        sh "terraform plan ${extraArgs}"
    }
}

def terraformApply(directory = 'terraform', extraArgs = '') {
    echo "Applying Terraform configuration in ${directory}"
    dir(directory) {
        sh "terraform apply -auto-approve ${extraArgs}"
    }
}

def terraformDestroy(directory = 'terraform', extraArgs = '') {
    echo "Destroying Terraform resources in ${directory}"
    dir(directory) {
        sh "terraform destroy -auto-approve ${extraArgs}"
    }
}

def terraformOutput(directory = 'terraform', outputName = '') {
    echo "Getting Terraform output from ${directory}"
    dir(directory) {
        def output = sh(
            script: "terraform output -json ${outputName}",
            returnStdout: true
        ).trim()
        return output
    }
}

def validateTerraform(directory = 'terraform') {
    echo "Validating Terraform configuration in ${directory}"
    dir(directory) {
        sh 'terraform validate'
    }
}

def setupTerraformBackend(bucket, key, region) {
    echo "Setting up Terraform backend configuration"
    def backendConfig = """
        terraform {
            backend "s3" {
                bucket = "${bucket}"
                key    = "${key}"
                region = "${region}"
            }
        }
    """
    writeFile file: 'terraform/backend.tf', text: backendConfig
}

def cleanupTerraform() {
    echo "Cleaning up Terraform files"
    sh '''
        rm -rf .terraform
        rm -f .terraform.lock.hcl
        rm -f terraform.tfstate*
        rm -f tfplan
    '''
}