import re
import os
import json
import fitz
import logging
import numpy as np
from django.conf import settings
from nltk.corpus import stopwords
from nltk.tokenize import sent_tokenize, word_tokenize
from bs4 import BeautifulSoup
import html2text
import markdown
from .advanced_splitter import AdvancedDocumentSplitter
from .entity_extractor import EntityExtractor
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

class DocumentProcessor:
    def __init__(self):
        self.splitter = AdvancedDocumentSplitter(chunk_size=512, chunk_overlap=64)
        self.entity_extractor = EntityExtractor()
        try:
            self.stop_words = set(stopwords.words('turkish'))
        except LookupError:
            import nltk
            nltk.download('stopwords', quiet=True)
            self.stop_words = set(stopwords.words('turkish'))
        # Embedder for chunk vectors
        self.embedding_model = SentenceTransformer(
            'sentence-transformers/all-MiniLM-L6-v2',
            device='cpu'
        )

    def process_document(self, file_path):
        """Process a document and return structured content with entities"""
        file_ext = os.path.splitext(file_path)[1].lower()

        try:
            if file_ext == '.pdf':
                text, metadata = self._process_pdf(file_path)
            elif file_ext in ['.txt', '.md']:
                text, metadata = self._process_text(file_path)
            else:
                raise ValueError(f"Unsupported file type: {file_ext}")

            # Extract entities from text
            entities = self.entity_extractor.extract_entities(text)

            # Split into chunks with preserved context
            chunks = self.splitter.split_document(text, os.path.basename(file_path))

            # Enrich chunks with entity information
            enriched_chunks = []
            for chunk in chunks:
                chunk_entities = self.entity_extractor.extract_entities(chunk['text'])
                chunk['entities'] = chunk_entities
                enriched_chunks.append(chunk)

            return {
                'text': text,
                'metadata': metadata,
                'chunks': enriched_chunks,
                'entities': entities
            }

        except Exception as e:
            logger.error(f"Error processing document {file_path}: {str(e)}")
        raise

    def _process_pdf(self, file_path):
        """Process PDF document with metadata extraction"""
        doc = fitz.open(file_path)
        text = ""
        metadata = {
            'page_count': doc.page_count,
            'author': doc.metadata.get('author', ''),
            'title': doc.metadata.get('title', os.path.basename(file_path)),
            'creation_date': doc.metadata.get('creationDate', ''),
            'chunks': []
        }

        for page_num in range(doc.page_count):
            page = doc.load_page(page_num)
            page_text = page.get_text()
            text += page_text + "\n\n"

        return text, metadata

    def _process_text(self, file_path):
        """Process text or Markdown file"""
        with open(file_path, 'r', encoding='utf-8') as f:
            text = f.read()

            # Handle markdown specifically
            if file_path.endswith('.md'):
                # Convert to HTML first for better structure preservation
                html = markdown.markdown(text)
                # Extract text while preserving some structure
                soup = BeautifulSoup(html, 'html.parser')
                text = soup.get_text(separator=' ', strip=True)

            metadata = {
                'title': os.path.basename(file_path),
                'source': file_path
            }

            return text, metadata
