from abstract_classes import Transport, Discovery
import configparser
import events
import os
import uuid
import asyncio
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class Node:

    CONFIG_PATH = "config.ini"

    def __init__(self, ip_and_mask, transport: Transport, discovery: Discovery, event_bus: events.EventBus):
        self.ip_and_mask = ip_and_mask
        if None in self.ip_and_mask:
            raise RuntimeError("Не удалось определить IP и маску для локального интерфейса.")
        self.node_addr = self.ip_and_mask[0]
        self.nodes = {}
        self.event_bus = event_bus
        self.event_bus.subscribe(events.NodeDiscoveredEvent, self._on_node_discovered)
        self.event_bus.subscribe(events.NodeLostEvent, self._on_node_lost)
        self.transport = transport
        self.discovery = discovery
        self.settings = self.load_config()
        self.node_uid = self.settings.get('uid')
        self.transport.set_uid(self.node_uid)
        self.discovery.set_uid(self.node_uid)
        self.transport.set_addr(self.node_addr)
        self.discovery.set_addr(self.node_addr)
        self.transport.set_port(self.settings.get('transport_port'))
        self.discovery.set_port(self.settings.get('discovery_port'))
        
    async def _on_node_discovered(self, event: events.NodeDiscoveredEvent):
        self.nodes[event.node_id] = event.node_metadata

    async def _on_node_lost(self, event: events.NodeLostEvent):
        del self.nodes[event.node_id]

    def ensure_config_exists(self):
        if not os.path.exists(self.CONFIG_PATH):
            config = configparser.ConfigParser()

            config["network"] = {
                "DiscoveryPort": "50000",
                "TransportPort": "50001",
                "uid": str(uuid.uuid4()),
            }

            with open(self.CONFIG_PATH, "w") as configfile:
                config.write(configfile)
                
    def load_config(self) -> dict:
        self.ensure_config_exists()

        config = configparser.ConfigParser()
        config.read(self.CONFIG_PATH)

        network = config["network"]
        return {
            "discovery_port": int(network["DiscoveryPort"]),
            "transport_port": int(network["TransportPort"]),
            "uid": network["uid"],
        }
    
    async def start_network(self):
        asyncio.create_task(self.transport.start())
        logging.info('[Node] Transport started')
        await self.discovery.start()
        logging.info('[Node] Discovery started')

    async def stop_network(self):
        await self.transport.stop()
        await self.discovery.stop()
