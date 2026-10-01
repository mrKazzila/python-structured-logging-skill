from dataclasses import dataclass


@dataclass(frozen=True)
class Message:
    message_id: str
    correlation_id: str
    payload: dict
    attempt: int = 1


class Broker:
    """Fake adapter: dispositions are observable; payloads are never rewritten."""
    def __init__(self):
        self.dispositions = []

    def ack(self, message):
        self.dispositions.append((message.message_id, 'ack', message.attempt))

    def retry(self, message):
        self.dispositions.append((message.message_id, 'retry', message.attempt))

    def dead_letter(self, message):
        self.dispositions.append((message.message_id, 'dead_letter', message.attempt))
