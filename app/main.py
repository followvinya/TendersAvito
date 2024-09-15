import os
from app.routes import ping, tenders, bids
from app.database import create_db_and_tables
import uvicorn
from fastapi.exceptions import RequestValidationError
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi import status


app = FastAPI()

@app.get("/")
async def root():
    return JSONResponse({
        "message": "Добро пожаловать в API управления тендерами",
        "version": "1.0",
        "available_endpoints": "start with /api, e.g. /api/tenders"
    })

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    first_error = exc.errors()[0]
    error_message = first_error.get("msg", "Некорректный запрос.")

    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "reason": error_message
        },
    )

@app.on_event("startup")
async def startup_event():
    create_db_and_tables()

app.include_router(ping.router, prefix="/api")
app.include_router(tenders.router, prefix="/api")
app.include_router(bids.router, prefix="/api")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("SERVER_PORT", "8080")))
