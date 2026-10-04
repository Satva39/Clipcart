from flask import Blueprint
from flask_jwt_extended import get_jwt_identity

from app.core.decorators import active_supplier_required

from app.utils.response import success_response
from .services import SupplierDashboardService

supplier_dashboard_bp = Blueprint(
    "supplier_dashboard",
    __name__,
    url_prefix="/api/supplier/dashboard",
)


@supplier_dashboard_bp.get("/")
@active_supplier_required
def dashboard():

    account_id = int(get_jwt_identity())

    data = SupplierDashboardService.dashboard(account_id)

    return success_response(data=data)
