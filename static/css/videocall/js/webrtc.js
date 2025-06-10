class WebRTCManager {
    constructor() {
        this.localStream = null;
        this.peerConnections = new Map();
        this.socket = null;
        this.roomId = null;
        this.username = null;
        this.userId = null;
        this.isVideoEnabled = true;
        this.isAudioEnabled = true;
        this.isScreenSharing = false;
        this.chatManager = null;
        
        // ICE Servers configuration
        this.iceServers = {
            iceServers: [
                { urls: 'stun:stun.l.google.com:19302' },
                { urls: 'stun:stun1.l.google.com:19302' },
                { urls: 'stun:stun2.l.google.com:19302' }
            ]
        };
        
        this.mediaConstraints = {
            video: {
                width: { ideal: 1280 },
                height: { ideal: 720 },
                frameRate: { ideal: 30 }
            },
            audio: {
                echoCancellation: true,
                noiseSuppression: true,
                autoGainControl: true
            }
        };
    }
    
    async initialize(roomId, username, userId) {
        this.roomId = roomId;
        this.username = username;
        this.userId = userId;
        
        try {
            await this.initializeLocalStream();
            this.initializeWebSocket();
            this.setupEventListeners();
            this.initializeChatManager();
            
            // Join room after everything is initialized
            this.joinRoom();
            
        } catch (error) {
            console.error('Error initializing WebRTC:', error);
            this.showError('Failed to initialize camera/microphone. Please check permissions.');
        }
    }
    
    async initializeLocalStream() {
        try {
            this.localStream = await navigator.mediaDevices.getUserMedia(this.mediaConstraints);
            const localVideo = document.getElementById('local-video');
            if (localVideo) {
                localVideo.srcObject = this.localStream;
                localVideo.muted = true; // Prevent echo
            }
            console.log('Local stream initialized');
        } catch (error) {
            console.error('Error accessing media devices:', error);
            // Try with basic constraints if high-quality fails
            try {
                this.mediaConstraints = { video: true, audio: true };
                this.localStream = await navigator.mediaDevices.getUserMedia(this.mediaConstraints);
                const localVideo = document.getElementById('local-video');
                if (localVideo) {
                    localVideo.srcObject = this.localStream;
                    localVideo.muted = true;
                }
            } catch (fallbackError) {
                throw fallbackError;
            }
        }
    }
    
    initializeWebSocket() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws/videocall/${this.roomId}/`;
        
        this.socket = new WebSocket(wsUrl);
        
        this.socket.onopen = () => {
            console.log('WebSocket connected');
            this.updateConnectionStatus('connected');
        };
        
        this.socket.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                this.handleWebSocketMessage(data);
            } catch (error) {
                console.error('Error parsing WebSocket message:', error);
            }
        };
        
        this.socket.onclose = (event) => {
            console.log('WebSocket disconnected:', event.code, event.reason);
            this.updateConnectionStatus('disconnected');
            this.handleDisconnection();
        };
        
        this.socket.onerror = (error) => {
            console.error('WebSocket error:', error);
            this.updateConnectionStatus('error');
        };
    }
    
    handleDisconnection() {
        // Try to reconnect after a delay
        setTimeout(() => {
            if (this.socket.readyState === WebSocket.CLOSED) {
                console.log('Attempting to reconnect...');
                this.initializeWebSocket();
            }
        }, 3000);
    }
    
    joinRoom() {
        this.sendMessage({
            type: 'join_room',
            room_id: this.roomId,
            username: this.username,
            user_id: this.userId
        });
    }
    
    handleWebSocketMessage(data) {
        switch (data.type) {
            case 'user_joined':
                this.handleUserJoined(data);
                break;
            case 'user_left':
                this.handleUserLeft(data);
                break;
            case 'offer':
                this.handleOffer(data);
                break;
            case 'answer':
                this.handleAnswer(data);
                break;
            case 'ice_candidate':
                this.handleIceCandidate(data);
                break;
            case 'room_users':
                this.handleRoomUsers(data);
                break;
            case 'user_video_toggle':
                this.handleVideoToggle(data);
                break;
            case 'user_audio_toggle':
                this.handleAudioToggle(data);
                break;
            case 'chat_message':
                this.handleChatMessage(data);
                break;
            case 'error':
                this.handleError(data);
                break;
            default:
                console.warn('Unknown message type:', data.type);
        }
    }
    
    async handleUserJoined(data) {
        console.log('User joined:', data.username);
        
        if (data.user_id !== this.userId) {
            // Create peer connection for new user
            await this.createPeerConnection(data.user_id, data.username, true);
        }
        
        this.updateParticipantCount();
    }
    
    handleUserLeft(data) {
        console.log('User left:', data.username);
        
        if (data.user_id !== this.userId) {
            // Close peer connection
            if (this.peerConnections.has(data.user_id)) {
                this.peerConnections.get(data.user_id).close();
                this.peerConnections.delete(data.user_id);
            }
            
            // Remove video element
            this.removeVideoElement(data.user_id);
        }
        
        this.updateParticipantCount();
    }
    
    async handleOffer(data) {
        console.log('Received offer from:', data.from_username);
        
        const peerConnection = await this.createPeerConnection(data.from_user_id, data.from_username, false);
        
        try {
            await peerConnection.setRemoteDescription(new RTCSessionDescription(data.offer));
            const answer = await peerConnection.createAnswer();
            await peerConnection.setLocalDescription(answer);
            
            this.sendMessage({
                type: 'answer',
                answer: answer,
                target_user_id: data.from_user_id
            });
        } catch (error) {
            console.error('Error handling offer:', error);
        }
    }
    
    async handleAnswer(data) {
        console.log('Received answer from:', data.from_username);
        
        const peerConnection = this.peerConnections.get(data.from_user_id);
        if (peerConnection) {
            try {
                await peerConnection.setRemoteDescription(new RTCSessionDescription(data.answer));
            } catch (error) {
                console.error('Error handling answer:', error);
            }
        }
    }
    
    async handleIceCandidate(data) {
        const peerConnection = this.peerConnections.get(data.from_user_id);
        if (peerConnection && data.candidate) {
            try {
                await peerConnection.addIceCandidate(new RTCIceCandidate(data.candidate));
            } catch (error) {
                console.error('Error adding ICE candidate:', error);
            }
        }
    }
    
    async handleRoomUsers(data) {
        console.log('Room users:', data.users);
        
        // Create peer connections for existing users
        for (const user of data.users) {
            if (user.user_id !== this.userId) {
                await this.createPeerConnection(user.user_id, user.username, true);
            }
        }
        
        this.updateParticipantCount();
    }
    
    handleVideoToggle(data) {
        this.updateUserVideoStatus(data.user_id, data.is_enabled);
    }
    
    handleAudioToggle(data) {
        this.updateUserAudioStatus(data.user_id, data.is_enabled);
    }
    
    handleChatMessage(data) {
        if (this.chatManager) {
            this.chatManager.addMessage(data.username, data.message, data.timestamp);
        }
    }
    
    handleError(data) {
        console.error('Server error:', data.message);
        this.showError(data.message);
    }
    
    async createPeerConnection(userId, username, shouldCreateOffer) {
        const peerConnection = new RTCPeerConnection(this.iceServers);
        this.peerConnections.set(userId, peerConnection);
        
        // Add local stream tracks
        if (this.localStream) {
            this.localStream.getTracks().forEach(track => {
                peerConnection.addTrack(track, this.localStream);
            });
        }
        
        // Handle remote stream
        peerConnection.ontrack = (event) => {
            console.log('Received remote track from:', username);
            this.handleRemoteStream(userId, username, event.streams[0]);
        };
        
        // Handle ICE candidates
        peerConnection.onicecandidate = (event) => {
            if (event.candidate) {
                this.sendMessage({
                    type: 'ice_candidate',
                    candidate: event.candidate,
                    target_user_id: userId
                });
            }
        };
        
        // Handle connection state changes
        peerConnection.onconnectionstatechange = () => {
            console.log(`Connection state with ${username}:`, peerConnection.connectionState);
            this.updateConnectionStatus(peerConnection.connectionState, userId);
            
            if (peerConnection.connectionState === 'failed') {
                this.handlePeerConnectionFailure(userId, username);
            }
        };
        
        // Handle ICE connection state changes
        peerConnection.oniceconnectionstatechange = () => {
            console.log(`ICE connection state with ${username}:`, peerConnection.iceConnectionState);
        };
        
        // Create offer if needed
        if (shouldCreateOffer) {
            try {
                const offer = await peerConnection.createOffer();
                await peerConnection.setLocalDescription(offer);
                
                this.sendMessage({
                    type: 'offer',
                    offer: offer,
                    target_user_id: userId
                });
            } catch (error) {
                console.error('Error creating offer:', error);
            }
        }
        
        return peerConnection;
    }
    
    async handlePeerConnectionFailure(userId, username) {
        console.log(`Peer connection failed with ${username}, attempting to reconnect...`);
        
        // Close existing connection
        if (this.peerConnections.has(userId)) {
            this.peerConnections.get(userId).close();
            this.peerConnections.delete(userId);
        }
        
        // Try to create new connection
        setTimeout(async () => {
            try {
                await this.createPeerConnection(userId, username, true);
            } catch (error) {
                console.error('Failed to reconnect to peer:', error);
            }
        }, 2000);
    }
    
    handleRemoteStream(userId, username, stream) {
        let videoElement = document.getElementById(`video-${userId}`);
        
        if (!videoElement) {
            videoElement = this.createVideoElement(userId, username);
        }
        
        videoElement.srcObject = stream;
        
        // Update connection status
        this.updateConnectionStatus('connected', userId);
    }
    
    createVideoElement(userId, username) {
        const videoGrid = document.getElementById('video-grid');
        const videoContainer = document.createElement('div');
        videoContainer.className = 'video-container remote-video';
        videoContainer.id = `container-${userId}`;
        
        const video = document.createElement('video');
        video.id = `video-${userId}`;
        video.autoplay = true;
        video.playsInline = true;
        
        const controls = document.createElement('div');
        controls.className = 'video-controls';
        
        const usernameSpan = document.createElement('span');
        usernameSpan.className = 'username';
        usernameSpan.textContent = username;
        
        const statusDiv = document.createElement('div');
        statusDiv.className = 'video-status';
        statusDiv.id = `status-${userId}`;
        
        const connectionStatus = document.createElement('div');
        connectionStatus.className = 'connection-status connecting';
        connectionStatus.id = `connection-${userId}`;
        connectionStatus.textContent = 'Connecting...';
        
        controls.appendChild(usernameSpan);
        controls.appendChild(statusDiv);
        
        videoContainer.appendChild(video);
        videoContainer.appendChild(controls);
        videoContainer.appendChild(connectionStatus);
        
        videoGrid.appendChild(videoContainer);
        
        return video;
    }
    
    removeVideoElement(userId) {
        const videoContainer = document.getElementById(`container-${userId}`);
        if (videoContainer) {
            videoContainer.remove();
        }
    }
    
    updateUserVideoStatus(userId, isEnabled) {
        const statusDiv = document.getElementById(`status-${userId}`);
        if (statusDiv) {
            const videoIcon = statusDiv.querySelector('.video-icon') || document.createElement('i');
            videoIcon.className = `fas ${isEnabled ? 'fa-video' : 'fa-video-slash'} status-icon video-icon ${!isEnabled ? 'muted' : ''}`;
            videoIcon.title = isEnabled ? 'Video On' : 'Video Off';
            
            if (!statusDiv.querySelector('.video-icon')) {
                statusDiv.appendChild(videoIcon);
            }
        }
        
        // Update video element display
        const videoElement = document.getElementById(`video-${userId}`);
        if (videoElement) {
            videoElement.style.display = isEnabled ? 'block' : 'none';
        }
    }
    
    updateUserAudioStatus(userId, isEnabled) {
        const statusDiv = document.getElementById(`status-${userId}`);
        if (statusDiv) {
            const audioIcon = statusDiv.querySelector('.audio-icon') || document.createElement('i');
            audioIcon.className = `fas ${isEnabled ? 'fa-microphone' : 'fa-microphone-slash'} status-icon audio-icon ${!isEnabled ? 'muted' : ''}`;
            audioIcon.title = isEnabled ? 'Audio On' : 'Audio Muted';
            
            if (!statusDiv.querySelector('.audio-icon')) {
                statusDiv.appendChild(audioIcon);
            }
        }
    }
    
    updateConnectionStatus(status, userId = null) {
        if (userId) {
            const connectionStatus = document.getElementById(`connection-${userId}`);
            if (connectionStatus) {
                connectionStatus.className = `connection-status ${status}`;
                
                switch (status) {
                    case 'connected':
                        connectionStatus.textContent = 'Connected';
                        connectionStatus.style.display = 'none';
                        break;
                    case 'connecting':
                        connectionStatus.textContent = 'Connecting...';
                        connectionStatus.style.display = 'block';
                        break;
                    case 'disconnected':
                        connectionStatus.textContent = 'Disconnected';
                        connectionStatus.style.display = 'block';
                        break;
                    case 'failed':
                        connectionStatus.textContent = 'Connection Failed';
                        connectionStatus.style.display = 'block';
                        break;
                    default:
                        connectionStatus.textContent = status.charAt(0).toUpperCase() + status.slice(1);
                        connectionStatus.style.display = 'block';
                }
            }
        } else {
            // Update general connection status
            console.log('General connection status:', status);
            this.updateGeneralConnectionIndicator(status);
        }
    }
    
    updateGeneralConnectionIndicator(status) {
        // Update any general connection indicator in the UI
        const indicator = document.getElementById('connection-indicator');
        if (indicator) {
            indicator.className = `connection-indicator ${status}`;
            indicator.textContent = status.charAt(0).toUpperCase() + status.slice(1);
        }
    }
    
    updateParticipantCount() {
        const count = this.peerConnections.size + 1; // +1 for local user
        const participantCount = document.getElementById('participant-count');
        if (participantCount) {
            participantCount.textContent = `${count} participant${count !== 1 ? 's' : ''}`;
        }
    }
    
    sendMessage(message) {
        if (this.socket && this.socket.readyState === WebSocket.OPEN) {
            this.socket.send(JSON.stringify(message));
        } else {
            console.warn('WebSocket not connected, message not sent:', message);
        }
    }
    
    setupEventListeners() {
        // Video toggle
        const toggleVideoBtn = document.getElementById('toggle-video');
        if (toggleVideoBtn) {
            toggleVideoBtn.addEventListener('click', () => this.toggleVideo());
        }
        
        // Audio toggle
        const toggleAudioBtn = document.getElementById('toggle-audio');
        if (toggleAudioBtn) {
            toggleAudioBtn.addEventListener('click', () => this.toggleAudio());
        }
        
        // Screen share
        const shareScreenBtn = document.getElementById('share-screen');
        if (shareScreenBtn) {
            shareScreenBtn.addEventListener('click', () => this.toggleScreenShare());
        }
        
        // Leave room
        const leaveRoomBtn = document.getElementById('leave-room');
        if (leaveRoomBtn) {
            leaveRoomBtn.addEventListener('click', () => this.leaveRoom());
        }
        
        // Copy room ID
        const copyRoomIdBtn = document.getElementById('copy-room-id');
        if (copyRoomIdBtn) {
            copyRoomIdBtn.addEventListener('click', () => this.copyRoomId());
        }
        
        // Prevent page unload without warning
        window.addEventListener('beforeunload', (event) => {
            if (this.peerConnections.size > 0) {
                event.preventDefault();
                event.returnValue = 'Are you sure you want to leave the call?';
                return event.returnValue;
            }
        });
        
        // Handle page visibility changes
        document.addEventListener('visibilitychange', () => {
            if (document.hidden) {
                console.log('Page hidden');
            } else {
                console.log('Page visible');
            }
        });
    }
    
    initializeChatManager() {
        this.chatManager = new ChatManager(this);
    }
    
    toggleVideo() {
        this.isVideoEnabled = !this.isVideoEnabled;
        
        if (this.localStream) {
            const videoTrack = this.localStream.getVideoTracks()[0];
            if (videoTrack) {
                videoTrack.enabled = this.isVideoEnabled;
            }
        }
        
        this.updateVideoButton();
        this.broadcastVideoToggle();
    }
    
    toggleAudio() {
        this.isAudioEnabled = !this.isAudioEnabled;
        
        if (this.localStream) {
            const audioTrack = this.localStream.getAudioTracks()[0];
            if (audioTrack) {
                audioTrack.enabled = this.isAudioEnabled;
            }
        }
        
        this.updateAudioButton();
        this.broadcastAudioToggle();
    }
    
    async toggleScreenShare() {
        if (!this.isScreenSharing) {
            try {
                const screenStream = await navigator.mediaDevices.getDisplayMedia({
                    video: true,
                    audio: true
                });
                
                // Replace video track in all peer connections
                const videoTrack = screenStream.getVideoTracks()[0];
                
                this.peerConnections.forEach(peerConnection => {
                    const sender = peerConnection.getSenders().find(s => 
                        s.track && s.track.kind === 'video'
                    );
                    if (sender) {
                        sender.replaceTrack(videoTrack);
                    }
                });
                
                // Update local video
                const localVideo = document.getElementById('local-video');
                if (localVideo) {
                    localVideo.srcObject = screenStream;
                }
                
                // Handle screen share end
                videoTrack.onended = () => {
                    this.stopScreenShare();
                };
                
                this.isScreenSharing = true;
                this.updateScreenShareButton();
                
            } catch (error) {
                console.error('Error starting screen share:', error);
                this.showError('Failed to start screen sharing');
            }
        } else {
            this.stopScreenShare();
        }
    }
    
    async stopScreenShare() {
        try {
            // Get camera stream back
            const cameraStream = await navigator.mediaDevices.getUserMedia(this.mediaConstraints);
            const videoTrack = cameraStream.getVideoTracks()[0];
            
            // Replace screen share track with camera track
            this.peerConnections.forEach(peerConnection => {
                const sender = peerConnection.getSenders().find(s => 
                    s.track && s.track.kind === 'video'
                );
                if (sender) {
                    sender.replaceTrack(videoTrack);
                }
            });
            
            // Update local stream
            this.localStream.getVideoTracks().forEach(track => track.stop());
            this.localStream.removeTrack(this.localStream.getVideoTracks()[0]);
            this.localStream.addTrack(videoTrack);
            
            // Update local video
            const localVideo = document.getElementById('local-video');
            if (localVideo) {
                localVideo.srcObject = this.localStream;
            }
            
            this.isScreenSharing = false;
            this.updateScreenShareButton();
            
        } catch (error) {
            console.error('Error stopping screen share:', error);
        }
    }
    
    updateVideoButton() {
        const btn = document.getElementById('toggle-video');
        const icon = btn?.querySelector('i');
        
        if (btn && icon) {
            if (this.isVideoEnabled) {
                btn.classList.add('active');
                icon.className = 'fas fa-video';
                btn.title = 'Turn off camera';
            } else {
                btn.classList.remove('active');
                icon.className = 'fas fa-video-slash';
                btn.title = 'Turn on camera';
            }
        }
    }
    
    updateAudioButton() {
        const btn = document.getElementById('toggle-audio');
        const icon = btn?.querySelector('i');
        
        if (btn && icon) {
            if (this.isAudioEnabled) {
                btn.classList.add('active');
                icon.className = 'fas fa-microphone';
                btn.title = 'Mute microphone';
            } else {
                btn.classList.remove('active');
                icon.className = 'fas fa-microphone-slash';
                btn.title = 'Unmute microphone';
            }
        }
    }
    
    updateScreenShareButton() {
        const btn = document.getElementById('share-screen');
        const icon = btn?.querySelector('i');
        
        if (btn && icon) {
            if (this.isScreenSharing) {
                btn.classList.add('active');
                icon.className = 'fas fa-stop';
                btn.title = 'Stop sharing';
            } else {
                btn.classList.remove('active');
                icon.className = 'fas fa-desktop';
                btn.title = 'Share screen';
            }
        }
    }
    
    broadcastVideoToggle() {
        this.sendMessage({
            type: 'video_toggle',
            is_enabled: this.isVideoEnabled
        });
    }
    
    broadcastAudioToggle() {
        this.sendMessage({
            type: 'audio_toggle',
            is_enabled: this.isAudioEnabled
        });
    }
    
    copyRoomId() {
        if (navigator.clipboard) {
            navigator.clipboard.writeText(this.roomId).then(() => {
                this.showSuccess('Room ID copied to clipboard');
            }).catch(() => {
                this.fallbackCopyToClipboard(this.roomId);
            });
        } else {
            this.fallbackCopyToClipboard(this.roomId);
        }
    }
    
    fallbackCopyToClipboard(text) {
        const textArea = document.createElement('textarea');
        textArea.value = text;
        document.body.appendChild(textArea);
        textArea.focus();
        textArea.select();
        
        try {
            document.execCommand('copy');
            this.showSuccess('Room ID copied to clipboard');
        } catch (error) {
            this.showError('Failed to copy room ID');
        }
        
        document.body.removeChild(textArea);
    }
    
    leaveRoom() {
        if (confirm('Are you sure you want to leave the room?')) {
            this.cleanup();
            
            // Redirect to room list or home
            window.location.href = '/videocall/rooms/';
        }
    }
    
    cleanup() {
        // Close all peer connections
        this.peerConnections.forEach(peerConnection => {
            peerConnection.close();
        });
        this.peerConnections.clear();
        
        // Stop local stream
        if (this.localStream) {
            this.localStream.getTracks().forEach(track => {
                track.stop();
            });
        }
        
        // Close WebSocket
        if (this.socket) {
            this.sendMessage({
                type: 'leave_room',
                room_id: this.roomId,
                user_id: this.userId
            });
            this.socket.close();
        }
    }
    
    showError(message) {
        this.showNotification(message, 'error');
    }
    
    showSuccess(message) {
        this.showNotification(message, 'success');
    }
    
    showNotification(message, type = 'info') {
        // Create notification element
        const notification = document.createElement('div');
        notification.className = `notification ${type}`;
        notification.textContent = message;
        
        // Add to page
        document.body.appendChild(notification);
        
        // Auto remove after 3 seconds
        setTimeout(() => {
            if (notification.parentNode) {
                notification.parentNode.removeChild(notification);
            }
        }, 3000);
    }
}

// // Chat Manager Class
// class ChatManager {
//     constructor(webrtcManager) {
//         this.webrtcManager = webrtcManager;
//         this.chatPanel = document.getElementById('chat-panel');
//         this.chatMessages = document.getElementById('chat-messages');
//         this.messageInput = document.getElementById('message-input');
//         this.sendButton = document.getElementById('send-message');
//         this.toggleButton = document.getElementById('toggle-chat');
//         this.closeButton = document.getElementById('close-chat');
        
//         this.setupEventListeners();
//     }
    
//     setupEventListeners() {
//         if (this.sendButton) {
//             this.sendButton.addEventListener('click', () => this.sendMessage());
//         }
        
//         if (this.messageInput) {
//             this.messageInput.addEventListener('keypress', (e) => {
//                 if (e.key === 'Enter' && !e.shiftKey) {
//                     e.preventDefault();
//                     this.sendMessage();
//                 }
//             });
//         }
        
//         if (this.toggleButton) {
//             this.toggleButton.addEventListener('click', () => this.toggleChat());
//         }
        
//         if (this.closeButton) {
//             this.closeButton.addEventListener('click', () => this.toggleChat());
//         }
//     }
    
//     sendMessage() {
//         const message = this.messageInput?.value.trim();
//         if (message && this.webrtcManager.socket) {
//             this.webrtcManager.sendMessage({
//                 type: 'chat_message',
//                 message: message,
//                 room_id: this.webrtcManager.roomId,
//                 username: this.webrtcManager.username
//             });
            
//             this.messageInput.value = '';
//         }
//     }
    
//     addMessage(username, message, timestamp) {
//         if (!this.chatMessages) return;
        
//         const messageElement = document.createElement('div');
//         messageElement.className = 'chat-message';
        
//         const isOwn = username === this.webrtcManager.username;
//         if (isOwn) {
//             messageElement.classList.add('own-message');
//         }
        
//         const time = new Date(timestamp).toLocaleTimeString([], {
//             hour: '2-digit',
//             minute: '2-digit'
//         });
        
//         messageElement.innerHTML = `
//             <div class="message-header">
//                 <span class="username">${username}</span>
//                 <span class="timestamp">${time}</span>
//             </div>
//             <div class="message-content">${this.escapeHtml(message)}</div>
//         `;
        
//         this.chatMessages.appendChild(messageElement);
//         this.chatMessages.scrollTop = this.chatMessages.scrollHeight;
        
//         // Show notification if chat is closed
//         if (!this.chatPanel?.classList.contains('active')) {
//             this.showNewMessageNotification();
//         }
//     }
    
//     toggleChat() {
//         if (this.chatPanel) {
//             this.chatPanel.classList.toggle('active');
            
//             // Clear notification when opening chat
//             if (this.chatPanel.classList.contains('active')) {
//                 this.clearNewMessageNotification();
//                 if (this.messageInput) {
//                     this.messageInput.focus();
//                 }
//             }
//         }
//     }
    
//     showNewMessageNotification() {
//         const toggleButton = this.toggleButton;
//         if (toggleButton) {
//             toggleButton.classList.add('has-notification');
//         }
//     }
    
//     clearNewMessageNotification() {
//         const toggleButton = this.toggleButton;
//         if (toggleButton) {
//             toggleButton.classList.remove('has-notification');
//         }
//     }
    
//     escapeHtml(unsafe) {
//         return unsafe
//             .replace(/&/g, "&amp;")
//             .replace(/</g, "&lt;")
//             .replace(/>/g, "&gt;")
//             .replace(/"/