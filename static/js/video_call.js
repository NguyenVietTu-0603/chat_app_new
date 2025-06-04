// This file contains JavaScript code for handling video call functionality.

document.addEventListener("DOMContentLoaded", function () {
    const wsProtocol = window.location.protocol === "https:" ? "wss" : "ws";
    const wsUrl = `${wsProtocol}://${window.location.host}/ws/video-call/${window.currentUsername}/`;
    const socket = new WebSocket(wsUrl);
    const startCallButton = document.getElementById("start-call-button");
    const endCallButton = document.getElementById("end-call");
    const localVideo = document.getElementById("local-video");
    const remoteVideo = document.getElementById("remote-video");
    const callStatus = document.getElementById("call-status");
    const cameraButton = document.getElementById("camera-button");


    let localStream;
    let remoteStream;
    let peerConnection;
    const configuration = {
        iceServers: [
            { urls: "stun:stun.l.google.com:19302" },
            { urls: "stun:stun1.l.google.com:19302" }
        ]
    };

    startCallButton.onclick = async () => {
        callStatus.textContent = "Starting call...";
        localStream = await navigator.mediaDevices.getUserMedia({ video: true, audio: true });
        localVideo.srcObject = localStream;

        peerConnection = new RTCPeerConnection(configuration);
        localStream.getTracks().forEach(track => peerConnection.addTrack(track, localStream));

        peerConnection.onicecandidate = event => {
            if (event.candidate) {
                console.log("Sending ICE candidate:", event.candidate); // Thêm log
                sendMessage({ type: "ice-candidate", candidate: event.candidate });
            }
        };

        peerConnection.ontrack = event => {
            if (!remoteStream) {
                remoteStream = new MediaStream();
                remoteVideo.srcObject = remoteStream;
            }
            console.log("Adding track to remote stream:", event.track); // Thêm log
            remoteStream.addTrack(event.track);
        };
        const offer = await peerConnection.createOffer();
        await peerConnection.setLocalDescription(offer);
        sendMessage({ type: "video-offer", offer: offer });
    };

    if (endCallButton) {
        endCallButton.onclick = () => {
            if (callStatus) callStatus.textContent = "Call ended.";
            if (peerConnection) {
                peerConnection.close();
                peerConnection = null;
            }
            if (localStream) {
                localStream.getTracks().forEach(track => track.stop());
                localVideo.srcObject = null;
            }
            if (remoteVideo) remoteVideo.srcObject = null;
        };
    }

    function sendMessage(message) {
        if (socket.readyState === WebSocket.OPEN) {
            socket.send(JSON.stringify(message));
        } else {
            console.warn("WebSocket is not open. Message not sent:", message);
            if (callStatus) callStatus.textContent = "Cannot send message: signaling connection closed.";
        }
    }

    // Implement WebSocket or other signaling method to receive messages
    function receiveMessage(message) {
        if (message.type === "video-offer") {
            handleVideoOffer(message.offer);
        } else if (message.type === "ice-candidate") {
            handleIceCandidate(message.candidate);
        }
    }

    async function handleVideoOffer(offer) {
        if (!localStream) {
            localStream = await navigator.mediaDevices.getUserMedia({ video: true, audio: true });
            localVideo.srcObject = localStream;
        }
        peerConnection = new RTCPeerConnection(configuration);
        localStream.getTracks().forEach(track => peerConnection.addTrack(track, localStream));
        await peerConnection.setRemoteDescription(new RTCSessionDescription(offer));

        const answer = await peerConnection.createAnswer();
        await peerConnection.setLocalDescription(answer);
        sendMessage({ type: "video-answer", answer: answer });
    }

    function handleIceCandidate(candidate) {
        console.log("Received ICE candidate:", candidate); // Thêm log
        peerConnection.addIceCandidate(new RTCIceCandidate(candidate));
    }



    socket.onmessage = function (event) {
        console.log("Message received:", event.data); // Thêm log
        const data = JSON.parse(event.data);
        receiveMessage(data);
    };


let isCameraOn = true;

cameraButton.onclick = () => {
    if (localStream) {
        const videoTrack = localStream.getVideoTracks()[0];
        if (videoTrack) {
            isCameraOn = !isCameraOn;
            videoTrack.enabled = isCameraOn; // Bật/tắt video track
            cameraButton.textContent = isCameraOn ? "Turn Off Camera" : "Turn On Camera";
            console.log(`Camera is now ${isCameraOn ? "ON" : "OFF"}`);
        }
    }
};
});