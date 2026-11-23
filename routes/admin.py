"""Lab 8 daily administrator sales report."""

from flask import Blueprint, current_app
from db import get_connection
from html_utils import escape_html, format_currency, html_page
from routes.auth import require_login

bp = Blueprint("admin", __name__)


@bp.get("/admin")
def admin_report():
    redirect_response = require_login()
    if redirect_response is not None:
        return redirect_response

    connection = None
    try:
        connection = get_connection()
        cursor = connection.cursor()
        cursor.execute("""
            SELECT YEAR(orderDate), MONTH(orderDate), DAY(orderDate), SUM(totalAmount)
            FROM ordersummary
            GROUP BY YEAR(orderDate), MONTH(orderDate), DAY(orderDate)
            ORDER BY YEAR(orderDate), MONTH(orderDate), DAY(orderDate)
        """)
        rows = cursor.fetchall()

        table = """
            <table border="1" cellpadding="8" cellspacing="0">
                <thead><tr><th>Order Date</th><th>Total Sales</th></tr></thead>
                <tbody>
        """
        for year, month, day, total in rows:
            order_date = (
                f"{year:04d}-{month:02d}-{day:02d}"
                if year is not None and month is not None and day is not None
                else "Unknown date"
            )
            table += (
                f"<tr><td>{escape_html(order_date)}</td>"
                f"<td>{format_currency(total)}</td></tr>"
            )
        table += "</tbody></table>"

        return html_page("Administrator Report", f"""
            <h1>Administrator Report</h1>
            {table}
            <p><a href="/">Main Page</a></p>
        """)
    except Exception:
        current_app.logger.exception("Unable to generate daily sales report")
        return html_page("Administrator Report", """
            <h1>Administrator Report</h1>
            <p>Unable to retrieve the daily sales report.</p>
            <p><a href="/">Main Page</a></p>
        """), 500
    finally:
        if connection is not None:
            connection.close()
