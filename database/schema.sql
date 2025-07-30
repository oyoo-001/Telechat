-- database/schema.sql

-- Create the database if it doesn't exist
CREATE DATABASE IF NOT EXISTS chat_app_db;

-- Use the newly created database
USE chat_app_db;

-- Table for users
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(255) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    reset_token VARCHAR(255),            -- For password recovery tokens
    reset_token_expiry DATETIME,         -- Expiry time for reset token
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Table for messages (supports direct and potentially group chats later)
CREATE TABLE IF NOT EXISTS messages (
    id INT AUTO_INCREMENT PRIMARY KEY,
    sender_id INT NOT NULL,
    receiver_id INT,                     -- Null for group chat (if group_id is used), or direct receiver
    -- chat_room_id INT,                 -- Uncomment and add FK if implementing dedicated group chats
    message_text TEXT,                   -- Content of the message
    media_url VARCHAR(255),              -- URL to media file if it's a media message
    message_type ENUM('text', 'image', 'video', 'audio', 'document', 'call_event') NOT NULL DEFAULT 'text',
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (sender_id) REFERENCES users(id) ON DELETE CASCADE
    -- Add FOREIGN KEY for receiver_id or chat_room_id if needed
);

-- Example for chat_rooms and room_members tables if you expand to group chats:
/*
CREATE TABLE IF NOT EXISTS chat_rooms (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) UNIQUE NOT NULL,
    created_by INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS room_members (
    room_id INT NOT NULL,
    user_id INT NOT NULL,
    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (room_id, user_id),
    FOREIGN KEY (room_id) REFERENCES chat_rooms(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);
*/

-- Add indexes for performance
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_messages_sender_id ON messages(sender_id);
CREATE INDEX idx_messages_receiver_id ON messages(receiver_id);
-- CREATE INDEX idx_messages_chat_room_id ON messages(chat_room_id);