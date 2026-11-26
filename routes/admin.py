"""Lab 8 administrator sales report."""

from datetime import date, timedelta

from flask import Blueprint, current_app, request
from db import get_connection
from html_utils import escape_html, format_currency, html_page
from routes.auth import require_login

bp = Blueprint("admin", __name__)


def parse_report_dates(start_value, end_value):
    """Validate optional ISO date values and reject an inverted range."""
    start_date = None
    end_date = None
    try:
        if start_value:
            start_date = date.fromisoformat(start_value)
        if end_value:
            end_date = date.fromisoformat(end_value)
    except ValueError:
        return None, None, "Enter valid dates."

    if start_date is not None and end_date is not None and start_date > end_date:
        return None, None, "Start date must be on or before the end date."

    return start_date, end_date, None


@bp.get("/admin")
def admin_report():
    redirect_response = require_login()
    if redirect_response is not None:
        return redirect_response

    start_value = request.args.get("start", "").strip()
    end_value = request.args.get("end", "").strip()
    start_date, end_date, range_error = parse_report_dates(start_value, end_value)

    if range_error:
        return html_page("Administrator Report", f"""
            <h1>Administrator Report</h1>
            <p role="alert" style="color: darkred;">{escape_html(range_error)}</p>
            <p><a href="/admin">Reset date filter</a></p>
        """), 400

    connection = None
    try:
        connection = get_connection()
        cursor = connection.cursor()

        conditions = []
        parameters = []
        if start_date is not None:
            conditions.append("orderDate >= ?")
            parameters.append(start_date.isoformat())
        if end_date is not None:
            conditions.append("orderDate < ?")
            parameters.append((end_date + timedelta(days=1)).isoformat())

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        daily_sales_sql = """
            SELECT YEAR(orderDate), MONTH(orderDate), DAY(orderDate),
                   SUM(totalAmount), COUNT(*)
            FROM ordersummary
            %s
            GROUP BY YEAR(orderDate), MONTH(orderDate), DAY(orderDate)
            ORDER BY YEAR(orderDate), MONTH(orderDate), DAY(orderDate)
        """ % where_clause
        if parameters:
            cursor.execute(daily_sales_sql, tuple(parameters))
        else:
            cursor.execute(daily_sales_sql)
        rows = cursor.fetchall()

        summary_sql = f"""
            SELECT SUM(totalAmount), COUNT(*)
            FROM ordersummary
            {where_clause}
        """
        if parameters:
            cursor.execute(summary_sql, tuple(parameters))
        else:
            cursor.execute(summary_sql)
        summary_row = cursor.fetchone()
        total_sales = summary_row[0] if summary_row is not None and summary_row[0] is not None else 0
        order_count = summary_row[1] if summary_row is not None else 0

        range_label = "All dates"
        if start_date is not None or end_date is not None:
            range_label = (
                f"{start_date.isoformat() if start_date else 'First available date'}"
                " through "
                f"{end_date.isoformat() if end_date else 'Last available date'}"
            )

        table = """
            <table border="1" cellpadding="8" cellspacing="0" style="border-collapse: collapse;">
                <thead><tr><th>Order Date</th><th>Orders</th><th>Total Sales</th></tr></thead>
                <tbody>
        """
        best_day = None
        best_day_total = None
        for year, month, day, total, count in rows:
            order_date = (
                f"{year:04d}-{month:02d}-{day:02d}"
                if year is not None and month is not None and day is not None
                else "Unknown date"
            )
            if best_day is None or total > best_day_total:
                best_day = order_date
                best_day_total = total
            table += (
                f"<tr><td>{escape_html(order_date)}</td>"
                f"<td>{escape_html(count)}</td>"
                f"<td>{format_currency(total)}</td></tr>"
            )
        table += "</tbody></table>"
        if not rows:
            table = "<p>No orders were found for this date range.</p>"

        summary = (
            "<div style='display: flex; gap: 24px; flex-wrap: wrap;'>"
            f"<p><strong>Orders:</strong> {escape_html(order_count)}</p>"
            f"<p><strong>Total sales:</strong> {format_currency(total_sales)}</p>"
            f"<p><strong>Best sales day:</strong> "
            f"{escape_html(best_day if best_day is not None else 'N/A')}"
            f"{(' (' + format_currency(best_day_total) + ')') if best_day is not None else ''}</p>"
            "</div>"
        )

        return html_page("Administrator Report", f"""
            <h1>Administrator Report</h1>
            <form method="get" action="/admin">
                <label>Start date:
                    <input type="date" name="start" value="{escape_html(start_value)}">
                </label>
                <label>End date:
                    <input type="date" name="end" value="{escape_html(end_value)}">
                </label>
                <button type="submit">Apply filter</button>
                <a href="/admin">Clear</a>
            </form>
            <h2>Sales summary ({escape_html(range_label)})</h2>
            {summary}
            <h2>Daily sales</h2>
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
