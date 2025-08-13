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
  return adjectives[Math.floor(Math.random() * adjectives.length)] +
    ' ' + nouns[Math.floor(Math.random() * nouns.length)];
}

function randomColor() {
  return '#' + Math.floor(Math.random() * 16777215).toString(16).padStart(6, '0');
}

io.on('connection', (socket) => {
  const id = socket.id;
  const name = getRandomName();
  // Start players at random positions within bounds (canvas ~800x600)
  players[id] = {
    id,
    name,
    x: Math.random() * (800 - 40) + 20,
    y: Math.random() * (600 - 40) + 20,
    direction: null,
    moving: false,
    color: randomColor(),
  };

  // Send current players and your info to the new connection
  socket.emit('currentPlayers', players);
  socket.emit('yourInfo', players[id]);

  // Notify other players
  socket.broadcast.emit('newPlayer', players[id]);

  // Movement start
  socket.on('moveStart', (direction) => {
    if (players[id]) {
      players[id].direction = direction;
      players[id].moving = true;
    }
  });

  // Movement stop
  socket.on('moveStop', () => {
    if (players[id]) {
      players[id].moving = false;
      players[id].direction = null;
    }
  });

  // Chat message
  socket.on('chat', (text) => {
    if (players[id]) {
      io.emit('chat', { id, text });
    }
  });

  // Disconnect
  socket.on('disconnect', () => {
    delete players[id];
    io.emit('playerDisconnected', id);
  });
});

// Movement update loop
const SPEED = 200; // pixels per second
const TICK_RATE = 30; // updates per second
setInterval(() => {
  const delta = 1 / TICK_RATE;
  for (const id in players) {
    const p = players[id];
    if (p.moving && p.direction) {
      const dist = SPEED * delta;
      if (p.direction === 'left') p.x -= dist;
      if (p.direction === 'right') p.x += dist;
      if (p.direction === 'up') p.y -= dist;
      if (p.direction === 'down') p.y += dist;
      // Clamp positions within canvas
      p.x = Math.max(0, Math.min(p.x, 800 - 20));
      p.y = Math.max(0, Math.min(p.y, 600 - 20));
    }
  }
  io.emit('state', players);
}, 1000 / TICK_RATE);

server.listen(PORT, () => {
  console.log(`Server listening on port ${PORT}`);
});
