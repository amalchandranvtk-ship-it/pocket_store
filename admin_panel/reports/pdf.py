from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.lib.pagesizes import landscape, A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from django.db.models import Count
from django.db.models import Sum
from django.utils import timezone
from datetime import timedelta

from customer.orders.models import Order


try:
    pdfmetrics.registerFont(
        TTFont("DejaVu", "DejaVuSans.ttf")
    )
    DEFAULT_FONT = "DejaVu"
except Exception:
    DEFAULT_FONT = "Helvetica"


styles = getSampleStyleSheet()

title_style = styles["Heading1"]
title_style.fontName = DEFAULT_FONT
title_style.alignment = TA_CENTER
title_style.fontSize = 20
title_style.spaceAfter = 20

heading_style = styles["Heading2"]
heading_style.fontName = DEFAULT_FONT

normal_style = styles["BodyText"]
normal_style.fontName = DEFAULT_FONT

right_style = styles["BodyText"]
right_style.fontName = DEFAULT_FONT
right_style.alignment = TA_RIGHT


def get_filtered_orders(request):
    

    report_type = request.GET.get("report_type", "daily")

    from_date = request.GET.get("from_date")
    to_date = request.GET.get("to_date")

    today = timezone.now()

    orders = (
        Order.objects.filter(order_status="delivered")
        .select_related("user", "payment")
        .order_by("-placed_at")
    )

    if report_type == "daily":

        orders = orders.filter(
            placed_at__date=today.date()
        )

    elif report_type == "weekly":

        start = today.date() - timedelta(days=7)

        orders = orders.filter(
            placed_at__date__gte=start,
            placed_at__date__lte=today.date(),
        )

    elif report_type == "monthly":

        orders = orders.filter(
            placed_at__year=today.year,
            placed_at__month=today.month,
        )

    elif report_type == "yearly":

        orders = orders.filter(
            placed_at__year=today.year
        )

    elif report_type == "custom":

        if from_date and to_date:

            orders = orders.filter(
                placed_at__date__range=[
                    from_date,
                    to_date,
                ]
            )

    summary = orders.aggregate(
        total_orders=Count("id"),
        total_sales=Sum("total_amount"),
        total_discount=Sum("discount_amount"),
        coupon_discount=Sum("coupon_discount_value"),
    )

    return (
        orders,
        summary,
        report_type,
        from_date,
        to_date,
    )


def header_footer(canvas, doc):

    canvas.saveState()

    canvas.setFont(DEFAULT_FONT, 16)

    canvas.drawString(
        30,
        570,
        "PocketStore"
    )

    canvas.setFont(DEFAULT_FONT, 9)

    canvas.drawRightString(
        800,
        570,
        f"Generated : {timezone.now().strftime('%d-%m-%Y %I:%M %p')}"
    )

    canvas.line(
        30,
        560,
        810,
        560,
    )

    canvas.setFont(DEFAULT_FONT, 9)

    canvas.drawCentredString(
        420,
        18,
        f"Page {doc.page}"
    )

    canvas.restoreState()


def build_summary_table(summary):

    data = [

        [
            "Total Orders",
            summary["total_orders"] or 0,
        ],

        [
            "Total Sales",
            f"₹ {summary['total_sales'] or 0}",
        ],

        [
            "Discount",
            f"₹ {summary['total_discount'] or 0}",
        ],

        [
            "Coupon Discount",
            f"₹ {summary['coupon_discount'] or 0}",
        ],
    ]

    table = Table(
        data,
        colWidths=[220, 180],
    )

    table.setStyle(

        TableStyle(

            [

                ("BACKGROUND", (0, 0), (-1, -1), colors.whitesmoke),

                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),

                ("FONTNAME", (0, 0), (-1, -1), DEFAULT_FONT),

                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),

                ("TOPPADDING", (0, 0), (-1, -1), 8),

                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#2563eb")),

                ("TEXTCOLOR", (0, 0), (0, -1), colors.white),

                ("ALIGN", (1, 0), (1, -1), "RIGHT"),

            ]

        )

    )

    return table

def generate_sales_report_pdf(request):
   

    orders, summary, report_type, from_date, to_date = get_filtered_orders(
        request
    )

    buffer = BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        leftMargin=20,
        rightMargin=20,
        topMargin=30,
        bottomMargin=30,
    )

    elements = []

    
    elements.append(
        Paragraph(
            "PocketStore Sales Report",
            title_style,
        )
    )

    elements.append(
        Paragraph(
            f"<b>Report Type :</b> {report_type.title()}",
            normal_style,
        )
    )

    if report_type == "custom":

        elements.append(
            Paragraph(
                f"<b>Date Range :</b> {from_date} to {to_date}",
                normal_style,
            )
        )

    else:

        elements.append(
            Paragraph(
                f"<b>Generated On :</b> {timezone.now().strftime('%d-%m-%Y %I:%M %p')}",
                normal_style,
            )
        )

    elements.append(Spacer(1, 20))

    

    elements.append(
        Paragraph(
            "Sales Summary",
            heading_style,
        )
    )

    elements.append(
        Spacer(1, 10)
    )

    elements.append(
        build_summary_table(summary)
    )

    elements.append(
        Spacer(1, 20)
    )

    
    elements.append(
        Paragraph(
            "Delivered Orders",
            heading_style,
        )
    )

    elements.append(
        Spacer(1, 10)
    )

   

    table_data = [

        [

            "Order No",

            "Customer",

            "Date",

            "Payment",

            "Status",

            "Discount",

            "Total",

        ]

    ]

    

    for order in orders:

        payment_method = "-"

        if hasattr(order, "payment"):

            payment_method = (
                order.payment.get_payment_method_display()
            )

        customer = ""

        if order.user:

            customer = (
                order.user.get_full_name()
                or order.user.username
            )

        table_data.append(

            [

                order.order_number,

                customer,

                order.placed_at.strftime("%d-%m-%Y"),

                payment_method,

                order.get_payment_status_display(),

                f"₹ {order.discount_amount}",

                f"₹ {order.total_amount}",

            ]

        )
      

    order_table = Table(
        table_data,
        colWidths=[
            100,   
            140,   
            90,    
            110,   
            90,    
            90,   
            90,    
        ],
        repeatRows=1,
    )

    order_table.setStyle(

        TableStyle(

            [

                
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2563EB")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), DEFAULT_FONT),
                ("FONTSIZE", (0, 0), (-1, 0), 10),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
                ("TOPPADDING", (0, 0), (-1, 0), 8),

                # Body
                ("FONTNAME", (0, 1), (-1, -1), DEFAULT_FONT),
                ("FONTSIZE", (0, 1), (-1, -1), 9),

                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),

                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),

                ("BACKGROUND", (0, 1), (-1, -1), colors.whitesmoke),

                ("BOTTOMPADDING", (0, 1), (-1, -1), 6),
                ("TOPPADDING", (0, 1), (-1, -1), 6),

            ]

        )

    )

    elements.append(order_table)

    elements.append(Spacer(1, 20))

    

    elements.append(

        Paragraph(

            f"""
            <b>Total Orders :</b> {summary['total_orders'] or 0}
            &nbsp;&nbsp;&nbsp;&nbsp;
            <b>Total Sales :</b> ₹ {summary['total_sales'] or 0}
            """,

            normal_style,

        )

    )

   

    doc.build(
        elements,
        onFirstPage=header_footer,
        onLaterPages=header_footer,
    )

    buffer.seek(0)

    return buffer