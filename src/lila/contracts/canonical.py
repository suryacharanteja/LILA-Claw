"""Restricted LILA canonical JSON, not a general RFC canonicalizer."""
import json
import unicodedata


def normalize(value, depth=0):
    if depth > 64:
        raise ValueError("JSON nesting limit")
    if value is None or isinstance(value,bool):
        return value
    if isinstance(value,int):
        if not -(2**63) <= value < 2**63:
            raise ValueError("integer outside signed 64-bit range")
        return value
    if isinstance(value,str):
        return unicodedata.normalize("NFC",value)
    if isinstance(value,list):
        return [normalize(item,depth+1) for item in value]
    if isinstance(value,dict):
        result = {}
        for key,item in value.items():
            if not isinstance(key,str):
                raise ValueError("JSON keys must be strings")
            key = unicodedata.normalize("NFC",key)
            if key in result:
                raise ValueError("normalized duplicate key")
            result[key] = normalize(item,depth+1)
        return result
    raise ValueError("unsupported canonical JSON value")


def canonical(value):
    return json.dumps(normalize(value),ensure_ascii=False,sort_keys=True,separators=(",",":"),allow_nan=False).encode("utf-8")
