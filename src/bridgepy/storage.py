import io
import pathlib
import click
import json
import ibm_boto3
import time
from ibm_botocore.client import Config
import enum
from typing import (NamedTuple, List, IO)

class Team(enum.Enum):
    WE = 0
    THEY = 1

class Suit(enum.Enum):
    NOTRUMP = 'n'
    SPADE = "s"
    HEART = "h"
    DIAMOND = "d"
    CLUB = "c"

class Honors(enum.IntEnum):
    H100 = 100
    H150 = 150
    NONE = 0

class Double(enum.Enum):
    NONE = 1
    DOUBLE = 2
    REDOUBLE = 4

class Result(NamedTuple):
    """Result of playing a hand.  It is using the enums which can not be converted to json so the methods
    to create a jsonable dictionary are provided"""
    team: Team
    bid: int
    suit: Suit
    over: int
    honors: Honors = Honors.NONE
    double: Double = Double.NONE
    def to_json_dictionary(self) -> dict:
        "Convert self to a jsonable dictionary"
        d = self._asdict()
        for k,v in Result.__annotations__.items():
            if isinstance(v, enum.EnumMeta):
                d[k] = d[k].value
        return d
    def from_json_dictionary(**hand_dict: dict) -> 'Result':
        "Create a Result from a jsonable dictionary"
        d = {}
        for k,v in hand_dict.items():
            enum_type = Result.__annotations__[k]
            if isinstance(enum_type, enum.EnumMeta):
                d[k] = enum_type(v)
            else:
                d[k] = v
        return Result(**d)


#def hands_to_json_file(f: io.FileIO, hands):
def hands_to_json_file(f: IO[str], hands):
    """write the hands array in json format to the file"""
    json.dump([hand.to_json_dictionary() for hand in hands], f)

#def hands_from_json_file(f: io.FileIO) -> List[Result]:
def hands_from_json_file(f: IO[str]) -> List[Result]:
    """Load a jso file and return the array of hands"""
    out = json.load(f)
    return [Result.from_json_dictionary(**hand_json) for hand_json in out]

def new_name_string() -> str:
    return time.strftime("%Y-%m-%d-%H-%M-%S.json")

def new_game_file(dir_str: str) -> pathlib.Path:
    file_name = new_name_string()
    directory = pathlib.Path(dir_str)
    file = directory / file_name
    if file.exists():
        raise FileExistsError()
    file.write_text("[]")
    return file
    
def existing_game_file(dir_str: str) -> pathlib.Path:
    directory = pathlib.Path(dir_str)
    paths = list(directory.glob("*-*-*-*-*-*.json"))
    if len(paths) == 0:
        raise FileNotFoundError()
    paths.sort()
    return paths[-1]

class ResultsFile:
    def __init__(self, dir: str):
        self.dir = dir
    def new_results(self) -> List[Result]:
        "create a new results file and return an empty list of results"
        self.hands_path = new_game_file(self.dir)
        return []
    def existing_results(self) -> List[Result]:
        "return a list results from the last results file persisted, create a new file if no files exist"
        try:
            hands_path = existing_game_file(self.dir)
        except FileNotFoundError:
            return self.new_results()
        with hands_path.open(mode="r") as f:
            self.hands_path = hands_path
            return hands_from_json_file(f)
    def store_results(self, hands:List[Result]):
        "store the results in the file created by new or existing_results"
        with self.hands_path.open(mode="w") as f:
            hands_to_json_file(f, hands)

class ResultsCOS:
    def __init__(self, bucket_name: str, ibm_api_key_id: str, ibm_service_instance_id: str, endpoint_url: str):
        print(bucket_name, ibm_api_key_id, ibm_service_instance_id, endpoint_url)

        # ibm_api_key_id = "EUbuWkafzLMJnT3gMuGfenF4iOQy3mCxIKjGlsT7P7g1"
        # ibm_service_instance_id = "crn:v1:bluemix:public:cloud-object-storage:global:a/713c783d9a507a53135fe6793c37cc74:4d533d24-ae88-471c-a86b-af2f29b9bd73::"
        # ibm_service_instance_id = "crn:v1:bluemix:public:cloud-object-storage:global:a/713c783d9a507a53135fe6793c37cc74:4d533d24-ae88-471c-a86b-af2f29b9bd73::"
        # endpoint_url = "https://s3.us-south.cloud-object-storage.appdomain.cloud"

        self.client = ibm_boto3.client('s3',
            ibm_api_key_id=ibm_api_key_id,
            ibm_service_instance_id=ibm_service_instance_id,
            config=Config(signature_version='oauth'),
            endpoint_url=endpoint_url,
        )
        self.resource = ibm_boto3.resource('s3',
            ibm_api_key_id=ibm_api_key_id,
            ibm_service_instance_id=ibm_service_instance_id,
            config=Config(signature_version='oauth'),
            endpoint_url=endpoint_url,
        )
        #self.bucket = self.get_or_create_bucket(bucket_name)
        self.bucket = self.resource.Bucket(bucket_name)
        for b in self.client.list_buckets():
            print(b)
        print('a0')
        for bo in self.client.list_objects(Bucket=bucket_name):
            print(bo)
        print('a1')
        for o in self.bucket.objects.all():
            print(o)
        print('a2')

    def get_bucket(self, bucket_name):
        for b in self.client.list_buckets():
            print(b)
        for bo in self.client.list_objects(Bucket=bucket_name):
            print(bo)
        for o in self.bucket.objects.all():
            print(o)
        bucket.load()
        bucket = self.resource.Bucket(bucket_name)
        return bucket

    def get_or_create_bucket(self, bucket_name):
        try:
            # self.client.head_bucket(Bucket=bucket_name) # raise exception if bucket_name does not exist
            return self.get_bucket(bucket_name)
        except:
            waiter_bucket_exists = self.client.get_waiter('bucket_exists')
            bucket = self.resource.create_bucket(Bucket=bucket_name)
            waiter_bucket_exists.wait(Bucket=bucket_name)
            return self.get_bucket()

    def get_latest_result_object(self):
        "Return the key of the object that is latest"
        object_summaries = self.bucket.objects.all()
        key_summary = {object_summary.key: object_summary for object_summary in self.bucket.objects.all()}
        keys = sorted(key_summary.keys())
        if len(keys) > 0:
            return keys[len(keys) - 1]
        else:
            return None

    def existing_results(self) -> List[Result]:
        "return a list results from the last results file persisted, create a new file if no files exist"
        key = self.get_latest_result_object()
        if key == None:
            return self.new_results()
        self.key = key
        hand_jsons = json.load(self.bucket.Object(key=key).get()["Body"])
        return [Result.from_json_dictionary(**hand_json) for hand_json in hand_jsons]
    def new_results(self) -> List[Result]:
        "create a new results file and return an empty list of results"
        self.key = None
        return []
    def store_results(self, hands:List[Result]):
        "store the results in the file created by new or existing_results"
        name = self.key
        if name == None:
            name = new_name_string()
        s = json.dumps([hand.to_json_dictionary() for hand in hands])
        self.bucket.Object(key=name).put(Body=s)