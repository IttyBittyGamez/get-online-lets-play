const express = require('express');
const http = require('http');
const socketIo = require('socket.io');

const app = express();
const server = http.createServer(app);
const io = socketIo(server);

// Serve static files from the public directory
app.use(express.static('public'));

const PORT = process.env.PORT || 3000;

// Store player states
const players = {};

function getRandomName() {
  const adjectives = ['Brave','Clever','Quick','Lucky','Sneaky'];
  const nouns = ['Fox','Tiger','Rabbit','Bear','Wolf'];
  return adjectives[Math.floor(Math.random() * adjectives.length)] + nouns[Math.floor(Math.random() * nouns.length)];
}

io.on('connection', (socket) => {
  const id = socket.id;
  const name = getRandomName();
  // Start players at random positions within bounds
  players[id] = { id, name, x: Math.random() * 780 + 10, y: Math.random() * 580 + 10, direction: null, moving: false };

  // Send existing state to the newly connected client
  socket.emit('init', { id, players });
  // Notify others of new player
  socket.broadcast.emit('playerJoined', players[id]);

  // Handle movement updates from clients
  socket.on('move', (data) => {
    const player = players[id];
    if (player) {
      player.direction = data.direction;
      player.moving = data.moving;
      io.emit('playerMoved', { id, direction: player.direction, moving: player.moving });
    }
  });

  // Relay chat messages
  socket.on('chat', (msg) => {
    const player = players[id];
    if (player) {
      io.emit('chat', { id, message: msg });
    }
  });

  // Handle disconnects
  socket.on('disconnect', () => {
    delete players[id];
    io.emit('playerLeft', id);
  });
});

// Start the server
server.listen(PORT, () => {
  console.log(`Server listening on port ${PORT}`);
});
