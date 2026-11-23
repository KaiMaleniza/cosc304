"""Question 1 (10 marks): list all orders and their ordered products."""

from flask import Blueprint, current_app
from db import get_connection
from html_utils import escape_html, format_currency, html_page

bp = Blueprint("listorder", __name__)


@bp.get("/listorder")
def list_orders():
    connection = None
    try:
        connection = get_connection()
        cursor = connection.cursor()

        cursor.execute("SELECT orderId, orderDate, customerId, totalAmount FROM ordersummary")
        orders = cursor.fetchall()

        content = "<h1>Order List</h1>"

        if not orders:
            content += "<p>No orders found in the database.</p>"
        else:
            content += """
            <table border="1" cellpadding="8" cellspacing="0" style="border-collapse: collapse; width: 100%;">
                <thead>
                    <tr style="background-color: #f2f2f2;">
                        <th>Order ID</th>
                        <th>Order Date</th>
                        <th>Customer ID</th>
                        <th>Total Amount</th>
                        <th>Ordered Products</th>
                    </tr>
                </thead>
                <tbody>
            """

            for order in orders:
                order_id, order_date, customer_id, total_amount = order

                item_sql = """
                    SELECT p.productName, op.quantity, op.price 
                    FROM orderproduct op 
                    JOIN product p ON op.productId = p.productId 
                    WHERE op.orderId = ?
                """
                cursor.execute(item_sql, (order_id,))
                items = cursor.fetchall()

                products_html = "<ul style='margin: 0; padding-left: 20px;'>"
                if items:
                    for item in items:
                        product_name, quantity, price = item
                        formatted_price = format_currency(price)
                        safe_product_name = escape_html(str(product_name))
                        products_html += f"<li>{safe_product_name} (Qty: {quantity}) - {formatted_price}</li>"
                else:
                    products_html += "<li>No items found for this order.</li>"
                products_html += "</ul>"

                content += "<tr>"
                content += f"<td>{escape_html(str(order_id))}</td>"
                content += f"<td>{escape_html(str(order_date))}</td>"
                content += f"<td>{escape_html(str(customer_id))}</td>"
                content += f"<td>{format_currency(total_amount)}</td>"
                content += f"<td>{products_html}</td>"
                content += "</tr>"

            content += "</tbody></table>"

        return html_page("Kai & Manhar Grocery Order List", content)

    except Exception:
        current_app.logger.exception("Unable to list orders")
        return html_page("Order List Error", "<h1>Unable to retrieve orders.</h1>"), 500
    finally:
        if connection is not None:
            connection.close()