from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views import View
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .models import Room, RoomParticipant
import json
import uuid

@login_required
def lobby_view(request):
    """Trang lobby để tạo hoặc join room"""
    user_rooms = Room.objects.filter(
        participants__user=request.user,
        is_active=True
    ).distinct()
    
    return render(request, 'videocall/lobby.html', {
        'user_rooms': user_rooms
    })

@login_required
def room_view(request, room_id):
    """Trang video call room"""
    room = get_object_or_404(Room, id=room_id, is_active=True)
    
    # Check if room is full
    current_count = room.current_participants_count
    if current_count >= room.max_participants:
        # Check if user is already in room
        existing_participant = RoomParticipant.objects.filter(
            room=room,
            user=request.user,
            is_active=True
        ).exists()
        
        if not existing_participant:
            return render(request, 'videocall/room_full.html', {'room': room})
    
    return render(request, 'videocall/room.html', {
        'room': room,
        'room_id': str(room.id),
        'user': request.user
    })

@api_view(['POST'])
@login_required
def create_room(request):
    """API để tạo room mới"""
    try:
        data = json.loads(request.body)
        room_name = data.get('name', f"{request.user.username}'s Room")
        room_type = data.get('type', 'private')
        max_participants = data.get('max_participants', 10)
        
        room = Room.objects.create(
            name=room_name,
            room_type=room_type,
            created_by=request.user,
            max_participants=max_participants
        )
        
        return JsonResponse({
            'success': True,
            'room_id': str(room.id),
            'room_name': room.name
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)

@api_view(['POST'])
@login_required
def join_room(request):
    """API để join room"""
    try:
        data = json.loads(request.body)
        room_id = data.get('room_id')
        
        room = get_object_or_404(Room, id=room_id, is_active=True)
        
        # Check if room is full
        if room.current_participants_count >= room.max_participants:
            existing_participant = RoomParticipant.objects.filter(
                room=room,
                user=request.user,
                is_active=True
            ).exists()
            
            if not existing_participant:
                return JsonResponse({
                    'success': False,
                    'error': 'Room is full'
                }, status=400)
        
        return JsonResponse({
            'success': True,
            'room_id': str(room.id),
            'room_name': room.name
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)

@api_view(['GET'])
@login_required
def room_participants(request, room_id):
    """API để lấy danh sách participants trong room"""
    try:
        room = get_object_or_404(Room, id=room_id)
        participants = RoomParticipant.objects.filter(
            room=room,
            is_active=True
        ).select_related('user')
        
        participants_data = [{
            'user_id': p.user.id,
            'username': p.user.username,
            'is_video_enabled': p.is_video_enabled,
            'is_audio_enabled': p.is_audio_enabled,
            'joined_at': p.joined_at.isoformat()
        } for p in participants]
        
        return JsonResponse({
            'success': True,
            'participants': participants_data,
            'total_count': len(participants_data)
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)
