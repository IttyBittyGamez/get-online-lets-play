const socket = io();

const canvas = document.getElementById('gameCanvas');
const ctx = canvas.getContext('2d');
const chatInput = document.getElementById('chatInput');

let players = {};
let myId = null;

// Helper to add chat message to a player with timeout
function addMessage(playerId, text) {
    const msgObj = { text };
    if (!players[playerId].messages) players[playerId].messages = [];
    players[playerId].messages.push(msgObj);
    // Keep only last 2 messages
    if (players[playerId].messages.length > 2) {
        players[playerId].messages.shift();
    }
    setTimeout(() => {
        const list = players[playerId].messages;
        const idx = list.indexOf(msgObj);
        if (idx !== -1) list.splice(idx, 1);
    }, 5000);
}

// Listen for server events
socket.on('currentPlayers', (data) => {
    players = data;
});
socket.on('yourInfo', (info) => {
    myId = info.id;
    players[info.id] = info;
});
socket.on('newPlayer', (player) => {
    players[player.id] = player;
});
socket.on('playerDisconnected', (id) => {
    delete players[id];
});
socket.on('state', (state) => {
    for (const id in state) {
        if (players[id]) {
            players[id].x = state[id].x;
            players[id].y = state[id].y;
        }
    }
});
socket.on('chat', (data) => {
    addMessage(data.id, data.text);
});

// Input handling
const keys = {};
document.addEventListener('keydown', (e) => {
    if (e.target === chatInput) return;
    if (e.key === 'Enter') {
        chatInput.style.display = 'block';
        chatInput.focus();
        return;
    }
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

document.addEventListener('keyup', (e) => {
    if (e.target === chatInput) return;
    switch (e.key) {
        case 'ArrowUp':
        case 'w':
        case 'W':
            if (keys.up) {
                keys.up = false;
                socket.emit('moveStop', { dir: 'up' });
            }
            break;
        case 'ArrowDown':
        case 's':
        case 'S':
            if (keys.down) {
                keys.down = false;
                socket.emit('moveStop', { dir: 'down' });
            }
            break;
        case 'ArrowLeft':
        case 'a':
        case 'A':
            if (keys.left) {
                keys.left = false;
                socket.emit('moveStop', { dir: 'left' });
            }
            break;
        case 'ArrowRight':
        case 'd':
        case 'D':
            if (keys.right) {
                keys.right = false;
                socket.emit('moveStop', { dir: 'right' });
            }
            break;
    }
});

// Chat input submission
chatInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') {
        const text = chatInput.value.trim();
        if (text) {
            socket.emit('chat', text);
            if (myId) {
                addMessage(myId, text);
            }
        }
        chatInput.value = '';
        chatInput.style.display = 'none';
    }
});

// Predictive movement update
let lastTime = performance.now();
const speed = 150; // pixels per second
function gameLoop(timestamp) {
    const dt = (timestamp - lastTime) / 1000;
    lastTime = timestamp;
    const me = players[myId];
    if (me) {
        if (keys.up) me.y -= speed * dt;
        if (keys.down) me.y += speed * dt;
        if (keys.left) me.x -= speed * dt;
        if (keys.right) me.x += speed * dt;
    }
    draw();
    requestAnimationFrame(gameLoop);
}

// Drawing function
function draw() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    for (const id in players) {
        const p = players[id];
        const size = 20;
        ctx.fillStyle = p.color || '#0f0';
        ctx.fillRect(p.x - size / 2, p.y - size / 2, size, size);
        ctx.fillStyle = '#fff';
        ctx.font = '12px Arial';
        ctx.textAlign = 'center';
        ctx.fillText(p.name || id, p.x, p.y - size / 2 - 10);
        if (p.messages) {
            for (let i = 0; i < p.messages.length; i++) {
                const msg = p.messages[p.messages.length - 1 - i];
                ctx.fillText(msg.text, p.x, p.y - size / 2 - 25 - i * 15);
            }
        }
    }
}

requestAnimationFrame(gameLoop);
