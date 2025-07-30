// static/js/main.js - Core chat logic

const socket = io();
let currentChatPartnerId = null;
let currentChatPartnerName = null;
let currentUserId; // Will be set on chat page load
let currentUsername; // Will be set on chat page load

const chatWindow = document.getElementById('chat-window');
const messageInput = document.getElementById('message-input');
const mediaInput = document.getElementById('media-input');
const chatPartnerNameSpan = document.getElementById('chat-partner-name');
const activeChatSection = document.getElementById('active-chat');
const usersListDiv = document.getElementById('users-list');

document.addEventListener('DOMContentLoaded', () => {
    // Get current user ID and username from the HTML (passed by Flask)
    currentUserId = parseInt(document.getElementById('current-user-id').value);
    currentUsername = document.getElementById('current-username').value;

    // Set up event listener for sending message on Enter key
    messageInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            sendMessage();
        }
    });
});

// --- Socket.IO Event Handlers ---

socket.on('connect', () => {
    console.log('Connected to server with SID:', socket.id);
    // On connect, the server will join the user to their room based on session.
});

socket.on('disconnect', () => {
    console.log('Disconnected from server');
    addSystemMessage('You have been disconnected from the chat. Please refresh.');
});

socket.on('receive_message', (data) => {
    console.log('Received message:', data);
    displayMessage(data);
});

socket.on('error', (data) => {
    console.error('Server error:', data.message);
    addSystemMessage(`Error: ${data.message}`);
});

socket.on('user_status_update', (data) => {
    console.log(`User ${data.user_id} is now ${data.status}`);
    const userElement = document.getElementById(`user-${data.user_id}`);
    if (userElement) {
        const statusSpan = userElement.querySelector('.user-status');
        if (statusSpan) {
            statusSpan.innerText = data.status === 'online' ? 'Online' : 'Offline';
            statusSpan.style.color = data.status === 'online' ? 'green' : 'red';
        }
    }
});


// --- Chat UI Functions ---

function addSystemMessage(message) {
    const messageDiv = document.createElement('div');
    messageDiv.classList.add('message', 'system-message');
    messageDiv.innerText = message;
    chatWindow.appendChild(messageDiv);
    chatWindow.scrollTop = chatWindow.scrollHeight;
}

function displayMessage(data) {
    // Only display if it's for the currently active chat
    if (data.sender_id === currentUserId || data.sender_id === currentChatPartnerId || data.receiver_id === currentChatPartnerId) {
        const messageDiv = document.createElement('div');
        messageDiv.classList.add('message');

        const senderDisplayName = data.sender_id === currentUserId ? 'You' : data.sender_username;
        const timestamp = new Date(data.timestamp).toLocaleTimeString();

        let content = '';
        if (data.message_type === 'text') {
            content = `${senderDisplayName}: ${data.message} <small>(${timestamp})</small>`;
        } else if (data.media_url) {
            const mediaType = data.message_type;
            const mediaLink = `<a href="${data.media_url}" target="_blank">View ${mediaType}</a>`;
            if (mediaType === 'image') {
                content = `${senderDisplayName}: <img src="${data.media_url}" alt="Image" style="max-width: 200px; display: block; margin-top: 5px;"> ${mediaLink} <small>(${timestamp})</small>`;
            } else if (mediaType === 'video' || mediaType === 'audio') {
                const tag = mediaType === 'video' ? 'video' : 'audio';
                content = `${senderDisplayName}: <${tag} controls src="${data.media_url}" style="max-width: 200px; display: block; margin-top: 5px;"></${tag}> ${mediaLink} <small>(${timestamp})</small>`;
            } else { // document or other
                content = `${senderDisplayName}: Sent a ${mediaType} file. ${mediaLink} <small>(${timestamp})</small>`;
            }
        } else if (data.message_type === 'call_event') {
             content = `${senderDisplayName}: ${data.message} <small>(${timestamp})</small>`;
             messageDiv.classList.add('system-message'); // Style call events differently
        }

        messageDiv.innerHTML = content;
        if (data.sender_id === currentUserId) {
            messageDiv.classList.add('my-message');
        } else {
            messageDiv.classList.add('other-message');
        }

        chatWindow.appendChild(messageDiv);
        chatWindow.scrollTop = chatWindow.scrollHeight; // Scroll to bottom
    }
}

function startPrivateChat(userId, username) {
    currentChatPartnerId = userId;
    currentChatPartnerName = username;
    chatPartnerNameSpan.innerText = username;
    activeChatSection.style.display = 'block';
    chatWindow.innerHTML = ''; // Clear previous chat
    addSystemMessage(`You are now chatting with ${username}.`);
    // In a real app, you'd load chat history here
}

function sendMessage() {
    const message = messageInput.value.trim();
    if (message && currentChatPartnerId) {
        socket.emit('send_message', {
            sender_id: currentUserId, // Sender ID is derived from session on server, but sent for clarity
            receiver_id: currentChatPartnerId,
            message: message,
            message_type: 'text'
        });
        messageInput.value = '';
    }
}

async function uploadMedia() {
    const file = mediaInput.files[0];

    if (!file) {
        alert('Please select a file to upload.');
        return;
    }

    if (!currentChatPartnerId) {
        alert('Please select a user to send the file to.');
        return;
    }

    const formData = new FormData();
    formData.append('media_file', file);

    try {
        const response = await fetch('/upload_media', {
            method: 'POST',
            body: formData
        });

        if (response.ok) {
            const mediaUrl = await response.text(); // Server returns the URL directly
            console.log('File uploaded successfully:', mediaUrl);

            // Determine message type based on file extension
            const fileExtension = file.name.split('.').pop().toLowerCase();
            let messageType = 'document';
            if (['png', 'jpg', 'jpeg', 'gif'].includes(fileExtension)) {
                messageType = 'image';
            } else if (['mp4', 'webm', 'ogg'].includes(fileExtension)) {
                messageType = 'video';
            } else if (['mp3', 'wav', 'ogg'].includes(fileExtension)) {
                messageType = 'audio';
            }

            // Send a chat message with the media URL
            socket.emit('send_message', {
                sender_id: currentUserId,
                receiver_id: currentChatPartnerId,
                message: `Sent a ${messageType} file.`, // A descriptive message
                media_url: mediaUrl,
                message_type: messageType
            });
            mediaInput.value = ''; // Clear file input
        } else {
            const errorText = await response.text();
            alert(`Error uploading file: ${errorText}`);
            console.error('Error uploading media:', response.status, errorText);
        }
    } catch (error) {
        console.error('Network error during media upload:', error);
        alert('Failed to upload file due to network error.');
    }
}