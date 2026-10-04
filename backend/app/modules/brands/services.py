from .repository import BrandRepository


class BrandService:

    @staticmethod
    def get_all():
        return BrandRepository.get_all()

    @staticmethod
    def get_by_slug(slug):
        return BrandRepository.get_by_slug(slug)