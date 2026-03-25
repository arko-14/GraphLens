import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging
from app.db.schema_setup import setup_constraints, create_indexes
from app.ingestion.parse_dataset import iter_jsonl_folder
from app.ingestion.clean_data import clean_dict
from app.ingestion.map_to_graph import map_customer, map_sales_order, map_product, map_delivery, map_billing, map_journal
from app.ingestion.create_nodes import create_nodes
from app.ingestion.create_relationships import create_relationships

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DATA_DIR = os.path.join("data", "raw", "sap-order-to-cash-dataset", "sap-o2c-data")

def ingest_customers():
    nodes = []
    for row in iter_jsonl_folder(DATA_DIR, "business_partners"):
        cleaned = clean_dict(row)
        nodes.append(map_customer(cleaned))
    create_nodes("Customer", nodes)

def ingest_products():
    nodes = []
    for row in iter_jsonl_folder(DATA_DIR, "products"):
        cleaned = clean_dict(row)
        nodes.append(map_product(cleaned))
    create_nodes("Product", nodes)

def ingest_sales_orders():
    nodes = []
    customer_edges = []
    for row in iter_jsonl_folder(DATA_DIR, "sales_order_headers"):
        cleaned = clean_dict(row)
        nodes.append(map_sales_order(cleaned))
        if cleaned.get("soldToParty"):
            customer_edges.append({
                "from_id": cleaned.get("soldToParty"),
                "to_id": cleaned.get("salesOrder"),
                "properties": {}
            })
    create_nodes("SalesOrder", nodes)
    create_relationships("PLACED_ORDER", "Customer", "SalesOrder", customer_edges)

def ingest_sales_order_items():
    nodes = []
    order_edges = []
    product_edges = []
    for row in iter_jsonl_folder(DATA_DIR, "sales_order_items"):
        cleaned = clean_dict(row)
        item_id = str(cleaned.get("salesOrder")) + "_" + str(cleaned.get("salesOrderItem"))
        nodes.append({
            "id": item_id,
            "requestedQuantity": cleaned.get("requestedQuantity"),
            "netAmount": cleaned.get("netAmount")
        })
        order_edges.append({
            "from_id": cleaned.get("salesOrder"),
            "to_id": item_id,
            "properties": {}
        })
        if cleaned.get("material"):
            product_edges.append({
                "from_id": item_id,
                "to_id": cleaned.get("material"),
                "properties": {}
            })
    create_nodes("SalesOrderItem", nodes)
    create_relationships("HAS_ITEM", "SalesOrder", "SalesOrderItem", order_edges)
    create_relationships("REQUESTS_PRODUCT", "SalesOrderItem", "Product", product_edges)

def ingest_deliveries():
    nodes = []
    for row in iter_jsonl_folder(DATA_DIR, "outbound_delivery_headers"):
        cleaned = clean_dict(row)
        nodes.append(map_delivery(cleaned))
    create_nodes("Delivery", nodes)

def ingest_delivery_items():
    nodes = []
    delivery_edges = []
    so_edges = []
    for row in iter_jsonl_folder(DATA_DIR, "outbound_delivery_items"):
        cleaned = clean_dict(row)
        item_no = str(cleaned.get("deliveryDocumentItem", "")).lstrip("0")
        item_id = str(cleaned.get("deliveryDocument")) + "_" + item_no
        nodes.append({
            "id": item_id,
            "actualDeliveryQuantity": cleaned.get("actualDeliveryQuantity")
        })
        delivery_edges.append({
            "from_id": cleaned.get("deliveryDocument"),
            "to_id": item_id,
            "properties": {}
        })
        if cleaned.get("referenceSdDocument") and cleaned.get("referenceSdDocumentItem"):
            so_item_id = str(cleaned.get("referenceSdDocument")) + "_" + str(cleaned.get("referenceSdDocumentItem")).lstrip("0")
            so_edges.append({
                "from_id": so_item_id,
                "to_id": item_id,
                "properties": {}
            })
    create_nodes("DeliveryItem", nodes)
    create_relationships("HAS_ITEM", "Delivery", "DeliveryItem", delivery_edges)
    create_relationships("SHIPPED_IN", "SalesOrderItem", "DeliveryItem", so_edges)

def ingest_billing():
    nodes = []
    for row in iter_jsonl_folder(DATA_DIR, "billing_document_headers"):
        cleaned = clean_dict(row)
        nodes.append(map_billing(cleaned))
    create_nodes("BillingDocument", nodes)

def ingest_billing_items():
    nodes = []
    billing_edges = []
    delivery_edges = []
    for row in iter_jsonl_folder(DATA_DIR, "billing_document_items"):
        cleaned = clean_dict(row)
        item_id = str(cleaned.get("billingDocument")) + "_" + str(cleaned.get("billingDocumentItem"))
        nodes.append({
            "id": item_id,
            "billingQuantity": cleaned.get("billingQuantity"),
            "netAmount": cleaned.get("netAmount")
        })
        billing_edges.append({
            "from_id": cleaned.get("billingDocument"),
            "to_id": item_id,
            "properties": {}
        })
        if cleaned.get("referenceSdDocument"):
            ref_id = str(cleaned.get("referenceSdDocument")) + "_" + str(cleaned.get("referenceSdDocumentItem", "")).lstrip("0")
            delivery_edges.append({
                "from_id": ref_id,
                "to_id": item_id,
                "properties": {}
            })
    create_nodes("BillingDocumentItem", nodes)
    create_relationships("HAS_ITEM", "BillingDocument", "BillingDocumentItem", billing_edges)
    create_relationships("BILLED_IN", "DeliveryItem", "BillingDocumentItem", delivery_edges)

def main():
    logger.info("Setting up constraints...")
    setup_constraints()
    create_indexes()
    
    logger.info("Ingesting nodes and edges...")
    ingest_customers()
    ingest_products()
    ingest_sales_orders()
    ingest_sales_order_items()
    ingest_deliveries()
    ingest_delivery_items()
    ingest_billing()
    ingest_billing_items()
    
    logger.info("Ingestion completed.")

if __name__ == "__main__":
    main()
