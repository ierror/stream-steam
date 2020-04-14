from collections import defaultdict, namedtuple

Field = namedtuple("Field", ["name_in", "name_out", "type"])

TIMESTAMP_FIELDS = ["event_datetime"]

# _cvar custom variables
# _rcn Campaign name
# _rck Campaign Keyword
#  lang: Accept-Language HTTP (already present for ios, check android)
#  uid user_id (str)
# cid  visitor ID (str)
# dimension[0-999] custom dimension

# events from clients
INCOMING = [
    # see https://developer.matomo.org/api-reference/tracking-api for details
    Field("idsite", "site_id", str),
    Field("r", "random_part", int),
    Field("_idts", "visitor_id_created_ts", int),
    Field("_idvc", "visitor_visit_count", int),
    Field("_refts", "referral_ts", int),
    Field("urlref", "referral_url", str),
    Field("_viewts", "visitor_last_visit_ts", int),
    Field("res", "display_resolutions", str),
    Field("lang", "language", str),
    Field("cdt", "event_datetime", str),
    Field("gt_ms", "performance_generation_time_ms", int),
    Field("pv_id", "page_view_id", str),
    Field("url", "page_view_url", str),
    Field("action_name", "action_name", str),
    Field("ag", "supports_silverlight", bool),
    Field("cookie", "supports_cookie", bool),
    Field("dir", "supports_director", bool),
    Field("fla", "supports_flash", bool),
    Field("gears", "supports_gears", bool),
    Field("java", "supports_java", bool),
    Field("pdf", "supports_pdf", bool),
    Field("qt", "supports_quicktime", bool),
    Field("wma", "supports_mplayer2", bool),
    Field("realp", "supports_realaudio", bool),
    Field("send_image", "send_image", bool),
    Field("e_c", "event_category", str),
    Field("e_a", "event_action", str),
    Field("e_n", "event_value_name", str),
    Field("e_v", "event_value_numeric", float),
]

# geo coding resolved data
GEO_INFO = [
    Field(
        "geo_info",
        None,
        [
            Field("ip", None, str),
            Field("hostname", None, str),
            Field("city", None, str),
            Field("region", None, str),
            Field("country", None, str),
            Field("loc", None, [Field("longitude", None, float), Field("latitude", None, float)]),
            Field("org", None, str),
            Field("postal", None, str),
            Field("timezone", None, str),
        ],
    )
]

# device classification resolved data
DEVICE_INFO = [
    Field(
        "device_info",
        None,
        [
            Field("ua", None, str),
            Field("type", None, str),
            Field("brand", None, str),
            Field("name", None, str),
            Field("url", None, str),
            Field(
                "os",
                None,
                [
                    Field("name", None, str),
                    Field("code", None, str),
                    Field("url", None, str),
                    Field("family", None, str),
                    Field("family_code", None, str),
                    Field("family_vendor", None, str),
                    Field("icon", None, str),
                    Field("icon_large", None, str),
                ],
            ),
            Field(
                "device",
                None,
                [
                    Field("is_mobile_device", None, bool),
                    Field("type", None, str),
                    Field("brand", None, str),
                    Field("brand_code", None, str),
                    Field("brand_url", None, str),
                    Field("name", None, str),
                ],
            ),
            Field(
                "browser",
                None,
                [
                    Field("name", None, str),
                    Field("version", None, str),
                    Field("version_major", None, str),
                    Field("engine", None, str),
                ],
            ),
            Field(
                "crawler",
                None,
                [Field("is_crawler", None, bool), Field("category", None, str), Field("last_seen", None, str)],
            ),
        ],
    )
]

# added while lambda-processing the event
PROCESSING = [
    Field("event_datetime", None, str),
]

# final schema for enriched events
ENRICHED = INCOMING + PROCESSING + GEO_INFO + DEVICE_INFO


def schema_to_flat_json(schema, converted, level=0, level_prev=0, path="", use_glue_types=True):
    # takes an event schema and creates a flat json
    # e.g.:
    #
    # {'action_name': 'action_name:string',
    #  'device_info': ['ua:string',
    #                  'type:string',
    #                   ...
    #  'device_info.os': ['name:string',
    #                     'code:string',
    #                   ...
    #  'display_resolutions': 'display_resolutions:string',
    for field in schema:
        field_name = field.name_out or field.name_in
        if level == 0:
            path = field_name
        elif level_prev > level:
            path = ".".join(path.split(".")[:-1])

        if isinstance(field.type, list):
            # nested struct
            if level != 0:
                # nested path => extend current path
                if path:
                    path = f"{path}.{field_name}"
                else:
                    path = field_name
            level_prev = schema_to_flat_json(
                field.type, converted=converted, level_prev=level_prev, level=level + 1, path=path
            )
        else:
            # flat struct
            if use_glue_types:
                if field_name in TIMESTAMP_FIELDS:
                    data_type = "timestamp"
                elif field.type == str:
                    data_type = "string"
                elif field.type == int:
                    data_type = "int"
                elif field.type == float:
                    data_type = "double"
                elif field.type == bool:
                    data_type = "boolean"
                else:
                    raise NotImplementedError(f"Unknown type {field.type}")
            else:
                data_type = field.type

            if level == 0:
                converted[path] = data_type
            else:
                converted[path].append(f"{field_name}:{data_type}")

    return level


# _schema_to_glue_table_struct
def schema_to_glue_schema(schema):
    json_schema = defaultdict(list)
    schema_to_flat_json(schema, converted=json_schema, use_glue_types=True)

    # sort by . to get deepest elements first
    nested_targets = defaultdict(dict)
    schema_glue = []

    for key in sorted(json_schema.keys(), key=lambda s: s.count("."), reverse=True):
        value = json_schema[key]

        if key in nested_targets:
            for sub_key, sub_value in nested_targets[key].items():
                value.append(f"{sub_key}:{sub_value}")
            struct_str = ",".join(value)
            struct_str = f"struct<{struct_str}>"
            schema_glue.append([key, struct_str])
        if isinstance(value, str):
            # flat value
            schema_glue.append([key, value])
        else:
            # e.g. from list to
            # struct<longitude:double,latitude:double>
            nested_struct_str = ",".join(value)
            nested_struct_str = f"struct<{nested_struct_str}>"
            if "." in key:
                # e.g. device_info.os => device_info
                # TODO make dynamic to support more than two nested levels
                target_key_l1, target_key_l2 = key.split(".")
                nested_targets[target_key_l1][target_key_l2] = nested_struct_str

    return schema_glue
