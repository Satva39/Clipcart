from .models import Category


class CategoryRepository:

    @staticmethod
    def get_by_id(category_id):
        return Category.query.get(category_id)