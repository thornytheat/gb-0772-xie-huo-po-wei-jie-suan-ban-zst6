from functools import cached_property

from app.archive.amend import changes,snapshot
from app.billing.rates import price
from app.billing.settle import accounting
from app.curb.bookings import at_arrival,revisions
from app.curb.detections import prepare
from app.curb.grid import collisions
from app.curb.merge import stays
from app.curb.outages import declared_rows,prepare as outages,review
from app.source.packet import load
from app.source.plates import scrub

STAGES=('intake','identity','occupancy','pricing','settlement')


class Clearing:
    def __init__(self, files, secret, parent=None):
        self.survey,self.sheets=load(files)
        self.secret=secret
        self.parent=parent

    @cached_property
    def anonymous(self):
        return {name:scrub(rows,self.secret) for name,(rows,_) in self.sheets.items()}

    @cached_property
    def declarations(self):
        rows=list(self.anonymous.get('outages',([],[]))[0])+declared_rows(self.survey)
        return outages(rows,self.survey)

    @cached_property
    def intake(self):
        detections, sensor_issues=prepare(self.anonymous['sensors'][0],self.survey)
        bookings, booking_issues=revisions(self.anonymous['bookings'][0],self.survey)
        declarations, outage_issues=self.declarations
        sheets=[]
        for name,(_,report) in self.sheets.items():
            _,invalid_plates=self.anonymous[name]
            sheets.append(report | {'bad_plates':invalid_plates})
        return {'sheets':sheets,'sensor_issues':sensor_issues,'booking_issues':booking_issues,
                'outage_issues':outage_issues,'kept_sensors':len(detections),
                'booking_ids':len(bookings),'outage_windows':len(declarations)}

    @cached_property
    def combined(self):
        readings,_=prepare(self.anonymous['sensors'][0],self.survey)
        return stays(readings)

    @cached_property
    def outage_review(self):
        return review(self.declarations[0],self.combined)

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
        return accounting(self.pricing['stays'],self.anonymous['payments'][0],self.survey,*self.coverage,
                          pending=self.outage_review['pending_by_berth'])

    @cached_property
    def outages(self):
        return self.outage_review

    @cached_property
    def amendment(self):
        """试算更正时，对照原留档给出各泊位待核与出账分钟变化。

        只用于页面预览，不并入证据正文，保证同一输入的留档摘要稳定。
        """
        if self.parent is None:
            return None
        diff=changes(snapshot(self.parent),snapshot({'evidence':{'settlement':self.settlement}}))
        diff['parent']=(self.parent.get('manifest') or {}).get('key')
        return diff

    def report(self):
        """证据正文：五个清算阶段加停测待核核算。

        ``outages`` 不是独立工序，而是对账页与首页共用的泊位分钟补充；
        顺序固定，保证同输入的留档摘要稳定。
        """
        return {stage:getattr(self,stage) for stage in STAGES} | {'outages':self.outage_review}
