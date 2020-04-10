import json
import os
from collections import defaultdict, namedtuple
from datetime import datetime, timezone
from urllib.parse import parse_qsl, urlparse
from uuid import uuid4

import boto3
import requests

firehose_client = boto3.client("firehose")
s3_client = boto3.client("s3")

API_USERSTACK_ENDPOINT = "http://api.userstack.com/detect"
API_IPINFO_ENDPOINT = "https://ipinfo.io"

Parameter = namedtuple("Parameter", ["name_in", "name_out", "type"])

# _cvar custom variables
# _rcn Campaign name
# _rck Campaign Keyword
#  lang: Accept-Language HTTP
#  uid user_id (str)
# cid  visitor ID (str)
# dimension[0-999] custom dimension


INCOMING_PARAMS_MAPPING = [
    # see https://developer.matomo.org/api-reference/tracking-api for details
    Parameter("idsite", "site_id", int),
    Parameter("r", "random_part", int),
    Parameter("_idts", "visitor_id_created_ts", int),
    Parameter("_idvc", "visitor_visit_count", int),
    Parameter("_refts", "referral_ts", int),
    Parameter("urlref", "referral_url", str),
    Parameter("_viewts", "visitor_last_visit_ts", int),
    Parameter("res", "display_resolutions", str),
    Parameter("gt_ms", "performance_generation_time_ms", int),
    Parameter("pv_id", "page_view_id", str),
    Parameter("url", "page_view_url", str),
    Parameter("action_name", "action_name", str),
    Parameter("ag", "supports_silverlight", bool),
    Parameter("cookie", "supports_cookie", bool),
    Parameter("dir", "supports_director", bool),
    Parameter("fla", "supports_flash", bool),
    Parameter("gears", "supports_gears", bool),
    Parameter("java", "supports_java", bool),
    Parameter("pdf", "supports_pdf", bool),
    Parameter("qt", "supports_quicktime", bool),
    Parameter("wma", "supports_mplayer2", bool),
    Parameter("realp", "supports_realaudio", bool),
    Parameter("send_image", "send_image", bool),
    Parameter("e_c", "event_category", str),
    Parameter("e_a", "event_action", str),
    Parameter("e_n", "event_value_name", str),
    Parameter("e_v", "event_value_numeric", float),
]

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

    # map incoming event_in params to readable ones and cast values - simple sanity checks... ;)
    for param in INCOMING_PARAMS_MAPPING:
        if param.name_in in post_data:
            event_out[param.name_out] = post_data[param.name_in]
        elif "queryStringParameters" in event_in and event_in["queryStringParameters"].get(param.name_in):
            event_out[param.name_out] = event_in["queryStringParameters"][param.name_in]

        # cast values
        if param.name_out in event_out:
            if param.type == bool:
                event_out[param.name_out] = bool(int(event_out[param.name_out]))
            else:
                event_out[param.name_out] = param.type(event_out[param.name_out])

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

            # split lon lat string in coords
            # e.g "48.1374,11.5755" => [latitude=48.1374, longitude=11.5755]
            long_lat_str = response_json.get("loc", "")
            if "," in long_lat_str:
                response_json["loc"] = {}
                response_json["loc"]["latitude"], response_json["loc"]["longitude"] = long_lat_str.split(",")
                response_json["loc"]["latitude"] = float(response_json["loc"]["latitude"])
                response_json["loc"]["longitude"] = float(response_json["loc"]["longitude"])
            else:
                response_json["loc"] = {
                    "latitude": None,
                    "longitude": None,
                }

            LOOKUP_CACHE["ip"][event_out["ip"]] = response_json
            geo_info = response_json

        event_out["geo_info"] = geo_info

    # set received_date_time
    # use api gw info requestContext.requestTime
    # e.g. '06/Apr/2020:09:07:05 +0000' => 2020-04-06T10:37:38+00:00
    # parse
    event_out["received_date_time"] = datetime.strptime(
        event_in["requestContext"]["requestTime"], "%d/%b/%Y:%H:%M:%S %z"
    )
    # to e.g. 2020-04-07T11:04.01.1586251321
    event_out["received_date_time"] = (
        event_out["received_date_time"].astimezone(timezone.utc).replace(tzinfo=None).isoformat()
    )

    # send event_to firehose
    firehose_client.put_record(
        DeliveryStreamName=os.environ["DELIVERY_STREAM_NAME"], Record={"Data": json.dumps(event_out) + "\n"},
    )
    return {"statusCode": 200}
