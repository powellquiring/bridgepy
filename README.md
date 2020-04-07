# bridgepy
Bridge scoring program.  Results can be stored locally on the file system but by default in ibm COS.

A IBM cloud function can be deployed in an existing cloud foundry namespace will return the score from the COS object.

A new IBM cloud function can be deployed in an existing cloud foundry namespace that will return the score from the COS object.

The github repository GitHub pages will return the score


# Notes 
Following the steps below will result in two files that you do not want to push to a source code repo:
- local.env
- terraform.tfvars - this file contains your api key

# Instructions

1. fork this github repo and clone it
1. in the github fork, open settings, turn on GitHub pages and choose **Select Source** as **master branch /docs** folder.  Then check out the GitHub section where it says **ready to be published at** for me it was https://powellquiring.github.io/bridgepy/.  This is the link users will use to see the score
1. In the ibm cloud console open [function namespace](https://cloud.ibm.com/functions/namespace-settings) and verify that a CF-Based namespace exists
1. cp local.env.template local.env; # edit the local.env file based on the comments
1. make all
1. eval $(make export);# BRIDGEPY variables put into environment
1. make venv
1. source venv/bin/activate

# Details and Trouble Shooting
**Make all** has a few steps.  The **prereq** target verifies that terraform is installed and is version v0.12 and the ibm provider is installed.  See the IBM docs for installing this stuff if it fails.
```
make prereq
terraform -version > /dev/null
terraform -version | grep 'Terraform v0.12'
Terraform v0.12.18
terraform -version | grep provider.ibm
+ provider.ibm v1.0.0
```

# Running cloud function code locally
Make the python virtual environment, source the python venv, initialize the environment variables
```
make venv
source venv/bin/activate
which python
make export
eval $(make export)
cd src
python __main__.py

# Debugging
```
make env
```
Take the output and past it into visual studio code launch.json debug configuraion.  Mine looked something like the following:
```
...
{
    "configurations": [
    ...
        {
            "name": "Debug Tests",
            "type": "python",
            "request": "test",
            "console": "integratedTerminal",
            "env": {
                "BRIDGEPY_ROOT": "bridgepy01",
                "BRIDGEPY_API_KEY": "NOTREALSTUFFNOTAPIKEY",
                "BRIDGEPY_COS_INSTANCE_ID": "crn:v1:bluemix:public:cloud-object-storage:global:a/12ab12ab12ab12ab12ab12ab12ab12ab:12ab12ab-12ab-12ab-12ab-12ab12ab12ab::",
                "BRIDGEPY_COS_SERVICE_ENDPOINT": "https://s3.us-south.cloud-object-storage.appdomain.cloud"
            }
        }
    ]
}
```

# Tutorial
I started with the great tutorial [Serverless web application and API[(https://cloud.ibm.com/docs/tutorials?topic=solution-tutorials-serverless-api-webapp#serverless-api-webapp)
