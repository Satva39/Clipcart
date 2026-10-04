import os

import cloudinary
import cloudinary.uploader
from dotenv import load_dotenv

load_dotenv()


class CloudinaryService:

    @staticmethod
    def _configure():
        cloud_name = os.getenv(
            "CLOUDINARY_CLOUD_NAME"
        )

        api_key = os.getenv(
            "CLOUDINARY_API_KEY"
        )

        api_secret = os.getenv(
            "CLOUDINARY_API_SECRET"
        )

        if not cloud_name:
            raise RuntimeError(
                "CLOUDINARY_CLOUD_NAME is missing."
            )

        if not api_key:
            raise RuntimeError(
                "CLOUDINARY_API_KEY is missing."
            )

        if not api_secret:
            raise RuntimeError(
                "CLOUDINARY_API_SECRET is missing."
            )

        cloudinary.config(
            cloud_name=cloud_name,
            api_key=api_key,
            api_secret=api_secret,
            secure=True,
        )

    @staticmethod
    def upload_image(
        file,
        folder="clipcart/products",
    ):
        CloudinaryService._configure()

        result = cloudinary.uploader.upload(
            file,
            folder=folder,
            resource_type="image",
        )

        return {
            "image_url": result["secure_url"],
            "public_id": result["public_id"],
        }

    @staticmethod
    def delete_image(public_id):
        CloudinaryService._configure()

        return cloudinary.uploader.destroy(
            public_id
        )