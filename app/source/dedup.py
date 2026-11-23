from collections import defaultdict


def resolve(rows,key,value):
    groups=defaultdict(list)
    chosen,isolated=[],[]
    for row in rows:
        groups[key(row)].append(row)
    for options in groups.values():
        first,*rest=sorted(options,key=lambda row:row['line'])
        if len({value(row) for row in options})>1:
            isolated.extend(row | {'code':'ID_CONFLICT'} for row in options)
        else:
            chosen.append(first)
            isolated.extend(row | {'code':'DUPLICATE'} for row in rest)
    return sorted(chosen,key=lambda row:row['line']),isolated
