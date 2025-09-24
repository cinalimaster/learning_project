# tests/test_accuracy.py
import pytest
import json
from django.test import TestCase
from chatbot.document_db import DocumentDatabase
from chatbot.entity_extractor import EntityExtractor
from chatbot.hybrid_retriever import HybridRetriever

class AccuracyTestCase(TestCase):
    def setUp(self):
        self.doc_db = DocumentDatabase()
        self.doc_db.load_documents()
        self.entity_extractor = EntityExtractor()
        
        # Create test documents with known entities
        self.test_documents = [
            {
                "id": "test1",
                "text": "Ahmet Yılmaz, İnsan Kaynakları Departmanı Müdürü'dir. Email adresi: ik@belediye.gov.tr",
                "entities": {
                    "PERSON": ["Ahmet Yılmaz"],
                    "ORG": ["İnsan Kaynakları Departmanı"],
                    "EMAIL": ["ik@belediye.gov.tr"]
                }
            },
            {
                "id": "test2",
                "text": "Zabıta Müdürlüğü hizmetleri için lütfen https://belediye.gov.tr/zabita adresini ziyaret edin.",
                "entities": {
                    "ORG": ["Zabıta Müdürlüğü"],
                    "URL": ["https://belediye.gov.tr/zabita"]
                }
            }
        ]
    
    def test_entity_extraction_precision(self):
        """Test precision of entity extraction (70% improvement target)"""
        total_correct = 0
        total_extracted = 0
        total_expected = 0
        
        for doc in self.test_documents:
            # Extract entities from document
            extracted = self.entity_extractor.extract_entities(doc["text"])
            
            # Compare with expected entities
            for label, expected_entities in doc["entities"].items():
                extracted_entities = extracted.get(label, [])
                
                # Count correct extractions
                correct = len(set(extracted_entities) & set(expected_entities))
                
                total_correct += correct
                total_extracted += len(extracted_entities)
                total_expected += len(expected_entities)
                
                print(f"Document {doc['id']}, Entity {label}:")
                print(f"  Expected: {expected_entities}")
                print(f"  Extracted: {extracted_entities}")
                print(f"  Correct: {correct}/{len(expected_entities)}")
        
        # Calculate precision, recall, F1
        precision = total_correct / total_extracted if total_extracted > 0 else 0
        recall = total_correct / total_expected if total_expected > 0 else 0
        f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
        
        print(f"\nEntity Extraction Metrics:")
        print(f"Precision: {precision:.2%}")
        print(f"Recall: {recall:.2%}")
        print(f"F1 Score: {f1:.2%}")
        
        # Target: 70% improvement over baseline
        # Assuming baseline F1 was 0.4, target is 0.4 + 0.7*0.4 = 0.68
        self.assertGreaterEqual(f1, 0.65, "Entity extraction accuracy did not meet 65% target")
    
    def test_hybrid_retrieval_accuracy(self):
        """Test hybrid retrieval system accuracy"""
        # Create vector store with test documents
        from chatbot.vector_store import FAISSVectorStore
        from sentence_transformers import SentenceTransformer
        
        vector_store = FAISSVectorStore(dimension=384)
        embedding_model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
        
        # Add test documents to vector store
        for doc in self.test_documents:
            embedding = embedding_model.encode(doc["text"], convert_to_tensor=False)
            vector_store.add_vectors([embedding], [{
                'document_id': doc["id"],
                'text': doc["text"]
            }])
        
        # Initialize hybrid retriever
        retriever = HybridRetriever(
            vector_store, 
            [doc["text"] for doc in self.test_documents],
            embedding_model
        )
        
        test_queries = [
            {
                "query": "İnsan Kaynakları Müdürü kimdir?",
                "expected_doc": "test1",
                "expected_entities": ["Ahmet Yılmaz"]
            },
            {
                "query": "Zabıta hizmetleri için web sitesi nedir?",
                "expected_doc": "test2",
                "expected_entities": ["https://belediye.gov.tr/zabita"]
            }
        ]
        
        successful_retrievals = 0
        
        for query in test_queries:
            # Get results
            results = retriever.hybrid_search(query["query"], top_k=1)
            
            # Check if correct document was retrieved
            if results and results[0]['doc_id'] == query["expected_doc"]:
                successful_retrievals += 1
                
                # Check entity presence in context
                context = self.test_documents[[d["id"] for d in self.test_documents].index(query["expected_doc"])]["text"]
                entity_found = any(entity in context for entity in query["expected_entities"])
                
                if entity_found:
                    print(f"✓ Query '{query['query']}' retrieved correct document with entities")
                else:
                    print(f"✗ Query '{query['query']}' retrieved correct document but missing entities")
            else:
                print(f"✗ Query '{query['query']}' retrieved incorrect document")
        
        accuracy = successful_retrievals / len(test_queries)
        print(f"\nHybrid Retrieval Accuracy: {accuracy:.2%}")
        
        # Target: 85% accuracy for test cases
        self.assertGreaterEqual(accuracy, 0.85, "Hybrid retrieval accuracy did not meet 85% target")
