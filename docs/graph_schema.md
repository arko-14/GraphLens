# Phase 0 & 1: Graph Schema Design

## Phase 0: Entity and Relationships Sheet

Based on the raw data investigation, here are the main entities and their structures. 

| Entity | Important properties | Possible relationships | Searchable text fields | Candidate embedding fields |
|---|---|---|---|---|
| **Customer** | id, name, industry | `(Customer)-[:SOLD_TO]->(SalesOrder)` | `name`, `industry` | `name` |
| **Product** | id, description, productType | `(SalesOrderItem)-[:REQUESTS]->(Product)` | `description` | `description` |
| **SalesOrder** | id, date, totalAmount, currency | `(SalesOrder)-[:HAS_ITEM]->(SalesOrderItem)` | | |
| **SalesOrderItem** | id, rel_order_id, quantity, amount | `(SalesOrderItem)-[:SHIPPED_IN]->(DeliveryItem)` | | |
| **Delivery** | id, date, status | `(Delivery)-[:HAS_ITEM]->(DeliveryItem)` | | |
| **DeliveryItem** | id, quantity | `(DeliveryItem)-[:BILLED_IN]->(BillingItem)` | | |
| **BillingDocument** | id, date, currency, totalAmount | `(BillingDoc)-[:HAS_ITEM]->(BillingItem)`<br>`(BillingDoc)-[:RECORDED_IN]->(JournalEntry)` | | |
| **BillingItem** | id, quantity, amount | | | |
| **JournalEntry** | id, amount, date | `(JournalEntry)-[:CLEARED_BY]->(Payment)` | | |
| **Payment** | id, amount, date | | | |
| **Plant** | id, name | `(DeliveryItem)-[:SHIPPED_FROM]->(Plant)` | `name` | `name` |

---

## Phase 1: Design Graph Schema

### Node Labels
- `(:Customer {id, name, industry})`
- `(:Product {id, description, productType, productGroup})`
- `(:SalesOrder {id, creationDate, totalNetAmount, transactionCurrency})`
- `(:SalesOrderItem {id, requestedQuantity, netAmount})`
- `(:Delivery {id, actualGoodsMovementDate})`
- `(:DeliveryItem {id, actualDeliveryQuantity})`
- `(:BillingDocument {id, billingDocumentDate, totalNetAmount})`
- `(:BillingDocumentItem {id, billingQuantity, netAmount})`
- `(:JournalEntry {id, postingDate, amountInTransactionCurrency})`
- `(:Payment {id, clearingDate, amountInTransactionCurrency})`

### Relationship Types
- `(:Customer)-[:PLACE_ORDER]->(:SalesOrder)`
- `(:SalesOrder)-[:HAS_ITEM]->(:SalesOrderItem)`
- `(:SalesOrderItem)-[:REQUESTS_PRODUCT]->(:Product)`
- `(:SalesOrderItem)-[:SHIPPED_IN]->(:DeliveryItem)` *(inferred via `referenceSdDocument`)*
- `(:Delivery)-[:HAS_ITEM]->(:DeliveryItem)`
- `(:DeliveryItem)-[:BILLED_IN]->(:BillingDocumentItem)` *(inferred via `referenceSdDocument`)*
- `(:BillingDocument)-[:HAS_ITEM]->(:BillingDocumentItem)`
- `(:BillingDocument)-[:RECORDED_IN]->(:JournalEntry)` *(inferred via `referenceDocument`)*
- `(:JournalEntry)-[:CLEARED_BY]->(:Payment)` *(inferred via `clearingAccountingDocument`)*

### Indexes and Embeddings Constraint Plan

1. **Unique Constraints**:
   - Create `CONSTRAINT` on `id` property for all Node Labels to ensure swift merges during ingestion.
2. **Full-Text Indexes**:
   - `Customer.name`
   - `Product.description`
3. **Vector Indexes**:
   - `Product.embedding` (generated from `description`)
   - `Customer.embedding` (generated from `name` and metadata)

This schema covers the complete O2C flow and fulfills the requirement to track flows like:
`Sales Order -> Delivery -> Billing -> Journal Entry` perfectly.
