The development of the **GraphLens Graph RAG Engine** involved several key architectural choices to balance performance, scalability, and developer experience.

## 1. Database: Neo4j (Graph) vs. Pinecone/Milvus (Pure Vector)
- **Decision**: Used **Neo4j** for both relational and vector data.
- **Reasoning**: Standard O2C data is inherently linked (**Order -> Delivery -> Billing**). A pure vector database would struggle to "Trace the full flow" because it doesn't maintain explicit relationships. Neo4j allows us to perform "Multi-Hop" traversals while still using Vector Indexes for the "Search" part of RAG.
- **Tradeoff**: Increased complexity in Cypher query writing, but 100% accurate relationship mapping.

## 2. Backend: FastAPI vs. Flask/Django
- **Decision**: **FastAPI**.
- **Reasoning**: FastAPI's asynchronous nature is perfect for handling multiple I/O-bound tasks (LLM calls and Neo4j queries) concurrently. It also provides automatic OpenAPI (Swagger) documentation.
- **Tradeoff**: Younger ecosystem than Django, but significantly faster for high-concurrency LLM applications.

## 3. LLM: Groq (Llama 3) vs. OpenAI (GPT-4)
- **Decision**: **Groq**.
- **Reasoning**: Groq's inference speed (500+ tokens/sec) is essential for a "Real-time" chat experience. It reduces the perceived latency of the Graph RAG pipeline.
- **Tradeoff**: Smaller context window than GPT-4, necessitating careful "Context Pruning" in our retrieval service.

## 4. Hosting: Render.com & Neo4j Aura
- **Decision**: Cloud-Native managed services.
- **Reasoning**: To ensure the project is "Submission Ready," we moved from local Docker to a persistent 24/7 cloud environment. This avoids the "Works on my machine" problem.
- **Tradeoff**: Free tier limitations (inactivity sleep), which we mitigated with a custom "Heartbeat" mechanism.

## 5. Security: Environment Sanitization
- **Decision**: Strict `.env` management and no-log policy for credentials.
- **Reasoning**: To prevent leaking the Groq and Aura keys during the assignment submission.
