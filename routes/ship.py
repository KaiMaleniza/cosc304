"""Process one order as an all-or-nothing shipment."""

from flask import Blueprint, current_app, request
from db import get_connection
from html_utils import escape_html, html_page

bp = Blueprint("ship", __name__)


@bp.get("/ship")
def ship_order():
    raw_order_id = request.args.get("orderId", "")

    try:
        order_id = int(raw_order_id)
        if order_id <= 0 or order_id > 2147483647:
            raise ValueError()
    except (TypeError, ValueError):
        return html_page("Shipment Processing", """
            <h1>Process Shipment</h1>
            <p>Invalid order ID.</p>
            <p><a href="/">Main Page</a></p>
        """), 400

    connection = None
    try:
        connection = get_connection()
        cursor = connection.cursor()
        cursor.execute(
            "SELECT productId, quantity FROM orderproduct WHERE orderId = ?",
            (order_id,),
        )
        items = cursor.fetchall()
        if not items:
            connection.rollback()
            return html_page("Shipment Processing", f"""
                <h1>Process Shipment</h1>
                <p>No order was found for order ID {escape_html(order_id)}.</p>
                <p><a href="/">Main Page</a></p>
            """), 404

        cursor.execute(
            """INSERT INTO shipment (shipmentDate, shipmentDesc, warehouseId)
               VALUES (GETDATE(), ?, 1)""",
            (f"Shipment for order {order_id}",),
        )

        for product_id, ordered_quantity in items:
            if ordered_quantity is None or ordered_quantity <= 0:
                connection.rollback()
                return html_page("Shipment Processing", f"""
                    <h1>Process Shipment</h1>
                    <p>Invalid quantity for product {escape_html(product_id)}.</p>
                    <p><a href="/">Main Page</a></p>
                """), 400

            cursor.execute(
                """SELECT quantity FROM productinventory
                   WHERE productId = ? AND warehouseId = 1""",
                (product_id,),
            )
            inventory = cursor.fetchone()
            if inventory is None:
                connection.rollback()
                return html_page("Shipment Processing", f"""
                    <h1>Process Shipment</h1>
                    <p>Insufficient inventory for product {escape_html(product_id)}.</p>
                    <p><a href="/">Main Page</a></p>
                """), 400

            available = inventory[0]
            if available is None or available < ordered_quantity:
                connection.rollback()
                return html_page("Shipment Processing", f"""
                    <h1>Process Shipment</h1>
                    <p>Insufficient inventory for product {escape_html(product_id)}:
                       ordered {escape_html(ordered_quantity)}, but only
                       {escape_html(available or 0)} available.</p>
                    <p><a href="/">Main Page</a></p>
                """), 400

            cursor.execute(
                """UPDATE productinventory
                   SET quantity = quantity - ?
                   WHERE productId = ? AND warehouseId = 1""",
                (ordered_quantity, product_id),
            )

        connection.commit()
        return html_page("Shipment Processing", f"""
            <h1>Shipment Successful</h1>
            <p>Order {escape_html(order_id)} was shipped from warehouse 1.</p>
            <p><a href="/">Main Page</a></p>
        """)
    except Exception:
        if connection is not None:
            connection.rollback()
        current_app.logger.exception("Unable to process shipment")
        return html_page("Shipment Processing", """
            <h1>Process Shipment</h1>
            <p>Unable to process the shipment. No inventory changes were saved.</p>
            <p><a href="/">Main Page</a></p>
        """), 500
    finally:
        if connection is not None:
            connection.close()
