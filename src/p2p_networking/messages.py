import json

class Message:
    def __init__(self, data):
        self.data = data

    @property
    def type(self):
        raise NotImplementedError("Subclasses must define the message type")
    
    def to_dict(self):
        return {
            'type': self.type,
            'body': self.data
        }
    
    def to_json(self):
        return json.dumps(self.to_dict())

class SystemMessage(Message):
    @property
    def type(self):
        return 'system'
    
class UserMessage(Message):
    @property
    def type(self):
        return 'user'
    
class MessageFactory:
    @staticmethod
    def get_message(json_data: str) -> Message:
        try:
            data = json.loads(json_data)
            msg_type = data.get('type', None)
            body = data.get('body', None)

            if msg_type == None:
                return None
            elif msg_type == 'system':
                return SystemMessage(body)
            elif msg_type == 'user':
                return UserMessage(body)
            else:
                raise ValueError(f"Unknown message type: {msg_type}")
        except json.JSONDecodeError:
            return None