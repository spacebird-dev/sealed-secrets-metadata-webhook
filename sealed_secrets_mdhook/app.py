import base64
from copy import deepcopy
import http
import logging
from json import JSONDecodeError
import sys
from typing import Any

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import JSONResponse
import json_logging
from jsonpatch import JsonPatch

app = FastAPI()
json_logging.init_fastapi(enable_json=True)
json_logging.init_request_instrument(app)

logger = logging.getLogger("sealed-secrets-mdhook")
logger.addHandler(logging.StreamHandler(sys.stdout))


def apply_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
    applied = deepcopy(metadata)
    applied["labels"] = metadata.get("labels", {}) | app.state.config.labels
    applied["annotations"] = (
        metadata.get("annotations", {}) | app.state.config.annotations
    )
    return applied


@app.post("/mutate")
async def mutate(request: Request):
    try:
        req = (await request.json())["request"]
        resource = req["object"]
        uid = req["uid"]
    except JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON Payload")
    except KeyError:
        raise HTTPException(
            status_code=400, detail="Malformed AdmissionReview")

    if (
        "spec" not in resource
        or "template" not in resource["spec"]
        or "metadata" not in resource["spec"]["template"]
    ):
        raise HTTPException(
            status_code=400,
            detail="Object is not a SealedSecret with spec.template.metadata struct",
        )

    resource_mut = deepcopy(resource)
    resource_mut["spec"]["template"]["metadata"] = apply_metadata(
        resource["spec"]["template"]["metadata"]
    )

    patch = JsonPatch.from_diff(resource, resource_mut)
    return JSONResponse(
        {
            "response": {
                "allowed": True,
                "uid": uid,
                "patch": base64.b64encode(str(patch).encode()).decode(),
                "patchType": "JSONPatch",
            }
        }
    )


@app.get("/health")
async def health():
    return Response("", status_code=http.HTTPStatus.NO_CONTENT)
