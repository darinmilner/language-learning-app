// pythonUtils.groovy

def installPythonDependencies() {
    echo "Installing Python testing dependencies"
    sh """
        pip install --upgrade pip
        pip install pytest pytest-mock pytest-cov boto3 moto
    """
}

def installLambdaDependencies() {
    echo "Installing Lambda-specific dependencies from requirements.txt"
    
    // Install dependencies for each Lambda function
    def lambdaDirs = [
        'lambdas/check_certificate',
        'lambdas/generate_certificate', 
        'lambdas/replace_certificate'
    ]
    
    lambdaDirs.each { dir ->
        if (fileExists("${dir}/requirements.txt")) {
            echo "Installing dependencies for ${dir}"
            dir(dir) {
                sh "pip install -r requirements.txt -t ."
            }
        }
    }
}

def runLambdaTests() {
    echo "Running Lambda function unit tests with coverage"
    
    def testResults = [:]
    def lambdaDirs = [
        'check_certificate': 'lambdas/check_certificate',
        'generate_certificate': 'lambdas/generate_certificate',
        'replace_certificate': 'lambdas/replace_certificate'
    ]
    
    // Run tests for each Lambda function
    lambdaDirs.each { lambdaName, dirPath ->
        echo "Running tests for ${lambdaName}"
        dir(dirPath) {
            try {
                def coverage = sh(
                    script: "python -m pytest test_*.py -v --cov=. --cov-report=term --cov-report=html --cov-report=xml",
                    returnStdout: true
                ).trim()
                
                testResults[lambdaName] = [
                    status: 'SUCCESS',
                    coverage: extractCoveragePercentage(coverage),
                    output: coverage
                ]
                
                echo "✅ ${lambdaName} tests passed with ${testResults[lambdaName].coverage}% coverage"
                
            } catch (Exception e) {
                testResults[lambdaName] = [
                    status: 'FAILED',
                    coverage: '0%',
                    output: e.getMessage()
                ]
                
                echo "❌ ${lambdaName} tests failed"
                currentBuild.result = 'UNSTABLE'
            }
        }
    }
    
    return testResults
}

def extractCoveragePercentage(coverageOutput) {
    // Extract coverage percentage from pytest output
    def coverageMatch = coverageOutput =~ /TOTAL\\s+\\d+\\s+\\d+\\s+(\\d+)%/
    if (coverageMatch) {
        return "${coverageMatch[0][1]}%"
    }
    return "Unknown"
}

def generateCombinedCoverageReport(testResults, bucketName) {
    echo "Generating combined test coverage report"
    
    // Create combined HTML report
    def htmlReport = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Lambda Test Coverage Report</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; }
            .summary { background: #f5f5f5; padding: 20px; border-radius: 5px; }
            .lambda { margin: 10px 0; padding: 10px; border-left: 4px solid #007acc; }
            .success { border-left-color: #28a745; }
            .failed { border-left-color: #dc3545; }
            .coverage { font-weight: bold; }
            .high { color: #28a745; }
            .medium { color: #ffc107; }
            .low { color: #dc3545; }
        </style>
    </head>
    <body>
        <h1>Lambda Test Coverage Report</h1>
        <div class="summary">
            <h2>Test Summary</h2>
            <p><strong>Generated:</strong> ${new Date()}</p>
            <p><strong>Total Lambdas:</strong> ${testResults.size()}</p>
            <p><strong>Passed:</strong> ${testResults.findAll { it.value.status == 'SUCCESS' }.size()}</p>
            <p><strong>Failed:</strong> ${testResults.findAll { it.value.status == 'FAILED' }.size()}</p>
        </div>
        <h2>Lambda Details</h2>
    """
    
    testResults.each { lambdaName, result ->
        def statusClass = result.status == 'SUCCESS' ? 'success' : 'failed'
        def coverageClass = getCoverageClass(result.coverage)
        
        htmlReport += """
        <div class="lambda ${statusClass}">
            <h3>${lambdaName}</h3>
            <p><strong>Status:</strong> ${result.status}</p>
            <p><strong>Coverage:</strong> <span class="coverage ${coverageClass}">${result.coverage}</span></p>
            <details>
                <summary>Test Output</summary>
                <pre>${result.output.replace('<', '&lt;').replace('>', '&gt;')}</pre>
            </details>
        </div>
        """
    }
    
    htmlReport += """
    </body>
    </html>
    """
    
    // Write combined report to file
    writeFile file: 'combined-coverage-report.html', text: htmlReport
    
    return htmlReport
}

def getCoverageClass(coverage) {
    def coverageValue = coverage.replace('%', '') as Integer
    if (coverageValue >= 80) return 'high'
    if (coverageValue >= 60) return 'medium'
    return 'low'
}

def uploadTestReportsToS3(bucketName, region) {
    echo "Uploading test reports to S3 bucket: ${bucketName}"
    
    def timestamp = new Date().format("yyyy-MM-dd-HH-mm-ss")
    def buildNumber = env.BUILD_NUMBER
    def s3BasePath = "test-reports/build-${buildNumber}-${timestamp}"
    
    // Upload individual coverage reports
    def lambdaDirs = [
        'check_certificate': 'lambdas/check_certificate',
        'generate_certificate': 'lambdas/generate_certificate',
        'replace_certificate': 'lambdas/replace_certificate'
    ]
    
    lambdaDirs.each { lambdaName, dirPath ->
        dir(dirPath) {
            if (fileExists('htmlcov')) {
                sh """
                    aws s3 sync htmlcov/ s3://${bucketName}/${s3BasePath}/${lambdaName}/htmlcov/ --region ${region}
                """
                echo "Uploaded HTML coverage for ${lambdaName}"
            }
            if (fileExists('coverage.xml')) {
                sh """
                    aws s3 cp coverage.xml s3://${bucketName}/${s3BasePath}/${lambdaName}/coverage.xml --region ${region}
                """
                echo "Uploaded XML coverage for ${lambdaName}"
            }
        }
    }
    
    // Upload combined report
    if (fileExists('combined-coverage-report.html')) {
        sh """
            aws s3 cp combined-coverage-report.html s3://${bucketName}/${s3BasePath}/combined-coverage-report.html --region ${region}
        """
        echo "Uploaded combined coverage report"
    }
    
    return s3BasePath
}

def validateTestCoverage(testResults, minimumCoverage = 70) {
    echo "Validating test coverage (minimum: ${minimumCoverage}%)"
    
    def failedLambdas = []
    testResults.each { lambdaName, result ->
        if (result.status == 'SUCCESS') {
            def coverageValue = result.coverage.replace('%', '') as Integer
            if (coverageValue < minimumCoverage) {
                failedLambdas.add("${lambdaName} (${result.coverage})")
                echo "❌ ${lambdaName} coverage ${result.coverage} below minimum ${minimumCoverage}%"
            } else {
                echo "✅ ${lambdaName} coverage ${result.coverage} meets minimum ${minimumCoverage}%"
            }
        } else {
            failedLambdas.add("${lambdaName} (TESTS FAILED)")
            echo "❌ ${lambdaName} tests failed"
        }
    }
    
    if (!failedLambdas.isEmpty()) {
        echo "Coverage validation failed for: ${failedLambdas.join(', ')}"
        currentBuild.result = 'UNSTABLE'
    } else {
        echo "✅ All Lambda functions meet minimum coverage requirements"
    }
    
    return failedLambdas.isEmpty()
}