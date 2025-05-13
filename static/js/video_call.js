const APP_ID = "20f1bf00f7144a7084d6bfb3dca4b173"; // Thay bằng App ID của bạn từ Agora
const TOKEN = "369994073dce47e1a2bbf2bc44bdc98a"; // Thay bằng token được tạo từ server
const CHANNEL = "test"; // Tên kênh video call

const client = AgoraRTC.createClient({ mode: "rtc", codec: "vp8" });
let localTrack, remoteTracks = {};

async function joinCall() {
    await client.join(APP_ID, CHANNEL, TOKEN);

    localTrack = await AgoraRTC.createMicrophoneAndCameraTracks();
    const localStreamContainer = document.getElementById("local-stream");
    localStreamContainer.appendChild(localTrack[1].play());

    client.on("user-published", async (user, mediaType) => {
        await client.subscribe(user, mediaType);
        if (mediaType === "video") {
            const remoteStreamContainer = document.getElementById("remote-streams");
            const remoteVideoTrack = user.videoTrack;
            const remoteVideoElement = document.createElement("div");
            remoteVideoElement.id = `user-${user.uid}`;
            remoteStreamContainer.appendChild(remoteVideoElement);
            remoteVideoTrack.play(remoteVideoElement);
        }
    });

    client.on("user-unpublished", (user) => {
        const remoteVideoElement = document.getElementById(`user-${user.uid}`);
        if (remoteVideoElement) remoteVideoElement.remove();
    });
}

document.getElementById("leave-call").onclick = async () => {
    localTrack[0].close();
    localTrack[1].close();
    await client.leave();
    window.location.href = "/";
};

joinCall();