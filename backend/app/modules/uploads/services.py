from app.services.cloudinary_service import CloudinaryService


class UploadService:
    ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}
    ALLOWED_MIME_TYPES = {"image/jpeg", "image/png", "image/webp"}
    MAX_IMAGE_BYTES = 5 * 1024 * 1024

    @classmethod
    def validate_image(cls, file):
        filename = str(getattr(file, "filename", "") or "").strip()
        if not filename:
            raise ValueError("No image selected.")
        if (
            "." not in filename
            or filename.rsplit(".", 1)[1].lower() not in cls.ALLOWED_EXTENSIONS
        ):
            raise ValueError("Invalid image format. Use JPG, JPEG, PNG or WEBP.")
        mimetype = str(getattr(file, "mimetype", "") or "").lower()
        if mimetype and mimetype not in cls.ALLOWED_MIME_TYPES:
            raise ValueError("Invalid image content type.")
        content = file.read(cls.MAX_IMAGE_BYTES + 1)
        file.stream.seek(0)
        if len(content) > cls.MAX_IMAGE_BYTES:
            raise ValueError("Image must be 5 MB or smaller.")

    @classmethod
    def upload(cls, file, folder="clipcart/products"):
        cls.validate_image(file)
        return CloudinaryService.upload_image(file, folder=folder)
