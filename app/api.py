from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.archive.appeal import issue
from app.archive.rerun import run
from app.clearing import Clearing,STAGES
from app.problems import DocketError
from app.source.packet import bundle

api=APIRouter(prefix='/api')


@api.get('/cases/{sample}/{stage}')
def preview(request:Request,sample:str,stage:str):
    if stage not in STAGES:
        raise DocketError('STAGE_BAD','没有这项清算工序',404)
    data=Clearing(bundle(sample),request.app.state.docket.secret)
    return getattr(data,stage)


@api.post('/dockets')
def archive(request:Request,payload:dict):
    record,reused=run(request.app.state.docket,payload)
    return {'key':record['manifest']['key'],'reused':reused,'manifest':record['manifest'],
            'totals':record['evidence']['settlement']['totals'],'money':record['evidence']['settlement']['money']}


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
