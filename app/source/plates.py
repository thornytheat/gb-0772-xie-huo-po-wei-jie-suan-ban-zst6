import hmac
import re
import unicodedata

VEHICLE=re.compile(r'(?:[京津沪渝冀豫云辽黑湘皖鲁新苏浙赣鄂桂甘晋蒙陕吉闽贵粤青藏川宁琼]|[A-Z])[A-Z][0-9A-Z]{5,6}')


def token(raw,salt):
    clean=''.join(unicodedata.normalize('NFKC',raw).split()).upper().replace('·','')
    if not VEHICLE.fullmatch(clean):
        raise ValueError('PLATE')
    return hmac.digest(salt,clean.encode(),'sha256').hex()


def scrub(entries,salt):
    good,bad=[],[]
    for row in entries:
        fields=row['fields']
        clean=row | {'fields':{k:v for k,v in fields.items() if k!='plate'}}
        try:
            good.append(clean | {'vehicle':token(fields['plate'],salt)})
        except ValueError as error:
            bad.append(clean | {'code':str(error)})
    return good,bad
