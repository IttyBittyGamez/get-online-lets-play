import asyncio
import json
import random
import math
from typing import Dict, Any, List, Tuple

# ===== Game constants =====
WIDTH, HEIGHT = 800, 600
TICK_RATE = 30.0           # server ticks per second
SPEED = 3.0                # px per tick, forward/back
ROTATE_SPEED = 3.0         # degrees per tick
PROJ_SPEED = 8.0           # projectile px per tick
PROJ_LIFETIME = 2.0        # seconds

# ===== State =====
players: Dict[str, Dict[str, Any]] = {}
connections: Dict[asyncio.StreamWriter, str] = {}
projectiles: List[Dict[str, Any]] = []
next_id = 1

ANIMALS = [
    "Aardvark", "Badger", "Cheetah", "Dolphin", "Eagle", "Fox", "Giraffe",
    "Hippo", "Iguana", "Jaguar", "Koala", "Lemur", "Meerkat", "Narwhal",
    "Otter", "Panda", "Quokka", "Raccoon", "Seal", "Tiger", "Urchin",
    "Viper", "Wolf", "Xerus", "Yak", "Zebra"
]

def random_color() -> str:
    return f"#{random.randint(0, 0xFFFFFF):06x}"

def clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))

async def send(writer: asyncio.StreamWriter, obj: dict):
    data = (json.dumps(obj) + "\n").encode("utf-8")
    writer.write(data)
    await writer.drain()

async def broadcast(obj: dict):
    data = (json.dumps(obj) + "\n").encode("utf-8")
    for w in list(connections.keys()):
        try:
            w.write(data)
            await w.drain()
        except Exception:
            # Ignore failed sends; cleanup happens on read loop end/close
            pass

async def handle_client(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
    global next_id
    addr: Tuple[str, int] = writer.get_extra_info("peername")  # (ip, port)
    pid = str(next_id); next_id += 1

    # Register player
    name = random.choice(ANIMALS) + str(random.randint(10, 99))
    color = random_color()
    players[pid] = {
        "id": pid,
        "name": name,
        "color": color,
        "x": float(random.randint(40, WIDTH - 40)),
        "y": float(random.randint(40, HEIGHT - 40)),
        "angle": 0.0,  # degrees; 0 = right, +90 = down
        "inputs": {"up": False, "down": False, "left": False, "right": False},
        "chat": []
    }
    connections[writer] = pid

    print(f"Client {pid} connected from {addr}")

    # Send initial info/state
    await send(writer, {"type": "yourInfo", "you": players[pid]})
    await send(writer, {"type": "currentPlayers", "players": players})
    await broadcast({"type": "newPlayer", "player": players[pid]})

    try:
        while True:
            line = await reader.readline()
            if not line:
                break
            try:
                msg = json.loads(line.decode("utf-8"))
            except Exception:
                continue

            t = msg.get("type")
            if t == "moveStart":
                d = msg.get("dir")
                if d in players[pid]["inputs"]:
                    players[pid]["inputs"][d] = True
            elif t == "moveStop":
                d = msg.get("dir")
                if d in players[pid]["inputs"]:
                    players[pid]["inputs"][d] = False
            elif t == "chat":
                txt = msg.get("text", "")[:140]
                if txt:
                    await broadcast({
                        "type": "chat",
                        "id": pid,
                        "text": txt
                    })
            elif t == "shoot":
                p = players.get(pid)
                if p:
                    projectiles.append({
                        "x": float(p["x"]),
                        "y": float(p["y"]),
                        "angle": float(p["angle"]),   # degrees
                        "owner": pid,
                        "ticks": int(PROJ_LIFETIME * TICK_RATE)
                    })
    except Exception:
        # Read loop error; treat as disconnect
        pass
    finally:
        # Cleanup on disconnect
        connections.pop(writer, None)
        if pid in players:
            await broadcast({"type": "playerDisconnected", "id": pid})
            players.pop(pid, None)
        print(f"Client {pid} disconnected")
        try:
            writer.close()
            await writer.wait_closed()
        except Exception:
            pass

async def game_loop():
    tick = 1.0 / TICK_RATE
    while True:
        # Apply inputs to players
        for p in list(players.values()):
            inp = p["inputs"]

            # rotation (left = -1, right = +1)
            rot_dir = (-1 if inp["left"] else 0) + (1 if inp["right"] else 0)
            p["angle"] = (p["angle"] + rot_dir * ROTATE_SPEED) % 360.0

            # forward/back (relative to facing)
            move = (1.0 if inp["up"] else 0.0) + (-1.0 if inp["down"] else 0.0)
            if move != 0.0:
                rad = math.radians(p["angle"])  # 0=right, +90=down
                p["x"] += math.cos(rad) * SPEED * move
                p["y"] += math.sin(rad) * SPEED * move
                p["x"] = clamp(p["x"], 10, WIDTH - 10)
                p["y"] = clamp(p["y"], 10, HEIGHT - 10)

        # Update projectiles
        expired_indices = []
        for i, pr in enumerate(projectiles):
            rad = math.radians(pr["angle"])
            pr["x"] += math.cos(rad) * PROJ_SPEED
            pr["y"] += math.sin(rad) * PROJ_SPEED
            pr["ticks"] -= 1
            if (pr["ticks"] <= 0 or
                pr["x"] < 0 or pr["x"] > WIDTH or
                pr["y"] < 0 or pr["y"] > HEIGHT):
                expired_indices.append(i)
        for i in reversed(expired_indices):
            projectiles.pop(i)

        # Broadcast current state
        await broadcast({"type": "state", "players": players, "projectiles": projectiles})

        await asyncio.sleep(tick)

async def main(host: str = "0.0.0.0", port: int = 8765):
    server = await asyncio.start_server(handle_client, host, port)
    print(f"Server started on {host}:{port}")
    async with server:
        loop_task = asyncio.create_task(game_loop())
        try:
            await server.serve_forever()
        except asyncio.CancelledError:
            pass
        finally:
            loop_task.cancel()
            await asyncio.gather(loop_task, return_exceptions=True)

async def shutdown():
    # Gracefully close all clients
    for w in list(connections.keys()):
        try:
            w.close()
            await w.wait_closed()
        except Exception:
            pass
    players.clear()
    connections.clear()
    projectiles.clear()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Server shutting down…")
        asyncio.run(shutdown())
