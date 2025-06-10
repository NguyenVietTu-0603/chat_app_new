import json
import base64
from channels.generic.websocket import AsyncWebsocketConsumer
from django.contrib.auth.models import User
from .models import ChatGroup, GroupMessage, PrivateMessage, PrivateChat
from asgiref.sync import sync_to_async
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage

class ChatroomConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.group_name = self.scope['url_route']['kwargs']['chatroom_name']
        self.room_group_name = f'chat_{self.group_name}'

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data):
        data = json.loads(text_data)
        message = data['message']
        username = data['username']

        user = await sync_to_async(User.objects.get)(username=username)
        group = await sync_to_async(ChatGroup.objects.get)(group_name=self.group_name)
        new_message = await sync_to_async(GroupMessage.objects.create)(
            group=group, author=user, body=message
        )

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message',
                'message': message,
                'username': username
            }
        )

    async def chat_message(self, event):
        message = event['message']
        username = event['username']

        await self.send(text_data=json.dumps({
            'message': message,
            'username': username
        }))

class PrivateChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope["user"]
        self.other_username = self.scope["url_route"]["kwargs"]["other_username"].split("_", 1)[1]

        if not self.user.is_authenticated:
            await self.close()
            return

        self.room_group_name = f"private_chat_{min(self.user.username, self.other_username)}_{max(self.user.username, self.other_username)}"
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data):
        data = json.loads(text_data)

        msg_type = data.get("type", "text")
        message = data.get("message", "")
        file_url = ""
        is_image = False
        is_video = False

        sender = self.user
        receiver = await self.get_user(self.other_username)

        if msg_type in ["image", "video", "file"]:
            raw_data = data.get("data", "")
            filename = data.get("filename", "file")

            if raw_data:
                format, base64_data = raw_data.split(";base64,", 1)
                decoded_file = ContentFile(base64.b64decode(base64_data), name=filename)

                file_path = f"private_chat_files/{filename}"
                saved_path = default_storage.save(file_path, decoded_file)
                file_url = f"/private_chat_files/{filename}"

                # Xác định loại file
                if msg_type == "video" or format.startswith("data:video"):
                    is_video = True
                    msg_type = "video"
                elif msg_type == "image" or format.startswith("data:image"):
                    try:
                        from PIL import Image
                        with default_storage.open(saved_path, 'rb') as f:
                            img = Image.open(f)
                            img.verify()
                        is_image = True
                        msg_type = "image"
                    except Exception:
                        is_image = False
                        msg_type = "file"
                else:
                    msg_type = "file"

        if receiver:
            chat = await self.get_or_create_private_chat(sender, receiver)

            # Tạo body tin nhắn dựa trên loại file
            message_body = message
            if not message and msg_type != "text":
                if msg_type == "image":
                    message_body = "[Hình ảnh]"
                elif msg_type == "video":
                    message_body = "[Video]"
                elif msg_type == "file":
                    message_body = f"[Tệp: {filename}]"

            new_message = await self.save_message(
                chat, 
                sender, 
                message_body, 
                file_url if msg_type != "text" else None, 
                is_image,
                is_video
            )

            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "chat_message",
                    "username": sender.username,
                    "realname": await sync_to_async(lambda: sender.profile.realname)(),
                    "message": message_body,
                    "file_url": file_url,
                    "msg_type": msg_type,
                    "filename": data.get("filename", "") if msg_type != "text" else "",
                    "timestamp": str(new_message.created),
                }
            )

    async def chat_message(self, event):
        await self.send(text_data=json.dumps(event))

    @staticmethod
    async def get_user(username):
        try:
            return await sync_to_async(User.objects.get)(username=username)
        except User.DoesNotExist:
            return None

    @staticmethod
    async def get_or_create_private_chat(user1, user2):
        chat, created = await sync_to_async(PrivateChat.objects.get_or_create)(
            user1=max(user1, user2, key=lambda u: u.username),
            user2=min(user1, user2, key=lambda u: u.username),
        )
        return chat

    @staticmethod
    async def save_message(chat, sender, message, file_url=None, is_image=False, is_video=False):
        new_message = await sync_to_async(PrivateMessage.objects.create)(
            chat=chat,
            sender=sender,
            body=message,
            file=file_url if file_url else None,
            is_image=is_image if file_url else False,
            is_video=is_video if file_url else False,
        )
        return new_message
    async def video_call_message(self, event):
        message = event['message']

        # Send message to WebSocket
        await self.send(text_data=json.dumps({
            'message': message
        }))
class VideoCallConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_name = self.scope['url_route']['kwargs']['room_name']
        self.room_group_name = f'video_call_{self.room_name}'
        
        print(f"VideoCall connecting to room: {self.room_group_name}")
        
        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.accept()
        
        # Notify others that user joined
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'user_status',
                'action': 'joined',
                'user': getattr(self.scope.get('user'), 'username', 'Anonymous')
            }
        )
        
        print(f"VideoCall connected: {self.channel_name}")

    async def disconnect(self, close_code):
        print(f"VideoCall disconnecting: {self.channel_name}")
        
        # Notify others that user left
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'user_status', 
                'action': 'left',
                'user': getattr(self.scope.get('user'), 'username', 'Anonymous')
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
            print(f"VideoCall received: {data.get('type', 'unknown')}")
            
            # Forward signaling messages to all room members
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'signaling_message',
                    'data': data,
                    'sender': self.channel_name
                }
            )
        except json.JSONDecodeError as e:
            print(f"VideoCall JSON decode error: {e}")
        except Exception as e:
            print(f"VideoCall receive error: {e}")

    async def signaling_message(self, event):
        data = event['data']
        sender = event['sender']
        
        # Don't send message back to sender
        if sender != self.channel_name:
            await self.send(text_data=json.dumps(data))

    async def user_status(self, event):
        # Send user status to frontend
        await self.send(text_data=json.dumps({
            'type': f"user-{event['action']}",
            'user': event['user']
        }))
        
class NotifyConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.username = self.scope['url_route']['kwargs']['username']
        self.group_name = f'notify_{self.username}'
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data):
        pass  # Không cần nhận gì từ client

    async def notify(self, event):
        await self.send(text_data=json.dumps(event['data']))