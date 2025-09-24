import re
try:
    import spacy
except Exception:
    spacy = None
from collections import defaultdict

class EntityExtractor:
    def __init__(self):
        if spacy is not None:
            try:
                self.nlp = spacy.load("tr_core_news_lg") # Turkish language model
            except Exception:
                self.nlp = spacy.blank("tr")
        else:
            self.nlp = None

        # Custom entity patterns for Turkish context
        self.custom_patterns = [
            # Turkish person name patterns with diacritics (two or more capitalized words)
            (r'\b([A-ZÇĞİÖŞÜ][a-zçğıöşü]+(?:\s+[A-ZÇĞİÖŞÜ][a-zçğıöşü]+)+)\b', 'PERSON'),
            # Organization full phrases ending with Müdürlük/Müdürlüğü or Departmanı
            (r'\b([A-ZÇĞİÖŞÜ][a-zçğıöşü]+(?:\s+[A-ZÇĞİÖŞÜa-zçğıöşü]+){0,3}\s+(?:Müdürlüğü|Müdürlügü|Müdürlük|Departmanı))\b', 'ORG'),
            # URLs
            (r'https?://[^\s<>"]+|www\.[^\s<>"]+', 'URL'),
            # Email addresses
            (r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', 'EMAIL'),
            # Turkish phone numbers
            (r'(?:\(\d{3}\)\s*\d{3}\s*\d{2}\s*\d{2})|(?:\d{3}[\s.-]?\d{3}[\s.-]?\d{4})', 'PHONE'),
            # Turkish ID numbers
            (r'\b\d{11}\b', 'TCKN')
        ]

    def extract_entities(self, text):
        """Extract entities from text using spaCy and custom patterns"""
        # Process with spaCy
        doc = self.nlp(text) if self.nlp else None
        entities = defaultdict(list)

        # Add spaCy entities
        if doc is not None and hasattr(doc, 'ents'):
            for ent in doc.ents:
                entities[ent.label_].append(ent.text)

        # Add custom pattern matches
        for pattern, label in self.custom_patterns:
            for match in re.finditer(pattern, text):
                entities[label].append(match.group(0))

        # Deduplicate and clean results
        for label in entities:
            # Remove duplicates
            entities[label] = list(set(entities[label]))
            # Clean whitespace
            entities[label] = [e.strip() for e in entities[label] if e.strip()]

        return dict(entities)
    
    def enhance_entity_context(self, text, entities):
        """Enhance text with entity markers for better context preservation"""
        for label, entity_list in entities.items():
            for entity in entity_list:
                # Create a marker that preserves the original casing
                marker = f"[{label}]{entity}[/{label}]"
                # Replace with case-insensitive matching
                text = re.sub(re.escape(entity), marker, text, flags=re.IGNORECASE)

        return text
