"""Lab 8 customer information for the logged-in customer."""

from flask import Blueprint, current_app, session
from db import get_connection
from html_utils import escape_html, html_page
from routes.auth import require_login

bp = Blueprint("customer", __name__)


@bp.get("/customer")
def customer_information():
    redirect_response = require_login()
    if redirect_response is not None:
        return redirect_response

    username = session["authenticatedUser"]
    connection = None
    try:
        connection = get_connection()
        cursor = connection.cursor()
        cursor.execute("""
            SELECT firstName, lastName, email, phonenum, address,
                   city, state, postalCode, country
            FROM customer
            WHERE userid = ?
        """, (username,))
        row = cursor.fetchone()
        if row is None:
            return html_page("Customer Information", """
                <h1>Customer Information</h1>
                <p>No customer record was found for the logged-in user.</p>
                <p><a href="/">Main Page</a></p>
            """), 404

        first_name, last_name, email, phone, address, city, state, postal, country = row
        values = (
            ("Name", f"{first_name or ''} {last_name or ''}".strip()),
            ("Email", email),
            ("Phone", phone),
            ("Address", address),
            ("City", city),
            ("State", state),
            ("Postal Code", postal),
            ("Country", country),
        )
        table = "<table border='1' cellpadding='8'><tbody>"
        for label, value in values:
            table += f"<tr><th>{escape_html(label)}</th><td>{escape_html(value)}</td></tr>"
        table += "</tbody></table>"
        return html_page("Customer Information", f"""
            <h1>Customer Information</h1>
            {table}
            <p><a href="/">Main Page</a></p>
        """)
    except Exception:
        current_app.logger.exception("Unable to retrieve customer information")
        return html_page("Customer Information", """
            <h1>Customer Information</h1>
            <p>Unable to retrieve customer information.</p>
            <p><a href="/">Main Page</a></p>
        """), 500
    finally:
        if connection is not None:
            connection.close()
