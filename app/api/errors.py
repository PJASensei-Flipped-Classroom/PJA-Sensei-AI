from fastapi import Request
from fastapi.responses import JSONResponse
from app.domain.exceptions import PrelabRequired

async def prelab_required_handler(request: Request, exc: PrelabRequired):
    message = "Wymagane ukończenie pre-labu." if exc.language == "pl" else "Pre-lab completion required."
    return JSONResponse(
        status_code=403,
        content={
            "message_id": "prelab_required",
            "detail": message
        }
    )