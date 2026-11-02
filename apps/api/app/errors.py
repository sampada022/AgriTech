from fastapi import Request
from fastapi.responses import JSONResponse

class AeroScoutError(Exception):
    def __init__(self, code: str, message: str, hint: str, status_code: int = 400):
        self.code = code
        self.message = message
        self.hint = hint
        self.status_code = status_code

async def aeroscout_exception_handler(request: Request, exc: AeroScoutError):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.code,
                "message": exc.message,
                "hint": exc.hint
            }
        }
    )

async def generic_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": str(exc),
                "hint": "Check server structured logs or retry."
            }
        }
    )

