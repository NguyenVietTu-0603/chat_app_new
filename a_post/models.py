from django.db import models
from django.contrib.auth.models import User
from django.templatetags.static import static

import uuid

class Post(models.Model):
    title = models.CharField(max_length=500)
    image = models.ImageField(upload_to='post/', null=True, blank=True) 
    author = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='posts')
    body = models.TextField()
    created = models.DateTimeField(auto_now_add=True)
    id = models.CharField(max_length=100, default=uuid.uuid4, unique=True, primary_key=True, editable=False)
    
    def __str__(self):
        return str(self.title)
    
    class Meta:
        ordering = ['-created']
        
    @property
    def images(self):
        try:
            images = self.image.url
        except:
            images = static('images/avt.jpg')
        return images