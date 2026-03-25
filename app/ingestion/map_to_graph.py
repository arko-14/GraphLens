from typing import Dict, Any, List

def map_customer(row: Dict[str, Any]) -> Dict[str, Any]:
    return {"id": row.get("businessPartner"), "name": row.get("businessPartnerFullName"), "industry": row.get("industry")}

def map_sales_order(row: Dict[str, Any]) -> Dict[str, Any]:
    return {"id": row.get("salesOrder"), "creationDate": row.get("creationDate"), "totalNetAmount": row.get("totalNetAmount"), "transactionCurrency": row.get("transactionCurrency")}

def map_product(row: Dict[str, Any]) -> Dict[str, Any]:
    # Product requires resolving descriptions later or just basic id for now
    return {"id": row.get("product"), "productType": row.get("productType"), "productGroup": row.get("productGroup")}

def map_delivery(row: Dict[str, Any]) -> Dict[str, Any]:
    return {"id": row.get("deliveryDocument"), "actualGoodsMovementDate": row.get("actualGoodsMovementDate")}

def map_billing(row: Dict[str, Any]) -> Dict[str, Any]:
    return {"id": row.get("billingDocument"), "billingDocumentDate": row.get("billingDocumentDate"), "totalNetAmount": row.get("totalNetAmount")}

def map_journal(row: Dict[str, Any]) -> Dict[str, Any]:
    return {"id": row.get("accountingDocument"), "postingDate": row.get("postingDate"), "amountInTransactionCurrency": row.get("amountInTransactionCurrency")}
