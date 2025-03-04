from django.shortcuts import render, redirect
from .models import *
from django.forms import ModelForm
from django import forms

def home_page(request):
    posts = Post.objects.all()
    return render(request, 'a_post/home.html', {'posts' : posts})

class PostCreateForm(ModelForm):
    class Meta:
        model = Post
        fields = '__all__'
        labels = {
            'body' : 'Caption',
        }
        widgets = {
            'body' : forms.Textarea(attrs={'rows':5, 'placeholder':'Add a caption ... '}),
        }

def post_create_page(request):
    form = PostCreateForm()
    if request.method == 'POST':
        form = PostCreateForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('home')
    return render(request, 'a_post/post_create.html', {'form' : form})

def post_delete_page(request, pk):
    post = Post.objects.get(id=pk)
    if request.method == 'POST':
        post.delete()
        return redirect('home')
    return render(request, 'a_post/post_delete.html', {'post' : post})