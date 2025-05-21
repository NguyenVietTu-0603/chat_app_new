from django.shortcuts import render, redirect, get_object_or_404
from .models import *
from django.forms import ModelForm
from django import forms
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST

@login_required(login_url='/accounts/login/')
def home_page(request):
    posts = Post.objects.all()
    return render(request, 'a_post/home.html', {'posts': posts})

class PostCreateForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = ['title', 'image', 'body']
        labels = {'body': 'Caption'}
        widgets = {'image': forms.FileInput()}

@login_required(login_url='/accounts/login/')
def post_create_page(request):
    form = PostCreateForm()
    if request.method == 'POST':
        form = PostCreateForm(request.POST, request.FILES)
        if form.is_valid():
            post = form.save(commit=False)
            post.author = request.user
            post.save()
            return redirect('home')
    return render(request, 'a_post/post_create.html', {'form': form})

@login_required(login_url='/accounts/login/')
def post_delete_page(request, pk):
    post = get_object_or_404(Post, id=pk)
    if request.method == 'POST':
        post.delete()
        return redirect('home')
    return render(request, 'a_post/post_delete.html', {'post': post})

# ====== XỬ LÝ LIKE ======
@require_POST
@login_required
def like_post(request):
    post_id = request.POST.get('post_id')
    post = get_object_or_404(Post, id=post_id)
    like, created = Like.objects.get_or_create(user=request.user, post=post)
    if not created:
        like.delete()
        liked = False
    else:
        liked = True
    return JsonResponse({'liked': liked, 'like_count': post.likes.count()})

# ====== XỬ LÝ COMMENT ======
@require_POST
@login_required
def add_comment(request):
    post_id = request.POST.get('post_id')
    content = request.POST.get('content')
    post = get_object_or_404(Post, id=post_id)
    comment = Comment.objects.create(user=request.user, post=post, content=content)
    return JsonResponse({
        'user': comment.user.profile.name if hasattr(comment.user, 'profile') else comment.user.username,
        'content': comment.content,
        'created_at': comment.created.strftime('%H:%M %d/%m/%Y')
    })

@login_required
def home_page(request):
    posts = Post.objects.all()
    liked_post_ids = set(request.user.likes.values_list('post_id', flat=True))
    return render(request, 'a_post/home.html', {
        'posts': posts,
        'liked_post_ids': liked_post_ids,
    })