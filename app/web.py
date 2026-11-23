from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.encoders import jsonable_encoder
from fastapi.responses import HTMLResponse
from jinja2 import Environment,FileSystemLoader,select_autoescape

from app.archive.appeal import issue
from app.clearing import Clearing
from app.curb.timeaxis import local
from app.problems import DocketError,LABEL
from app.setup import POLICY
from app.source.packet import bundle

STEPS={'intake':'停靠与预约采信','identity':'车牌匿名关联','occupancy':'占用区间重建','pricing':'首免与升级价',
       'settlement':'逐单与泊位对账','history':'清算批次复跑','appeal':'理赔证据签发'}
workbench=APIRouter()
views=Environment(loader=FileSystemLoader(Path(__file__).parent/'templates'),
                  autoescape=select_autoescape(('html','j2')))


def yuan(cents):
    prefix='−' if cents<0 else ''
    weight,fraction=divmod(abs(cents),100)
    return f'{prefix}¥{weight:,}.{fraction:02d}'


@workbench.get('/',response_class=HTMLResponse)
@workbench.get('/clearing/{screen}',response_class=HTMLResponse)
def screen(request:Request,screen:str='overview',sample:str='dirty',key:str|None=None):
    if screen!='overview' and screen not in STEPS:
        raise DocketError('STAGE_BAD','没有这项清算工序',404)
    docket=request.app.state.docket
    signed=None
    if key:
        record=docket.require(key)
        report,meta=record['evidence'],record['manifest']
        if meta['source'] in {'clean','dirty'}:
            sample=meta['source']
        if screen=='appeal':
            signed=issue(record)
    else:
        clearing=Clearing(bundle(sample),docket.secret)
        report=jsonable_encoder(clearing.report())
        meta={'rule':POLICY,'survey':jsonable_encoder(vars(clearing.survey))}
    stages=list(STEPS)
    index=stages.index(screen) if screen in stages else -1
    history=docket.manifests() if screen=='history' else []
    path=lambda page: str(request.url_for('screen',screen=page).include_query_params(sample=sample,**({'key':key} if key else {})))
    return views.get_template('desk.html').render(screen=screen,steps=STEPS,index=index,next_step=stages[index+1] if index<6 else None,
        previous=stages[index-1] if index>0 else None,path=path,key=key,sample=sample,report=report,meta=meta,
        history=history,signed=signed,label=LABEL,local=local,yuan=yuan)
