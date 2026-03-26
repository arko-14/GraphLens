# GraphLens / SAP Order-to-Cash (Graph RAG)

This repository contains a full **Context Graph System** using Neo4j, Groq (Llama 3), and FastAPI to analyze the SAP Order-to-Cash process.

---
### 🚀 Production Status: [LIVE]
The system is fully deployed and production-hardened:
- **Frontend/Backend**: [https://graphlens-wf7m.onrender.com/](https://graphlens-wf7m.onrender.com/) (Render)
- **Database**: Neo4j Aura Cloud (Persistent)
- **Hardening**: Built-in retry loops (3x), 60s connection lifetimes, and strict No-Hallucination guardrails.
---

## Architecture Decisions & Constraints

### 1. Database Choice: Neo4j
Neo4j was chosen over purely vector-based databases because the SAP O2C dataset is highly relational (Sales Orders $\rightarrow$ Deliveries $\rightarrow$ Billing $\rightarrow$ Journal Entries). Neo4j excels at multi-hop traversals which is required to "Trace the full flow of a billing document". Neo4j vector indexes also allow for hybrid retrieval on text-heavy nodes natively.

### 2. LLM Prompting Strategy & Hybrid Retrieval
We employed a Hybrid Retrieval mechanism using **Groq** (`llama3-70b-8192`) and local `sentence-transformers` embeddings:
1. **Semantic Vector Search**: Incoming natural language queries are converted to embeddings to find relevant `Product` nodes via Vector Search on the `description` field.
2. **Graph Expansion**: We hop 1-2 degrees from the semantic hits to gather related structure (Orders, Customers).
3. **Data Grounding**: The results from the Graph and Vector searches are serialized and injected into the LLM context.
4. **Synthesis Prompt**: The LLM is given a strict system prompt instructing it to answer *only* based on the provided JSON context, preventing hallucination.

### 3. Guardrails
A dual-layer guardrail system is implemented:
- **Pre-Retrieval Regex/Keyword Guardrail**: Intercepts blatantly out-of-domain phrases (e.g., general knowledge, sports, weather) directly at the API route and returns the mandated response: `"This system is designed to answer questions related to the provided dataset only."`
- **Post-Retrieval Grounded Prompts**: The LLM is instructed not to hallucinate any SAP documents that do not exist in the retrieved context graph.

## How to Run

1. **Start Neo4j**:  
   ```bash
   docker-compose up -d
   ```
2. **Setup virtual environment & install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
3. **Set Environment Variables**:
   Create a `.env` file containing:
   ```env
   GROQ_API_KEY=your_api_key_here
   NEO4J_URI=bolt://localhost:7687
   NEO4J_USER=neo4j
   NEO4J_PASSWORD=password
   ```
4. **Run Ingestion Pipeline**:
   ```bash
   python scripts/run_ingestion.py
   python app/ingestion/create_embeddings.py
   ```
5. **Start the API & UI**:
   ```bash
   uvicorn app.main:app --reload
   ```
6. **Access UI**:  
   Open `http://127.0.0.1:8000` in your web browser. The left pane provides visualization (vis.js), and the right pane provides the data assistant chat.
