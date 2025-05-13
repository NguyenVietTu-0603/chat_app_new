from django.db import models
from django.contrib.auth.models import User
import shortuuid
from PIL import Image
import os

class ChatGroup(models.Model):
    group_name = models.CharField(max_length=128, unique=True, blank=True)
    groupchat_name = models.CharField(max_length=128, null=True, blank=True)
    admin = models.ForeignKey(User, related_name='groupchats', blank=True, null=True, on_delete=models.SET_NULL)
    users_online = models.ManyToManyField(User, related_name='online_in_groups', blank=True)
    members = models.ManyToManyField(User, related_name='chat_groups', blank=True)
    is_private = models.BooleanField(default=False)
    
    def __str__(self):
        return self.group_name

    def save(self, *args, **kwargs):
        if not self.group_name:
            self.group_name = shortuuid.uuid()
        super().save(*args, **kwargs)
    
    
class GroupMessage(models.Model):
    group = models.ForeignKey(ChatGroup, related_name='chat_messages', on_delete=models.CASCADE)
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    body = models.CharField(max_length=300, blank=True, null=True)
    file = models.FileField(upload_to='files/', blank=True, null=True)
    created = models.DateTimeField(auto_now_add=True)
    
    @property
    def filename(self):
        if self.file:
            return os.path.basename(self.file.name)
        else:
            return None
    
    def __str__(self):
        if self.body:
            return f'{self.author.username} : {self.body}'
        elif self.file:
            return f'{self.author.username} : {self.filename}'
    
    class Meta:
        ordering = ['-created']
        
    @property    
    def is_image(self):
        try:
            image = Image.open(self.file) 
            image.verify()
            return True 
        except:
            return False
        
class PrivateChat(models.Model):
    user1 = models.ForeignKey(User, related_name='private_chats_1', on_delete=models.CASCADE)
    user2 = models.ForeignKey(User, related_name='private_chats_2', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user1', 'user2')
    
    def __str__(self):
        return f"Chat between {self.user1.username} and {self.user2.username}"

class PrivateMessage(models.Model):
    chat = models.ForeignKey(PrivateChat, related_name='messages', on_delete=models.CASCADE)
    sender = models.ForeignKey(User, on_delete=models.CASCADE)
    body = models.CharField(max_length=300, blank=True, null=True)
    file = models.FileField(upload_to='private_chat_files/', blank=True, null=True)
    is_image = models.BooleanField(default=False)
    is_video = models.BooleanField(default=False)
    created = models.DateTimeField(auto_now_add=True)

    @property
    def filename(self):
        if self.file:
            return os.path.basename(self.file.name)
        return None

    def __str__(self):
        if self.body:
            return f'{self.sender.username}: {self.body}'
        elif self.file:
            return f'{self.sender.username}: {self.filename}'
        return f'{self.sender.username}: [No content]'

    class Meta:
        ordering = ['-created']

    @property
    def is_image_fn(self):
        try:
            image = Image.open(self.file)
            image.verify()
            return True
        except:
            return False