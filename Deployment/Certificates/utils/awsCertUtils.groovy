def loadAWSSDK() {
    // Load SDK from pre-installed location
    def sdkDir = new File('/opt/aws-sdk/latest')
    if(!sdkDir.exists()) {
        error "AWS SDK not found at ${sdkDir.path}"
    }
    
    // Add JARs to classpath
    def classLoader = this.class.classLoader
    sdkDir.eachFileRecurse { file ->
        if(file.name.endsWith('.jar')) {
            classLoader.addURL(file.toURI().toURL())
        }
    }
    echo "AWS SDK loaded successfully"
}

def createS3Bucket(region, bucketName) {
    loadAWSSDK()
    def s3 = new com.amazonaws.services.s3.AmazonS3ClientBuilder()
                .withRegion(region)
                .build()
    
    if(!s3.doesBucketExistV2(bucketName)) {
        s3.createBucket(bucketName)
        s3.setBucketEncryptionConfiguration(
            new com.amazonaws.services.s3.model.SetBucketEncryptionConfigurationRequest(
                bucketName,
                new com.amazonaws.services.s3.model.BucketEncryptionConfiguration()
                    .withServerSideEncryptionConfiguration(
                        new com.amazonaws.services.s3.model.ServerSideEncryptionConfiguration()
                            .withRules(
                                new com.amazonaws.services.s3.model.ServerSideEncryptionRule()
                                    .withApplyServerSideEncryptionByDefault(
                                        new com.amazonaws.services.s3.model.ServerSideEncryptionByDefault()
                                            .withSSEAlgorithm("AES256")
                                    )
                            )
                    )
            )
        )
        echo "Created encrypted bucket: ${bucketName}"
    }
    return bucketName
}

def checkCertificate(domain, region) {
    loadAWSSDK()
    def acm = new com.amazonaws.services.certificatemanager.AWSCertificateManagerClientBuilder()
                .withRegion(region)
                .build()
    
    def certificates = acm.listCertificates().certificateSummaryList
    def now = new Date()
    
    for(cert in certificates) {
        if(cert.domainName == domain) {
            def details = acm.describeCertificate(
                new com.amazonaws.services.certificatemanager.model.DescribeCertificateRequest()
                    .withCertificateArn(cert.certificateArn)
            )
            
            if(details.certificate.status == "ISSUED" && 
               details.certificate.notAfter.after(now)) {
                echo "Found valid certificate: ${cert.certificateArn}"
                return cert.certificateArn
            }
        }
    }
    return null
}

def generateCertificate(domain, email, workDir) {
    withCredentials([
        string(credentialsId: 'CERTBOT_AWS_ACCESS_KEY', variable: 'AWS_ACCESS_KEY_ID'),
        string(credentialsId: 'CERTBOT_AWS_SECRET_KEY', variable: 'AWS_SECRET_ACCESS_KEY')
    ]) {
        sh """
        docker run --rm --read-only \
            -e AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID} \
            -e AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY} \
            -v ${workDir}:/cert-output \
            certbot/dns-route53 certonly \
            --non-interactive \
            --agree-tos \
            --email ${email} \
            --dns-route53 \
            -d ${domain} \
            --config-dir /cert-output \
            --work-dir /tmp \
            --logs-dir /tmp
        """
    }
}

def encryptAndUpload(bucketName, region, workDir, domain, gpgPassphrase) {
    loadAWSSDK()
    def s3 = new com.amazonaws.services.s3.AmazonS3ClientBuilder()
                .withRegion(region)
                .build()
    
    // Encrypt private key
    sh "gpg --batch --passphrase ${gpgPassphrase} -c ${workDir}/live/${domain}/privkey.pem"
    
    // Upload files
    def uploadFile = { key, filePath ->
        s3.putObject(bucketName, key, new File(filePath))
    }
    
    uploadFile("cert.pem", "${workDir}/live/${domain}/cert.pem")
    uploadFile("chain.pem", "${workDir}/live/${domain}/chain.pem")
    uploadFile("privkey.gpg", "${workDir}/live/${domain}/privkey.pem.gpg")
}

def importCertificate(bucketName, region, domain, gpgPassphrase) {
    loadAWSSDK()
    def lambda = new com.amazonaws.services.lambda.AWSLambdaClientBuilder()
                    .withRegion(region)
                    .build()
    
    def payload = [
        action: 'import_certificate',
        domain: domain,
        region: region,
        s3_bucket: bucketName,
        gpg_passphrase: gpgPassphrase
    ]
    
    def request = new com.amazonaws.services.lambda.model.InvokeRequest()
        .withFunctionName("acm-cert-manager")
        .withPayload(JsonOutput.toJson(payload))
    
    def result = lambda.invoke(request)
    def response = new groovy.json.JsonSlurper().parseText(result.payload.array())
    
    if(response.errorMessage) {
        error "Certificate import failed: ${response.errorMessage}"
    }
    return response.arn
}

def cleanupS3Bucket(bucketName, region) {
    loadAWSSDK()
    def s3 = new com.amazonaws.services.s3.AmazonS3ClientBuilder()
                .withRegion(region)
                .build()
    
    // Delete all objects
    def objects = s3.listObjectsV2(bucketName).objectSummaries
    objects.each { obj ->
        s3.deleteObject(bucketName, obj.key)
    }
    
    // Delete bucket
    s3.deleteBucket(bucketName)
    echo "Cleaned up S3 bucket: ${bucketName}"
}