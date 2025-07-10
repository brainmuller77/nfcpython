const express = require('express');
const http = require('http');
const socketIo = require('socket.io');
const axios = require('axios');

const app = express();
const server = http.createServer(app);
const io = socketIo(server, {
  cors: {
    origin: '*',
  }
});

const PHP_ENDPOINT = 'https://creatorsacademy.skuulmasta.com/server/uploadtest.php'; // replace with your actual URL

io.on('connection', (socket) => {
  console.log('✅ Client connected');

  socket.on('face-image', async (data) => {
    try {
      const response = await axios.post(PHP_ENDPOINT, {
        imageBase64: data.imageBase64,
        studentId: data.studentId
      });

      if (response.data.success) {
        socket.emit('upload-success', { file: response.data.file });
      } else {
        socket.emit('upload-failed', { error: response.data.error });
      }
    } catch (error) {
      console.error('Error sending to PHP backend:', error.message);
      socket.emit('upload-failed', { error: 'PHP backend error' });
    }
  });

  socket.on('disconnect', () => {
    console.log('❌ Client disconnected');
  });
});

server.listen(3000, () => {
  console.log('🚀 Socket bridge running on http://localhost:3000');
});
