# vector_store.py
"""
FAISS-based vector store for efficient similarity search.
Leverages GPU acceleration (e.g., RTX 5090) when available.
"""

import faiss
import numpy as np
import os
import json
from django.conf import settings
from sentence_transformers import SentenceTransformer

# Configure logging
import logging
logger = logging.getLogger(__name__)


class FAISSVectorStore:
    def __init__(self, dimension=384, index_path=None, use_gpu=True):
        self.dimension = dimension
        self.index_path = index_path or os.path.join(settings.BASE_DIR, 'data', 'vector_store')
        os.makedirs(self.index_path, exist_ok=True)

        # Initialize index: try GPU first, fall back to CPU
        if use_gpu and faiss.get_num_gpus() > 0:
            try:
                logger.info("Initializing GPU-accelerated FAISS index...")
                self.index = faiss.IndexFlatIP(dimension)
                # Wrap in GPU wrapper
                self.index = faiss.index_cpu_to_all_gpus(self.index)
                logger.info(f"Using {faiss.get_num_gpus()} GPU(s) for FAISS.")
            except Exception as e:
                logger.warning(f"Failed to initialize GPU FAISS: {e}. Falling back to CPU.")
                self.index = faiss.IndexFlatIP(dimension)
        else:
            logger.info("Using CPU-based FAISS index.")
            self.index = faiss.IndexFlatIP(dimension)

        # Metadata storage
        self.metadata = []
        self._load_index()

    def _load_index(self):
        """Load FAISS index and metadata from disk if they exist."""
        index_file = os.path.join(self.index_path, 'faiss_index.bin')
        metadata_file = os.path.join(self.index_path, 'metadata.json')

        # Check if both files exist
        if os.path.exists(index_file) and os.path.exists(metadata_file):
            try:
                logger.info(f"Loading FAISS index from {index_file}")
                self.index = faiss.read_index(index_file)
                with open(metadata_file, 'r') as f:
                    self.metadata = json.load(f)
                logger.info(f"Loaded {len(self.metadata)} vectors from disk.")
            except Exception as e:
                logger.error(f"Failed to load index or metadata: {e}")
                # Reset if corrupted
                self.index = faiss.IndexFlatIP(self.dimension)
                self.metadata = []
        else:
            logger.info("No existing index found. Starting fresh.")

    def add_vectors(self, vectors, metadata_list):
        """
        Add vectors and their metadata to the FAISS index.
        Vectors are normalized using L2 before insertion.
        """
        if not vectors:
            return

        # Convert to float32 (required by FAISS)
        vectors = np.array(vectors).astype('float32')

        # Normalize for cosine similarity
        faiss.normalize_L2(vectors)

        # Add to index
        try:
            self.index.add(vectors)
            self.metadata.extend(metadata_list)
            logger.info(f"Added {len(vectors)} vectors to index.")

            # Save periodically (every 100 additions)
            if len(self.metadata) % 100 == 0:
                self.save_index()
        except Exception as e:
            logger.error(f"Failed to add vectors: {e}")
            raise

    def save_index(self):
        """Save FAISS index and metadata to disk."""
        index_file = os.path.join(self.index_path, 'faiss_index.bin')
        metadata_file = os.path.join(self.index_path, 'metadata.json')

        try:
            # Save FAISS index
            faiss.write_index(self.index, index_file)
            logger.info(f"FAISS index saved to {index_file}")

            # Save metadata
            with open(metadata_file, 'w') as f:
                json.dump(self.metadata, f, indent=2)
            logger.info(f"Metadata saved to {metadata_file}")

        except Exception as e:
            logger.error(f"Failed to save index or metadata: {e}")
            raise

    def search(self, query_vector, k=10):
        """
        Search for the k most similar vectors using cosine similarity.
        Returns list of results with scores and metadata.
        """
        if not self.index or len(self.metadata) == 0:
            logger.warning("No index or metadata available.")
            return []

        # Convert query vector to float32
        query_vector = np.array(query_vector).astype('float32')

        # Normalize query for cosine similarity
        faiss.normalize_L2(query_vector.reshape(1, -1))

        try:
            distances, indices = self.index.search(query_vector.reshape(1, -1), k)
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []

        results = []
        for i, idx in enumerate(indices[0]):
            if idx == -1:
                continue  # Invalid index
            try:
                results.append({
                    'score': float(distances[0][i]),
                    'metadata': self.metadata[idx]
                })
            except IndexError:
                logger.warning(f"Metadata index {idx} out of range.")
                continue

        return results

    def __len__(self):
        """Return number of stored vectors."""
        return int(getattr(self.index, 'ntotal', 0))