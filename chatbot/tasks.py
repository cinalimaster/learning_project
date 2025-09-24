# tasks.py - Celery task-based embedding generation using multi-core CPU effectively
from celery import shared_task
from .vector_store import FAISSVectorStore
from sentence_transformers import SentenceTransformer
import numpy as np
from .document_db import DocumentDatabase
import logging

logger = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=3)
def generate_embeddings_task(self, document_id, chunks):
    """
    Generate embeddings for document chunks asynchronously using Celery.
    Utilizes GPU (if available) and caches the model across tasks.
    """
    try:
        # Initialize model only once per worker process
        if not hasattr(generate_embeddings_task, 'model'):
            logger.info("Loading SentenceTransformer model...")
            generate_embeddings_task.model = SentenceTransformer(
                'sentence-transformers/all-MiniLM-L6-v2',
                device='cuda'  # Use GPU (e.g., RTX 4090 or similar)
            )

        model = generate_embeddings_task.model  # ✅ Correct: get the actual model

        # Extract text from chunks
        texts = [chunk['text'] for chunk in chunks]
        
        # Generate embeddings
        logger.info(f"Generating embeddings for {len(texts)} chunks...")
        vectors = model.encode(texts, convert_to_tensor=False)  # Returns numpy array
        vectors = np.array(vectors)  # Ensure it's a NumPy array

        # Prepare metadata
        metadata_list = [
            {
                'document_id': document_id,
                'chunk_id': chunk['id'],
                'text': chunk['text'],
                'url': chunk.get('url', '')
            }
            for chunk in chunks
        ]

        # Save to FAISS vector store
        logger.info("Saving vectors to FAISS index...")
        vector_store = FAISSVectorStore()
        vector_store.add_vectors(vectors, metadata_list)
        vector_store.save_index()

        logger.info(f"Successfully processed {len(chunks)} chunks for document_id={document_id}")

        return {
            'status': 'success',
            'chunks_processed': len(chunks),
            'document_id': document_id
        }

    except Exception as e:
        logger.error(f"Failed to generate embeddings for document_id={document_id}: {str(e)}")
        # Retry with exponential backoff (2^retries seconds)
        raise self.retry(exc=e, countdown=2 ** self.request.retries)