# acm-cert-manager.py
import boto3
import gnupg
import tempfile
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    s3 = boto3.client('s3')
    acm = boto3.client('acm', region_name=event['region'])
    
    try:
        if event['action'] == 'import_certificate':
            return handle_import(event, s3, acm)
        else:
            return {"error": "Invalid action specified"}
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        return {"errorMessage": str(e)}

def handle_import(event, s3, acm):
    with tempfile.TemporaryDirectory() as tmpdir:
        # Download files from S3
        s3.download_file(event['s3_bucket'], 'cert.pem', f'{tmpdir}/cert.pem')
        s3.download_file(event['s3_bucket'], 'chain.pem', f'{tmpdir}/chain.pem')
        s3.download_file(event['s3_bucket'], 'privkey.gpg', f'{tmpdir}/privkey.gpg')
        
        # Initialize GPG
        gpg = gnupg.GPG(gnupghome=tmpdir)
        
        # Decrypt private key
        with open(f'{tmpdir}/privkey.gpg', 'rb') as f:
            decrypted = gpg.decrypt_file(f, passphrase=event['gpg_passphrase'])
            
        if not decrypted.ok:
            raise Exception(f"Decryption failed: {decrypted.status}")
            
        with open(f'{tmpdir}/privkey.pem', 'w') as f:
            f.write(str(decrypted))
        
        # Read certificate files
        with open(f'{tmpdir}/cert.pem', 'r') as f1, \
             open(f'{tmpdir}/privkey.pem', 'r') as f2, \
             open(f'{tmpdir}/chain.pem', 'r') as f3:
            
            cert = f1.read()
            private_key = f2.read()
            chain = f3.read()
            
            # Import to ACM
            response = acm.import_certificate(
                Certificate=cert,
                PrivateKey=private_key,
                CertificateChain=chain
            )
            
            return {
                "arn": response['CertificateArn'],
                "domain": event['domain']
            }