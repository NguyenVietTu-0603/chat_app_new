from django.shortcuts import render, redirect
from .models import *
from django.forms import ModelForm
from django import forms

def home_page(request):
    posts = Post.objects.all()
    return render(request, 'a_post/home.html', {'posts' : posts})

class PostCreateForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = ['title', 'image', 'body']  # Không lấy 'author' vì sẽ tự động gán
        labels = {'body': 'Caption'}
        widgets = {'image': forms.FileInput()}

def post_create_page(request):
    form = PostCreateForm()
    if request.method == 'POST':
        form = PostCreateForm(request.POST, request.FILES)  
        if form.is_valid():
            post = form.save(commit=False)  # Chưa lưu ngay vào DB
            post.author = request.user  # Gán tác giả cho bài viết
            post.save()  # Lưu vào DB
            return redirect('home')
    return render(request, 'a_post/post_create.html', {'form': form})

def post_delete_page(request, pk):
    post = Post.objects.get(id=pk)
    if request.method == 'POST':
        post.delete()
        return redirect('home')
    return render(request, 'a_post/post_delete.html', {'post' : post})