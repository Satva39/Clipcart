import csv
import io

from flask import Blueprint, Response, request
from flask_jwt_extended import get_jwt_identity

from app.core.decorators import active_supplier_required
from app.modules.products.models import Product
from app.modules.orders.enums import OrderStatus
from app.modules.orders.services import OrderService
from app.utils.response import error_response, success_response
from .services import SupplierPortalService, _supplier_order_rows, resolve_range

supplier_portal_bp = Blueprint(
    "supplier_portal", __name__, url_prefix="/api/supplier/portal"
)


@supplier_portal_bp.get("/profile")
@active_supplier_required
def get_profile():
    return success_response(data=SupplierPortalService.profile(int(get_jwt_identity())))


@supplier_portal_bp.put("/profile")
@active_supplier_required
def update_profile():
    try:
        data = SupplierPortalService.update_profile(
            int(get_jwt_identity()), request.get_json(silent=True) or {}
        )
    except ValueError as exc:
        return error_response(message=str(exc), status_code=400)
    return success_response(message="Supplier profile updated.", data=data)


@supplier_portal_bp.get("/dashboard")
@active_supplier_required
def dashboard():
    try:
        data = SupplierPortalService.dashboard(
            int(get_jwt_identity()), request.args.get("start"), request.args.get("end")
        )
    except ValueError as exc:
        return error_response(message=str(exc), status_code=400)
    return success_response(data=data)


@supplier_portal_bp.get("/analytics")
@active_supplier_required
def analytics():
    try:
        data = SupplierPortalService.analytics(
            int(get_jwt_identity()), request.args.get("start"), request.args.get("end")
        )
    except ValueError as exc:
        return error_response(message=str(exc), status_code=400)
    return success_response(data=data)


@supplier_portal_bp.get("/catalog")
@active_supplier_required
def catalog():
    return success_response(
        data=SupplierPortalService.catalog(
            int(get_jwt_identity()),
            search=request.args.get("search"),
            status=request.args.get("status"),
            page=request.args.get("page", 1, type=int),
            per_page=request.args.get("per_page", 20, type=int),
        )
    )


@supplier_portal_bp.post("/import/orders")
@active_supplier_required
def import_orders():
    supplier_id = int(get_jwt_identity())
    uploaded = request.files.get("file")
    if uploaded is None or not uploaded.filename:
        return error_response("CSV file is required.", 400)

    filename = str(uploaded.filename).strip().lower()
    if not filename.endswith(".csv"):
        return error_response("Please select a CSV file.", 400)

    if request.content_length and request.content_length > 2 * 1024 * 1024:
        return error_response("CSV file must be 2 MB or smaller.", 413)

    try:
        raw = uploaded.read(2 * 1024 * 1024 + 1)
    except Exception:
        return error_response("Unable to read the CSV file.", 400)
    if len(raw) > 2 * 1024 * 1024:
        return error_response("CSV file must be 2 MB or smaller.", 413)

    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        return error_response("CSV must be UTF-8 encoded.", 400)

    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        return error_response("CSV must contain a header row.", 400)

    normalized_headers = {
        str(header or "").strip().lower(): header for header in reader.fieldnames
    }
    order_header = normalized_headers.get("order id")
    status_header = normalized_headers.get("status")
    if not order_header or not status_header:
        return error_response("CSV must contain 'Order ID' and 'Status' columns.", 400)

    rows = []
    seen = set()
    for line_number, row in enumerate(reader, start=2):
        raw_order_id = str(row.get(order_header) or "").strip()
        raw_status = str(row.get(status_header) or "").strip().upper()
        if not raw_order_id and not raw_status:
            continue
        try:
            order_id = int(raw_order_id)
        except (TypeError, ValueError):
            return error_response(f"Row {line_number}: Order ID must be a number.", 400)
        if order_id in seen:
            return error_response(
                f"Row {line_number}: duplicate Order ID {order_id}.", 400
            )
        seen.add(order_id)
        if raw_status != OrderStatus.PROCESSING.value:
            return error_response(
                f"Row {line_number}: suppliers can import only PROCESSING status.",
                400,
            )
        if len(rows) >= 200:
            return error_response("A single import can contain at most 200 rows.", 400)
        if not OrderService.get_supplier_order(supplier_id, order_id):
            return error_response(
                f"Row {line_number}: Order #{order_id} was not found for this supplier.",
                404,
            )
        rows.append(order_id)

    if not rows:
        return error_response("The CSV contains no order rows to import.", 400)

    updated = 0
    unchanged = 0
    try:
        for order_id in rows:
            before = OrderService.get_supplier_order(supplier_id, order_id)
            current_status = before.get("status") if before else None
            if current_status == OrderStatus.PROCESSING.value:
                unchanged += 1
                continue
            OrderService.update_supplier_status(
                supplier_id,
                order_id,
                OrderStatus.PROCESSING.value,
            )
            updated += 1
    except ValueError as exc:
        return error_response(str(exc), 400)

    return success_response(
        "Supplier order CSV imported.",
        {"rows": len(rows), "updated": updated, "unchanged": unchanged},
    )


@supplier_portal_bp.get("/export/<kind>")
@active_supplier_required
def export_data(kind):
    supplier_id = int(get_jwt_identity())
    kind = str(kind).lower()
    start = request.args.get("start")
    end = request.args.get("end")
    try:
        start_date, end_date = resolve_range(start, end)
    except ValueError as exc:
        return error_response(message=str(exc), status_code=400)

    output = io.StringIO()
    writer = csv.writer(output)

    if kind == "products":
        writer.writerow(
            [
                "Product ID",
                "Name",
                "SKU",
                "Category",
                "Brand",
                "Price",
                "Compare Price",
                "Stock",
                "Status",
            ]
        )
        for p in (
            Product.query.filter_by(seller_id=supplier_id)
            .order_by(Product.id.asc())
            .all()
        ):
            writer.writerow(
                [
                    p.id,
                    p.name,
                    p.sku or "",
                    p.category.name if p.category else "",
                    p.brand.name if p.brand else "",
                    float(p.price or 0),
                    float(p.compare_price) if p.compare_price is not None else "",
                    int(p.stock or 0),
                    p.status,
                ]
            )
        filename = "clipcart-supplier-products.csv"
    elif kind == "orders":
        writer.writerow(
            [
                "Order ID",
                "Order Date",
                "Customer",
                "Status",
                "Supplier Revenue",
                "Units",
            ]
        )
        for group in _supplier_order_rows(supplier_id, start_date, end_date):
            order = group["order"]
            revenue = SupplierPortalService._supplier_revenue(
                group["items"], order.status.value
            )
            units = sum(int(item.quantity or 0) for item in group["items"])
            writer.writerow(
                [
                    order.id,
                    order.created_at,
                    order.delivery_full_name or order.customer_name,
                    order.status.value,
                    revenue,
                    units,
                ]
            )
        filename = "clipcart-supplier-orders.csv"
    elif kind in {"sales", "earnings"}:
        analytics = SupplierPortalService.analytics(
            supplier_id, start_date.isoformat(), end_date.isoformat()
        )
        writer.writerow(["Date", "Sales", "Orders", "Units Sold"])
        for row in analytics["series"]:
            writer.writerow([row["date"], row["sales"], row["orders"], row["units"]])
        writer.writerow([])
        writer.writerow(["Metric", "Value"])
        for key, value in analytics["summary"].items():
            writer.writerow([key, value])
        filename = "clipcart-supplier-earnings.csv"
    else:
        return error_response(message="Unsupported export type.", status_code=400)

    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
