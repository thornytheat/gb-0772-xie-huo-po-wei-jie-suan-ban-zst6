from hashlib import sha256
import json

from app.problems import DocketError
from app.setup import SAMPLES
from app.source.csvscan import scan
from app.source.structure import SCHEMAS,Survey

NAMES=('survey',*SCHEMAS)


def bundle(name):
    if name not in {'dirty','clean'}:
        raise DocketError('SAMPLE_BAD','找不到选定的清算样例',404)
    return {key:(SAMPLES/name/(key+('.json' if key=='survey' else '.csv'))).read_bytes().decode()
            for key in NAMES}


def decode(payload):
    if isinstance(payload,dict) and set(payload)=={'sample'}:
        name=str(payload['sample'])
        return bundle(name),name
    files=payload.get('bundle') if isinstance(payload,dict) and set(payload)=={'bundle'} else None
    if not isinstance(files,dict) or set(files)!=set(NAMES) or any(
        not isinstance(text,str) or len(text)>200_000 for text in files.values()
    ):
        raise DocketError('BUNDLE_BAD','需清算窗口和三份 UTF-8 单据')
    try:
        for text in files.values():
            text.encode()
    except UnicodeEncodeError:
        raise DocketError('BUNDLE_BAD','原件含错误字符') from None
    return files,'upload'


def load(files):
    try:
        obj=json.loads(files['survey'].removeprefix('\ufeff'))
    except (json.JSONDecodeError,RecursionError):
        raise DocketError('SURVEY_BAD','清算窗口 JSON 无效') from None
    return Survey.build(obj),{name:scan(files[name],name) for name in SCHEMAS}


def fingerprint(files):
    return {name:sha256(text.encode()).hexdigest() for name,text in sorted(files.items())}
