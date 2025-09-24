# hybrid_retriever.py
from rank_bm25 import BM25
import numpy as np
from sentence_transformers import util
from .entity_retriever import EntityAwareRetriever


class HybridRetriever:
    def __init__(self, vector_store, documents, embedding_model=None):
        self.vector_store = vector_store
        self.documents = documents  # List of documents (dicts with 'id', 'text', etc.)
        self.embedding_model = embedding_model

        # Initialize entity-aware retriever
        self.entity_retriever = EntityAwareRetriever(vector_store, embedding_model)

        # Prepare BM25: tokenize corpus
        self.tokenized_corpus = [doc['text'].split() for doc in documents]  # assuming 'text' field exists
        self.bm25 = BM25(self.tokenized_corpus)

    def hybrid_search(self, query, top_k=5, weights=(0.6, 0.3, 0.1)):
        """
        Perform hybrid search combining:
        1. Dense vector search (FAISS)
        2. Sparse BM25 search
        3. Entity-aware search

        Args:
            query (str): Input query string.
            top_k (int): Number of final results to return.
            weights (tuple): (vector_weight, bm25_weight, entity_weight)

        Returns:
            List[dict]: Top-k documents with hybrid scores and details.
        """
        # 1. Dense vector search
        query_embedding = self.embedding_model.encode(query, convert_to_tensor=False)
        vector_results = self.vector_store.search(query_embedding, k=top_k * 2)

        # 2. Sparse BM25 search
        tokenized_query = query.split()
        bm25_scores = self.bm25.get_scores(tokenized_query)
        # Get top-k indices
        bm25_top_indices = np.argsort(bm25_scores)[::-1][:top_k * 2]

        # 3. Entity-aware search
        entity_results = self.entity_retriever.retrieve_with_entities(query, top_k * 2)

        # Unified result map: key is doc_id, value is dict of scores
        result_map = {}

        # Process vector results
        for result in vector_results:
            doc_id = result['metadata']['document_id']
            if doc_id not in result_map:
                result_map[doc_id] = {
                    'vector_score': result['score'],
                    'bm25_score': 0,
                    'entity_score': 0
                }
            else:
                result_map[doc_id]['vector_score'] = result['score']

        # Process BM25 results
        for idx in bm25_top_indices:
            doc_id = self.documents[idx]['id']  # Assumes each doc has 'id' field
            score = bm25_scores[idx]
            # Normalize: scale by max score to get [0,1] range
            norm_score = score / (np.max(bm25_scores) + 1e-10)
            if doc_id not in result_map:
                result_map[doc_id] = {
                    'vector_score': 0,
                    'bm25_score': norm_score,
                    'entity_score': 0
                }
            else:
                result_map[doc_id]['bm25_score'] = norm_score

        # Process entity results
        for result in entity_results:
            doc_id = result['metadata']['document_id']
            score = result['score']
            if doc_id not in result_map:
                result_map[doc_id] = {
                    'vector_score': 0,
                    'bm25_score': 0,
                    'entity_score': score
                }
            else:
                result_map[doc_id]['entity_score'] = score

        # Compute hybrid score and collect results
        hybrid_results = []
        for doc_id, scores in result_map.items():
            hybrid_score = (
                weights[0] * scores['vector_score'] +
                weights[1] * scores['bm25_score'] +
                weights[2] * scores['entity_score']
            )
            hybrid_results.append({
                'doc_id': doc_id,
                'score': hybrid_score,
                'details': scores
            })

        # Sort by hybrid score (descending)
        hybrid_results.sort(key=lambda x: x['score'], reverse=True)

        return hybrid_results[:top_k]