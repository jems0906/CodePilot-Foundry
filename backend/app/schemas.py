from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class TaskCreate(BaseModel):
    title: str = Field(min_length=3, max_length=120)
    description: str = Field(min_length=10, max_length=2000)


class TaskRead(BaseModel):
    id: int
    title: str
    description: str
    status: str
    created_at: datetime | str


class RunRead(BaseModel):
    id: int
    task_id: int
    provider: str
    status: str
    plan: list[str]
    diff: str
    self_review: str
    test_result: dict[str, Any]
    created_at: datetime | str


class ReviewCreate(BaseModel):
    decision: Literal["approved", "rejected"]
    note: str = Field(default="", max_length=1000)


class ReviewRead(BaseModel):
    id: int
    run_id: int
    decision: str
    note: str
    created_at: datetime | str
