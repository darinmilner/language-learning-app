✅ How to use
Push a single image (defaults to latest)
python docker_login.py lambda
If your local image is lambda:latest, this works fine.

Push multiple images with explicit tags
python docker_login.py lambda:1.0 package main:2.0 --tag sha-123abc
This will:

Tag each image as my-repo:<repo>-<tag_suffix> (e.g., lambda-sha-123abc)

Push to your ECR repository

Stream progress and show errors

Notes
Automatically defaults tag to latest if none is provided

Handles multiple images in one command

Avoids the common Docker 404 (latest:latest) by always requiring a repository

Simple and perfect for demos