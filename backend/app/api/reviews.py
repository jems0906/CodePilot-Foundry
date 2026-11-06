from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from app.review_service import submit_review
from app.schemas import ReviewCreate

router = APIRouter(prefix="/api/reviews", tags=["reviews"])


@router.post("/{run_id}", status_code=201)
def review_run(run_id: int, payload: ReviewCreate, request: Request) -> dict[str, object]:
    try:
        return submit_review(run_id, payload.decision, payload.note, request.app.state.settings)
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
