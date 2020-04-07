import ibm_boto3
from ibm_botocore.client import Config
import json

with open("creds.json") as f:
    creds = json.load(f)

api_key = creds["apikey"]
service_instance_id = creds["resource_instance_id"]
auth_endpoint = 'https://iam.bluemix.net/oidc/token'
service_endpoint = 'https://s3-api.us-geo.objectstorage.softlayer.net'

bridgepy_bucket = 'pfq-bridgepy'

# ibm_auth_endpoint=auth_endpoint,
cos = ibm_boto3.resource('s3',
    ibm_api_key_id=api_key,
    ibm_service_instance_id=service_instance_id,
    config=Config(signature_version='oauth'),
    endpoint_url=service_endpoint,
)

client = ibm_boto3.client('s3',
    ibm_api_key_id=api_key,
    ibm_service_instance_id=service_instance_id,
    config=Config(signature_version='oauth'),
    endpoint_url=service_endpoint,
)
waiter_bucket_exists = client.get_waiter('bucket_exists')
waiter_bucket_not_exists = client.get_waiter('bucket_not_exists')

bucket = cos.Bucket(bridgepy_bucket)
bucket.load()
buckets = {bucket.name: bucket for bucket in cos.buckets.all()}
if bridgepy_bucket in buckets:
    bucket = buckets[bridgepy_bucket]
    print("bucket exists")
else:
    print("creating a bucket")
    bucket = cos.create_bucket(Bucket=bridgepy_bucket)
    print("waitin")
    waiter_bucket_exists.wait(Bucket=bridgepy_bucket)

print(bucket.name)