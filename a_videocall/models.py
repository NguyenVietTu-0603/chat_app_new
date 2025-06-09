from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import uuid

class Room(models.Model):
    ROOM_TYPES = (
        ('private', 'Private Call'),
        ('group', 'Group Call'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    room_type = models.CharField(max_length=10, choices=ROOM_TYPES, default='private')
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_rooms')
    created_at = models.DateTimeField(default=timezone.now)
    is_active = models.BooleanField(default=True)
    max_participants = models.IntegerField(default=10)
    
    def __str__(self):
        return f"{self.name} ({self.room_type})"
    
    @property
    def current_participants_count(self):
        return self.participants.filter(is_active=True).count()

class RoomParticipant(models.Model):
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name='participants')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    joined_at = models.DateTimeField(default=timezone.now)
    left_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    is_video_enabled = models.BooleanField(default=True)
    is_audio_enabled = models.BooleanField(default=True)
    
    class Meta:
        unique_together = ['room', 'user']
    
    def __str__(self):
        return f"{self.user.username} in {self.room.name}"

class CallSession(models.Model):
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name='sessions')
    started_at = models.DateTimeField(default=timezone.now)
    ended_at = models.DateTimeField(null=True, blank=True)
    duration = models.DurationField(null=True, blank=True)
    
    def __str__(self):
        return f"Session for {self.room.name}"