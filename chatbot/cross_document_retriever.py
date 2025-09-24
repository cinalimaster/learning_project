from collections import defaultdict
import numpy as np
from sentence_transformers import util
import re

class CrossDocumentRetriever:
    def __init__(self, vector_store, document_db, embedding_model):
        self.vector_store = vector_store
        self.document_db = document_db
        self.embedding_model = embedding_model

    def find_related_documents(self, query, top_k=3):
        """Find documents related to the query and identify relationships between them"""
        # Get initial results
        query_embedding = self.embedding_model.encode(query, convert_to_tensor=False)
        results = self.vector_store.search(query_embedding, k=top_k*2)

        # Extract document IDs
        doc_ids = list(set([r['metadata']['document_id'] for r in results]))

        # Get full document content
        documents = [self.document_db.get_document(doc_id) for doc_id in doc_ids]

        # Analyze relationships between documents
        relationships = self._analyze_document_relationships(documents, query)

        return {
            'primary_documents': results[:top_k],
            'related_documents': [d for d in results[top_k:] if d['score'] > 0.5],
            'relationships': relationships
        }
    
    def _analyze_document_relationships(self, documents, query):
        """Analyze how documents relate to each other regarding the query"""
        # Extract entities from all documents
        all_entities = defaultdict(list)
        for i, doc in enumerate(documents):
            for label, entities in doc.get('entities', {}).items():
                for entity in entities:
                    all_entities[entity].append(i) # Track which document contains the entity


        
        # Find shared entities that connect documents
        shared_entities = {e: docs for e, docs in all_entities.items() if len(docs) > 1}

        # Analyze query-specific relationships
        query_entities = self._extract_query_entities(query)
        connections = []

        for entity, doc_indices in shared_entities.items():
            if entity in query_entities:
                # Direct connection to query
                connections.append({
                    'type': 'direct',
                    'entity': entity,
                    'documents': [documents[i]['id'] for i in doc_indices],
                    'relevance': 0.9
                })
            else:
                # indirect connection
                connections.append({
                    'type': 'indirect',
                    'entity': entity,
                    'documents': [documents[i]['id'] for i in doc_indices],
                    'relevance': 0.6
                })
        # Sort by relevance
        connections.sort(key=lambda x: x['relevance'], reverse=True)
        return connections[:5] # Return top 5 relationships
    

    def _extract_query_entities(self, query):
        """Extract key entities from the query"""
        # Simple entity extraction for query
        entities = []

        # Person names (capitalized words)
        person_matches = re.findall(r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b', query)
        entities.extend(person_matches)

        # Organizations (Turkish-Specific)
        org_matches = re.findall(r'\b([Bb]elediye|[Vv]akıf|[Kk]urum)\b', query)
        entities.extend(org_matches)

        # URLs and emails
        url_matches = re.findall(r'https?://[^\s]+', query)
        entities.extend(url_matches)

        return list(set(entities))
    
    def generate_cross_document_context(self, query):
        """Generate context that combines information from multiple documents"""
        analysis = self.find_related_documents(query)

        # Build context from primary documents
        context_parts = []
        for result in analysis['primary_documents']:
            context_parts.append(result['metadata']['text'])

        # Add relationship information
        if analysis['relationships']:
            context_parts.append("\n\nAyrıca ilgili belgeler arasında şu bağlantılar bulunmaktadır:")
            for rel in analysis['relationships'][:2]: # Limit to top 2 relationships
                docs_str = ", ".join([f"belge {i+1}" for i in range(len(rel['documents']))])
                context_parts.append(f"- '{rel['entity']} bilgisi {docs_str} arasında ortak olarak geçmektedir.")

        return "\n\n".join(context_parts)
