from datetime import UTC, datetime, timedelta, timezone

M = timedelta(minutes=1)
LOCAL = timezone(timedelta(hours=8))


def minute(raw):
    try:
        result = datetime.fromisoformat(raw.replace('Z','+00:00'))
        if not result.tzinfo or result.second or result.microsecond or not 2000 <= result.year <= 2099:
            raise ValueError
        return result.astimezone(UTC)
    except (AttributeError,ValueError,OverflowError):
        raise ValueError('TIMESTAMP') from None


def count(start,end):
    return (end-start)//M


def span(start,end):
    return (start + offset*M for offset in range(count(start,end)))


def local(utc_text):
    return minute(utc_text).astimezone(LOCAL).strftime('%m/%d %H:%M')
