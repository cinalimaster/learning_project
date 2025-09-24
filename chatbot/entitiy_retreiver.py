# entity_retriever specialized entity extraction and retrieval system to achieve high accuracy

import re
import spacy
from .vector_store import FAISSVectorStore
from sentence_transformers import util, SentenceTransformer
import numpy as np

# Load spaCy model (en_core_web_lg for better entity recognition)
try:
    nlp = spacy.load("en_core_web_lg")
except:
    from spacy.cli import download
    download("en_core_web_lg")
    nlp = spacy.load("en_core_web_lg")


class EntitiyAwareRetriever:
    def __init__(self, vector_store, embedding_model=None):
        self.vector_store = vector_store
        self.embedding_model = embedding_model or SentenceTransformer(
            'sentence-transformers/all-MiniLM-L6-v2',
            device='cuda'
        )


    def extract_entities(self, text):
        """Extract and categorize entities from text"""
        doc = nlp(text)
        entities = {
            'PERSON': [],
            'ORG': [],
            'GPE': [],
            'URL': [],
            'EMAIL': [],
            'DATE': [],
            'PHONE': [],
        }

        # Extract standard spaCy entities
        for ent in doc.ents:
            if ent.label_ in entities:
                entities[ent.label_].append(ent.text)

        # Extract URLs using regex
        url_pattern = r'https?://[^\s<>"]+|www\.[^\s<>"]+'
        entities['URL'] = re.findall(url_pattern, text)

        # Extract emails
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        entities['EMAIL'] = re.findall(email_pattern, text)

        # Extract phone numbers
        phone_pattern = r'\b(?:\+?(\d{1,3}))?[-. (]*(\d{3,4})[-. )]*(\d{3,4})[-. ]*(\d{4})(?:[ -](\d{2,5}))?\b'
        entities['PHONE'] = [''.join(m) for m in re.findall(phone_pattern, text)]

        return {k: list(set(v)) for k, v in entities.items() if v}
    

    def enhance_query(self, query):
        """Enhance query with entity information for better retrieval"""
        entities = self.extract_entities(query)
        enhanced_terms = []

        # Add entity-specific terms to query // YOU NEED TO ADD MORE ENTITY TYPES FOR YOUR CONTENT HERE IN FUTURE
        if entities.get("PERSON"):
            enhanced_terms.append("person name")
            enhanced_terms.append("manager")
            enhanced_terms.append("director")

        if entities.get("ORG"):
            enhanced_terms.append("department")
            enhanced_terms.append("organizations")

        if entities.get("URL") or entities.get("EMAIL"):
            enhanced_terms.append("contact information")
            enhanced_terms.append("web address")

        # Create enhanced query
        enhanced_query = query
        if enhanced_terms:
            enhanced_query += " " + " ".join(enhanced_terms)

        return enhanced_query, entities
    

    def retrieve_with_entities(self, query, top_k=5):
        """Retrieve documents with special handling for entity queries"""
        enhanced_query, entities = self.enhance_query(query)

        # Generate query embedding
        query_embedding = self.embedding_model.encode(
            enhanced_query,
            convert_to_tensor=False
        ).astype('float32')

        # Get base results from vector store
        base_results = self.vector_store.search(query_embedding, k=top_k*2)

        # Score results based on entity presence
        scored_results = []
        for result in base_results:
            score = result['score']
            text = result['metadata']['text']

            # Boost score if relevant entities are present
            entity_boost = 0
            if entities.get('PERSON'):
                for person in entities['PERSON']:
                    if person.lower() in text.lower():
                        entity_boost += 0.15

            if entities.get('URL') or entities.get('EMAIL'):
                if any(url in text for url in entities.get('URL', [])) or \
                any(email in text for email in entities.get('EMAIL', [])):
                    entity_boost += 0.2

            # Apply boost (capped at 1.0)
            final_score = min(1.0, score + entity_boost)
            scored_results.append({**result, 'score': final_score})

        # Sort by final score
        scored_results.sort(key=lambda x: x['score'], reverse=True)
        return scored_results[:top_k]
