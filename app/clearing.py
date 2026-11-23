from functools import cached_property

from app.billing.rates import price
from app.billing.settle import accounting
from app.curb.bookings import at_arrival,revisions
from app.curb.detections import prepare
from app.curb.grid import collisions
from app.curb.merge import stays
from app.source.packet import load
from app.source.plates import scrub

STAGES=('intake','identity','occupancy','pricing','settlement')


class Clearing:
    def __init__(self, files, secret):
        self.survey,self.sheets=load(files)
        self.secret=secret

    @cached_property
    def anonymous(self):
        return {name:scrub(rows,self.secret) for name,(rows,_) in self.sheets.items()}

    @cached_property
    def intake(self):
        detections, sensor_issues=prepare(self.anonymous['sensors'][0],self.survey)
        bookings, booking_issues=revisions(self.anonymous['bookings'][0],self.survey)
        sheets=[]
        for name,(_,report) in self.sheets.items():
            _,invalid_plates=self.anonymous[name]
            sheets.append(report | {'bad_plates':invalid_plates})
        return {'sheets':sheets,'sensor_issues':sensor_issues,'booking_issues':booking_issues,
                'kept_sensors':len(detections),'booking_ids':len(bookings)}

    @cached_property
    def combined(self):
        readings,_=prepare(self.anonymous['sensors'][0],self.survey)
        return stays(readings)

    @cached_property
    def occupancy(self):
        combined=self.combined
        _,disputed=self.coverage
        return {'stays':combined,'removed_overlap_minutes':sum(s['observed_minutes']-s['minutes'] for s in combined),
                'disputes':[{'berth':berth,'at':when,'code':code} for (berth,when),code in sorted(disputed.items())]}

    @cached_property
    def coverage(self):
        return collisions(self.combined)

    @cached_property
    def identity(self):
        aliases,issues=revisions(self.anonymous['bookings'][0],self.survey)
        matched=[]
        for stay in self.occupancy['stays']:
            booking,reason,history=at_arrival(stay,aliases)
            matched.append(stay | {'booking':booking,'association':reason,'candidates':history})
        return {'stays':matched,'booking_issues':issues}

    @cached_property
    def pricing(self):
        items=price(self.identity['stays'],self.coverage[1])
        return {'stays':items,'due_cents':sum(s['due_cents'] for s in items)}

    @cached_property
    def settlement(self):
        return accounting(self.pricing['stays'],self.anonymous['payments'][0],self.survey,*self.coverage)

    def report(self):
        return {stage:getattr(self,stage) for stage in STAGES}
