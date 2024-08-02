from django.db import models


# Create your models here.
class MessageType(models.TextChoices):
    COMMAND = "COMMAND"
    QUERY = "QUERY"


class MessageStatus(models.TextChoices):
    UNPROCESSED = "UNPROCESSED"
    PROCESSING = "PROCESSING"
    PROCESSED = "PROCESSED"


class Message(models.Model):
    orchestrator = models.UUIDField(null=True)
    message_type = models.CharField(
        choices=MessageType,
        max_length=16,
    )
    message_status = models.CharField(
        choices=MessageStatus,
        max_length=16,
        default=MessageStatus.UNPROCESSED,
    )
    prompt = models.TextField()
    result = models.TextField(default="")
    created_at = models.TimeField(auto_now_add=True)
