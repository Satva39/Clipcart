from app.extensions import db

from .models import DeliveryAssignment
from .enums import PickupStatus, DeliveryStatus


class DeliveryAssignmentRepository:
    @staticmethod
    def get_by_order_id(order_id):
        return DeliveryAssignment.query.filter_by(order_id=order_id).first()

    @staticmethod
    def get_or_create(order_id):
        assignment = DeliveryAssignmentRepository.get_by_order_id(order_id)
        if assignment:
            return assignment

        assignment = DeliveryAssignment(
            order_id=order_id,
            pickup_status=PickupStatus.PENDING,
            delivery_status=DeliveryStatus.NOT_STARTED,
            delivery_attempts=0,
        )
        db.session.add(assignment)
        db.session.flush()
        return assignment

    @staticmethod
    def save(assignment):
        db.session.add(assignment)
        db.session.commit()
        return assignment
