# Deployment Guide 🚀

This guide explains how to deploy the **Nexus-O2C Graph RAG Engine** to **Render.com** using **Neo4j Aura Cloud**.

## 1. Neo4j Aura Cloud (The Database)
- Sign up for a free instance at [neo4j.com/cloud/aura](https://neo4j.com/cloud/aura/).
- Download your credentials file (`neo4j-credentials.txt`).
- You will need: `NEO4J_URI`, `NEO4J_USERNAME` (always `neo4j`), and `NEO4J_PASSWORD`.

## 2. Ingest Data (Local to Cloud)
- Update your local `.env` with the Aura credentials.
- Run the following in your terminal:
```bash
python scripts/run_ingestion.py
python app/ingestion/create_embeddings.py
```
- Wait for it to finish (this loads your data into the cloud).

## 3. Render.com (The App)
- Go to [dashboard.render.com](https://dashboard.render.com).
- Click **New +** → **Blueprint**.
- Connect your GitHub repository.
- Render will automatically detect the `render.yaml` file.
- It will prompt you for the following **Environment Variables**:
  - `NEO4J_URI`: Your Aura URI (starts with `neo4j+s://`)
  - `NEO4J_USERNAME`: `neo4j`
  - `NEO4J_PASSWORD`: Your Aura password
  - `GROQ_API_KEY`: Your Groq API key
- Click **Apply** or **Deploy**.

## 4. Verification
- Once the deployment is "Live" in Render, click the provided URL (e.g., `https://graph-rag-engine.onrender.com`).
- Your **Dodge AI** styled UI will load.
- Type a query like "Trace the flow of billing document 90504248" to test the integration.

---

**Note**: Since we use Render's **Blueprint**, the `Dockerfile` and `render.yaml` already handle all the port settings and runtime requirements automatically.
