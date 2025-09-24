import re
import os
import json
import logging
from django.conf import settings
from .vector_store import FAISSVectorStore
from .document_processor import DocumentProcessor
from .entity_extractor import EntityExtractor

logger = logging.getLogger(__name__)

class DocumentDatabase:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DocumentDatabase, cls).__new__(cls)
            cls._instance.initialized = False
        return cls._instance
    
    def __init__(self):
        if self.initialized:
            return

        # Initialize vector store
        self.vector_store = FAISSVectorStore(
            dimension = 384, # all-MiniLM-L6-v2 output dimension
            index_path= os.path.join(settings.BASE_DIR, 'vector_store')
        )

        # Document processor
        self.processor = DocumentProcessor()

        # Entity extractor
        self.entity_extractor = EntityExtractor()

        self.documents = {}
        self.initialized = True

    @classmethod
    def load_documents(cls):
        """Load documents from the documents directory"""
        instance = cls()

        documents_dir = os.path.join(settings.BASE_DIR, 'documents')
        logger.info(f"Loading documents from {documents_dir}")

        # Clear existing index
        instance.vector_store.index.reset()
        instance.documents = {}

        # Process each document
        for filename in os.listdir(documents_dir):
            if filename.startswith('.'):
                continue

            file_path = os.path.join(documents_dir, filename)
            if os.path.isfile(file_path):
                try:
                    # Process document
                    doc_data = instance.processor.process_document(file_path)

                    # Store document metadata
                    doc_id = os.path.splitext(filename)[0]
                    instance.documents[doc_id] = {
                        'id': doc_id,
                        'title': filename,
                        'path': file_path,
                        'text': doc_data['text'],
                        'metadata': doc_data['metadata'],
                        'entities': doc_data['entities']
                    }

                    # Add chunk to vector store
                    for chunk in doc_data['chunks']:
                        # Generate embedding for the chunk
                        embedding = instance.processor.embedding_model.encode(
                            chunk['text'],
                            convert_to_tensor = False
                        ).astype('float32')

                        # Add metadata for the chunk
                        chunk_metadata = {
                            'document_id': doc_id,
                            'chunk_id': chunk['id'],
                            'text': chunk['text'],
                            'section_title': chunk.get('section_title', ''),
                            'url': chunk.get('url', '')
                        }

                        # Add to vector store
                        instance.vector_store.add_vectors([embedding], [chunk_metadata])

                    logger.info(f"Successfully processed document: {filename}")

                except Exception as e:
                    logger.error(f"Error processing document {filename}: {str(e)}")

        # Save the index
        instance.vector_store.save_index()
        logger.info(f"Loaded {len(instance.documents)} documents into the database")

    def get_context_for_query(self, query, top_k=5):
        """Get relevant context for a query using the enhanced retrieval system"""

        # Generate query embedding
        query_embedding = self.processor.embedding_model.encode(
            query,
            convert_to_tensor = False
        ).astype('float32')

        # Search vector store
        results = self.vector_store.search(query_embedding, k=top_k)

        # Build context from results
        context_part = []
        urls = []

        for result in results:
            metadata = result['metadata']
            context_part.append(metadata['text'])

            # Collect URLs
            if metadata.get('url'):
                urls.append(metadata['url'])

        context = "\n\n".join(context_part)
        return context, urls

    def get_document(self, doc_id):
        """Get a document by ID"""
        return self.documents.get(doc_id)
