import asyncio
import websockets
import json
import random

players = {}
connected = set()
next_id = 1
ws_to_id = {}

adjectives = ['Brave','Clever','Quick','Lucky','Sneaky']
nouns = ['Fox','Tiger','Rabbit','Bear','Wolf']

def random_name():
    """Generate a random player name."""
    return f"{random.choice(adjectives)} {random.choice(nouns)}"

def random_color():
    """Generate a random hex colour string with leading #."""
    return f"#{random.randint(0, 0xFFFFFF):06x}"

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
    players[pid] = {
        'id': pid,
        'name': random_name(),
        'x': random.randint(50, 550),
        'y': random.randint(50, 350),
        'direction': '',
        'moving': False,
        'color': random_color(),
    }
    ws_to_id[websocket] = pid
    connected.add(websocket)
    # send existing players and your id to new player
    await websocket.send(json.dumps({'type': 'currentPlayers', 'players': players}))
    await websocket.send(json.dumps({'type': 'yourInfo', 'id': pid}))
    # notify others
    await broadcast({'type': 'newPlayer', 'player': players[pid]})
    return pid

async def unregister_player(websocket):
    """Handle player disconnection."""
    pid = ws_to_id.get(websocket)
    if pid:
        players.pop(pid, None)
        ws_to_id.pop(websocket, None)
        connected.discard(websocket)
        await broadcast({'type': 'playerDisconnected', 'id': pid})

async def handler(websocket):
    """Handle incoming websocket connection."""
    pid = await register_player(websocket)
    try:
        async for message in websocket:
            data = json.loads(message)
            mtype = data.get('type')
            if not mtype:
                continue
            mtype_lower = mtype.lower()
            if mtype_lower == 'movestart':
                direction = data.get('dir') or data.get('direction')
                if direction and pid in players:
                    players[pid]['direction'] = direction
                    players[pid]['moving'] = True
            elif mtype_lower == 'movestop':
                if pid in players:
                    players[pid]['moving'] = False
            elif mtype_lower == 'chat':
                text = data.get('text')
                if text:
                    await broadcast({'type': 'chat', 'id': pid, 'text': text})
    except websockets.ConnectionClosed:
        pass
    finally:
        await unregister_player(websocket)

async def game_loop():
    """Main game loop to update player positions and broadcast state."""
    SPEED = 3
    TICK_RATE = 30
    while True:
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
    async with websockets.serve(handler_wrapper, '0.0.0.0', 3000):
        await game_loop()

async def handler_wrapper(websocket, path=None):
    """Compatibility wrapper accepting optional path argument."""
    await handler(websocket)

if __name__ == '__main__':
    asyncio.run(main())
