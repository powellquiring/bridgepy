import bridgepy
import json

api_key = "api_key"
def main(dict):
    body = bridgepy.function_call_get_score(dict)
    return { 'body': body }

import os
if __name__=="__main__":
    the_api_key = "no BRIDGEPY_API_KEY in environment"
    if "BRIDGEPY_API_KEY" in os.environ:
        the_api_key = os.environ["BRIDGEPY_API_KEY"]
        d = main({"api_key": the_api_key})
        print(json.dumps(d))
    else:
        print('Expecting BRIDGEPY_API_KEY')
