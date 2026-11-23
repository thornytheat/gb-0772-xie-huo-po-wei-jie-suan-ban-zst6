import os
from pathlib import Path

from fastapi import FastAPI,Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api import api
from app.archive.docket import Docket
from app.problems import DocketError
from app.web import workbench


def create_app(path=None):
    app=FastAPI(title='卸货泊位结算板')
    app.state.docket=Docket(path or os.getenv('CURB_DOCKET','var/curb.sqlite3'))
    app.mount('/static',StaticFiles(directory=Path(__file__).parent/'static'),name='static')
    app.include_router(api)
    app.include_router(workbench)

    @app.exception_handler(DocketError)
    async def domain_failure(_request:Request,error:DocketError):
        return JSONResponse({'code':error.code,'message':str(error)},status_code=error.status)

    return app
