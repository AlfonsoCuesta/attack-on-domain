"""
Example: two bounded contexts with a shared entity name (Product).

Run with: uv run python code/examples/diagram.py
"""

from aod import BoundedContext, Entity, RootEntity, Service
from aod.diagram import render_html


def sales_context() -> BoundedContext:
    class OrderLine(Entity):
        id: int
        product_id: int
        quantity: int
        unit_price: float

    class Product(RootEntity):
        id: int
        name: str
        price: float

    class Customer(RootEntity):
        id: int
        name: str

    class Order(RootEntity):
        id: int
        customer_id: int
        total: float
        lines: list[OrderLine]

    return BoundedContext(
        aggregate_roots=[Product, Customer, Order],
        name="Sales",
    )


def inventory_context() -> BoundedContext:
    class StockItem(Entity):
        id: int
        quantity: int

    class Product(RootEntity):
        id: int
        name: str
        weight: float
        stock: list[StockItem]

    class Warehouse(RootEntity):
        id: int
        code: str
        location: str

    class InventoryService(Service):
        def reserve(self, product: Product, qty: int) -> None:
            pass

    return BoundedContext(
        aggregate_roots=[Product, Warehouse],
        services=[InventoryService],
        name="Inventory",
    )


if __name__ == "__main__":
    from aod import App

    sales = sales_context()
    inventory = inventory_context()

    app = App("MyStore", sales, inventory)

    html = render_html(app)
    with open("diagrama.html", "w") as f:
        f.write(html)

    print("Saved diagrama.html")
