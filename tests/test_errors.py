from http import HTTPStatus

from app.core.errors import _error_code_for_status


def test_error_code_for_status_maps_bad_request():
    assert _error_code_for_status(HTTPStatus.BAD_REQUEST) == "bad_request"


def test_error_code_for_status_maps_conflict():
    assert _error_code_for_status(HTTPStatus.CONFLICT) == "conflict"
