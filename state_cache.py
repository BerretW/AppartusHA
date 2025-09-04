import threading

class StateCache:
    """A thread-safe class to store the latest state of MQTT topics."""
    def __init__(self):
        self._states = {}
        self._lock = threading.Lock()

    def set(self, topic, value):
        """Sets the value for a given topic."""
        with self._lock:
            self._states[topic] = value

    def get(self, topic):
        """Gets the value for a given topic."""
        with self._lock:
            return self._states.get(topic)

    def get_all(self):
        """Returns a copy of all stored states."""
        with self._lock:
            return self._states.copy()