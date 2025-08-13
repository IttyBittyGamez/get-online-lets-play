import asyncio
import websockets
import json
import random

players = {}
connected = set()
next_id = 1

adjectives = ['Brave', 'Clever', 'Quick', 'Lucky', 'Sneaky']
nouns = ['Fox', 'Tiger', 'Rabbit', 'Bear', 'Wolf']

def random_name():
    """Generate a random player name."""
    return f"{random.choice(adjectives)} {random.choice(nouns)}"

def random_color():
    """Generate a random hex colour string."""
    return f"{random.randint(0, 0xFFFFFF):06x}"

async def broadcast(message):
    """Broadcast a JSON-serialisable message to all connected clients."""
    if connected:
        data = json.dumps(message)
        await asyncio.gather(*(ws.send(data) for ws in connected), return_exceptions=True)

async def register_player(websocket):
    """Register a new player when a websocket connects."""
    global next_id
    pid = str(next_id)
    next_id += 1
    player = {
        'id': pid,
        'name': random_name(),
        'x': random.randint(0, 780),
        'y': random.randint(0, 580),
        'direction': None,
        'moving': False,
        'color': random_color()
    }
    players[pid] = player
    # Send current players and your own info to the new client
    await websocket.send(json.dumps({'type': 'currentPlayers', 'players': players}))
    await websocket.send(json.dumps({'type': 'yourInfo', 'id': pid, 'name': player['name'], 'color': player['color']}))
    # Notify others about the new player
    await broadcast({'type': 'newPlayer', 'player': player})
    return pid

async def unregister_player(pid):
    """Remove a player when they disconnect and notify others."""
    if pid in players:
        del players[pid]
        await broadcast({'type': 'playerDisconnected', 'id': pid})

async def handler(websocket):
    """Handle incoming websocket connections and messages."""
    connected.add(websocket)
    pid = await register_player(websocket)
    try:
        async for msg in websocket:
            try:
                data = json.loads(msg)
            except json.JSONDecodeError:
                continue
            mtype = data.get('type')
            if mtype in ('moveStart', 'movestart'):
                direction = data.get('dir') or data.get('direction')
                if direction in ('up', 'down', 'left', 'right'):
                    players[pid]['direction'] = direction
                    players[pid]['moving'] = True
            elif mtype in ('moveStop', 'movestop'):
                players[pid]['moving'] = False
            elif mtype == 'chat':
                text = data.get('text', '')
                await broadcast({'type': 'chat', 'id': pid, 'text': text})
    except websockets.exceptions.ConnectionClosed:
        pass
    finally:
        connected.remove(websocket)
        await unregister_player(pid)

async def handler_wrapper(websocket, path=None):
    """Compat wrapper for websockets versions that pass a path."""
    await handler(websocket)

async def game_loop():
    """Main game loop to update player positions and broadcast state."""
    SPEED = 3
    TICK_RATE = 30
    while True:
        # iterate over a copy to avoid RuntimeError if players are removed

        
        for p in list(players.values()):
            if p['moving']:
                if p['direction'] == 'up':
                    p['y'] -= SPEED
                elif p['direction'] == 'down':
                    p['y'] += SPEED
                elif p['direction'] == 'left':
                    p['x'] -= SPEED
                elif p['direction'] == 'right':
                    p['x'] += SPEED
        await broadcast({'type': 'state', 'players': players})
        await asyncio.sleep(1 / TICK_RATE)

async def main():
    """Start the websocket server and the game loop."""
    async with websockets.serve(handler_wrapper, '0.0.0.0', 8765):
        await game_loop()

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
