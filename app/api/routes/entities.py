from fastapi import APIRouter, HTTPException, Depends
from app.api.deps import get_neo4j_client
from app.db.neo4j_client import Neo4jClient
from app.models.response_models import EntityDetails

router = APIRouter()

@router.get("/{entity_type}/{entity_id}", response_model=EntityDetails)
def get_entity_details(entity_type: str, entity_id: str, client: Neo4jClient = Depends(get_neo4j_client)):
    # Validate allowed labels to prevent Cypher injection
    allowed_labels = ["Customer", "Product", "SalesOrder", "SalesOrderItem", "Delivery", "DeliveryItem", "BillingDocument", "BillingDocumentItem", "JournalEntry", "Payment", "Plant"]
    if entity_type not in allowed_labels:
        raise HTTPException(status_code=400, detail="Invalid entity type")
    
    query = f"""
    MATCH (n:{entity_type})
    WHERE n.id = $id OR n.id = toInteger($id)
    OPTIONAL MATCH (n)-[r]-(m)
    RETURN properties(n) AS props, collect({{rel_type: type(r), connected_id: m.id, connected_label: labels(m)[0]}}) AS rels
    """
    results = client.execute_query(query, {"id": entity_id})
    if not results:
        raise HTTPException(status_code=404, detail="Entity not found")
        
    return EntityDetails(
        properties=results[0]["props"] or {},
        relationships=results[0]["rels"] if results[0].get("rels") and results[0]["rels"][0]["rel_type"] is not None else []
    )
