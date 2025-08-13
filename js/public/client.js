const socket = io();

const canvas = document.getElementById('gameCanvas');
const ctx = canvas.getContext('2d');
const chatInput = document.getElementById('chatInput');

// Players state keyed by id
let players = {};
let myId = null;

// Helper to add a chat message to a player with timeout
function addMessage(playerId, text) {
  const msgObj = { text };
  if (!players[playerId].messages) players[playerId].messages = [];
  players[playerId].messages.push(msgObj);
  // Keep only last two messages
  if (players[playerId].messages.length > 2) players[playerId].messages.shift();
  // Remove after 5 seconds
  setTimeout(() => {
    const list = players[playerId].messages;
    const idx = list.indexOf(msgObj);
    if (idx !== -1) list.splice(idx, 1);
  }, 5000);
}

// Listen for server events
socket.on('currentPlayers', data => {
  players = data;
});

socket.on('yourInfo', info => {
  myId = info.id;
  if (players[myId]) {
    players[myId].name = info.name;
    players[myId].color = info.color;
  }
});

socket.on('newPlayer', player => {
  players[player.id] = player;
});

socket.on('playerDisconnected', id => {
  delete players[id];
});

socket.on('state', data => {
  // Update positions from server state
  for (const id in data) {
    const pdata = data[id];
    if (!players[id]) players[id] = pdata;
    else {
      players[id].x = pdata.x;
      players[id].y = pdata.y;
    }
  }
  render();
});

socket.on('chat', ({ id, text }) => {
  if (players[id]) addMessage(id, text);
  render();
});

// Render all players and messages
function render() {
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  ctx.font = '12px sans-serif';
  ctx.textBaseline = 'bottom';
  for (const id in players) {
    const p = players[id];
    // Draw square
    ctx.fillStyle = p.color || '#4444ff';
    ctx.fillRect(p.x, p.y, 20, 20);
    // Draw name below square
    ctx.fillStyle = '#000000';
    const name = p.name || id;
    ctx.fillText(name, p.x, p.y);
    // Draw messages above square
    if (p.messages) {
      for (let i = 0; i < p.messages.length; i++) {
        const msg = p.messages[p.messages.length - 1 - i];
        ctx.fillText(msg.text, p.x, p.y - 10 - i * 14);
      }
    }
  }
}

// Keyboard handling for movement and chat
const keys = { up: false, down: false, left: false, right: false };
let chatMode = false;

document.addEventListener('keydown', e => {
  if (e.key === 'Enter') {
    // Toggle chat mode
    if (!chatMode) {
      chatMode = true;
      chatInput.style.display = 'block';
      chatInput.focus();
    } else {
      const text = chatInput.value.trim();
      if (text) {
        socket.emit('chat', text);
        addMessage(myId, text);
      }
      chatInput.value = '';
      chatInput.style.display = 'none';
      chatMode = false;
      render();
    }
    return;
  }

  if (chatMode) return; // don't move when typing
  switch (e.key) {
    case 'ArrowUp':
    case 'w':
    case 'W':
      if (!keys.up) {
        keys.up = true;
        socket.emit('moveStart', { dir: 'up' });
      }
      break;
    case 'ArrowDown':
    case 's':
    case 'S':
      if (!keys.down) {
        keys.down = true;
        socket.emit('moveStart', { dir: 'down' });
      }
      break;
    case 'ArrowLeft':
    case 'a':
    case 'A':
      if (!keys.left) {
        keys.left = true;
        socket.emit('moveStart', { dir: 'left' });
      }
      break;
    case 'ArrowRight':
    case 'd':
    case 'D':
      if (!keys.right) {
        keys.right = true;
        socket.emit('moveStart', { dir: 'right' });
      }
      break;
  }
});

document.addEventListener('keyup', e => {
  if (chatMode) return;
  switch (e.key) {
    case 'ArrowUp':
    case 'w':
    case 'W':
      if (keys.up) {
        keys.up = false;
        socket.emit('moveStop');
      }
      break;
    case 'ArrowDown':
    case 's':
    case 'S':
      if (keys.down) {
        keys.down = false;
        socket.emit('moveStop');
      }
      break;
    case 'ArrowLeft':
    case 'a':
    case 'A':
      if (keys.left) {
        keys.left = false;
        socket.emit('moveStop');
      }
      break;
    case 'ArrowRight':
    case 'd':
    case 'D':
      if (keys.right) {
        keys.right = false;
        socket.emit('moveStop');
      }
      break;
  }
});

// Prevent chat input keystrokes from propagating to document
chatInput.addEventListener('keydown', e => {
  e.stopPropagation();
});
