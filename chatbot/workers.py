import time
import logging
import threading  # Required for Thread
from django.conf import settings
from .queue_manager import QueryQueue
from .services import get_best_document_context, generate_response_with_guidance
from .document_db import DocumentDatabase

logger = logging.getLogger(__name__)


def query_worker():
    """Worker process that handles queued queries"""
    queue = QueryQueue()
    db = DocumentDatabase()
    logger.info("Query worker started and waiting for requests")

    while True:
        try:
            # Get next query from queue
            result = queue.dequeue()
            if not result:
                time.sleep(0.1)  # Short sleep if queue is empty
                continue

            request_id, request_data = result
            query = request_data.get('query', '')

            logger.info(f"Processing query {request_id}: '{query[:50]}{'...' if len(query) > 50 else ''}'")

            try:
                # Update status to processing
                queue.update_status(request_id, 'processing')

                # Process the query
                start_time = time.time()

                # Get context with entity-aware retrieval
                context, selected_urls = get_best_document_context(query)

                # Generate response
                answer = generate_response_with_guidance(query, context, selected_urls)

                # Calculate processing time
                processing_time = time.time() - start_time

                # Log performance metrics (correct f-string syntax)
                logger.info(f"Query {request_id} processed in {processing_time:.2f}s")

                # Store result — assuming update_status accepts a third argument (data dict)
                queue.update_status(
                    request_id,
                    'completed',
                    {
                        'answer': answer,
                        'context': context,
                        'urls': selected_urls,
                        'processing_time': processing_time
                    }
                )

            except Exception as e:
                logger.error(f"Error processing query {request_id}: {str(e)}", exc_info=True)
                queue.update_status(request_id, 'failed', {'error': str(e)})

        except Exception as e:
            logger.critical(f"Worker encountered a critical error: {str(e)}", exc_info=True)
            time.sleep(5)  # Prevent tight loop on critical failure


def start_workers(num_workers=4):
    """Start multiple worker threads"""
    workers = []
    for i in range(num_workers):
        worker = threading.Thread(target=query_worker, daemon=True)
        worker.start()
        workers.append(worker)  # ✅ Fixed: append to list `workers`, not `worker`
        logger.info(f"Started worker thread {i+1}/{num_workers}")

    return workers