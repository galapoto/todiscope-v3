from fastapi import APIRouter, HTTPException

from backend.app.core.artifacts.store import get_artifact_store


router = APIRouter(prefix="/api/v3/artifacts", tags=["artifacts"])


@router.post("/put-test")
async def put_test_artifact() -> dict:
    store = get_artifact_store()
    stored = await store.put_bytes(key="test/hello.txt", data=b"hello", content_type="text/plain")
    return {"uri": stored.uri, "sha256": stored.sha256, "size_bytes": stored.size_bytes}


@router.get("/get-test")
async def get_test_artifact() -> dict:
    store = get_artifact_store()
    try:
        data = await store.get_bytes(key="test/hello.txt")
    except Exception as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return {"data": data.decode("utf-8")}

