"""Closed JSON codec for worker checkpoints. Never imports serialized types."""
import base64
import json
from lila.contracts.canonical import canonical, normalize

TAG = "$lila_checkpoint"


def _encode(value, depth=0):
    if depth > 64:
        raise ValueError("checkpoint nesting limit")
    if type(value) is bytes:
        return {TAG: "bytes", "value": base64.b64encode(value).decode("ascii")}
    # Import a single explicitly supported class, never a payload-supplied name.
    from langgraph.types import Interrupt
    if type(value) is Interrupt:
        if not isinstance(value.id, str):
            raise ValueError("invalid interrupt id")
        return {TAG: "interrupt", "id": value.id, "value": _encode(value.value, depth+1)}
    if isinstance(value, (list, tuple)):
        return [_encode(item, depth+1) for item in value]
    if type(value) is dict:
        if TAG in value:
            raise ValueError("reserved checkpoint key")
        return {key: _encode(item, depth+1) for key, item in value.items()}
    return normalize(value)


def _decode(value, depth=0):
    if depth > 64:
        raise ValueError("checkpoint nesting limit")
    if isinstance(value, list):
        return [_decode(item, depth+1) for item in value]
    if isinstance(value, dict):
        if TAG not in value:
            return {key: _decode(item, depth+1) for key, item in value.items()}
        if value[TAG] == "bytes" and set(value) == {TAG, "value"}:
            if not isinstance(value["value"], str):
                raise ValueError("invalid byte tag")
            try:
                return base64.b64decode(value["value"], validate=True)
            except (ValueError, UnicodeError):
                raise ValueError("invalid byte tag") from None
        if value[TAG] == "interrupt" and set(value) == {TAG, "id", "value"} and isinstance(value["id"], str):
            from langgraph.types import Interrupt
            return Interrupt(value=_decode(value["value"], depth+1), id=value["id"])
        raise ValueError("unsupported checkpoint tag")
    return value


def dumps(value, limit=1024*1024):
    data = canonical(_encode(value))
    if len(data) > limit:
        raise ValueError("checkpoint size limit")
    return data.decode("utf-8")


def loads(data, limit=1024*1024):
    if not isinstance(data, str) or len(data.encode("utf-8")) > limit:
        raise ValueError("checkpoint size limit")
    def unique(pairs):
        result = {}
        for key, value in pairs:
            key = normalize(key)
            if key in result:
                raise ValueError("duplicate checkpoint key")
            result[key] = value
        return result
    try:
        value = json.loads(data, object_pairs_hook=unique,
                           parse_constant=lambda _: (_ for _ in ()).throw(ValueError("nonfinite number")))
        return _decode(normalize(value))
    except (RecursionError, UnicodeError):
        raise ValueError("invalid checkpoint JSON") from None


class CheckpointSerializer:
    def dumps_typed(self, value):
        return "lila-json-v1", dumps(value).encode("utf-8")

    def loads_typed(self, data):
        kind, payload = data
        if kind != "lila-json-v1":
            raise ValueError("unsupported checkpoint encoding")
        return loads(payload.decode("utf-8"))
