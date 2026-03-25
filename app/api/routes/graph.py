from fastapi import APIRouter
from app.db.neo4j_client import neo4j_client

router = APIRouter()

@router.get("/")
async def get_graph():
    # Returns a small sample of the graph for visualization
    query = """
    MATCH (n)-[r]->(m)
    RETURN 
        n.id AS source_id, labels(n)[0] AS source_label, 
        type(r) AS rel_type, 
        m.id AS target_id, labels(m)[0] AS target_label
    LIMIT 100
    """
    results = neo4j_client.execute_query(query)
    
    nodes = set()
    edges = []
    nodes_info = {}
    
    for row in results:
        src = row["source_id"]
        tgt = row["target_id"]
        nodes.add(src)
        nodes.add(tgt)
        nodes_info[src] = {"id": src, "label": f"{row['source_label']}\\n{src}", "group": row['source_label']}
        nodes_info[tgt] = {"id": tgt, "label": f"{row['target_label']}\\n{tgt}", "group": row['target_label']}
        edges.append({"from": src, "to": tgt, "label": row["rel_type"]})
        
    return {"nodes": list(nodes_info.values()), "edges": edges}
