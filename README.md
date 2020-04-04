StreamSteam
-----------

Scaleable and Hackable Analytics on AWS 


## Installation and Setup

Fork the project and run git clone as always

### Install pipenv globally e.g.

    pip3 install pipenv

###. Install project dependencies. pipenv takes care of creating the virtualenv for you - omit the `--dev` flag for installations in production environments    
    
    pipenv install --dev --python python3.7
    
### Activate the created virtualenv

    pipenv shell

## Quickstart

Configure the project

    ./stream-steam config
    
Deploy it!

    ./stream-steam config
    
Describe your deployment

    ./steam-steam describe-deployment
    
Run the Webtracking Demo

    ./steam-steam webtracking-demo
    
After 60s you can inspect the enriched events in your S3 Bucket (S3BucketName)

    /enriched/...
    
Destroy it!

    ./steam-steam destroy
    
Whats next?
