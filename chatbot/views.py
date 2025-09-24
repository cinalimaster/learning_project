from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.conf import settings
import os
import uuid
import time
from .document_db import DocumentDatabase
from .tasks import process_document_task
from .rete_limiter import RateLimiter
from .services import get_best_document_context, generate_response_with_guidance
from .models import ChatInteraction


class AskView(APIView):
    @method_decorator(csrf_exempt)
    def post(self, request, *args, **kwargs):
        # Initialize rate limiter (20 requests per 24 hours)
        rate_limiter = RateLimiter(max_requests=20, window_seconds=86400)

        # Check rate limit
        if not rate_limiter.check_rate_limit(request):
            remaining = rate_limiter.get_remaining_requests(request)
            reset_time = 86400 - (time.time() % 86400)  # Seconds until next day
            return Response({
                'error': 'Rate limit exceeded',
                'message': 'You have exceeded the maximum number of requests (20 per day). You can continue to use this service after 24 hours.',
                'remaining_requests': remaining,
                'reset_seconds': int(reset_time)
            }, status=status.HTTP_429_TOO_MANY_REQUESTS)

        # Process the request
        try:
            question = request.data.get('question', '').strip()
            session_id = request.data.get('session_id') or str(uuid.uuid4())

            if not question:
                return Response({'error': 'Question cannot be empty'}, status=status.HTTP_400_BAD_REQUEST)

            # Get context and generate response
            context, selected_urls = get_best_document_context(question)
            answer = generate_response_with_guidance(question, context, selected_urls)

            # Log the interaction
            ChatInteraction.objects.create(
                question=question,
                guidance="",  # Optional: consider making it nullable or removing if not needed
                answer=answer,
                session_id=session_id
            )

            return Response({
                'answer': answer,
                'context': context,
                'urls': selected_urls,
                'session_id': session_id,
                'remaining_requests': rate_limiter.get_remaining_requests(request)
            })

        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class DocumentUploadView(APIView):
    @method_decorator(csrf_exempt)
    def post(self, request, *args, **kwargs):
        # Check if file was uploaded
        if 'file' not in request.FILES:
            return Response({'error': 'No file provided'}, status=status.HTTP_400_BAD_REQUEST)

        file = request.FILES['file']

        # Validate file size (max 40MB)
        if file.size > 40 * 1024 * 1024:  # 40MB in bytes
            return Response({'error': 'File too large (> 40MB)'}, status=status.HTTP_400_BAD_REQUEST)

        # Check document count limit (500 files)
        doc_db = DocumentDatabase()
        if len(doc_db.documents) >= 500:
            return Response({'error': 'Document count limit reached (500 files)'}, status=status.HTTP_400_BAD_REQUEST)

        # Determine document type
        file_extension = os.path.splitext(file.name)[1].lower()[1:]
        allowed_types = ['pdf', 'txt', 'md', 'docx']
        if file_extension not in allowed_types:
            return Response({
                'error': f'Unsupported file type. Allowed types: {", ".join(allowed_types)}'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Save the file
        upload_dir = os.path.join(settings.BASE_DIR, 'documents')
        os.makedirs(upload_dir, exist_ok=True)

        # Create unique filename
        file_id = str(uuid.uuid4())
        filename = f"{file_id}.{file_extension}"
        file_path = os.path.join(upload_dir, filename)

        # Write file
        with open(file_path, 'wb+') as destination:
            for chunk in file.chunks():
                destination.write(chunk)

        # Queue for processing
        process_document_task.delay(file_path)

        return Response({
            'status': 'success',
            'message': 'Document uploaded and queued for processing',
            'document_id': file_id,
            'file_name': file.name
        }, status=status.HTTP_201_CREATED)


class DocumentStatusView(APIView):
    def get(self, request, document_id):
        """Check the processing status of a document"""
        # In a real implementation, you'd check Celery task status
        # This is a simplified version

        doc_db = DocumentDatabase()
        document = doc_db.get_document(document_id)

        if document:
            return Response({
                'status': 'processed',
                'document_id': document_id,
                'title': document['title']
            })

        # Fallback: assume it's still being processed
        # In real apps, check Celery task state via `app.AsyncResult(...)`
        return Response({
            'status': 'processing',
            'document_id': document_id
        })


def index(request):
    return render(request, 'index.html')