from app.config import settings
from botocore.exceptions import BotoCoreError, ClientError
from fastapi import FastAPI, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

from app.dependencies import get_db, require_permission
from app.orm_models import User

from .routers import (
    auth,
    buildings,
    engineers,
    floors,
    incident_tickets,
    seats,
    ticket_note_attachments,
    ticket_notes,
    users,
)

import boto3

FRONTEND_ORIGIN = settings.frontend_origin
s3 = boto3.client('s3')
bucket_1 = '[INSERT_INCIDENT_NOTE_S3_BUCKET_NAME]'
bucket_2 = '[INSERT_FRONTEND_S3_BUCKET_NAME]'

app = FastAPI(
    title="ACME Incident Report Centre",
    description="[Placeholder]",
    version="0.1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_ORIGIN],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health", tags=["health"])
async def health_check() -> dict[str, str]:
    return {"status": "OK"}

@app.get("/health/ready", tags=["health"])
async def health_readiness_check(
    db: AsyncSession = Depends(get_db)
) -> JSONResponse:
    db_command = select(1)
    output = await db.execute(db_command)
    if not output:
        return JSONResponse(
            status_code=503,
            content={"status-503": "Database is currently unreachable."}
        )
    return JSONResponse(
        status_code=200,
        content={"status-200": "Database is currently reachable."}
    )

@app.get("/health/detail", tags=["health"])
async def health_readiness_check(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("users:read"))
) -> JSONResponse:
    checks = {
        "database": {
            "status": "unreachable",
            "status code": 503,
        },
        "s3_service_reports": {
            "status": "unreachable",
            "status code": 503,
        },
        "s3_frontend": {
            "status": "unreachable",
            "status code": 503,
        }
    }

    try:
        await db.execute(select(1))
        checks["database"]["status"] = "reachable"
        checks["database"]["status code"] = 200
    except SQLAlchemyError as e:
        checks["database"]["status code"] = 503

    try:
        s3_output = await run_in_threadpool(s3.head_bucket, Bucket=bucket_1)
        checks["s3_service_reports"]["status"] = "reachable"
        checks["s3_service_reports"]["status code"] = s3_output["ResponseMetadata"]["HTTPStatusCode"]
    except ClientError as e:
        checks["s3_service_reports"]["status code"] = e.response["ResponseMetadata"].get(
            "HTTPStatusCode", 503
        )
    except BotoCoreError:
        checks["s3_service_reports"]["status code"] = 503
    status_code = (200 if all(check["status"] == "reachable" for check in checks.values()) else 503)

    try:
        s3_output = await run_in_threadpool(s3.head_bucket, Bucket=bucket_2)
        checks["s3_frontend"]["status"] = "reachable"
        checks["s3_frontend"]["status code"] = s3_output["ResponseMetadata"]["HTTPStatusCode"]
    except ClientError as e:
        checks["s3_frontend"]["status code"] = e.response["ResponseMetadata"].get(
            "HTTPStatusCode", 503
        )
    except BotoCoreError:
        checks["s3_frontend"]["status code"] = 503
    status_code = (200 if all(check["status"] == "reachable" for check in checks.values()) else 503)
    
    response = JSONResponse(
        status_code=status_code,
        content=checks
    )
    return response

@app.get("/version", tags=["version"])
async def version_check() -> dict[str, str]:
    return {"version": app.version}

# INSERT APP ROUTES HERE
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(buildings.router)
app.include_router(engineers.router)
app.include_router(floors.router)
app.include_router(incident_tickets.router)
app.include_router(seats.router)
app.include_router(ticket_notes.router)
app.include_router(ticket_note_attachments.router)

@app.exception_handler(IntegrityError)
async def integrity_error_handler(request: Request, exc: IntegrityError) -> JSONResponse:
    return JSONResponse(
        status_code=409,
        content={"detail": "Database constraint violation."}
    )

@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=500,
        content={"detail": "Unknown error detected. Please see the developer console for more details."}
    )