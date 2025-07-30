# Real-time Chat Application

A real-time chat application built with Flask, Socket.IO, and MySQL, featuring user authentication, password recovery, media file sharing, and basic WebRTC-based video calls.

## Features

* **User Authentication:** Secure sign-up and sign-in.
* **Password Recovery:** Reset password via email.
* **Real-time Chat:** Instant messaging between users using WebSockets.
* **Media File Sharing:** Send images, videos, audio, and documents.
* **Video Calls:** Peer-to-peer audio/video calls using WebRTC.
* **MySQL Database:** Persistent storage for user data and chat history.
* **Deployment Ready:** Configured for deployment on platforms like Railway.com or Render.com.

## Technologies Used

* **Backend:** Python (Flask, Flask-SocketIO, Flask-Bcrypt, Flask-Mail)
* **Database:** MySQL
* **Real-time:** WebSockets (via Socket.IO)
* **Media Calls:** WebRTC
* **Frontend:** HTML, CSS, JavaScript (with Socket.IO client and WebRTC APIs)
* **Deployment:** Gunicorn, Railway/Render

## Project Structure