from fastapi import APIRouter
from guppy import hpy

router = APIRouter(
    prefix="/debug",
    tags=["internal"],
)


@router.get("/heap")
async def heap_dump():
    h = hpy()
    heap = h.heap()
    print(str(heap))
    return {"heap_dump": str(heap)}


@router.get("/breakpoint")
async def breakpoint():
    import pdb

    pdb.set_trace()
