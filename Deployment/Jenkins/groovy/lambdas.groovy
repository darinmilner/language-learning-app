// groovy/lambdas.groovy

def validateLambdaFolder(lambdaFolder) {
    if (!fileExists("${lambdaFolder}")) {
        error "🚫 Lambda folder '${lambdaFolder}' not found"
    }
    if (!fileExists("${lambdaFolder}/requirements.txt")) {
        echo "⚠️ No requirements.txt found - proceeding without dependencies"
    }
    echo "✅ Validated Lambda folder: ${lambdaFolder}"
}

def setupPythonEnvironment(lambdaFolder, venvDir) {
    sh """
        # Create virtual environment
        python3 -m venv ${lambdaFolder}/${venvDir}
        
        # Activate virtual environment
        . ${lambdaFolder}/${venvDir}/bin/activate
        
        # Upgrade base tools
        pip install --upgrade pip setuptools
        deactivate
    """
    echo "🐍 Created Python virtual environment"
}

def installPythonDependencies(lambdaFolder, venvDir) {
    // Only install if requirements.txt exists
    if (fileExists("${lambdaFolder}/requirements.txt")) {
        sh """
            . ${lambdaFolder}/${venvDir}/bin/activate
            pip install -r ${lambdaFolder}/requirements.txt -t ${lambdaFolder}/
            deactivate
        """
        echo "📦 Installed Python dependencies"
    }
}

def packageLambdaFunction(lambdaFolder, venvDir) {
    sh """
        # Package with site-packages and lambda code
        cd ${lambdaFolder}
        
        # Include hidden files and maintain directory structure
        zip -r9 ../${lambdaFolder}.zip . -x "${venvDir}/*" 
        cd ..
    """
    echo "📦 Created deployment package: ${lambdaFolder}.zip"
}

def uploadToS3(lambdaFolder, s3Bucket, awsRegion, awsCredentialsId) {
    withCredentials([[
        $class: 'AmazonWebServicesCredentialsBinding',
        credentialsId: awsCredentialsId
    ]]) {
        sh """
            aws s3 cp ${lambdaFolder}.zip \
                s3://${s3Bucket}/${lambdaFolder}/${lambdaFolder}.zip \
                --region ${awsRegion}
        """
    }
    echo "🚀 Uploaded to S3: s3://${s3Bucket}/${lambdaFolder}/"
}

def cleanUpResources(lambdaFolder, venvDir) {
    // Remove zip file
    sh "rm -f ${lambdaFolder}.zip || true"
    
    // Remove virtual environment
    sh "rm -rf ${lambdaFolder}/${venvDir} || true"
    
    // Remove installed packages (if any)
    if (fileExists("${lambdaFolder}/requirements.txt")) {
        sh """
            rm -rf ${lambdaFolder}/bin \
                   ${lambdaFolder}/include \
                   ${lambdaFolder}/lib \
                   ${lambdaFolder}/__pycache__ || true
        """
    }
    echo "Cleaned up build artifacts"
}

// Return utility map for external access
return [
    validate: this.&validateLambdaFolder,
    setupEnv: this.&setupPythonEnvironment,
    installDeps: this.&installPythonDependencies,
    package: this.&packageLambdaFunction,
    uploadS3: this.&uploadToS3,
    cleanup: this.&cleanUpResources
]