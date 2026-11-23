from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.archive.appeal import issue
from app.archive.rerun import run
from app.clearing import Clearing,STAGES
from app.problems import DocketError
from app.source.packet import bundle

api=APIRouter(prefix='/api')


@api.get('/cases/{sample}/{stage}')
def preview(request:Request,sample:str,stage:str,parent:str|None=None):
    if stage not in STAGES and stage!='outages':
        raise DocketError('STAGE_BAD','没有这项清算工序',404)
    docket=request.app.state.docket
    base=docket.find(parent) if parent else None
    if parent and base is None:
        raise DocketError('PARENT_BAD','找不到引用的原清算批次',404)
    data=Clearing(bundle(sample),docket.secret,base)
    result=getattr(data,'outage_review' if stage=='outages' else stage)
    if base is not None and isinstance(result,dict) and data.amendment:
        result=dict(result) | {'amendment':data.amendment}
    return result


@api.post('/dockets')
def archive(request:Request,payload:dict):
    record,reused=run(request.app.state.docket,payload)
    evidence=record['evidence']
    response={'key':record['manifest']['key'],'reused':reused,'manifest':record['manifest'],
              'totals':evidence['settlement']['totals'],'money':evidence['settlement']['money'],
              'pending':evidence['settlement']['pending']}
    if record['manifest'].get('changes'):
        response['amendment']=record['manifest']['changes']
    return response


@api.get('/dockets')
def history(request:Request):
    return {'dockets':request.app.state.docket.manifests()}


@api.get('/dockets/{key}')
def read(request:Request,key:str):
    return request.app.state.docket.require(key)


@api.get('/export/{key}')
def export(request:Request,key:str):
    item=issue(request.app.state.docket.require(key))
    return JSONResponse(item,headers={'Content-Disposition':f'attachment; filename="appeal-{key}.json"'})
