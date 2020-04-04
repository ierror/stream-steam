import json
import os
from collections import defaultdict
from urllib.parse import parse_qsl, urlparse
from uuid import uuid4

import boto3
import requests

firehose_client = boto3.client("firehose")
s3_client = boto3.client("s3")

API_USERSTACK_ENDPOINT = "http://api.userstack.com/detect"
API_IPINFO_ENDPOINT = "https://ipinfo.io"


INCOMING_PARAMS_TO_READABLE = {
    "idsite": "site_id",
    "r": "random_part",
    "h": "hour",
    "m": "minute",
    "s": "second",
    "_idts": "visitor_id_created_ts",
    "_idvc": "visitor_visit_count",
    "_refts": "referral_ts",
    "_viewts": "visitor_last_visit_ts",
    "res": "display_resolutions",
    "gt_ms": "performance_generation_time_ms",
    "pv_id": "page_view_id",
    "url": "page_view_url",
    "action_name": "action_name",
    "ag": "supports_silverlight",
    "cookie": "supports_cookie",
    "dir": "supports_director",
    "fla": "supports_flash",
    "gears": "supports_gears",
    "java": "supports_java",
    "pdf": "supports_pdf",
    "qt": "supports_quicktime",
    "wma": "supports_mplayer2",
    "realp": "supports_realaudio",
    "send_image": "send_image",
    "e_c": "event_category",
    "e_a": "event_action",
    "e_n": "event_value_name",
    "e_v": "event_value_numeric",
}

LOOKUP_CACHE = {
    "user_agent": defaultdict(dict),
    "ip": defaultdict(dict),
}


def lambda_handler(event_in, context):
    print(event_in)

    event_out = {
        "id": str(uuid4()),
        "user_agent": event_in["requestContext"]["identity"]["userAgent"],
        "ip": event_in["requestContext"]["identity"]["sourceIp"],
    }

    # extract post data
    post_data = {}
    if event_in.get("body") is not None:
        post_data = json.loads(event_in["body"])["requests"][0]
        post_data = dict(parse_qsl(urlparse(post_data).query))

    # map incoming event_in params to readable ones
    for param, readable in INCOMING_PARAMS_TO_READABLE.items():
        if "queryStringParameters" in event_in and event_in["queryStringParameters"].get(param):
            event_out[readable] = event_in["queryStringParameters"][param]
        if param in post_data:
            event_out[readable] = post_data[param]

    # Device lookup
    device_detection_enabled = True if os.environ.get("DEVICE_DETECTION_ENABLED") == "true" else False
    if device_detection_enabled and event_out["user_agent"]:
        # cache hit?
        cached = LOOKUP_CACHE["user_agent"][event_out["user_agent"]]
        if cached:
            device_info = cached
        else:
            response = requests.get(
                API_USERSTACK_ENDPOINT,
                {"access_key": os.environ["USERSTACK_API_TOKEN"], "ua": event_out["user_agent"]},
            )
            response.raise_for_status()
            response_json = response.json()

            if "error" in response_json:
                raise RuntimeError(f"User Agent Lookup not successful, response was: {response_json}")
            device_info = response_json
            LOOKUP_CACHE["user_agent"][event_out["user_agent"]] = response_json
        event_out["device_info"] = device_info

    # IP lookup
    ip_geocoding_enabled = True if os.environ.get("IP_GEOCODING_ENABLED") == "true" else False
    if ip_geocoding_enabled and event_out["ip"]:
        # cache hit?
        cached = LOOKUP_CACHE["ip"][event_out["ip"]]
        if cached:
            geo_info = cached
        else:
            response = requests.get(
                f"{API_IPINFO_ENDPOINT}/{event_out['ip']}", params={"token": os.environ["IP_INFO_API_TOKEN"]},
            )
            response.raise_for_status()
            response_json = response.json()
            LOOKUP_CACHE["ip"][event_out["ip"]] = response_json
            geo_info = response_json
        event_out["geo_info"] = geo_info

    # send event_to firehose for raw data archiving
    firehose_client.put_record(
        DeliveryStreamName=os.environ["DELIVERY_STREAM_NAME"], Record={"Data": json.dumps(event_out) + "\n"},
    )

    return {"statusCode": 200}
