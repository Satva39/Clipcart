from flask import Blueprint, request

from app.modules.uploads.services import UploadService
from app.utils.response import success_response, error_response
from app.core.decorators import supplier_or_admin_required

upload_bp = Blueprint("uploads", __name__)


@upload_bp.route("/upload", methods=["POST"])
@supplier_or_admin_required
def upload_image():

    if "image" not in request.files:
        return error_response("Image is required.")

    image = request.files["image"]

    try:
        result = UploadService.upload(image)
    except ValueError as exc:
        return error_response(message=str(exc), status_code=400)

    return success_response(
        "Image uploaded successfully.",
        result,
    )
