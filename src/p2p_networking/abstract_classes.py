from abc import ABC, abstractmethod
from typing import Any
from p2p_networking import events
import messages

class Discovery(ABC):

    def __init__(self, event_bus: events.EventBus):
        self.event_bus = event_bus
        self.discovered_nodes = {}
        self.uid = None
        self.addr = None
        self.port = None

    @abstractmethod
    async def start(self) -> None:
        pass

    @abstractmethod
    async def stop(self) -> None:
        pass

    def get_discovered_nodes(self) -> dict[str, Any]:
        return self.discovered_nodes.copy()

    async def publish_node_discovered_event(self, uid: str, nodedata: dict[str, Any]) -> None:
        event = events.NodeDiscoveredEvent(uid, nodedata)
        await self.event_bus.publish(event)

    async def publish_node_lost_event(self, uid: str) -> None:
        event = events.NodeLostEvent(uid)
        await self.event_bus.publish(event)

    def set_uid(self, uid: str) -> None:
        self.uid = uid

    def set_addr(self, addr:str) -> None:
        self.addr = addr

    def set_port(self, port:int) -> None:
        self.port = port

class Transport(ABC):

    def __init__(self, event_bus: events.EventBus):
        self.uid = None
        self.event_bus = event_bus
        self.addr = None
        self.port = None

    @abstractmethod
    async def start(self) -> None:
        pass

    @abstractmethod
    async def stop(self) -> None:
        pass

    @abstractmethod
    async def send_to_peer(self, uid: str, message: str) -> None:
        pass

    async def publish_message_received_event(self, message:messages.Message, uid: str) -> None:
        event = events.MessageReceivedEvent(message, uid)
        await self.event_bus.publish(event)

    def set_uid(self, uid: str) -> None:
        self.uid = uid

    def set_addr(self, addr:str) -> None:
        self.addr = addr

    def set_port(self, port:int) -> None:
        self.port = port