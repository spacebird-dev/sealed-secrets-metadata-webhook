import base64
from copy import deepcopy
from http import HTTPStatus
import json
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

from sealed_secrets_mdhook import make_app

app = make_app(Path("test/config.json"))
client = TestClient(app)

REQ_UID = "87772275-6d39-4558-8e73-0a63df11e4ab"
BASE_REQUEST = {
    "request": {
        "uid": REQ_UID,
        "object": {
            "apiVersion": "bitnami.com/v1alpha1",
            "kind": "SealedSecret",
            "metadata": {"name": "empty", "namespace": "default"},
            "spec": {
                "template": {
                    "metadata": {
                        "name": "empty",
                        "namespace": "default",
                        "annotations": {},
                        "labels": {},
                    }
                }
            },
        },
    }
}


def check_response(expected_patch: list[dict[str, Any]], resp_raw: dict[str, Any]):
    assert resp_raw["apiVersion"] == "admission.k8s.io/v1"
    assert resp_raw["kind"] == "AdmissionReview"
    assert resp_raw["response"]
    response = resp_raw["response"]
    assert response["allowed"]
    assert response["uid"] == REQ_UID
    assert response["patchType"] == "JSONPatch"
    response_patch = json.loads(base64.b64decode(response["patch"]))
    assert len(expected_patch) == len(response_patch)
    for patch in expected_patch:
        assert patch in response_patch


def test_health():
    resp = client.get("/health")
    assert resp.status_code == HTTPStatus.NO_CONTENT
    assert resp.content == b""


def test_fully_add():
    expected_patch = [
        {
            "op": "add",
            "path": "/spec/template/metadata/labels/webhook-label",
            "value": "test",
        },
        {
            "op": "add",
            "path": "/spec/template/metadata/annotations/webhook-annotation",
            "value": "test",
        },
    ]
    resp = client.post("/mutate", json=deepcopy(BASE_REQUEST))
    assert resp.status_code == HTTPStatus.OK
    check_response(expected_patch, resp.json())


def test_fully_replace():
    req = deepcopy(BASE_REQUEST)
    req["request"]["object"]["spec"]["template"]["metadata"]["annotations"][
        "webhook-annotation"
    ] = "space"
    req["request"]["object"]["spec"]["template"]["metadata"]["labels"][
        "webhook-label"
    ] = "bird"
    expected_patch = [
        {
            "op": "replace",
            "path": "/spec/template/metadata/labels/webhook-label",
            "value": "test",
        },
        {
            "op": "replace",
            "path": "/spec/template/metadata/annotations/webhook-annotation",
            "value": "test",
        },
    ]
    resp = client.post("/mutate", json=req)
    assert resp.status_code == HTTPStatus.OK
    check_response(expected_patch, resp.json())


def test_add_and_replace():
    req = deepcopy(BASE_REQUEST)
    req["request"]["object"]["spec"]["template"]["metadata"]["labels"][
        "webhook-label"
    ] = "bird"
    expected_patch = [
        {
            "op": "replace",
            "path": "/spec/template/metadata/labels/webhook-label",
            "value": "test",
        },
        {
            "op": "add",
            "path": "/spec/template/metadata/annotations/webhook-annotation",
            "value": "test",
        },
    ]
    resp = client.post("/mutate", json=req)
    assert resp.status_code == HTTPStatus.OK
    check_response(expected_patch, resp.json())


def test_partially_replace():
    req = deepcopy(BASE_REQUEST)
    req["request"]["object"]["spec"]["template"]["metadata"]["annotations"][
        "webhook-annotation"
    ] = "test"
    req["request"]["object"]["spec"]["template"]["metadata"]["labels"][
        "webhook-label"
    ] = "bird"
    expected_patch = [
        {
            "op": "replace",
            "path": "/spec/template/metadata/labels/webhook-label",
            "value": "test",
        },
    ]
    resp = client.post("/mutate", json=req)
    assert resp.status_code == HTTPStatus.OK
    check_response(expected_patch, resp.json())


def test_no_unneeded_changes():
    req = deepcopy(BASE_REQUEST)
    req["request"]["object"]["spec"]["template"]["metadata"]["annotations"][
        "webhook-annotation"
    ] = "test"
    req["request"]["object"]["spec"]["template"]["metadata"]["labels"][
        "webhook-label"
    ] = "test"
    expected_patch = []
    resp = client.post("/mutate", json=req)
    assert resp.status_code == HTTPStatus.OK
    check_response(expected_patch, resp.json())


def test_preserve_existing_metadata():
    req = deepcopy(BASE_REQUEST)
    req["request"]["object"]["spec"]["template"]["metadata"]["annotations"][
        "already-existing"
    ] = "space"
    req["request"]["object"]["spec"]["template"]["metadata"]["labels"][
        "already-existing"
    ] = "bird"
    expected_patch = [
        {
            "op": "add",
            "path": "/spec/template/metadata/labels/webhook-label",
            "value": "test",
        },
        {
            "op": "add",
            "path": "/spec/template/metadata/annotations/webhook-annotation",
            "value": "test",
        },
    ]
    resp = client.post("/mutate", json=req)
    assert resp.status_code == HTTPStatus.OK
    check_response(expected_patch, resp.json())
