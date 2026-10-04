from flask import jsonify
from sqlalchemy.exc import SQLAlchemyError


def register_error_handlers(app):
    """Return predictable JSON errors from the API instead of HTML error pages."""

    @app.errorhandler(400)
    def handle_bad_request(error):
        return (
            jsonify(
                {
                    "success": False,
                    "message": getattr(error, "description", "Bad request."),
                    "data": None,
                }
            ),
            400,
        )

    @app.errorhandler(404)
    def handle_not_found(_error):
        return (
            jsonify(
                {
                    "success": False,
                    "message": "Resource not found.",
                    "data": None,
                }
            ),
            404,
        )

    @app.errorhandler(405)
    def handle_method_not_allowed(_error):
        return (
            jsonify(
                {
                    "success": False,
                    "message": "Method not allowed.",
                    "data": None,
                }
            ),
            405,
        )

    @app.errorhandler(SQLAlchemyError)
    def handle_database_error(_error):
        if app.debug:
            # Keep API responses generic while exposing the full traceback in
            # the local development server so database/schema issues can be
            # diagnosed without leaking details to clients.
            app.logger.exception("Database error while handling API request.")
        else:
            app.logger.error("Database error while handling API request.")
        return (
            jsonify(
                {
                    "success": False,
                    "message": "A database error occurred.",
                    "data": None,
                }
            ),
            500,
        )

    @app.errorhandler(Exception)
    def handle_unexpected_error(_error):
        app.logger.exception("Unhandled API error.")
        return (
            jsonify(
                {
                    "success": False,
                    "message": "An unexpected server error occurred.",
                    "data": None,
                }
            ),
            500,
        )
