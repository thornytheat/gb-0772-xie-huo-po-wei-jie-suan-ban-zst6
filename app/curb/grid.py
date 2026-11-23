from collections import defaultdict

from app.curb.timeaxis import span


def collisions(stops):
    by_berth,by_vehicle=defaultdict(list),defaultdict(list)
    for stop in stops:
        for when in span(stop['start'],stop['end']):
            by_berth[stop['berth'],when].append(stop)
            by_vehicle[stop['vehicle'],when].append(stop)
    disputed={}
    for (berth,when), group in by_berth.items():
        if len(group)>1:
            disputed[berth,when]='PLATE_OVERLAP'
        elif len(by_vehicle[group[0]['vehicle'],when])>1:
            disputed[berth,when]='BERTH_OVERLAP'
    return by_berth,disputed
