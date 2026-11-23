"""Question 2 (20 marks): validate and save a completed order."""

from flask import Blueprint, request, session, current_app
from db import get_connection
from html_utils import escape_html, format_currency, html_page

bp = Blueprint("order", __name__)

@bp.post("/order")
def place_order():
    customer_id = request.form.get("customerId", "")
    products = list(session.get("productList", {}).values())
    connection = None

    try:
        try:
            cust_id_int = int(customer_id)
            if cust_id_int <= 0:
                raise ValueError()
        except ValueError:
            return html_page(
                "Order Processing Error",
                "<h1>Invalid Customer ID</h1><p>Customer ID must be a positive integer.</p>"
            ), 400

        connection = get_connection()
        cursor = connection.cursor()

        cursor.execute("SELECT customerId FROM customer WHERE customerId = ?", (cust_id_int,))
        if not cursor.fetchone():
            connection.close()
            return html_page(
                "Order Processing Error",
                "<h1>Customer Not Found</h1><p>The specified Customer ID does not exist in the database.</p>"
            ), 400

        if not products:
            connection.close()
            return html_page(
                "Order Processing Error",
                "<h1>Cart is Empty</h1><p>You cannot place an order with an empty product list.</p>"
            ), 400

        cursor.execute(
            "INSERT INTO ordersummary (customerId, orderDate) OUTPUT INSERTED.orderId VALUES (?, GETDATE())",
            (cust_id_int,)
        )
        row = cursor.fetchone()
        if not row:
            raise Exception("Failed to retrieve generated orderId.")
        order_id = row[0]

        total_amount = 0.0

        for prod in products:
            prod_id = prod.get("id")
            prod_price = float(prod.get("price", 0.0))
            prod_quantity = int(prod.get("quantity", 1))
            total_amount += prod_price * prod_quantity

            cursor.execute(
                "INSERT INTO orderproduct (orderId, productId, quantity, price) VALUES (?, ?, ?, ?)",
                (order_id, prod_id, prod_quantity, prod_price)
            )

        cursor.execute(
            "UPDATE ordersummary SET totalAmount = ? WHERE orderId = ?",
            (total_amount, order_id)
        )

        connection.commit()

        session.pop("productList", None)

        content = f"<h1>Order Placed Successfully!</h1>"
        content += f"<p><strong>Order ID:</strong> {escape_html(str(order_id))}</p>"
        content += f"<p><strong>Customer ID:</strong> {escape_html(str(cust_id_int))}</p>"
        content += "<h2>Purchased Products</h2>"
        content += """
        <table border="1" cellpadding="8" cellspacing="0" style="border-collapse: collapse; width: 100%;">
            <thead>
                <tr style="background-color: #f2f2f2;">
                    <th>Product Name</th>
                    <th>Price</th>
                    <th>Quantity</th>
                    <th>Subtotal</th>
                </tr>
            </thead>
            <tbody>
        """

        for prod in products:
            name = escape_html(str(prod.get("name", "")))
            price = float(prod.get("price", 0.0))
            qty = int(prod.get("quantity", 1))
            subtotal = price * qty

            content += "<tr>"
            content += f"<td>{name}</td>"
            content += f"<td>{format_currency(price)}</td>"
            content += f"<td>{qty}</td>"
            content += f"<td>{format_currency(subtotal)}</td>"
            content += "</tr>"

        content += "</tbody></table>"
        content += f"<h3>Total Amount: {format_currency(total_amount)}</h3>"

        return html_page("Kai & Manhar Grocery Order Processing", content)

    except Exception:
        current_app.logger.exception("Unable to process order")
        if connection is not None:
            try:
                connection.rollback()
            except Exception:
                pass
        return html_page(
            "Order Processing Error",
            "<h1>Unable to process the order.</h1>"
        ), 500
    finally:
        if connection is not None:
            connection.close()