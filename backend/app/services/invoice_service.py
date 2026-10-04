import os
from datetime import datetime
from decimal import Decimal

from flask import current_app
from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from xml.sax.saxutils import escape

from app.extensions import db
from app.modules.invoices.models import Invoice


class InvoiceService:
    @staticmethod
    def _text(value):
        return escape(str(value or ""), {'"': "&quot;"})

    @staticmethod
    def _directory():
        configured = current_app.config.get("INVOICE_DIR")
        if configured:
            path = configured
        else:
            path = os.path.abspath(
                os.path.join(current_app.root_path, "..", "storage", "invoices")
            )
        os.makedirs(path, exist_ok=True)
        return path

    @staticmethod
    def ensure_record(order):
        invoice = Invoice.query.filter_by(order_id=order.id).first()
        if invoice:
            return invoice
        invoice = Invoice(
            order_id=order.id,
            invoice_number=f"CC-INV-{order.id:08d}",
            status="PENDING",
        )
        db.session.add(invoice)
        db.session.commit()
        return invoice

    @staticmethod
    def generate(order):
        invoice = InvoiceService.ensure_record(order)
        directory = InvoiceService._directory()
        path = os.path.join(directory, f"{invoice.invoice_number}.pdf")

        styles = getSampleStyleSheet()
        styles.add(
            ParagraphStyle(
                name="InvoiceSmall",
                parent=styles["BodyText"],
                fontSize=8.5,
                leading=11,
            )
        )
        styles.add(
            ParagraphStyle(
                name="InvoiceRight",
                parent=styles["BodyText"],
                fontSize=9,
                leading=12,
                alignment=TA_RIGHT,
            )
        )
        styles.add(
            ParagraphStyle(
                name="InvoiceTitle",
                parent=styles["Heading1"],
                fontSize=22,
                leading=26,
                spaceAfter=2,
            )
        )

        document = SimpleDocTemplate(
            path,
            pagesize=A4,
            rightMargin=18 * mm,
            leftMargin=18 * mm,
            topMargin=16 * mm,
            bottomMargin=16 * mm,
            title=invoice.invoice_number,
            author="Clipcart",
        )
        story = []
        story.append(Paragraph("CLIPCART", styles["InvoiceTitle"]))
        story.append(Paragraph("Customer invoice", styles["InvoiceSmall"]))
        story.append(Spacer(1, 8 * mm))

        order_date = order.created_at.strftime("%d %b %Y, %I:%M %p")
        header = Table(
            [
                [
                    Paragraph(
                        f"<b>Invoice</b><br/>{invoice.invoice_number}<br/><br/><b>Order</b><br/>#{order.id}",
                        styles["BodyText"],
                    ),
                    Paragraph(
                        f"<b>Order date</b><br/>{order_date}<br/><br/><b>Payment</b><br/>{order.payment.status if order.payment else 'UNPAID'}",
                        styles["InvoiceRight"],
                    ),
                ]
            ],
            colWidths=[90 * mm, 90 * mm],
        )
        header.setStyle(
            TableStyle(
                [
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LINEBELOW", (0, 0), (-1, -1), 0.6, colors.HexColor("#DDDDDD")),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                ]
            )
        )
        story.append(header)
        story.append(Spacer(1, 6 * mm))

        customer_text = f"<b>Bill to</b><br/>{InvoiceService._text(order.customer_name)}<br/>{InvoiceService._text(order.customer_email)}"
        delivery_lines = [
            InvoiceService._text(order.delivery_full_name),
            InvoiceService._text(order.delivery_address_line_1),
        ]
        if order.delivery_address_line_2:
            delivery_lines.append(InvoiceService._text(order.delivery_address_line_2))
        if order.delivery_landmark:
            delivery_lines.append(InvoiceService._text(order.delivery_landmark))
        delivery_lines.append(
            f"{InvoiceService._text(order.delivery_city)}, {InvoiceService._text(order.delivery_state)} {InvoiceService._text(order.delivery_postal_code)}"
        )
        delivery_lines.append(InvoiceService._text(order.delivery_country))
        delivery_lines.append(InvoiceService._text(order.delivery_phone))
        delivery_text = "<b>Deliver to</b><br/>" + "<br/>".join(delivery_lines)
        parties = Table(
            [
                [
                    Paragraph(customer_text, styles["BodyText"]),
                    Paragraph(delivery_text, styles["BodyText"]),
                ]
            ],
            colWidths=[90 * mm, 90 * mm],
        )
        parties.setStyle(
            TableStyle(
                [
                    ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#DDDDDD")),
                    ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#EEEEEE")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("PADDING", (0, 0), (-1, -1), 7),
                ]
            )
        )
        story.append(parties)
        story.append(Spacer(1, 7 * mm))

        rows = [
            [
                Paragraph("Product", styles["InvoiceSmall"]),
                Paragraph("Variant", styles["InvoiceSmall"]),
                Paragraph("Qty", styles["InvoiceSmall"]),
                Paragraph("Unit price", styles["InvoiceSmall"]),
                Paragraph("Amount", styles["InvoiceSmall"]),
            ]
        ]
        for item in order.items:
            variant = InvoiceService._text(
                item.variant_value_snapshot
                or (item.variant.value if item.variant else "—")
            )
            product_name = InvoiceService._text(
                item.product_name_snapshot
                or (item.product.name if item.product else "Product")
            )
            rows.append(
                [
                    Paragraph(product_name, styles["InvoiceSmall"]),
                    Paragraph(variant, styles["InvoiceSmall"]),
                    Paragraph(str(item.quantity), styles["InvoiceSmall"]),
                    Paragraph(
                        f"₹ {Decimal(str(item.unit_price)):.2f}", styles["InvoiceRight"]
                    ),
                    Paragraph(
                        f"₹ {Decimal(str(item.subtotal)):.2f}", styles["InvoiceRight"]
                    ),
                ]
            )
        item_table = Table(
            rows, colWidths=[56 * mm, 45 * mm, 15 * mm, 29 * mm, 35 * mm], repeatRows=1
        )
        item_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F4F5F7")),
                    ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#DDDDDD")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("ALIGN", (2, 1), (2, -1), "CENTER"),
                    ("PADDING", (0, 0), (-1, -1), 5),
                ]
            )
        )
        story.append(item_table)
        story.append(Spacer(1, 6 * mm))

        totals = [
            ["Subtotal", f"₹ {Decimal(str(order.subtotal)):.2f}"],
            ["Discount", f"− ₹ {Decimal(str(order.discount)):.2f}"],
            ["Marketing fee", f"₹ {Decimal(str(order.marketing_fee)):.2f}"],
            [
                "Tax",
                f"₹ {Decimal(str(order.tax)):.2f}",
            ],
            ["Final total", f"₹ {Decimal(str(order.total)):.2f}"],
        ]
        totals_table = Table(totals, colWidths=[125 * mm, 55 * mm], hAlign="RIGHT")
        totals_table.setStyle(
            TableStyle(
                [
                    ("ALIGN", (1, 0), (1, -1), "RIGHT"),
                    ("LINEABOVE", (0, 4), (-1, 4), 0.8, colors.HexColor("#222222")),
                    ("FONTNAME", (0, 4), (-1, 4), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ]
            )
        )
        story.append(totals_table)
        story.append(Spacer(1, 8 * mm))
        story.append(
            Paragraph(
                "Taxable base used for Clipcart tax: discounted merchandise subtotal. Marketing fee is added separately after tax.",
                styles["InvoiceSmall"],
            )
        )
        story.append(Spacer(1, 3 * mm))
        story.append(
            Paragraph(
                "This invoice is generated from the permanent Clipcart order record and reflects the amount verified at payment time.",
                styles["InvoiceSmall"],
            )
        )

        document.build(story)
        invoice.file_path = path
        invoice.status = "GENERATED"
        invoice.generated_at = datetime.utcnow()
        db.session.commit()
        return path
