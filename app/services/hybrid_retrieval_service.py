import os
import json
import logging
from typing import Dict, Any, List
from app.db.neo4j_client import neo4j_client
from app.core.config import settings
from app.core.constants import GROQ_MODEL

try:
    from groq import Groq
    groq_client = Groq(api_key=settings.GROQ_API_KEY)
except ImportError:
    groq_client = None

try:
    from fastembed import TextEmbedding
    embedder = TextEmbedding("BAAI/bge-small-en-v1.5")
except ImportError:
    embedder = None

logger = logging.getLogger(__name__)

class HybridRetrievalService:
    def __init__(self):
        pass

    def embed_query(self, query: str) -> List[float]:
        if not embedder:
            logger.warning("Embedder model not loaded.")
            return []
        return list(embedder.embed([query]))[0].tolist()

    def vector_search(self, query_embedding: List[float], top_k: int = 5) -> List[Dict[str, Any]]:
        # This is a hypothetical neo4j vector search query; adjust for Neo4j version
        cypher = """
        CALL db.index.vector.queryNodes('product_embedding_idx', $top_k, $vector)
        YIELD node, score
        RETURN node.id AS id, node.description AS text, score
        """
        try:
            return neo4j_client.execute_query(cypher, {"top_k": top_k, "vector": query_embedding})
        except Exception as e:
            logger.error(f"Vector search failed (index might not exist): {e}")
            return []

    def graph_expand(self, start_ids: List[str]) -> List[Any]:
        # Simple 1-hop expansion from seed nodes
        if not start_ids:
            return []
        cypher = """
        MATCH (n)-[r]-(m)
        WHERE n.id IN $start_ids
        RETURN labels(n)[0] AS n_label, n.id AS n_id, type(r) AS rel, labels(m)[0] AS m_label, m.id AS m_id
        LIMIT 50
        """
        return neo4j_client.execute_query(cypher, {"start_ids": start_ids})

    def synthesize_answer(self, user_query: str, context_nodes: List[Dict], graph_context: List[Any], history: List[Dict[str, str]] = None) -> str:
        if not groq_client:
            return "Groq client not initialized. Install groq and set GROQ_API_KEY."

        context_str = "Vector Search Findings:\\n" + json.dumps(context_nodes, default=str) + "\\n\\n"
        context_str += "Graph Traversal Context:\\n" + json.dumps(graph_context, default=str)

        sys_prompt = (
            "You are a helpful data assistant for answering O2C (Order2Cash) logistics queries. "
            "Use the provided graph data to answer the user query based solely on the dataset.\\n\\n"
            "CRITICAL GUARDRAIL - STRICT COMPLIANCE:\\n"
            "If the user asks a conversational question, general knowledge question, requests creative writing, "
            "or asks ANYTHING completely unrelated to the SAP O2C dataset (e.g. Sales Orders, Customers, "
            "Deliveries, Billing, Products, Plants), you MUST reject the prompt and immediately output EXACTLY this string:\\n"
            '"This system is designed to answer questions related to the provided dataset only."\\n\\n'
            "FORMATTING RULES:\\n"
            "- Always format your responses clearly using Markdown.\\n"
            "- Use bolding for Entity IDs or important metrics.\\n"
            "- When tracing a flow (Sales Order → Delivery → Billing → Journal), format it as a numbered step-by-step chain:\\n"
            "  e.g. **Step 1 — Sales Order**: ID=..., Customer=... → **Step 2 — Delivery**: ...\\n"
            "- Use structured tables or clean bulleted lists when presenting multiple items.\\n"
            "- Keep your final analysis concise, professional, and highly organized."
        )
        messages = [{"role": "system", "content": sys_prompt}]
        if history:
            for msg in history[-4:]:  # keep last 4 turns to avoid context overflow
                messages.append({"role": msg["role"], "content": msg["content"]})
        messages.append({"role": "user", "content": f"Context:\\n{context_str}\\n\\nQuestion: {user_query}"})

        try:
            chat_completion = groq_client.chat.completions.create(
                messages=messages,
                model=GROQ_MODEL,
            )
            return chat_completion.choices[0].message.content
        except Exception as e:
            logger.error(f"LLM synthesis failed: {e}")
            return f"Error connecting to LLM: {str(e)}"

    def handle_search(self, user_query: str, history: List[Dict[str, str]] = None) -> Dict:
        lower_query = user_query.lower()
        emb = self.embed_query(user_query)
        v_results = self.vector_search(emb) if emb else []
        node_ids = [r['id'] for r in v_results]
        g_results = self.graph_expand(node_ids)
        
        if "trace" in lower_query or "flow" in lower_query or "billing document " in lower_query:
            words = lower_query.split()
            doc_id = None
            for w in words:
                if w.isdigit() and len(w) > 4:  # billing doc IDs are long numbers
                    doc_id = w
                    break
            if doc_id:
                flow_query = """
                MATCH (bd:BillingDocument)
                WHERE bd.id = $doc_id OR bd.id = toInteger($doc_id)
                OPTIONAL MATCH (bd)-[:HAS_ITEM]->(bi:BillingDocumentItem)
                OPTIONAL MATCH (bi)<-[:BILLED_IN]-(di:DeliveryItem)
                OPTIONAL MATCH (di)<-[:HAS_ITEM]-(d:Delivery)
                OPTIONAL MATCH (di)<-[:SHIPPED_IN]-(si:SalesOrderItem)
                OPTIONAL MATCH (si)<-[:HAS_ITEM]-(so:SalesOrder)
                OPTIONAL MATCH (so)<-[:PLACE_ORDER]-(c:Customer)
                OPTIONAL MATCH (si)-[:REQUESTS_PRODUCT]->(p:Product)
                OPTIONAL MATCH (bd)-[:RECORDED_IN]->(je:JournalEntry)
                OPTIONAL MATCH (je)-[:CLEARED_BY]->(pay:Payment)
                RETURN 
                    properties(bd)  AS billing_document,
                    collect(DISTINCT properties(bi))  AS billing_items,
                    collect(DISTINCT properties(d))   AS deliveries,
                    collect(DISTINCT properties(di))  AS delivery_items,
                    collect(DISTINCT properties(so))  AS sales_orders,
                    collect(DISTINCT properties(si))  AS sales_order_items,
                    collect(DISTINCT properties(c))   AS customers,
                    collect(DISTINCT properties(p))   AS products,
                    collect(DISTINCT properties(je))  AS journal_entries,
                    collect(DISTINCT properties(pay)) AS payments
                LIMIT 1
                """
                try:
                    flow_res = neo4j_client.execute_query(flow_query, {"doc_id": doc_id})
                    if flow_res:
                        g_results.append({"Full O2C Flow Trace for Billing Document": flow_res[0]})
                except Exception as e:
                    logger.error(f"Flow trace query failed: {e}")

        if "highest" in lower_query or "most" in lower_query or "billing documents" in lower_query:
            agg_query = """
            MATCH (p:Product)<-[:REQUESTS_PRODUCT]-(si:SalesOrderItem)-[:SHIPPED_IN]->(di:DeliveryItem)-[:BILLED_IN]->(bi:BillingDocumentItem)<-[:HAS_ITEM]-(bd:BillingDocument)
            RETURN p.id AS product_id, p.description AS name, count(DISTINCT bd.id) AS billing_document_count
            ORDER BY billing_document_count DESC LIMIT 5
            """
            try:
                agg_res = neo4j_client.execute_query(agg_query)
                g_results.append({"Analytical Context for 'Highest/Most' queries": agg_res})
                # Also bulk-inject these products as highlight nodes
                for row in agg_res:
                    v_results.append({"id": row["product_id"], "description": row.get("name", row["product_id"])})
            except Exception as e:
                logger.error(f"Agg query failed: {e}")

        if "broken" in lower_query or "incomplete" in lower_query or "not billed" in lower_query or "without delivery" in lower_query:
            try:
                # Case 1: SalesOrders with deliveries but NO billing
                delivered_not_billed_q = """
                MATCH (so:SalesOrder)-[:HAS_ITEM]->(si:SalesOrderItem)-[:SHIPPED_IN]->(di:DeliveryItem)
                WHERE NOT (di)-[:BILLED_IN]->(:BillingDocumentItem)
                RETURN DISTINCT so.id AS sales_order_id, count(di) AS unmatched_deliveries
                ORDER BY unmatched_deliveries DESC LIMIT 10
                """
                res1 = neo4j_client.execute_query(delivered_not_billed_q)
                g_results.append({"Delivered But NOT Billed (Broken Flow - Type 1)": res1})

                # Case 2: BillingDocuments with NO delivery link
                billed_no_delivery_q = """
                MATCH (so:SalesOrder)-[:HAS_ITEM]->(si:SalesOrderItem)
                WHERE NOT (si)-[:SHIPPED_IN]->(:DeliveryItem)
                  AND (si)<-[:FULFILLS]-(:BillingDocumentItem)
                RETURN DISTINCT so.id AS sales_order_id
                LIMIT 10
                """
                res2 = neo4j_client.execute_query(billed_no_delivery_q)
                g_results.append({"Billed WITHOUT Delivery (Broken Flow - Type 2)": res2})

                # Case 3: SalesOrders with no delivery at all
                no_delivery_q = """
                MATCH (so:SalesOrder)-[:HAS_ITEM]->(si:SalesOrderItem)
                WHERE NOT (si)-[:SHIPPED_IN]->(:DeliveryItem)
                RETURN DISTINCT so.id AS sales_order_id, count(si) AS items_without_delivery
                ORDER BY items_without_delivery DESC LIMIT 10
                """
                res3 = neo4j_client.execute_query(no_delivery_q)
                g_results.append({"Sales Orders With NO Delivery (Incomplete Flow - Type 3)": res3})
            except Exception as e:
                logger.error(f"Broken flow query failed: {e}")

        # Gather node objects that are highly relevant to dynamically draw/highlight in UI
        highlight_nodes = [{"id": r['id'], "label": r.get('description', r.get('name', r['id']))[:20], "group": "Product"} for r in v_results]
        
        answer = self.synthesize_answer(user_query, v_results, g_results, history)
        return {"answer": answer, "nodes": highlight_nodes}

hybrid_retrieval_service = HybridRetrievalService()
