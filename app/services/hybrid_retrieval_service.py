import os
import re
import json
import logging
import time
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
        cypher = """
        CALL db.index.vector.queryNodes('product_embedding_idx', $top_k, $vector)
        YIELD node, score
        RETURN node.id AS id, node.description AS text, score
        """
        retries = 2
        while retries >= 0:
            try:
                return neo4j_client.execute_query(cypher, {"top_k": top_k, "vector": query_embedding})
            except Exception as e:
                if "routing information" in str(e).lower() and retries > 0:
                    logger.warning(f"Aura routing error, retrying search (retries left: {retries})...")
                    time.sleep(1)
                    retries -= 1
                    continue
                logger.error(f"Vector search failed (index might not exist or Aura busy): {e}")
                return []

    def graph_expand(self, start_ids: List[str]) -> List[Any]:
        if not start_ids:
            return []
        cypher = """
        MATCH (n)-[r]-(m)
        WHERE n.id IN $start_ids
        RETURN labels(n)[0] AS n_label, n.id AS n_id, type(r) AS rel, labels(m)[0] AS m_label, m.id AS m_id
        LIMIT 50
        """
        retries = 2
        while retries >= 0:
            try:
                return neo4j_client.execute_query(cypher, {"start_ids": start_ids})
            except Exception as e:
                if "routing information" in str(e).lower() and retries > 0:
                    time.sleep(1)
                    retries -= 1
                    continue
                logger.error(f"Graph expansion failed: {e}")
                return []

    def synthesize_answer(self, user_query: str, context_nodes: List[Dict], graph_context: List[Any], history: List[Dict[str, str]] = None) -> str:
        if not groq_client:
            return "Groq client not initialized. Install groq and set GROQ_API_KEY."

        context_str = "Vector Search Findings:\\n" + json.dumps(context_nodes, default=str) + "\\n\\n"
        context_str += "Graph Traversal Context:\\n" + json.dumps(graph_context, default=str)

        sys_prompt = (
            "You are a helpful data assistant for answering O2C (Order2Cash) logistics queries based on the provided SAP dataset.\\n\\n"
            "GUIDELINES:\\n"
            "- If the question is about the dataset (Orders, Customers, Deliveries, Billing, Products, Plants), answer accurately using ONLY the provided context.\\n"
            "- **STRICT NO-HALLUCINATION POLICY**: If the context is empty or does not contain the specific ID/Product requested, you MUST say: 'I found no data for [Entity] in the current dataset.'\\n"
            "- **SEARCH TIPS**: If the context is empty, suggest that the user provide a specific ID like **740552** (Sales Order), **80738072** (Delivery), or **90504248** (Billing) to get started.\\n"
            "- **NEVER** invent placeholder IDs, names, or prices (e.g. do not use SO-123, Product A, $100 unless they are in the context).\\n"
            "- If the question is slightly out of scope but related to logistics or business, try to be helpful while staying grounded in the data.\\n"
            "- If the question is completely unrelated to the dataset (e.g. general trivia, creative writing), politely state: "
            '"This system is designed to answer questions related to the provided dataset only."\\n\\n'
            "FORMATTING RULES:\\n"
            "- Always format your responses using professional Markdown.\\n"
            "- Use bolding for Entity IDs (e.g. **SO-123**) and key metrics.\\n"
            "- For O2C flows, always follow this step-by-step numbered chain format (ONLY if you have the real data):\\n"
            "  1. **Step 1 — Sales Order**: ID=..., Customer=...\\n"
            "  2. **Step 2 — Delivery**: ID=..., Status=...\\n"
            "  3. **Step 3 — Billing**: ID=..., Total=...\\n"
            "  4. **Step 4 — Payment**: ...\\n"
            "- Use tables for lists of items to ensure visual clarity."
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
        
        # Improved ID Extraction for various O2C stages (Sales Order '74...', Delivery '80...', Billing '90...')
        doc_id_match = re.search(r'\b(74\d{4}|80\d{6}|90\d{6})\b', user_query) or re.search(r'\b(\d{6,10})\b', user_query)
        
        if doc_id_match:
            doc_id = doc_id_match.group(1)
            if any(x in lower_query for x in ["trace", "flow", "lifecycle", "order", "delivery", "billing", "document"]):
                # Universal O2C trace starting from ANY node in the chain
                flow_query = """
                MATCH (n)
                WHERE n.id = $doc_id OR n.id = toString($doc_id) OR n.id = toInteger($doc_id)
                WITH n
                OPTIONAL MATCH (so:SalesOrder) WHERE so.id = n.id OR (n:SalesOrderItem AND (so)-[:HAS_ITEM]->(n))
                OPTIONAL MATCH (so)-[:HAS_ITEM]->(si:SalesOrderItem)
                OPTIONAL MATCH (si)-[:SHIPPED_IN]->(di:DeliveryItem)<-[:HAS_ITEM]-(d:Delivery)
                OPTIONAL MATCH (di)-[:BILLED_IN]->(bi:BillingDocumentItem)<-[:HAS_ITEM]-(bd:BillingDocument)
                OPTIONAL MATCH (si)-[:REQUESTS_PRODUCT]->(p:Product)
                OPTIONAL MATCH (c:Customer)-[:PLACED_ORDER]->(so)
                RETURN 
                    properties(so) AS sales_order,
                    collect(DISTINCT properties(si)) AS sales_order_items,
                    collect(DISTINCT properties(d)) AS deliveries,
                    collect(DISTINCT properties(di)) AS delivery_items,
                    collect(DISTINCT properties(bd)) AS billing_documents,
                    collect(DISTINCT properties(bi)) AS billing_items,
                    collect(DISTINCT properties(c)) AS customers,
                    collect(DISTINCT properties(p)) AS products
                LIMIT 1
                """
                retries = 2
                while retries >= 0:
                    try:
                        flow_res = neo4j_client.execute_query(flow_query, {"doc_id": doc_id})
                        if flow_res:
                            g_results.append({"Unified O2C Lifecycle Trace": flow_res[0]})
                        break
                    except Exception as e:
                        if "routing information" in str(e).lower() and retries > 0:
                            time.sleep(1)
                            retries -= 1
                            continue
                        logger.error(f"Universal trace query failed: {e}")
                        break

        if "highest" in lower_query or "most" in lower_query or "billing documents" in lower_query:
            agg_query = """
            MATCH (p:Product)<-[:REQUESTS_PRODUCT]-(si:SalesOrderItem)-[:SHIPPED_IN]->(di:DeliveryItem)-[:BILLED_IN]->(bi:BillingDocumentItem)<-[:HAS_ITEM]-(bd:BillingDocument)
            RETURN p.id AS product_id, p.description AS name, count(DISTINCT bd.id) AS billing_document_count
            ORDER BY billing_document_count DESC LIMIT 5
            """
            retries = 2
            while retries >= 0:
                try:
                    agg_res = neo4j_client.execute_query(agg_query)
                    g_results.append({"Analytical Context for 'Highest/Most' queries": agg_res})
                    # Also bulk-inject these products as highlight nodes
                    for row in agg_res:
                        v_results.append({"id": row["product_id"], "description": row.get("name", row["product_id"])})
                    break
                except Exception as e:
                    if "routing information" in str(e).lower() and retries > 0:
                        time.sleep(1)
                        retries -= 1
                        continue
                    logger.error(f"Agg query failed: {e}")
                    break

        if "broken" in lower_query or "incomplete" in lower_query or "not billed" in lower_query or "without delivery" in lower_query:
            try:
                # Case 1: SalesOrders with deliveries but NO billing
                delivered_not_billed_q = """
                MATCH (so:SalesOrder)-[:HAS_ITEM]->(si:SalesOrderItem)-[:SHIPPED_IN]->(di:DeliveryItem)
                WHERE NOT (di)-[:BILLED_IN]->(:BillingDocumentItem)
                RETURN DISTINCT so.id AS sales_order_id, count(di) AS unmatched_deliveries
                ORDER BY unmatched_deliveries DESC LIMIT 10
                """
                
                # Case 2: BillingDocuments with NO delivery link (Highly unlikely in this schema, but for completeness)
                billed_no_delivery_q = """
                MATCH (bi:BillingDocumentItem)<-[:HAS_ITEM]-(bd:BillingDocument)
                WHERE NOT (bi)-[:BILLED_IN]->(:DeliveryItem)
                RETURN DISTINCT bd.id AS billing_id
                LIMIT 10
                """
                
                # Case 3: SalesOrders with no delivery at all
                no_delivery_q = """
                MATCH (so:SalesOrder)-[:HAS_ITEM]->(si:SalesOrderItem)
                WHERE NOT (si)-[:SHIPPED_IN]->(:DeliveryItem)
                RETURN DISTINCT so.id AS sales_order_id, count(si) AS items_without_delivery
                ORDER BY items_without_delivery DESC LIMIT 10
                """
                
                retries = 2
                while retries >= 0:
                    try:
                        res1 = neo4j_client.execute_query(delivered_not_billed_q)
                        g_results.append({"Delivered But NOT Billed (Broken Flow - Type 1)": res1})
                        
                        res2 = neo4j_client.execute_query(billed_no_delivery_q)
                        g_results.append({"Billed WITHOUT Delivery (Broken Flow - Type 2)": res2})
                        
                        res3 = neo4j_client.execute_query(no_delivery_q)
                        g_results.append({"Sales Orders With NO Delivery (Incomplete Flow - Type 3)": res3})
                        break
                    except Exception as e:
                        if "routing information" in str(e).lower() and retries > 0:
                            time.sleep(1)
                            retries -= 1
                            continue
                        logger.error(f"Broken flow query failed: {e}")
                        break
            except Exception as e:
                logger.error(f"Broken flow block failed: {e}")

        # Gather node objects that are highly relevant to dynamically draw/highlight in UI
        highlight_nodes = [{"id": r['id'], "label": r.get('description', r.get('name', r['id']))[:20], "group": "Product"} for r in v_results]
        
        answer = self.synthesize_answer(user_query, v_results, g_results, history)
        return {"answer": answer, "nodes": highlight_nodes}

hybrid_retrieval_service = HybridRetrievalService()
