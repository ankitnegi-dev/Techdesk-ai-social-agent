"""
RAG pipeline — embeds incoming signals and retrieves relevant
knowledge base chunks to inject as context into the LLM prompt.
"""
import uuid
import logging
from fastembed import TextEmbedding
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from shared.db.models import KnowledgeChunk

log = logging.getLogger("rag")

# Load embedding model once at startup (downloads ~50MB on first run)
_embedder = None

def get_embedder() -> TextEmbedding:
    global _embedder
    if _embedder is None:
        log.info("Loading embedding model (first run may take 30s)...")
        _embedder = TextEmbedding(model_name="BAAI/bge-small-en-v1.5")
        log.info("Embedding model loaded")
    return _embedder

def embed_text(text: str) -> list[float]:
    embedder = get_embedder()
    embeddings = list(embedder.embed([text]))
    return embeddings[0].tolist()

async def retrieve_context(query: str, db: AsyncSession, top_k: int = 3) -> list[dict]:
    """Embed query and retrieve top-K relevant knowledge chunks."""
    try:
        query_embedding = embed_text(query)
        result = await db.execute(
            text("""
                SELECT id, title, content, category,
                       1 - (embedding <=> CAST(:embedding AS vector)) AS similarity
                FROM knowledge_base
                WHERE embedding IS NOT NULL
                ORDER BY embedding <=> CAST(:embedding AS vector)
                LIMIT :top_k
            """),
            {"embedding": str(query_embedding), "top_k": top_k}
        )
        rows = result.fetchall()
        chunks = [
            {"title": r.title, "content": r.content,
             "category": r.category, "similarity": round(r.similarity, 3)}
            for r in rows
        ]
        log.debug(f"Retrieved {len(chunks)} chunks for query: {query[:60]}")
        return chunks
    except Exception as e:
        log.warning(f"RAG retrieval failed: {e}")
        return []

async def add_knowledge_chunk(
    db: AsyncSession, title: str, content: str, category: str
) -> str:
    """Add a document chunk to the knowledge base with embedding."""
    embedding = embed_text(f"{title}. {content}")
    chunk = KnowledgeChunk(
        id=str(uuid.uuid4()),
        title=title,
        content=content,
        category=category,
        embedding=embedding,
    )
    db.add(chunk)
    await db.commit()
    log.info(f"Added knowledge chunk: {title}")
    return chunk.id

async def seed_knowledge_base(db: AsyncSession):
    """Seed with sample brand FAQs — replace with your real content."""
    existing = await db.execute(select(KnowledgeChunk).limit(1))
    if existing.fetchone():
        log.info("Knowledge base already seeded — skipping")
        return

    faqs = [
        ("Dark mode support", "Dark mode is available under Preferences > Display > Theme. Select 'Dark' from the dropdown. Available on all platforms including mobile.", "feature"),
        ("Data loss issue", "If you experience data loss, immediately go to Settings > Backup > Restore. All data is backed up every 24 hours. Contact support@yourbrand.com with your account ID for urgent recovery.", "support"),
        ("Pricing plans", "We offer three plans: Free (up to 3 users), Pro ($12/month per user), and Enterprise (custom pricing). All plans include a 14-day free trial.", "pricing"),
        ("Account deletion", "To delete your account go to Settings > Account > Delete Account. This is permanent and cannot be undone. Export your data first via Settings > Export.", "account"),
        ("Mobile app", "Our mobile app is available on iOS (App Store) and Android (Google Play). Search for 'YourBrand' and install the official app.", "product"),
        ("API access", "API access is available on Pro and Enterprise plans. Generate your API key at Settings > Developer > API Keys. Full documentation at docs.yourbrand.com.", "developer"),
        ("Response time", "Our support team responds within 2 hours on weekdays and 24 hours on weekends. For urgent issues use the in-app live chat.", "support"),
        ("Integrations", "We integrate with Slack, Google Workspace, Microsoft Teams, Zapier, and 50+ other tools. See all integrations at yourbrand.com/integrations.", "product"),
    ]

    for title, content, category in faqs:
        await add_knowledge_chunk(db, title, content, category)

    log.info(f"Knowledge base seeded with {len(faqs)} FAQ entries")
