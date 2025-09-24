from django.db import models


class ChatInteraction(models.Model):
    session_id = models.CharField(max_length=64, db_index=True)
    question = models.TextField()
    guidance = models.TextField(blank=True, default='')
    answer = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
