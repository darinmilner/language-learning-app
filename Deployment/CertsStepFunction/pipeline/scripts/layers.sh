#!/bin/bash

cd ../../terraform/lambdas

# Create directories for layers
mkdir -p layers/python

cd layers/python
pip install -r requirements.txt
# Create zip files for layers
zip -r ../python_layer.zip . && cd ../..

echo "Layers built successfully"