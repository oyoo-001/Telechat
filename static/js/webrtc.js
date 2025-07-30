// static/js/webrtc.js - WebRTC specific logic

// These variables are assumed to be available from main.js or a global scope:
// const socket = io();
// let currentChatPartnerId;
// let currentUserId;
// let currentChatPartnerName;
// const chatWindow; // for displaying call events

let localStream;
let remoteStream;
let peerConnection;

const localVideo = document.getElementById('localVideo');
const remoteVideo = document.getElementById('remoteVideo');
const callButtonsDiv = document.getElementById('call-buttons');

const STUN_SERVERS = [
    { urls: 'stun:stun.l.google.com:19302' },
    { urls: 'stun:stun1.l.google.com:19302' },
    // You might need a TURN server for complex network environments
    // { urls: 'turn:your-turn-server.com:3478', username: 'user', credential: 'password' }
];

// --- WebRTC Setup Functions ---

async function initializePeerConnection() {
    peerConnection = new RTCPeerConnection({ iceServers: STUN_SERVERS });

    peerConnection.onicecandidate = (event) => {
        if (event.candidate) {
            console.log('Sending ICE candidate:', event.candidate);
            socket.emit('webrtc_ice_candidate', {
                target_user_id: currentChatPartnerId,
                ice_candidate: event.candidate.toJSON()
            });
        }
    };

    peerConnection.ontrack = (event) => {
        console.log('Received remote track');
        if (remoteVideo.srcObject !== event.streams[0]) {
            remoteVideo.srcObject = event.streams[0];
            remoteStream = event.streams[0];
        }
    };

    peerConnection.onconnectionstatechange = (event) => {
        console.log('RTCPeerConnection state:', peerConnection.connectionState);
        switch (peerConnection.connectionState) {
            case 'connected':
                addSystemMessage('Call connected!');
                break;
            case 'disconnected':
            case 'failed':
            case 'closed':
                addSystemMessage('Call disconnected or failed.');
                endCall();
                break;
        }
    };

    peerConnection.onnegotiationneeded = async () => {
        try {
            const offer = await peerConnection.createOffer();
            await peerConnection.setLocalDescription(offer);
            console.log('Sending WebRTC offer:', peerConnection.localDescription);
            socket.emit('webrtc_offer', {
                target_user_id: currentChatPartnerId,
                sdp_offer: peerConnection.localDescription.toJSON()
            });
        } catch (err) {
            console.error('Error creating offer or setting local description:', err);
        }
    };
}

async function startCall() {
    if (!currentChatPartnerId) {
        alert('Please select a user to call first.');
        return;
    }
    if (peerConnection && peerConnection.connectionState !== 'closed') {
        alert('A call is already in progress.');
        return;
    }

    try {
        // Get local media stream
        localStream = await navigator.mediaDevices.getUserMedia({ video: true, audio: true });
        localVideo.srcObject = localStream;

        await initializePeerConnection();

        // Add local tracks to peer connection
        localStream.getTracks().forEach(track => peerConnection.addTrack(track, localStream));

        addSystemMessage(`Calling ${currentChatPartnerName}...`);
        // The offer will be created and sent via onnegotiationneeded
    } catch (error) {
        console.error('Error starting call:', error);
        alert('Failed to start call. Please ensure camera/microphone permissions are granted.');
        endCall();
    }
}

function endCall() {
    if (peerConnection) {
        peerConnection.close();
        peerConnection = null;
    }
    if (localStream) {
        localStream.getTracks().forEach(track => track.stop());
        localStream = null;
    }
    if (remoteStream) {
        remoteStream.getTracks().forEach(track => track.stop());
        remoteStream = null;
    }

    localVideo.srcObject = null;
    remoteVideo.srcObject = null;

    if (currentChatPartnerId) {
        socket.emit('webrtc_call_end', { target_user_id: currentChatPartnerId });
    }
    addSystemMessage('Call ended.');
}

// --- Socket.IO WebRTC Signaling Handlers ---

socket.on('webrtc_offer', async (data) => {
    // Check if the offer is for this client and from the current chat partner
    if (data.sender_id === currentChatPartnerId) {
        if (peerConnection && peerConnection.connectionState !== 'closed') {
            addSystemMessage('Already in a call or connection exists.');
            // Send busy signal back (optional)
            return;
        }

        const acceptCall = confirm(`Incoming call from ${currentChatPartnerName}. Accept?`);
        if (!acceptCall) {
            addSystemMessage(`Call from ${currentChatPartnerName} rejected.`);
            // Send rejection message back to caller (optional)
            return;
        }

        try {
            addSystemMessage(`Accepting call from ${currentChatPartnerName}...`);
            localStream = await navigator.mediaDevices.getUserMedia({ video: true, audio: true });
            localVideo.srcObject = localStream;

            await initializePeerConnection();

            await peerConnection.setRemoteDescription(new RTCSessionDescription(data.sdp_offer));
            localStream.getTracks().forEach(track => peerConnection.addTrack(track, localStream));

            const answer = await peerConnection.createAnswer();
            await peerConnection.setLocalDescription(answer);
            console.log('Sending WebRTC answer:', peerConnection.localDescription);
            socket.emit('webrtc_answer', {
                target_user_id: data.sender_id,
                sdp_answer: peerConnection.localDescription.toJSON()
            });

        } catch (error) {
            console.error('Error accepting call:', error);
            alert('Failed to accept call.');
            endCall();
        }
    } else {
        // Offer from someone else not currently in chat context
        console.log(`Ignoring offer from user ${data.sender_id}.`);
        addSystemMessage(`Incoming call from a different user (ID: ${data.sender_id}). Please switch chat to answer.`);
    }
});

socket.on('webrtc_answer', async (data) => {
    // Check if the answer is for this client and from the current chat partner
    if (peerConnection && data.sender_id === currentChatPartnerId) {
        console.log('Received WebRTC answer:', data.sdp_answer);
        await peerConnection.setRemoteDescription(new RTCSessionDescription(data.sdp_answer));
    }
});

socket.on('webrtc_ice_candidate', async (data) => {
    // Check if the candidate is for this client and from the current chat partner
    if (peerConnection && data.sender_id === currentChatPartnerId && data.ice_candidate) {
        try {
            console.log('Adding ICE candidate:', data.ice_candidate);
            await peerConnection.addIceCandidate(new RTCIceCandidate(data.ice_candidate));
        } catch (e) {
            console.error('Error adding received ICE candidate:', e);
        }
    }
});

socket.on('webrtc_call_ended', (data) => {
    // If the other party ended the call
    if (data.sender_id === currentChatPartnerId) {
        addSystemMessage(`${currentChatPartnerName} has ended the call.`);
        endCall();
    }
});