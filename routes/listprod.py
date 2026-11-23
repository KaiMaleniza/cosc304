"""Question 2 (10 marks): display/search products and provide cart links."""

from flask import Blueprint, request, current_app, url_for
from db import get_connection
from html_utils import escape_html, format_currency, html_page

bp = Blueprint("listprod", __name__)


@bp.get("/listprod")
def list_products():
    name = request.args.get("productName", "")
    form = ("<h1>Search for the products you want to buy:</h1>"
            '<form method="get" action="/listprod">'
            f'<input type="text" name="productName" size="50" value="{escape_html(name)}">'
            '<input type="submit" value="Submit"> '
            '<input type="reset" value="Reset"> '
            '(Leave blank for all products)</form>')

    connection = None
    try:
        connection = get_connection()
        cursor = connection.cursor()

        if name and name.strip():
            sql = "SELECT productId, productName, productPrice FROM product WHERE productName LIKE ?"
            cursor.execute(sql, (f"%{name}%",))
        else:
            sql = "SELECT productId, productName, productPrice FROM product"
            cursor.execute(sql)

        products = cursor.fetchall()

        content = form + "<h2>Product List</h2>"

        if not products:
            content += "<p>No products found matching your search.</p>"
        else:
            content += """
            <table border="1" cellpadding="8" cellspacing="0" style="border-collapse: collapse; width: 100%;">
                <thead>
                    <tr style="background-color: #f2f2f2;">
                        <th>Product ID</th>
                        <th>Product Name</th>
                        <th>Price</th>
                        <th>Action</th>
                    </tr>
                </thead>
                <tbody>
            """

            for prod in products:
                prod_id, prod_name, prod_price = prod

                cart_url = url_for('addcart.add_to_cart', id=prod_id, name=prod_name, price=prod_price)

                safe_id = escape_html(str(prod_id))
                safe_name = escape_html(str(prod_name))
                formatted_price = format_currency(prod_price)

                content += "<tr>"
                content += f"<td>{safe_id}</td>"
                content += f"<td>{safe_name}</td>"
                content += f"<td>{formatted_price}</td>"
                content += f'<td><a href="{cart_url}">Add to Cart</a></td>'
                content += "</tr>"

            content += "</tbody></table>"

        return html_page("Kai & Manhar Grocery", content)

    except Exception:
        current_app.logger.exception("Unable to list products")
        return html_page("Product Search Error", form +
                         "<p>Unable to search products.</p>"), 500
    finally:
        if connection is not None:
            connection.close()