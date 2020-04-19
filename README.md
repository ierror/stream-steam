StreamSteam
-----------

Scalable and Hackable Analytics for AWS

> Installed and configured in minutes, yet extensible and scalable  

## Installation and Setup

Fork the project and run git clone as always

### Install pipenv globally e.g.

    pip3 install pipenv

### Install project dependencies. pipenv takes care of creating the virtualenv for you - omit the `--dev` flag for installations in production environments    
    
    pipenv install --dev --python python3.7
    
### Activate the created virtualenv

    pipenv shell

## Quickstart

Configure the project

    ./stream-steam config
    
Deploy it!

    ./stream-steam deploy
    
Describe your deployment

    ./stream-steam describe-deployment
    
Run the Webtracking Demo

    ./stream-steam demo-web-tracking
    
After 60s you can inspect the enriched events in your S3 Bucket (S3BucketName)

    /enriched/...
    
Destroy it!

    ./stream-steam destroy
    
Whats next?

## Moudules

    ./stream-steam module list

### Redash

    ./stream-steam module enable --name redash
    
... TODO
