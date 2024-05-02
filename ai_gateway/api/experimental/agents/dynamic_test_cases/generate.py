import structlog
from fastapi import APIRouter, Request
from pydantic import BaseModel
from starlette.authentication import requires

__all__ = [
    "router",
]

log = structlog.stdlib.get_logger("dynamic-test-cases")

router = APIRouter()


class TestCaseRequest(BaseModel):
    project_id: int
    base_url: str


class TestCaseCompletion(BaseModel):
    completion: str


@router.post("/generate", response_model=TestCaseCompletion)
@requires("experiments")
async def generate(
    request: Request,
    payload: TestCaseRequest,
):

    return TestCaseCompletion(completion="i am some test")
