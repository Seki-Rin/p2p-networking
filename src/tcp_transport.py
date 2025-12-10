from abstract_classes import Transport
import messages
import events
import asyncio
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class PeerConnection:

    def __init__(self, id:str, ip: str, on_message: callable, on_connection_lost: callable, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        self.uid = id
        self.ip = ip
        self.on_message = on_message
        self.on_connection_lost = on_connection_lost
        self.writer = writer
        self.reader = reader
        self._is_closing = False
        self._listen_task: asyncio.Task = None
        self._keep_alive_task: asyncio.Task = None

    def set_listen_task(self, task):
        self._listen_task = task

    def set_keep_alive_task(self, task):
        self._keep_alive_task = task

    async def send_message(self, message:str):
        encoded_message = message.encode()
        length = len(encoded_message).to_bytes(4, 'big')
        try:
            self.writer.write(length + encoded_message)
            await self.writer.drain()
        except ConnectionResetError:
            await self.on_connection_lost(self.uid, self.ip)
        except Exception as e:
            logging.warning(f'[PeerConnection] [{self.uid}]: Error sending message: {e}')
    
    async def _receive_message(self):
        length_bytes = await self.reader.readexactly(4)
        length = int.from_bytes(length_bytes, 'big')
        message = await self.reader.readexactly(length)
        return message.decode()
    
    async def close(self):
        if self._is_closing:
            return
        self._is_closing = True
        self.writer.close()
        await self.writer.wait_closed()
        if self._listen_task:
            self._listen_task.cancel()
            try:
                await self._listen_task
            except asyncio.CancelledError:
                pass
        if self._keep_alive_task:
            self._keep_alive_task.cancel()
            try:
                await self._keep_alive_task
            except asyncio.CancelledError:
                pass
        logging.info(f'[PeerConnection] [{self.uid}]: Connection closed')
    
    async def start_listen(self):
        try:
            while True:
                try:
                    message = await self._receive_message()
                    await self.on_message(message, self.uid)
                except asyncio.IncompleteReadError as e:
                    if e.partial == b'':
                        await asyncio.sleep(0.1)
                        continue
                    else:
                        logging.info(f'[PeerConnection] [{self.uid}]: The connection was not completely broken: {e}')
                        await self.on_connection_lost(self.uid, self.ip)
                        break
        except (ConnectionResetError , asyncio.IncompleteReadError) as e:
            logging.info(f'[PeerConnection] [{self.uid}]: The connection was lost due to an error: {e}')
            await self.on_connection_lost(self.uid, self.ip)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logging.warning(f'[PeerConnection] [{self.uid}]: unexpected error: {e}')
    
    async def start_keep_alive(self, interval=10):
        try:
            while not self._is_closing:
                await asyncio.sleep(interval)
                try:
                    await self.send_message('__keepalive__')
                except Exception as e:
                    logging.warning(f'[TcpTransport] [{self.uid}]: Failed to send keepalive: {e}')
                    break
        except asyncio.CancelledError:
            pass

class TcpTransport(Transport):
     
    def __init__(self, event_bus):
        super().__init__(event_bus)
        self.peer_connections = {}
        self._server = None
        self.lock = asyncio.Lock()
        self.event_bus.subscribe(events.NodeLostEvent, self.delete_peer)
        self.event_bus.subscribe(events.NodeDiscoveredEvent, self.open_connection)

    async def delete_peer(self, event: events.NodeLostEvent):
        peer = None
        uid = event.node_id
        async with self.lock:
            if uid in self.peer_connections.keys():
                    peer, _ = self.peer_connections[uid]
                    del self.peer_connections[uid]
        if peer:
            await peer.close()
            logging.info(f'PeerConnection object was closed for {uid}')

               

    async def _on_connected(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        try:
            length_bytes = await reader.readexactly(4)
            length = int.from_bytes(length_bytes, 'big')
            message_data = await reader.readexactly(length)
            message = messages.MessageFactory.get_message(message_data.decode())
            if message == None:
                writer.close()
                await writer.wait_closed()
                return
            elif message.type == 'system':
                ip = message.data.get('ip')
                id = message.data.get('id')
                logging.info(f"[TcpTransport] New connection from {ip}")
                await self._create_peer_connection(id, ip, reader, writer)
                logging.info(f"[TcpTransport] PeerConnection object was created for [{id}]")
        except Exception as e:
            logging.warning(f'[TcpTransport] unexpected error: {e}')

    async def start(self):
        self._server = await asyncio.start_server(self._on_connected,self.addr, self.port)
        async with self._server:
            await self._server.serve_forever()
    
    async def stop(self):
        if self._server:
            self._server.close()
            await self._server.wait_closed()
            self._server = None
            async with self.lock:
                peer_ids = list(self.peer_connections.keys())
                for peer_id in peer_ids:
                    peer_info = self.peer_connections.get(peer_id)
                    peer, _ = peer_info
                    del self.peer_connections[peer_id]
                asyncio.create_task(peer.close())
            logging.info('[TcpTransport] Server stopped')
        
    async def _create_peer_connection(self, id, ip, reader, writer):
        peer: PeerConnection = PeerConnection(id, ip, self._on_message, self._on_connection_lost, reader, writer)
        listen_task = asyncio.create_task(peer.start_listen())
        keep_alive_task = asyncio.create_task(peer.start_keep_alive())
        peer.set_keep_alive_task(keep_alive_task)
        peer.set_listen_task(listen_task)
        async with self.lock:
            self.peer_connections[id] = (peer, listen_task)
        return peer

    async def _on_connection_lost(self, id, ip):
        asyncio.create_task(self._try_reconnect(id, ip))

    async def _try_reconnect(self, id, ip):
        try:
            async with self.lock:
                pair = self.peer_connections.get(id, None)
                peer = None
                if pair:
                    peer, _ = pair
                if peer:
                    del self.peer_connections[id]
            if peer:
                await peer.close()
                for i in range(3):
                    try:
                        await self.open_connection(id, ip, self.port)
                        break
                    except ConnectionRefusedError:
                        logging.info(f"[TcpTransport] [{id}]: Reconnection attempt {i+1} failed (connection refused)")
                    if i < 2:
                        await asyncio.sleep(0.5)
        except Exception as e:
            logging.warning(f'[TcpTransport] unexpected error:{e}')

    async def open_connection(self, event: events.NodeDiscoveredEvent):
        logging.info(f'[TcpTransport] NodeDiscoveredEvent detected, open_connection started')
        id = event.node_id
        ip = event.node_metadata.get('ip')
        async with self.lock:
            if id in self.peer_connections:
                return
        if id > self.uid:
            logging.info(f"[TcpTransport] Connecting to node {id} at address {ip} via TCP")
            try:
                reader, writer = await asyncio.open_connection(ip, self.port)
                peer = await self._create_peer_connection(id, ip, reader, writer)
                message_data = {'id': self.uid, 'ip': self.addr}
                message = messages.SystemMessage(message_data)
                await peer.send_message(message.to_json())
                logging.info(f"[TcpTransport] Connected and sent system message to [{id}]")
            except ConnectionRefusedError as e:
                logging.info(f'[TcpTransport] Unable to connect: {e}')
            except Exception as e:
                logging.warning(f'[TcpTransport] unexpected error: {e}')
        else:
            return
    
    async def send_to_peer(self, uid, message_data):
        peer: PeerConnection = None
        async with self.lock:
            pair = self.peer_connections.get(uid, None)
            if pair:
                peer, _ = pair
        if peer:
            message = messages.UserMessage(message_data)
            await peer.send_message(message.to_json())
        else:
            logging.info(f'[TcpTransport] No connection to {uid}')


    async def _on_message(self, message_data, uid):
        if message_data == '__keepalive__':
            return
        message = messages.MessageFactory.get_message(message_data)
        await self.publish_message_received_event(message, uid)