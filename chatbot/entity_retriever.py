import re
from typing import Dict, List, Tuple

try:
    import spacy
except Exception:
    spacy = None
from sentence_transformers import SentenceTransformer


def _load_spacy_model():
    if spacy is None:
        return None
    try:
        return spacy.load("en_core_web_lg")
    except Exception:
        try:
            return spacy.blank("en")
        except Exception:
            return None


_NLP = _load_spacy_model()


class EntityAwareRetriever:
    def __init__(self, vector_store, embedding_model: SentenceTransformer | None = None):
        self.vector_store = vector_store
        # Prefer CPU by default to avoid CUDA dependency in dev/test
        self.embedding_model = embedding_model or SentenceTransformer(
            'sentence-transformers/all-MiniLM-L6-v2',
            device='cpu'
        )

    def extract_entities(self, text: str) -> Dict[str, List[str]]:
        doc = _NLP(text) if _NLP is not None else None
        entities: Dict[str, List[str]] = {
            'PERSON': [], 'ORG': [], 'GPE': [], 'URL': [], 'EMAIL': [], 'DATE': [], 'PHONE': []
        }
        if doc is not None:
            for ent in getattr(doc, 'ents', []):
                if ent.label_ in entities:
                    entities[ent.label_].append(ent.text)

        url_pattern = r'https?://[^\s<>"]+|www\.[^\s<>"]+'
        entities['URL'] = re.findall(url_pattern, text)

        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        entities['EMAIL'] = re.findall(email_pattern, text)

        phone_pattern = r'\b(?:\+?(\d{1,3}))?[-. (]*(\d{3,4})[-. )]*(\d{3,4})[-. ]*(\d{4})(?:[ -](\d{2,5}))?\b'
        entities['PHONE'] = [''.join(m) for m in re.findall(phone_pattern, text)]

        return {k: sorted(set(v)) for k, v in entities.items() if v}

    def enhance_query(self, query: str) -> Tuple[str, Dict[str, List[str]]]:
        entities = self.extract_entities(query)
        enhanced_terms: List[str] = []
        if entities.get("PERSON"):
            enhanced_terms += ["person name", "manager", "director"]
        if entities.get("ORG"):
            enhanced_terms += ["department", "organizations"]
        if entities.get("URL") or entities.get("EMAIL"):
            enhanced_terms += ["contact information", "web address"]
        enhanced_query = query + (" " + " ".join(enhanced_terms) if enhanced_terms else "")
        return enhanced_query, entities

    def retrieve_with_entities(self, query: str, top_k: int = 5):
        enhanced_query, entities = self.enhance_query(query)
        query_embedding = self.embedding_model.encode(enhanced_query, convert_to_tensor=False).astype('float32')
        base_results = self.vector_store.search(query_embedding, k=top_k * 2)

        scored_results = []
        for result in base_results:
            score = result.get('score', 0.0)
            text = result.get('metadata', {}).get('text', '')
            entity_boost = 0.0
            if entities.get('PERSON'):
                for person in entities['PERSON']:
                    if person.lower() in text.lower():
                        entity_boost += 0.15
            if entities.get('URL') or entities.get('EMAIL'):
                if any(url in text for url in entities.get('URL', [])) or any(email in text for email in entities.get('EMAIL', [])):
                    entity_boost += 0.2
            final_score = min(1.0, score + entity_boost)
            scored_results.append({**result, 'score': final_score})

        scored_results.sort(key=lambda x: x['score'], reverse=True)
        return scored_results[:top_k]

