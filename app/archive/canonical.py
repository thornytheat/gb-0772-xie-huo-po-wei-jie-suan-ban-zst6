import json
from hashlib import sha256
from fastapi.encoders import jsonable_encoder


def serialize(value):
    return json.dumps(jsonable_encoder(value),ensure_ascii=False,sort_keys=True,separators=(',',':'))


def digest(value):
    return sha256(serialize(value).encode()).hexdigest()
