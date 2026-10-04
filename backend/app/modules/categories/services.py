from app.extensions import db
from .models import Category


def get_categories():
    return Category.query.all()


def create_category(name, slug, parent_id=None):

    category = Category(
        name=name,
        slug=slug,
        parent_id=parent_id,
    )

    db.session.add(category)
    db.session.commit()

    return category

def get_category(category_id):
    return Category.query.get(category_id)