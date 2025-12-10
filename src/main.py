from net import Net
from utils import get_main_local_ip
import tcp_transport
import broadcast_discovery
import events
import node
from pathlib import Path
from fastapi import FastAPI, WebSocket, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from starlette.websockets import WebSocketState
from contextlib import asynccontextmanager
from pydantic import BaseModel
import asyncio
import uvicorn
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

BASE_DIR = Path(__file__).resolve().parent.parent

class Message(BaseModel):
    body_of_message: str
net = Net((get_main_local_ip()))
event_bus = events.EventBus()
transport = tcp_transport.TcpTransport(event_bus)
discovery = broadcast_discovery.BroadcastManager(net.broadcast_address, event_bus)
gui_ws = None
peer = None
list_events = []

@asynccontextmanager
async def lifespan(app: FastAPI):
    global peer
    peer = node.Node((net.ip, net.mask), transport, discovery, event_bus)
    event_bus.subscribe(events.MessageReceivedEvent, on_message)
    event_bus.subscribe(events.NodeDiscoveredEvent, on_node_discovered)
    event_bus.subscribe(events.NodeLostEvent, on_node_lost)
    logging.info(f"Node's IP: {peer.node_addr} ID: {peer.node_uid}")
    await peer.start_network()
    logging.info(f"Server started")
    try:
        yield
    finally:
        await peer.stop_network()
app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],              # В продакшене лучше указать конкретные: ["http://127.0.0.1:8000", "http://localhost:8000"]
    allow_credentials=True,
    allow_methods=["*"],              # Разрешаем все методы (GET, POST, OPTIONS и т.д.)
    allow_headers=["*"],
)

async def on_node_discovered(event: events.NodeDiscoveredEvent):
    if gui_ws and gui_ws.application_state == WebSocketState.CONNECTED:
        try:
            message_info = {'event': 'NodeDiscovered', 'uid': event.node_id, 'node_info': event.node_metadata}
            await gui_ws.send_json(message_info)
        except Exception as e:
            logging.info(f'Непредвиденная ошибка: {e}')
    else:
        logging.info("⚠️ GUI не подключён — сообщение не отправлено")
        list_events.append(event)

async def on_node_lost(event: events.NodeLostEvent):
    if gui_ws and gui_ws.application_state == WebSocketState.CONNECTED:
        try:
            message_info = {'event': 'NodeLost', 'uid': event.node_id}
            await gui_ws.send_json(message_info)
        except Exception as e:
            logging.info(f'Непредвиденная ошибка: {e}')
    else:
        logging.info("⚠️ GUI не подключён — сообщение не отправлено")

async def on_message(event: events.MessageReceivedEvent):
    logging.info(f'message from {event.node_id}: {str(event.message.to_dict())}')
    if gui_ws and gui_ws.application_state == WebSocketState.CONNECTED:
        try:
            message_info = {'event': 'MessageReceived', 'uid': event.node_id, 'message': event.message.to_dict()}
            await gui_ws.send_json(message_info)
        except Exception as e:
            logging.info(f'Непредвиденная ошибка: {e}')
    else:
        logging.info("⚠️ GUI не подключён — сообщение не отправлено")

@app.websocket("/ws")
async def init_websocket_endpoint(websocket: WebSocket):
    global gui_ws
    await websocket.accept()
    gui_ws = websocket
    logging.info(f'GUI подключен')
    if len(list_events) > 0:
        for event in list_events:
            await on_node_discovered(event)

    try:
        while True:
            await asyncio.sleep(60)
    except Exception as e:
        logging.info(f'GUI отключился: {e}')
    finally:
        gui_ws = None

@app.post("/nodes/{uid}")
async def send_message(uid: str, message: Message):
    await peer.transport.send_to_peer(uid, message.body_of_message)
    return {"status": "ok", "to": uid, "body": message.body_of_message}

@app.get("/ping")
def ping():
    return {"status": "ok"}

app.mount("/static", StaticFiles(directory="."), name="static")

@app.get("/", response_class=HTMLResponse)
async def get_index():
    index_path = BASE_DIR / "web" / "index.html"
    with open(index_path, encoding="utf-8") as f:
        return f.read()

if __name__ == '__main__':
    uvicorn.run('main:app', host='127.0.0.1', port=8000, reload=True)