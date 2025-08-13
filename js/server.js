const express = require('express');
const http = require('http');
const socketIo = require('socket.io');

const app = express();
const server = http.createServer(app);
const io = socketIo(server);

const PORT = process.env.PORT || 3000;

// Serve static files from the public directory
app.use(express.static('public'));

// Store player states
const players = {};

function getRandomName() {
  const adjectives = ['Brave','Clever','Quick','Lucky','Sneaky'];
  const nouns = ['Fox','Tiger','Rabbit','Bear','Wolf'];
  return adjectives[Math.floor(Math.random() * adjectives.length)] + ' ' +
         nouns[Math.floor(Math.random() * nouns.length)];
}

function randomColor() {
  return '#' + Math.floor(Math.random() * 16777215).toString(16).padStart(6, '0');
}

io.on('connection', (socket) => {
  const id = socket.id;
  const name = getRandomName();
  const color = randomColor();
  const player = {
    id,
    name,
    x: Math.floor(Math.random() * 800),
    y: Math.floor(Math.random() * 600),
    direction: null,
    moving: false,
    color,
    messages: []
  };
  players[id] = player;

  // Send current players to the new player
  socket.emit('currentPlayers', players);
  // Send your info to the new player
  socket.emit('yourInfo', { id, name, color });

  // Broadcast new player to existing players
  socket.broadcast.emit('newPlayer', player);

  socket.on('moveStart', (dir) => {
    let direction;
    if (typeof dir === 'string') direction = dir;
    else if (dir && typeof dir.dir === 'string') direction = dir.dir;
    if (direction) {
      players[id].direction = direction;
      players[id].moving = true;
    }
  });

  socket.on('moveStop', () => {
    players[id].moving = false;
  });

  socket.on('chat', (text) => {
    io.emit('chat', { id, text });
  });

  socket.on('disconnect', () => {
    delete players[id];
    io.emit('playerDisconnected', id);
  });
});

const SPEED = 3;
const TICK_RATE = 30;

setInterval(() => {
  for (const id in players) {
    const player = players[id];
    if (player.moving) {
      switch (player.direction) {
        case 'up':
          player.y -= SPEED;
          break;
        case 'down':
          player.y += SPEED;
          break;
        case 'left':
          player.x -= SPEED;
          break;
        case 'right':
          player.x += SPEED;
          break;
      }
    }
  }
  io.emit('state', players);
}, 1000 / TICK_RATE);

server.listen(PORT, () => {
  console.log(`Server listening on port ${PORT}`);
});
