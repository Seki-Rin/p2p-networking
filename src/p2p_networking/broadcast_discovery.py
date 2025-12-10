from p2p_networking.abstract_classes import Discovery
from p2p_networking import events
import asyncio
import socket
import logging
import json
import time

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class UDPProtocol(asyncio.DatagramProtocol):

    def __init__(self, on_datagram_received, transport_ready):
        self.transport_ready = transport_ready
        self.on_datagram_received = on_datagram_received
        self.transport = None


    def connection_made(self, transport):
        try:
            self.transport = transport
            sock = transport.get_extra_info('socket')

            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

            self.transport_ready.set_result(transport)
        except Exception as e:
            logging.exception(f'[UDP Protocol] unexpected error: {e}')

    def datagram_received(self, data, addr):
        message = data.decode()
        self.on_datagram_received(message, addr)

    def error_received(self, exc):
        logging.error(f"[UDP Protocol] Error received: {exc}")
    
    def connection_lost(self, exc):
        self.transport = None


class BroadcastManager(Discovery):

    KEY_ID = 'id'
    KEY_IP = 'ip'
    KEY_ACTION = 'action'
    BROADCAST_INTERVAL = 10
    CLEANUP_INTERVAL = 10
    NODE_TIMEOUT = 30

    def __init__(self, broadcast_addr: "None | str", event_bus: events.EventBus):
        super().__init__(event_bus)
        self.broadcast_address = broadcast_addr
        self.transport = None
        self.protocol_instance = None
        self.sending_task: asyncio.Task = None
        self.cleaning_task: asyncio.Task = None
        self.lock = asyncio.Lock()
    
    def set_broadcast_addr(self, addr: str):
        self.broadcast_address = addr

    async def start(self):
        loop = asyncio.get_running_loop()
        if self.broadcast_address is not None and self.addr is not None:
            transport_ready = loop.create_future()
            self.transport, self.protocol_instance = await loop.create_datagram_endpoint(
                lambda: UDPProtocol(self._on_datagram_received, transport_ready),
                local_addr=('0.0.0.0', self.port),
                family=socket.AF_INET,
                proto=socket.IPPROTO_UDP,
                allow_broadcast=True
            )

            await asyncio.wait_for(transport_ready, timeout=5)

            self.sending_task = asyncio.create_task(self._schedule_broadcasts())
            self.cleaning_task = asyncio.create_task(self._cleanup_nodes())
        else:
            raise ValueError('[Broadcast Manager] Broadcast address or node address is None')
    
    async def stop(self):
        if self.transport:
            await self._say_goodbye()
            self.transport.close()
            if self.sending_task:
                self.sending_task.cancel()
                try:
                    await self.sending_task
                except asyncio.CancelledError:
                    logging.info("[Broadcast Manager] The message sending task was successfully cancelled.")
            if self.cleaning_task:
                self.cleaning_task.cancel()
                try:
                    await self.cleaning_task
                except asyncio.CancelledError:
                    logging.info("[Broadcast Manager] The cleanup nodes task was successfully cancelled.")
            self.transport = None
            self.protocol_instance = None
            self.sending_task = None
            self.cleaning_task = None

    async def _send_message(self, message:str):
        if not self.transport:
            return
        try:
            self.transport.sendto(message.encode(),(self.broadcast_address, self.port))
        except Exception as e:
            logging.exception(f'[Broadcast Manager] unexpected error: {e}')

    def _on_datagram_received(self, message, addr):
        try:
            data = json.loads(message)
            action = data.get(self.KEY_ACTION)
            uid = data.get(self.KEY_ID)
            ip = data.get(self.KEY_IP)
            node_data = {self.KEY_IP: ip, 'last_seen': time.time()}
            if uid and ip and uid != self.uid:
                if action == 'hello':
                    asyncio.create_task(self._update_nodes(uid, node_data))
                elif action == 'bye':
                    asyncio.create_task(self._delete_node(uid))
                    logging.info(f'[Broadcast Manager] Received a farewell message from {uid}')
        except json.JSONDecodeError:
            logging.warning(f'[Broadcast Manager] incorrect JSON in message from {addr}: {message}')
        except KeyError as e:
            logging.warning(f'[Broadcast Manager] Expected field {e} missing in message from {addr}: {message}')
        except Exception as e:
            logging.error(f'[Broadcast Manager] unexpected error processing message from {addr}: {e}')
    
    async def _delete_node(self, uid):
        node_info = self.discovered_nodes.get(uid, None)
        if node_info:
            async with self.lock:
                del self.discovered_nodes[uid]
            logging.info(f"[Broadcast Manager] Node {uid} was deleted from the list")
            await self.publish_node_lost_event(uid)
        else:
            logging.warning(f"[Broadcast Manager] Attempt to delete non-existent node: {uid}.")
    
    async def _update_nodes(self, uid, node_data):
        async with self.lock:
            is_new_node = uid not in self.discovered_nodes
            self.discovered_nodes[uid] = node_data
        node_info = {self.KEY_IP: node_data[self.KEY_IP]}
        if is_new_node:
            await self.publish_node_discovered_event(uid, node_info)
            logging.info(f"[Broadcast Manager] Discovered the new node {uid}. Total: {len(self.discovered_nodes)}")

    async def _say_goodbye(self):
        message_data = {
            self.KEY_ACTION: 'bye',
            self.KEY_ID: self.uid,
            self.KEY_IP: self.addr
        }
        message = json.dumps(message_data)
        try:
            for _ in range(3):    
                await self._send_message(message)
                await asyncio.sleep(0.3)
        except Exception as e:
            logging.warning(f"[Broadcast Manager] Failed to send goodbye message: {e}")

    async def _schedule_broadcasts(self):
        while True:
            message_data = {
                self.KEY_ACTION: 'hello',
                self.KEY_ID: self.uid,
                self.KEY_IP: self.addr
            }
            message = json.dumps(message_data)
            await self._send_message(message)
            await asyncio.sleep(self.BROADCAST_INTERVAL)

    async def _cleanup_nodes(self):
        while True:
            current_time = time.time()
            async with self.lock:
                expired = [uid for uid, data in self.discovered_nodes.items() if current_time - data['last_seen'] > self.NODE_TIMEOUT]
                for uid in expired:
                    await self._delete_node(uid)
            await asyncio.sleep(self.CLEANUP_INTERVAL)