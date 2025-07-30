# -*- coding: utf-8 -*-
"""
Created on Wed Jul 30 10:49:58 2025

@author: Byron Okoth
"""

# app.py
from flask import Flask, render_template, request, redirect, url_for, flash, session, send_from_directory
from flask_socketio import SocketIO, emit, join_room, leave_room
from flask_bcrypt import Bcrypt
from flask_mail import Mail, Message
import mysql.connector
import os
import secrets
from datetime import datetime, timedelta

# Import configuration from config.py
from config import Config

app = Flask(__name__)
app.config.from_object(Config) # Load configuration

socketio = SocketIO(app)
bcrypt = Bcrypt(app)
mail = Mail(app)

# Ensure the uploads folder exists
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

# --- Database connection helper ---
def get_db_connection():
    try:
        conn = mysql.connector.connect(
            host=app.config['MYSQL_HOST'],
            user=app.config['MYSQL_USER'],
            password=app.config['MYSQL_PASSWORD'],
            database=app.config['MYSQL_DB']
        )
        return conn
    except mysql.connector.Error as err:
        print(f"Database connection error: {err}")
        # In a real app, you'd log this and show a user-friendly error page
        raise

# --- User Session Management (Basic) ---
# For a more robust solution, consider Flask-Login or similar.
# This simple setup uses Flask's session object.
@app.before_request
def make_session_permanent():
    session.permanent = True
    app.permanent_session_lifetime = timedelta(minutes=30) # Adjust as needed

def login_required(f):
    def wrap(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    wrap.__name__ = f.__name__ # Preserve original function name
    return wrap


# --- Routes for Authentication ---

@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('chat_page'))
    return redirect(url_for('login'))

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if 'user_id' in session:
        return redirect(url_for('chat_page'))

    if request.method == 'POST':
        username = request.form['username'].strip()
        email = request.form['email'].strip()
        password = request.form['password']

        if not username or not email or not password:
            flash('All fields are required.', 'danger')
            return render_template('auth/signup.html')

        if len(password) < 6:
            flash('Password must be at least 6 characters long.', 'danger')
            return render_template('auth/signup.html')

        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')

        conn = None
        cursor = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("INSERT INTO users (username, email, password_hash) VALUES (%s, %s, %s)",
                           (username, email, hashed_password))
            conn.commit()
            flash('Account created successfully! Please log in.', 'success')
            return redirect(url_for('login'))
        except mysql.connector.Error as err:
            if err.errno == 1062: # Duplicate entry error
                flash('Username or email already exists. Please choose another.', 'danger')
            else:
                flash(f'An unexpected error occurred: {err}', 'danger')
            return render_template('auth/signup.html')
        finally:
            if cursor: cursor.close()
            if conn and conn.is_connected(): conn.close()
    return render_template('auth/signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('chat_page'))

    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password']

        conn = None
        cursor = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT id, username, password_hash FROM users WHERE username = %s", (username,))
            user = cursor.fetchone()

            if user and bcrypt.check_password_hash(user['password_hash'], password):
                session['user_id'] = user['id']
                session['username'] = user['username']
                flash('Logged in successfully!', 'success')
                return redirect(url_for('chat_page'))
            else:
                flash('Invalid username or password.', 'danger')
        except mysql.connector.Error as err:
            flash(f'Database error: {err}', 'danger')
        finally:
            if cursor: cursor.close()
            if conn and conn.is_connected(): conn.close()
    return render_template('auth/login.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('username', None)
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form['email'].strip()
        if not email:
            flash('Please enter your email address.', 'danger')
            return render_template('auth/forgot_password.html')

        conn = None
        cursor = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT id, username FROM users WHERE email = %s", (email,))
            user = cursor.fetchone()

            if user:
                token = secrets.token_urlsafe(32)
                expiry = datetime.now() + timedelta(hours=1) # Token valid for 1 hour
                cursor.execute("UPDATE users SET reset_token = %s, reset_token_expiry = %s WHERE id = %s",
                               (token, expiry, user['id']))
                conn.commit()

                reset_link = url_for('reset_password', token=token, _external=True)
                msg = Message('Password Reset Request for Chat App',
                              recipients=[email])
                msg.body = f"""
                Hello {user['username']},

                You have requested a password reset for your chat account.
                Please click on the following link to reset your password:
                {reset_link}

                This link will expire in 1 hour.
                If you did not request this, please ignore this email.

                Thanks,
                Your Chat App Team
                """
                mail.send(msg)
                flash('A password reset link has been sent to your email if an account exists.', 'info')
            else:
                # To prevent user enumeration, we give a generic message.
                flash('A password reset link has been sent to your email if an account exists.', 'info')
        except Exception as e:
            print(f"Error sending password reset email: {e}")
            flash(f'An error occurred while processing your request. Please try again later.', 'danger')
        finally:
            if cursor: cursor.close()
            if conn and conn.is_connected(): conn.close()
        return render_template('auth/forgot_password.html')
    return render_template('auth/forgot_password.html')

@app.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id FROM users WHERE reset_token = %s AND reset_token_expiry > %s",
                       (token, datetime.now()))
        user = cursor.fetchone()

        if not user:
            flash('Invalid or expired password reset link.', 'danger')
            return redirect(url_for('forgot_password'))

        if request.method == 'POST':
            new_password = request.form['new_password']
            confirm_password = request.form['confirm_password']

            if not new_password or not confirm_password:
                flash('Both password fields are required.', 'danger')
                return render_template('auth/reset_password.html', token=token)

            if new_password != confirm_password:
                flash('Passwords do not match.', 'danger')
                return render_template('auth/reset_password.html', token=token)

            if len(new_password) < 6:
                flash('New password must be at least 6 characters long.', 'danger')
                return render_template('auth/reset_password.html', token=token)

            hashed_password = bcrypt.generate_password_hash(new_password).decode('utf-8')
            cursor.execute("UPDATE users SET password_hash = %s, reset_token = NULL, reset_token_expiry = NULL WHERE id = %s",
                           (hashed_password, user['id']))
            conn.commit()
            flash('Your password has been reset successfully. Please log in.', 'success')
            return redirect(url_for('login'))

    except Exception as e:
        print(f"Error in reset_password: {e}")
        flash(f'An error occurred: {e}', 'danger')
    finally:
        if cursor: cursor.close()
        if conn and conn.is_connected(): conn.close()
    return render_template('auth/reset_password.html', token=token)

@app.route('/chat')
@login_required # Protect this route
def chat_page():
    current_user_id = session.get('user_id')
    current_username = session.get('username')

    if not current_user_id: # Should be caught by login_required, but a double-check
        flash('You are not logged in.', 'danger')
        return redirect(url_for('login'))

    conn = None
    cursor = None
    users = []
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        # Fetch all users except the current one for chat selection
        cursor.execute("SELECT id, username FROM users WHERE id != %s", (current_user_id,))
        users = cursor.fetchall()
    except mysql.connector.Error as err:
        flash(f'Error loading users: {err}', 'danger')
    finally:
        if cursor: cursor.close()
        if conn and conn.is_connected(): conn.close()

    return render_template('chat/chat.html', current_user_id=current_user_id, current_username=current_username, users=users)

# --- WebSocket Event Handlers ---
user_sid_map = {} # Maps user_id to socket_id for direct messaging

@socketio.on('connect')
def handle_connect():
    user_id = session.get('user_id')
    if user_id:
        user_sid_map[user_id] = request.sid
        join_room(str(user_id)) # User joins their own room for direct messages
        print(f'User {user_id} connected with SID: {request.sid}')
        # Emit 'user_online' event to all connected clients
        emit('user_status_update', {'user_id': user_id, 'status': 'online'}, broadcast=True)
    else:
        print(f'Unauthenticated client connected: {request.sid}')
        # You might want to disconnect unauthenticated clients or redirect them
        # emit('redirect_to_login', {}, room=request.sid)

@socketio.on('disconnect')
def handle_disconnect():
    user_id = None
    for uid, sid in user_sid_map.items():
        if sid == request.sid:
            user_id = uid
            break
    if user_id:
        if user_id in user_sid_map:
            del user_sid_map[user_id] # Remove from mapping
        leave_room(str(user_id))
        print(f'User {user_id} disconnected with SID: {request.sid}')
        # Emit 'user_offline' event to all connected clients
        emit('user_status_update', {'user_id': user_id, 'status': 'offline'}, broadcast=True)
    else:
        print(f'Client disconnected: {request.sid}')

@socketio.on('send_message')
def handle_send_message(data):
    sender_id = session.get('user_id') # Get sender from session, not client data
    if not sender_id:
        emit('error', {'message': 'Not authenticated to send message'}, room=request.sid)
        return

    receiver_id = data.get('receiver_id')
    message_text = data.get('message')
    message_type = data.get('message_type', 'text')
    media_url = data.get('media_url')

    if not receiver_id or not (message_text or media_url):
        emit('error', {'message': 'Invalid message data'}, room=request.sid)
        return

    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Save message to DB
        cursor.execute("INSERT INTO messages (sender_id, receiver_id, message_text, media_url, message_type) VALUES (%s, %s, %s, %s, %s)",
                       (sender_id, receiver_id, message_text, media_url, message_type))
        conn.commit()

        # Get sender's username for displaying message
        cursor.execute("SELECT username FROM users WHERE id = %s", (sender_id,))
        sender_username = cursor.fetchone()[0]

        message_payload = {
            'sender_id': sender_id,
            'sender_username': sender_username,
            'message': message_text,
            'media_url': media_url,
            'message_type': message_type,
            'timestamp': datetime.now().isoformat()
        }

        # Emit message to recipient(s) - use the user_id room
        # Check if receiver is online and has a connected socket
        if receiver_id in user_sid_map:
            emit('receive_message', message_payload, room=str(receiver_id))
        else:
            print(f"Receiver {receiver_id} is offline. Message saved, but not delivered in real-time.")
            # In a real app, you'd add logic for offline messages (e.g., push notifications)

        # Also emit back to sender to confirm message sent and update their UI
        emit('receive_message', message_payload, room=request.sid)

    except Exception as e:
        print(f"Error sending message: {e}")
        emit('error', {'message': 'Failed to send message'}, room=request.sid)
    finally:
        if cursor: cursor.close()
        if conn and conn.is_connected(): conn.close()


# --- Media File Handling ---
# NOTE: For production, store files in a cloud storage service like AWS S3.
# The current setup stores them locally, which is not persistent on platforms like Render/Railway.
@app.route('/upload_media', methods=['POST'])
@login_required # Only logged-in users can upload
def upload_media():
    if 'media_file' not in request.files:
        flash('No file part', 'danger')
        return "No file part", 400
    file = request.files['media_file']
    if file.filename == '':
        flash('No selected file', 'danger')
        return "No selected file", 400

    if file:
        # Basic validation (add more as needed)
        allowed_extensions = {'png', 'jpg', 'jpeg', 'gif', 'mp4', 'mp3', 'pdf', 'doc', 'docx'}
        filename_parts = file.filename.rsplit('.', 1)
        if len(filename_parts) < 2 or filename_parts[1].lower() not in allowed_extensions:
            return "File type not allowed.", 400

        filename = secrets.token_urlsafe(16) + '.' + filename_parts[1].lower()
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        media_url = url_for('uploaded_file', filename=filename, _external=True)

        # You would typically send this media_url via SocketIO to the recipient
        # For example, calling `handle_send_message` with type 'image' and the URL
        # emit('file_uploaded_success', {'media_url': media_url, 'filename': filename}, room=request.sid)
        return media_url, 200 # Return the URL to the client
    return "Error uploading file", 500

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    # Ensure the file exists and is within the allowed directory
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# --- WebRTC Signaling ---
# These handlers facilitate the exchange of SDP offers/answers and ICE candidates
# between two users who want to start a call. The actual audio/video stream
# flows peer-to-peer, not through the Python server.

@socketio.on('webrtc_offer')
def handle_webrtc_offer(data):
    sender_id = session.get('user_id')
    if not sender_id: return # Not authenticated

    target_user_id = data.get('target_user_id')
    sdp_offer = data.get('sdp_offer')
    if target_user_id and sdp_offer and target_user_id in user_sid_map:
        emit('webrtc_offer', {'sender_id': sender_id, 'sdp_offer': sdp_offer}, room=str(target_user_id))
    else:
        emit('error', {'message': 'Invalid target or offer for WebRTC'}, room=request.sid)

@socketio.on('webrtc_answer')
def handle_webrtc_answer(data):
    sender_id = session.get('user_id')
    if not sender_id: return

    target_user_id = data.get('target_user_id')
    sdp_answer = data.get('sdp_answer')
    if target_user_id and sdp_answer and target_user_id in user_sid_map:
        emit('webrtc_answer', {'sender_id': sender_id, 'sdp_answer': sdp_answer}, room=str(target_user_id))
    else:
        emit('error', {'message': 'Invalid target or answer for WebRTC'}, room=request.sid)

@socketio.on('webrtc_ice_candidate')
def handle_webrtc_ice_candidate(data):
    sender_id = session.get('user_id')
    if not sender_id: return

    target_user_id = data.get('target_user_id')
    ice_candidate = data.get('ice_candidate')
    if target_user_id and ice_candidate and target_user_id in user_sid_map:
        emit('webrtc_ice_candidate', {'sender_id': sender_id, 'ice_candidate': ice_candidate}, room=str(target_user_id))
    else:
        emit('error', {'message': 'Invalid target or ICE candidate for WebRTC'}, room=request.sid)

# To handle call termination gracefully
@socketio.on('webrtc_call_end')
def handle_webrtc_call_end(data):
    sender_id = session.get('user_id')
    if not sender_id: return

    target_user_id = data.get('target_user_id')
    if target_user_id and target_user_id in user_sid_map:
        emit('webrtc_call_ended', {'sender_id': sender_id}, room=str(target_user_id))
    else:
        emit('error', {'message': 'Cannot signal call end'}, room=request.sid)


if __name__ == '__main__':
    socketio.run(app, debug=True, host='0.0.0.0', port=5000) # Use 0.0.0.0 for Docker/deployment