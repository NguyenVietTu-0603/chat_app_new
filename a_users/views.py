from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from django.db.models import Count
from django.contrib import messages
from django.contrib.sites.models import Site
from django.http import Http404
from django.contrib.auth.models import User
# from allauth.account.utils import send_email_confirmation
# from a_posts.forms import ReplyCreateForm
# from a_inbox.forms import InboxNewMessageForm
from .forms import *
from .forms import *

@login_required
def profile_page(request):
    user = request.user
    # Kiểm tra nếu user chưa có profile, tạo mới
    profile, created = Profile.objects.get_or_create(user=user)
    return render(request, 'a_users/profile.html', {'profile': profile})

@login_required
def profile_edit_page(request):
    form = ProfileForm(instance=request.user.profile)
    
    if request.method == 'POST':
        form = ProfileForm(request.POST, request.FILES, instance=request.user.profile)
        if form.is_valid():
            form.save()
            
    # if request.path == reverse('profile-onboarding'):
    #     template = 'a_users/profile_onboarding.html'
    # else:
    #     template = 'a_users/profile_edit.html'
    template = 'a_users/edit_profile.html'
         
    return render(request, template, {'form':form})