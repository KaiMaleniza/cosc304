"""Lab 8 product details with URL and database images."""

from flask import Blueprint, current_app, request, url_for
from db import get_connection
from html_utils import escape_html, format_currency, html_page

bp = Blueprint("product", __name__)


@bp.get("/product")
def product_details():
    product_id_text = request.args.get("id", "")

    try:
        product_id = int(product_id_text)
        if product_id <= 0 or product_id > 2147483647:
            raise ValueError()
    except (TypeError, ValueError):
        return html_page("Invalid Product", """
            <h1>Invalid Product</h1>
            <p>The product ID is invalid.</p>
            <p><a href="/listprod">Continue Shopping</a></p>
        """), 400

    connection = None
    try:
        connection = get_connection()
        cursor = connection.cursor()
        cursor.execute(
            """SELECT productId, productName, productPrice, productDesc,
                      productImageURL, productImage
               FROM product WHERE productId = ?""",
            (product_id,),
        )
        row = cursor.fetchone()
        if row is None:
            return html_page("Product Not Found", """
                <h1>Product Not Found</h1>
                <p>No product exists for that ID.</p>
                <p><a href="/listprod">Continue Shopping</a></p>
            """), 404

        _, name, price, description, image_url, database_image = row
        has_database_image = database_image is not None
        safe_name = escape_html(name)
        safe_description = escape_html(description)
        formatted_price = format_currency(price)

        images = ""
        if image_url:
            image_url = str(image_url).strip()
            if image_url.startswith("http://") or image_url.startswith("https://"):
                src = image_url
            elif image_url.startswith("/"):
                src = image_url
            elif image_url.startswith("static/"):
                src = "/" + image_url
            elif image_url.startswith("img/"):
                src = "/static/" + image_url
            else:
                src = "/static/" + image_url
            images += f'<img src="{escape_html(src)}" alt="{safe_name}"><br>'
        if has_database_image:
            src = url_for("display_image.display_image", id=product_id)
            images += f'<img src="{escape_html(src)}" alt="{safe_name}"><br>'

        cart_url = url_for(
            "addcart.add_to_cart",
            id=product_id,
            name=name,
            price=str(price),
        )
        content = f"""
            <h1>{safe_name}</h1>
            {images}
            <p><strong>Price:</strong> {formatted_price}</p>
            <p>{safe_description or "No description available."}</p>
            <p><a href="{escape_html(cart_url)}">Add to Cart</a></p>
            <p><a href="/listprod">Continue Shopping</a> |
               <a href="/">Main Page</a></p>
        """
        return html_page("Product Details", content)
    except Exception:
        current_app.logger.exception("Unable to retrieve product details")
        return html_page("Product Error", """
            <h1>Product Error</h1>
            <p>Unable to retrieve product details.</p>
            <p><a href="/listprod">Continue Shopping</a></p>
        """), 500
    finally:
        if connection is not None:
            connection.close()
