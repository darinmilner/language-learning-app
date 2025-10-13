// terraformUtils.groovy

def installTerraform(version = '1.1.7') {
    echo "Installing Terraform ${version}"
    sh """
        wget -q https://releases.hashicorp.com/terraform/${version}/terraform_${version}_linux_amd64.zip
        unzip -q terraform_${version}_linux_amd64.zip
        sudo mv terraform /usr/local/bin/
        rm terraform_${version}_linux_amd64.zip
        terraform version
    """
}

def installAwsCli(version = '2.4.0') {
    echo "Installing AWS CLI ${version}"
    sh """
        curl -s "https://awscli.amazonaws.com/awscli-exe-linux-x86_64-${version}.zip" -o "awscliv2.zip"
        unzip -q awscliv2.zip
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

def packageLambdaFunctions() {
    echo "Packaging Lambda functions"
    
    def lambdaDirs = [
        'lambdas/check_certificate',
        'lambdas/generate_certificate',
        'lambdas/replace_certificate'
    ]
    
    lambdaDirs.each { dir ->
        if (fileExists(dir)) {
            echo "Packaging ${dir}"
            // Remove any existing zip files and test artifacts
            sh """
                cd ${dir} && \
                rm -f *.zip && \
                rm -rf __pycache__ && \
                rm -rf *.pyc && \
                rm -rf htmlcov && \
                rm -f .coverage && \
                rm -f coverage.xml
            """
            
            // Create zip file with only necessary files
            sh """
                cd ${dir} && \
                zip -r ../${dir.split('/').last()}.zip . -x "test_*" "*.pyc" "__pycache__/*" ".pytest_cache/*" "htmlcov/*"
            """
        }
    }
    
    echo "Lambda functions packaged successfully"
}