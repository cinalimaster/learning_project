# tests/test_performance.py
import time
import json
import pytest
from django.test import TestCase, Client
from django.urls import reverse
from concurrent.futures import ThreadPoolExecutor, as_completed
from chatbot.document_db import DocumentDatabase
from chatbot.services import generate_response_with_guidance

class PerformanceTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        # Load test documents
        self.doc_db = DocumentDatabase()
        self.doc_db.load_documents()
    
    def test_single_query_performance(self):
        """Test that a single query completes within 10 seconds"""
        query = "Belediye hizmetleriyle ilgili temel bilgiler nelerdir?"
        
        start_time = time.time()
        response = self.client.post(
            reverse('ask'),
            json.dumps({'question': query}),
            content_type='application/json'
        )
        duration = time.time() - start_time
        
        self.assertEqual(response.status_code, 200)
        self.assertLess(duration, 10.0, f"Query took {duration:.2f}s, exceeding 10s limit")
        print(f"Single query completed in {duration:.2f}s")
    
    def test_concurrent_user_performance(self):
        """Test system performance under concurrent load"""
        queries = [
            "Zabıta müdürü kimdir?",
            "Belediyenin iletişim bilgileri nelerdir?",
            "İmar barışı başvurusu nasıl yapılır?",
            "Su faturası ödemeleri nereden yapılır?",
            "Park yeri rezervasyonu nasıl yapılır?"
        ]
        
        def make_request(query):
            start = time.time()
            response = self.client.post(
                reverse('ask'),
                json.dumps({'question': query}),
                content_type='application/json'
            )
            duration = time.time() - start
            return query, duration, response.status_code
        
        # Test with 10 concurrent users
        results = []
        with ThreadPoolExecutor(max_workers=10) as executor:
            future_to_query = {executor.submit(make_request, query): query for query in queries * 2}
            
            for future in as_completed(future_to_query):
                query, duration, status = future.result()
                results.append((query, duration, status))
                print(f"Query '{query[:30]}...' completed in {duration:.2f}s with status {status}")
        
        # Assert all queries completed successfully
        for _, duration, status in results:
            self.assertEqual(status, 200)
            self.assertLess(duration, 10.0)
        
        # Calculate average response time
        avg_time = sum(duration for _, duration, _ in results) / len(results)
        print(f"Average response time under load: {avg_time:.2f}s")
        self.assertLess(avg_time, 5.0)  # Target average < 5s under load
    
    def test_entity_extraction_accuracy(self):
        """Test entity extraction accuracy with known test cases"""
        test_cases = [
            {
                "query": "Zabıta müdürü kimdir?",
                "expected_entities": ["Zabıta Müdürü"],
                "min_score": 0.85
            },
            {
                "query": "İnsan kaynakları departmanının email adresi nedir?",
                "expected_entities": ["İnsan Kaynakları", "email"],
                "min_score": 0.9
            },
            {
                "query": "Belediyenin resmi websitesi nedir?",
                "expected_entities": ["website", "URL"],
                "min_score": 0.95
            }
        ]
        
        for case in test_cases:
            # Get context for the query
            context, urls = self.doc_db.get_context_for_query(case["query"])
            
            # Generate response
            response = generate_response_with_guidance(case["query"], context, urls)
            
            # Check if expected entities are in the response
            found_entities = 0
            for entity in case["expected_entities"]:
                if entity.lower() in response.lower():
                    found_entities += 1
            
            accuracy = found_entities / len(case["expected_entities"])
            self.assertGreaterEqual(accuracy, case["min_score"], 
                                   f"Entity extraction accuracy too low for '{case['query']}'")
            print(f"Entity extraction accuracy for '{case['query']}': {accuracy:.2%}")
