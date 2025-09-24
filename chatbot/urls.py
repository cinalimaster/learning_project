from django.urls import path

from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('api/ask/', views.AskView.as_view(), name='ask'),
    path('api/upload/', views.DocumentUploadView.as_view(), name='upload'),
    path('api/documents/<str:document_id>/status/', views.DocumentStatusView.as_view(), name='document-status'),
]
