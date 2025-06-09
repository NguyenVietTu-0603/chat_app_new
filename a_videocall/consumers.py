import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import User
from .models import Room, RoomParticipant
import logging

logger = logging.getLogger(__name__)

class VideoCallConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_id = self.scope['url_route']['kwargs']['room_id']
        self.room_group_name = f'videocall_{self.room_id}'
        self.user = self.scope['user']
        
        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.accept()
        
        # Add user to room participants
        await self.add_user_to_room()
        
        # Notify others about new user
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'user_joined',
                'user_id': self.user.id,
                'username': self.user.username,
                'channel_name': self.channel_name
            }
        )

    async def disconnect(self, close_code):
        # Remove user from room participants
        await self.remove_user_from_room()
        
        # Notify others about user leaving
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'user_left',
                'user_id': self.user.id,
                'username': self.user.username,
                'channel_name': self.channel_name
            }
        )
        
        # Leave room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            message_type = data.get('type')
            
            if message_type == 'offer':
                await self.handle_offer(data)
            elif message_type == 'answer':
                await self.handle_answer(data)
            elif message_type == 'ice_candidate':
                await self.handle_ice_candidate(data)
            elif message_type == 'toggle_video':
                await self.handle_toggle_video(data)
            elif message_type == 'toggle_audio':
                await self.handle_toggle_audio(data)
            elif message_type == 'get_room_users':
                await self.send_room_users()
                
        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Invalid JSON format'
            }))

    async def handle_offer(self, data):
        target_user_id = data.get('target_user_id')
        offer = data.get('offer')
        
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'webrtc_offer',
                'offer': offer,
                'from_user_id': self.user.id,
                'from_username': self.user.username,
                'target_user_id': target_user_id,
                'from_channel': self.channel_name
            }
        )

    async def handle_answer(self, data):
        target_user_id = data.get('target_user_id')
        answer = data.get('answer')
        
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'webrtc_answer',
                'answer': answer,
                'from_user_id': self.user.id,
                'from_username': self.user.username,
                'target_user_id': target_user_id,
                'from_channel': self.channel_name
            }
        )

    async def handle_ice_candidate(self, data):
        target_user_id = data.get('target_user_id')
        candidate = data.get('candidate')
        
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'webrtc_ice_candidate',
                'candidate': candidate,
                'from_user_id': self.user.id,
                'target_user_id': target_user_id,
                'from_channel': self.channel_name
            }
        )

    async def handle_toggle_video(self, data):
        is_enabled = data.get('is_enabled', True)
        await self.update_participant_video(is_enabled)
        
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'user_video_toggle',
                'user_id': self.user.id,
                'is_enabled': is_enabled
            }
        )

    async def handle_toggle_audio(self, data):
        is_enabled = data.get('is_enabled', True)
        await self.update_participant_audio(is_enabled)
        
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'user_audio_toggle',
                'user_id': self.user.id,
                'is_enabled': is_enabled
            }
        )

    async def send_room_users(self):
        users = await self.get_room_participants()
        await self.send(text_data=json.dumps({
            'type': 'room_users',
            'users': users
        }))

    # WebSocket message handlers
    async def user_joined(self, event):
        if event['channel_name'] != self.channel_name:
            await self.send(text_data=json.dumps({
                'type': 'user_joined',
                'user_id': event['user_id'],
                'username': event['username']
            }))

    async def user_left(self, event):
        if event['channel_name'] != self.channel_name:
            await self.send(text_data=json.dumps({
                'type': 'user_left',
                'user_id': event['user_id'],
                'username': event['username']
            }))

    async def webrtc_offer(self, event):
        if (event.get('target_user_id') == self.user.id or 
            event.get('target_user_id') is None) and \
           event['from_channel'] != self.channel_name:
            await self.send(text_data=json.dumps({
                'type': 'offer',
                'offer': event['offer'],
                'from_user_id': event['from_user_id'],
                'from_username': event['from_username']
            }))

    async def webrtc_answer(self, event):
        if event.get('target_user_id') == self.user.id and \
           event['from_channel'] != self.channel_name:
            await self.send(text_data=json.dumps({
                'type': 'answer',
                'answer': event['answer'],
                'from_user_id': event['from_user_id'],
                'from_username': event['from_username']
            }))

    async def webrtc_ice_candidate(self, event):
        if (event.get('target_user_id') == self.user.id or 
            event.get('target_user_id') is None) and \
           event['from_channel'] != self.channel_name:
            await self.send(text_data=json.dumps({
                'type': 'ice_candidate',
                'candidate': event['candidate'],
                'from_user_id': event['from_user_id']
            }))

    async def user_video_toggle(self, event):
        await self.send(text_data=json.dumps({
            'type': 'user_video_toggle',
            'user_id': event['user_id'],
            'is_enabled': event['is_enabled']
        }))

    async def user_audio_toggle(self, event):
        await self.send(text_data=json.dumps({
            'type': 'user_audio_toggle',
            'user_id': event['user_id'],
            'is_enabled': event['is_enabled']
        }))

    # Database operations
    @database_sync_to_async
    def add_user_to_room(self):
        try:
            room = Room.objects.get(id=self.room_id)
            participant, created = RoomParticipant.objects.get_or_create(
                room=room,
                user=self.user,
                defaults={'is_active': True}
            )
            if not created:
                participant.is_active = True
                participant.save()
        except Room.DoesNotExist:
            logger.error(f"Room {self.room_id} does not exist")

    @database_sync_to_async
    def remove_user_from_room(self):
        try:
            participant = RoomParticipant.objects.get(
                room_id=self.room_id,
                user=self.user,
                is_active=True
            )
            participant.is_active = False
            participant.left_at = timezone.now()
            participant.save()
        except RoomParticipant.DoesNotExist:
            pass

    @database_sync_to_async
    def update_participant_video(self, is_enabled):
        try:
            participant = RoomParticipant.objects.get(
                room_id=self.room_id,
                user=self.user,
                is_active=True
            )
            participant.is_video_enabled = is_enabled
            participant.save()
        except RoomParticipant.DoesNotExist:
            pass

    @database_sync_to_async
    def update_participant_audio(self, is_enabled):
        try:
            participant = RoomParticipant.objects.get(
                room_id=self.room_id,
                user=self.user,
                is_active=True
            )
            participant.is_audio_enabled = is_enabled
            participant.save()
        except RoomParticipant.DoesNotExist:
            pass

    @database_sync_to_async
    def get_room_participants(self):
        try:
            participants = RoomParticipant.objects.filter(
                room_id=self.room_id,
                is_active=True
            ).select_related('user')
            
            return [{
                'user_id': p.user.id,
                'username': p.user.username,
                'is_video_enabled': p.is_video_enabled,
                'is_audio_enabled': p.is_audio_enabled
            } for p in participants]
        except:
            return []