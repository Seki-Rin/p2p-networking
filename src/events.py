from collections import defaultdict
import messages

class Event:
    pass

class NodeDiscoveredEvent(Event):

    def __init__(self, node_id: str, node_metadata:dict):
        self.node_id = node_id
        self.node_metadata = node_metadata

class NodeLostEvent(Event):

    def __init__(self, node_id):
        self.node_id = node_id

class MessageReceivedEvent(Event):

    def __init__(self, message: messages.Message, uid: str):
        self.message = message
        self.node_id = uid

class EventBus:

    def __init__(self):
        self._subscribers = defaultdict(list)

    async def publish(self, event: Event):
        if type(event) in self._subscribers:
            for handler in self._subscribers[type(event)]:
                await handler(event)

    def subscribe(self, event_type: type[Event], handler: callable):
        self._subscribers[event_type].append(handler)
