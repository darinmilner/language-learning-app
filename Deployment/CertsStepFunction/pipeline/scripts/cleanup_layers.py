#!/usr/bin/env python3
import boto3 

lambda_client = boto3.client('lambda')

def cleanup_old_layer_versions(layer_name, keep_versions=5):
    # Get all versions of the layer
    response = lambda_client.list_layer_versions(LayerName=layer_name)
    versions = response['LayerVersions']
    
    # Sort by version number (newest first)
    versions.sort(key=lambda x: x['Version'], reverse=True)
    
    # Delete old versions (keep the most recent ones)
    for version in versions[keep_versions:]:
        print(f"Deleting {layer_name} version {version['Version']}")
        lambda_client.delete_layer_version(
            LayerName=layer_name,
            VersionNumber=version['Version']
        )

if __name__ == "__main__":
    cleanup_old_layer_versions("python_layer")
