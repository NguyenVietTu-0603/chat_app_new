// video-call.js - Fixed version with debugging
class VideoCallManager {
    constructor() {
        this.localStream = null;
        this.remoteStream = null;
        this.peerConnection = null;
        this.socket = null;
        this.isCallActive = false;
        this.isMuted = false;
        this.isCameraOff = false;
        this.isScreenSharing = false;
        this.callStartTime = null;
        this.callDurationInterval = null;
        this.isInitiator = false; // Track who initiates the call
        
        // DOM elements
        this.localVideo = document.getElementById('localVideo');
        this.remoteVideo = document.getElementById('remoteVideo');
        this.loadingOverlay = document.getElementById('loadingOverlay');
        this.noVideoMessage = document.getElementById('noVideoMessage');
        this.callerName = document.getElementById('callerName');
        this.callerAvatar = document.getElementById('callerAvatar');
        this.callStatus = document.getElementById('callStatus');
        this.callDuration = document.getElementById('callDuration');
        this.statusIndicator = document.getElementById('statusIndicator');
        this.connectionText = document.getElementById('connectionText');
        this.chatSidebar = document.getElementById('chatSidebar');
        this.chatMessages = document.getElementById('chatMessages');
        this.chatInput = document.getElementById('chatInput');
        
        // Control buttons
        this.muteBtn = document.getElementById('muteBtn');
        this.cameraBtn = document.getElementById('cameraBtn');
        this.endCallBtn = document.getElementById('endCallBtn');
        this.chatBtn = document.getElementById('chatBtn');
        this.shareBtn = document.getElementById('shareBtn');
        this.closeChatBtn = document.getElementById('closeChatBtn');
        this.chatSendBtn = document.getElementById('chatSendBtn');
        
        // WebRTC configuration
        this.rtcConfiguration = {
            iceServers: [
                { urls: 'stun:stun.l.google.com:19302' },
                { urls: 'stun:stun1.l.google.com:19302' },
                { urls: 'stun:stun2.l.google.com:19302' }
            ]
        };
        
        // Debug logging
        this.enableDebugLogging();
        
        this.init();
    }
    
    enableDebugLogging() {
        console.log('=== VIDEO CALL DEBUG MODE ===');
        console.log('Current URL:', window.location.href);
        console.log('Current user:', this.getCurrentUser());
        console.log('Other user:', this.getOtherUser());
    }
    
    async init() {
        try {
            console.log('Initializing VideoCallManager...');
            
            // Check if we're the initiator (first to load)
            this.isInitiator = new URLSearchParams(window.location.search).get('initiator') === 'true';
            console.log('Is initiator:', this.isInitiator);
            
            // Initialize WebSocket connection
            this.initWebSocket();
            
            // Set up event listeners
            this.setupEventListeners();
            
            // Initialize media devices
            await this.initializeMedia();
            
            // Hide loading overlay
            this.hideLoading();
            
            // Wait a bit for socket connection, then handle call logic
            setTimeout(() => {
                if (this.isInitiator) {
                    console.log('Starting call as initiator...');
                    this.startCall();
                } else {
                    console.log('Waiting for call as receiver...');
                    this.waitForCall();
                }
            }, 1000);
            
        } catch (error) {
            console.error('Initialization error:', error);
            this.handleError('Không thể khởi tạo cuộc gọi video: ' + error.message);
        }
    }
    
    initWebSocket() {
        const currentUser = this.getCurrentUser();
        const otherUser = this.getOtherUser();
        
        // Create consistent room name (alphabetical order)
        const users = [currentUser, otherUser].sort();
        const roomName = `${users[0]}_${users[1]}`;
        
        console.log('Connecting to room:', roomName);
        
        const protocol = window.location.protocol === 'https:' ? 'wss://' : 'ws://';
        const wsUrl = `${protocol}${window.location.host}/ws/video-call/${roomName}/`;
        console.log('WebSocket URL:', wsUrl);
        
        this.socket = new WebSocket(wsUrl);
        
        this.socket.onopen = () => {
            console.log('WebSocket connected successfully');
            this.updateConnectionStatus('connected', 'Đã kết nối');
            
            // Send user info
            this.sendSignalingMessage({
                type: 'user-info',
                user: currentUser,
                avatar: this.getUserAvatar(currentUser)
            });
        };
        
        this.socket.onmessage = (event) => {
            console.log('WebSocket message received:', event.data);
            const data = JSON.parse(event.data);
            this.handleWebSocketMessage(data);
        };
        
        this.socket.onclose = (event) => {
            console.log('WebSocket disconnected:', event.code, event.reason);
            this.updateConnectionStatus('disconnected', 'Mất kết nối');
        };
        
        this.socket.onerror = (error) => {
            console.error('WebSocket error:', error);
            this.updateConnectionStatus('disconnected', 'Lỗi kết nối');
        };
    }
    
    setupEventListeners() {
        // Control buttons
        if (this.muteBtn) this.muteBtn.addEventListener('click', () => this.toggleMute());
        if (this.cameraBtn) this.cameraBtn.addEventListener('click', () => this.toggleCamera());
        if (this.endCallBtn) this.endCallBtn.addEventListener('click', () => this.endCall());
        if (this.chatBtn) this.chatBtn.addEventListener('click', () => this.toggleChat());
        if (this.shareBtn) this.shareBtn.addEventListener('click', () => this.toggleScreenShare());
        if (this.closeChatBtn) this.closeChatBtn.addEventListener('click', () => this.closeChat());
        if (this.chatSendBtn) this.chatSendBtn.addEventListener('click', () => this.sendChatMessage());
        
        // Chat input
        if (this.chatInput) {
            this.chatInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') {
                    this.sendChatMessage();
                }
            });
        }
        
        // Handle page visibility change
        document.addEventListener('visibilitychange', () => {
            if (document.hidden) {
                this.handlePageHidden();
            } else {
                this.handlePageVisible();
            }
        });
        
        // Handle before unload
        window.addEventListener('beforeunload', () => {
            this.cleanup();
        });
    }
    
    async initializeMedia() {
        try {
            console.log('Requesting user media...');
            
            // Get user media with fallback options
            const constraints = {
                video: {
                    width: { ideal: 1280, max: 1920 },
                    height: { ideal: 720, max: 1080 },
                    facingMode: 'user'
                },
                audio: {
                    echoCancellation: true,
                    noiseSuppression: true,
                    autoGainControl: true
                }
            };
            
            this.localStream = await navigator.mediaDevices.getUserMedia(constraints);
            console.log('Local stream obtained:', this.localStream);
            console.log('Video tracks:', this.localStream.getVideoTracks().length);
            console.log('Audio tracks:', this.localStream.getAudioTracks().length);
            
            if (this.localVideo) {
                this.localVideo.srcObject = this.localStream;
                this.localVideo.muted = true; // Prevent echo
                await this.localVideo.play();
                console.log('Local video playing');
            }
            
            // Initialize peer connection
            this.initializePeerConnection();
            
        } catch (error) {
            console.error('Media initialization error:', error);
            this.handleMediaError(error);
        }
    }
    
    initializePeerConnection() {
        console.log('Initializing peer connection...');
        this.peerConnection = new RTCPeerConnection(this.rtcConfiguration);
        
        // Add local stream to peer connection
        if (this.localStream) {
            this.localStream.getTracks().forEach(track => {
                console.log('Adding track to peer connection:', track.kind);
                this.peerConnection.addTrack(track, this.localStream);
            });
        }
        
        // Handle remote stream
        this.peerConnection.ontrack = (event) => {
            console.log('Remote track received:', event.track.kind);
            console.log('Remote streams:', event.streams.length);
            
            if (event.streams.length > 0) {
                this.remoteStream = event.streams[0];
                console.log('Setting remote stream to video element');
                
                if (this.remoteVideo) {
                    this.remoteVideo.srcObject = this.remoteStream;
                    this.remoteVideo.play().then(() => {
                        console.log('Remote video playing');
                        this.hideNoVideoMessage();
                    }).catch(err => {
                        console.error('Error playing remote video:', err);
                    });
                }
            }
        };
        
        // Handle ICE candidates
        this.peerConnection.onicecandidate = (event) => {
            if (event.candidate) {
                console.log('Sending ICE candidate:', event.candidate.type);
                this.sendSignalingMessage({
                    type: 'ice-candidate',
                    candidate: event.candidate
                });
            } else {
                console.log('ICE candidate gathering completed');
            }
        };
        
        // Handle connection state changes
        this.peerConnection.onconnectionstatechange = () => {
            const state = this.peerConnection.connectionState;
            console.log('Peer connection state changed to:', state);
            
            switch (state) {
                case 'connected':
                    this.updateConnectionStatus('connected', 'Đã kết nối');
                    if (this.callStatus) this.callStatus.textContent = 'Đang trong cuộc gọi';
                    break;
                case 'disconnected':
                case 'failed':
                    this.updateConnectionStatus('disconnected', 'Mất kết nối');
                    if (this.callStatus) this.callStatus.textContent = 'Mất kết nối';
                    break;
                case 'connecting':
                    this.updateConnectionStatus('connecting', 'Đang kết nối');
                    break;
            }
        };
        
        // Handle ICE connection state
        this.peerConnection.oniceconnectionstatechange = () => {
            console.log('ICE connection state:', this.peerConnection.iceConnectionState);
        };
        
        // Handle ICE gathering state
        this.peerConnection.onicegatheringstatechange = () => {
            console.log('ICE gathering state:', this.peerConnection.iceGatheringState);
        };
    }
    
    async startCall() {
        try {
            console.log('Starting call...');
            this.isCallActive = true;
            this.callStartTime = Date.now();
            this.startCallDurationTimer();
            
            // Create and send offer
            console.log('Creating offer...');
            const offer = await this.peerConnection.createOffer({
                offerToReceiveAudio: true,
                offerToReceiveVideo: true
            });
            
            console.log('Setting local description...');
            await this.peerConnection.setLocalDescription(offer);
            
            console.log('Sending offer through WebSocket...');
            this.sendSignalingMessage({
                type: 'offer',
                offer: offer
            });
            
            this.updateConnectionStatus('connecting', 'Đang gọi...');
            
        } catch (error) {
            console.error('Error starting call:', error);
            this.handleError('Không thể bắt đầu cuộc gọi: ' + error.message);
        }
    }
    
    waitForCall() {
        console.log('Waiting for incoming call...');
        this.updateConnectionStatus('waiting', 'Đang chờ cuộc gọi...');
        if (this.callStatus) this.callStatus.textContent = 'Đang chờ cuộc gọi...';
    }
    
    async handleWebSocketMessage(data) {
        try {
            console.log('Handling WebSocket message type:', data.type);
            
            switch (data.type) {
                case 'offer':
                    await this.handleOffer(data.offer);
                    break;
                case 'answer':
                    await this.handleAnswer(data.answer);
                    break;
                case 'ice-candidate':
                    await this.handleIceCandidate(data.candidate);
                    break;
                case 'chat-message':
                    this.handleChatMessage(data);
                    break;
                case 'call-ended':
                    this.handleRemoteCallEnd();
                    break;
                case 'user-info':
                    this.handleUserInfo(data);
                    break;
                case 'user-joined':
                    this.handleUserJoined(data);
                    break;
                case 'user-left':
                    this.handleUserLeft(data);
                    break;
                default:
                    console.log('Unknown message type:', data.type);
            }
        } catch (error) {
            console.error('Error handling WebSocket message:', error);
        }
    }
    
    async handleOffer(offer) {
        try {
            console.log('Handling offer...');
            
            if (!this.isCallActive) {
                this.isCallActive = true;
                this.callStartTime = Date.now();
                this.startCallDurationTimer();
            }
            
            console.log('Setting remote description...');
            await this.peerConnection.setRemoteDescription(new RTCSessionDescription(offer));
            
            console.log('Creating answer...');
            const answer = await this.peerConnection.createAnswer({
                offerToReceiveAudio: true,
                offerToReceiveVideo: true
            });
            
            console.log('Setting local description with answer...');
            await this.peerConnection.setLocalDescription(answer);
            
            console.log('Sending answer...');
            this.sendSignalingMessage({
                type: 'answer',
                answer: answer
            });
            
            this.updateConnectionStatus('connecting', 'Đang kết nối...');
            
        } catch (error) {
            console.error('Error handling offer:', error);
            this.handleError('Lỗi xử lý cuộc gọi đến: ' + error.message);
        }
    }
    
    async handleAnswer(answer) {
        try {
            console.log('Handling answer...');
            await this.peerConnection.setRemoteDescription(new RTCSessionDescription(answer));
            console.log('Remote description set successfully');
        } catch (error) {
            console.error('Error handling answer:', error);
            this.handleError('Lỗi xử lý phản hồi: ' + error.message);
        }
    }
    
    async handleIceCandidate(candidate) {
        try {
            console.log('Adding ICE candidate:', candidate.type);
            await this.peerConnection.addIceCandidate(new RTCIceCandidate(candidate));
            console.log('ICE candidate added successfully');
        } catch (error) {
            console.error('Error adding ICE candidate:', error);
            // Don't show error to user for ICE candidate failures
        }
    }
    
    handleUserInfo(data) {
        console.log('User info received:', data);
        if (this.callerName && data.user) {
            this.callerName.textContent = data.user;
        }
        if (this.callerAvatar && data.avatar) {
            this.callerAvatar.src = data.avatar;
        }
    }
    
    // Continue with remaining methods...
    toggleMute() {
        this.isMuted = !this.isMuted;
        console.log('Toggle mute:', this.isMuted);
        
        if (this.localStream) {
            const audioTrack = this.localStream.getAudioTracks()[0];
            if (audioTrack) {
                audioTrack.enabled = !this.isMuted;
            }
        }
        
        // Update button appearance
        if (this.muteBtn) {
            if (this.isMuted) {
                this.muteBtn.classList.add('muted');
                this.muteBtn.innerHTML = '<i class="fas fa-microphone-slash"></i>';
                this.muteBtn.title = 'Bật micro';
            } else {
                this.muteBtn.classList.remove('muted');
                this.muteBtn.innerHTML = '<i class="fas fa-microphone"></i>';
                this.muteBtn.title = 'Tắt micro';
            }
        }
        
        // Notify other user
        this.sendSignalingMessage({
            type: 'audio-toggle',
            muted: this.isMuted
        });
    }
    
    toggleCamera() {
        this.isCameraOff = !this.isCameraOff;
        console.log('Toggle camera:', this.isCameraOff);
        
        if (this.localStream) {
            const videoTrack = this.localStream.getVideoTracks()[0];
            if (videoTrack) {
                videoTrack.enabled = !this.isCameraOff;
            }
        }
        
        // Update button appearance
        if (this.cameraBtn) {
            if (this.isCameraOff) {
                this.cameraBtn.classList.add('off');
                this.cameraBtn.innerHTML = '<i class="fas fa-video-slash"></i>';
                this.cameraBtn.title = 'Bật camera';
                this.showNoVideoMessage();
            } else {
                this.cameraBtn.classList.remove('off');
                this.cameraBtn.innerHTML = '<i class="fas fa-video"></i>';
                this.cameraBtn.title = 'Tắt camera';
                this.hideNoVideoMessage();
            }
        }
        
        // Notify other user
        this.sendSignalingMessage({
            type: 'video-toggle',
            cameraOff: this.isCameraOff
        });
    }
    
    sendSignalingMessage(data) {
        if (this.socket && this.socket.readyState === WebSocket.OPEN) {
            console.log('Sending signaling message:', data.type);
            this.socket.send(JSON.stringify(data));
        } else {
            console.error('WebSocket not connected, cannot send message:', data.type);
        }
    }
    
    getCurrentUser() {
        const urlParams = new URLSearchParams(window.location.search);
        const pathParts = window.location.pathname.split('/');
        return urlParams.get('user') || pathParts[pathParts.length - 2] || 'user1';
    }
    
    getOtherUser() {
        const urlParams = new URLSearchParams(window.location.search);
        return urlParams.get('other') || 'user2';
    }
    
    getUserAvatar(username) {
        // Return default avatar or fetch from somewhere
        return `/static/images/avatars/${username}.jpg`;
    }
    
    updateConnectionStatus(status, text) {
        if (this.statusIndicator) {
            this.statusIndicator.className = `status-indicator ${status}`;
        }
        if (this.connectionText) {
            this.connectionText.textContent = text;
        }
        console.log('Connection status updated:', status, text);
    }
    
    hideLoading() {
        if (this.loadingOverlay) {
            this.loadingOverlay.style.display = 'none';
        }
    }
    
    showNoVideoMessage() {
        if (this.noVideoMessage) {
            this.noVideoMessage.style.display = 'flex';
        }
    }
    
    hideNoVideoMessage() {
        if (this.noVideoMessage) {
            this.noVideoMessage.style.display = 'none';
        }
    }
    
    handleError(message) {
        console.error('VideoCall Error:', message);
        if (this.callStatus) this.callStatus.textContent = message;
        this.updateConnectionStatus('error', 'Có lỗi xảy ra');
        alert(message); // Simple error display
    }
    
    handleMediaError(error) {
        let errorMessage = 'Không thể truy cập camera/microphone';
        
        if (error.name === 'NotAllowedError') {
            errorMessage = 'Vui lòng cho phép truy cập camera và microphone';
        } else if (error.name === 'NotFoundError') {
            errorMessage = 'Không tìm thấy camera hoặc microphone';  
        } else if (error.name === 'NotReadableError') {
            errorMessage = 'Camera hoặc microphone đang được sử dụng';
        }
        
        this.handleError(errorMessage);
    }
    
    startCallDurationTimer() {
        this.callDurationInterval = setInterval(() => {
            if (this.callStartTime && this.callDuration) {
                const duration = Date.now() - this.callStartTime;
                const minutes = Math.floor(duration / 60000);
                const seconds = Math.floor((duration % 60000) / 1000);
                this.callDuration.textContent = `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
            }
        }, 1000);
    }
    
    endCall() {
        console.log('Ending call...');
        this.sendSignalingMessage({ type: 'call-ended' });
        this.cleanup();
        this.redirectToChat();
    }
    
    cleanup() {
        console.log('Cleaning up...');
        
        if (this.callDurationInterval) {
            clearInterval(this.callDurationInterval);
        }
        
        if (this.peerConnection) {
            this.peerConnection.close();
        }
        
        if (this.localStream) {
            this.localStream.getTracks().forEach(track => track.stop());
        }
        
        if (this.socket) {
            this.socket.close();
        }
        
        this.isCallActive = false;
    }
    
    redirectToChat() {
        // Go back to previous page or chat
        if (document.referrer) {
            window.location.href = document.referrer;
        } else {
            window.location.href = '/chat/';
        }
    }
    
    // Stub methods for missing functionality
    toggleChat() {
        if (this.chatSidebar) {
            this.chatSidebar.classList.toggle('open');
        }
    }
    
    closeChat() {
        if (this.chatSidebar) {
            this.chatSidebar.classList.remove('open');
        }
    }
    
    sendChatMessage() {
        if (!this.chatInput) return;
        const message = this.chatInput.value.trim();
        if (!message) return;
        
        const chatData = {
            type: 'chat-message',
            message: message,
            sender: this.getCurrentUser(),
            timestamp: new Date().toISOString()
        };
        
        this.sendSignalingMessage(chatData);
        this.addChatMessage(chatData, true);
        this.chatInput.value = '';
    }
    
    handleChatMessage(data) {
        this.addChatMessage(data, false);
    }
    
    addChatMessage(data, isSent) {
        if (!this.chatMessages) return;
        
        const messageDiv = document.createElement('div');
        messageDiv.className = `chat-message ${isSent ? 'sent' : 'received'}`;
        
        const time = new Date(data.timestamp).toLocaleTimeString();
        messageDiv.innerHTML = `
            <div class="message-content">${data.message}</div>
            <div class="message-time">${time}</div>
        `;
        
        this.chatMessages.appendChild(messageDiv);
        this.chatMessages.scrollTop = this.chatMessages.scrollHeight;
    }
    
    handleUserJoined(data) {
        console.log('User joined:', data.user);
        this.updateConnectionStatus('connecting', 'Người dùng đã tham gia');
    }
    
    handleUserLeft(data) {
        console.log('User left:', data.user);
        this.endCall();
    }
    
    handleRemoteCallEnd() {
        console.log('Remote call ended');
        this.cleanup();
        this.redirectToChat();
    }
    
    handlePageHidden() {
        // Minimize bandwidth usage when page hidden
    }
    
    handlePageVisible() {
        // Resume full quality when page visible
    }
    
    toggleScreenShare() {
        console.log('Screen share not implemented yet');
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    console.log('DOM loaded, initializing VideoCallManager...');
    window.videoCallManager = new VideoCallManager();
});

// Export for external access
window.toggleMute = () => window.videoCallManager?.toggleMute();
window.toggleCamera = () => window.videoCallManager?.toggleCamera();
window.endCall = () => window.videoCallManager?.endCall();