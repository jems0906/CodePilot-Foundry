from pydantic import BaseModel, Field


class EvaluationCreate(BaseModel):
    run_id: int = Field(gt=0)
    scenario_id: str = "unicode-normalization"
