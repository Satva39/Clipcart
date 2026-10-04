"""Compatibility wrappers for older modules."""

from app.shared.utils.api_response import error, success


def success_response(message="", data=None, status_code=200):
    return success(message=message, data=data, status_code=status_code)


def error_response(message="", status_code=400, data=None):
    return error(message=message, status_code=status_code, data=data)
