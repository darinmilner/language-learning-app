def downloadTerraform(version = '1.8.1') {
    def os = "linux"
    def arch = "amd64"
    def url = "https://releases.hashicorp.com/terraform/${version}/terraform_${version}_${os}_${arch}.zip"

    echo "Downloading Terraform ${version} from ${url}"
    sh """
        curl -o terraform.zip ${url}
        unzip terraform.zip
        chmod +x terraform
        mv terraform /usr/local/bin/terraform || sudo mv terraform /usr/local/bin/terraform
        rm terraform.zip
    """
}

def terraformInit(String dir) {
    echo "Initializing Terraform in directory: ${dir}"
    sh "cd ${dir} && terraform init"
}

def terraformValidate(String dir) {
    echo "Validating Terraform configuration in directory: ${dir}"
    sh "cd ${dir} && terraform validate"
}

def terraformApply(String dir) {
    echo "Applying Terraform configuration in directory: ${dir}"
    sh "cd ${dir}/scripts python3 run_terraform.py"
}

def terraformDestroy(String dir, String tfVarsFile = 'terraform.tfvars') {
    echo "Destroying Terraform-managed infrastructure in directory: ${dir}"
    // sh "cd ${dir} && terraform destroy -auto-approve -var-file=${tfVarsFile}"
    // TODO: pass destroy command to python file
    sh "cd ${dir}/scripts python3 run_terraform.py"
}

return this
