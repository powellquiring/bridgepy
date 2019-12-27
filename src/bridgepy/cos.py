import ibm_boto3
from ibm_botocore.client import Config
import json

with open("creds.json") as f:
    creds = json.load(f)

api_key = creds["apikey"]
service_instance_id = creds["resource_instance_id"]
auth_endpoint = 'https://iam.bluemix.net/oidc/token'
service_endpoint = 'https://s3-api.us-geo.objectstorage.softlayer.net'

new_bucket = 'pfq-newbucket'
new_cold_bucket = 'pfq-newcoldbucket'

cos = ibm_boto3.resource('s3',
    ibm_api_key_id=api_key,
    ibm_service_instance_id=service_instance_id,
    ibm_auth_endpoint=auth_endpoint,
    config=Config(signature_version='oauth'),
    endpoint_url=service_endpoint)

for bucket in cos.buckets.all():
    print(bucket.name)

cos.create_bucket(Bucket=new_bucket)

