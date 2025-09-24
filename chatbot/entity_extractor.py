import re
import spacy
from collections import defaultdict

class EntityExtractor:
    def __init__(self):
        try:
            self.nlp = spacy.load("tr_core_news_lg") # Turkish language model
        except:
            import subprocess
            subprocess.run(["python", "-m", "spacy", "download", "tr_core_news_lg"])
            self.nlp = spacy.load("tr_core_news_lg")

        # Custom entity patterns for Turkish context
        self.custom_patterns = [
            # Turkish person name patterns
            (r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)', 'PERSON'),
            # Turkish organization patterns
            (r'(?:[Bb]elediye|[Vv]akıf|[Kk]urum|[Mm]üdürl[üü]k|[Dd]aire|[Bb]akanl[ıı]k)', 'ORG'),
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
        doc = self.nlp(text)
        entities = defaultdict(list)

        # Add spaCy entities
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
