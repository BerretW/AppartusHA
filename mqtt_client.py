import paho.mqtt.client as mqtt
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MQTTClient:
    def __init__(self, broker_host, broker_port, client_id="rpi_smarthome_backend"):
        self.client = mqtt.Client(client_id)
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message
        self.broker_host = broker_host
        self.broker_port = broker_port
        self.subscriptions = {} # topic -> callback_func
        self.message_handlers = {} # topic -> list of callback_funcs

    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            logger.info(f"Connected to MQTT Broker at {self.broker_host}:{self.broker_port}!")
            for topic in self.subscriptions:
                self.client.subscribe(topic)
                logger.info(f"Subscribed to: {topic}")
        else:
            logger.error(f"Failed to connect, return code {rc}\n")

    def _on_message(self, client, userdata, msg):
        topic = msg.topic
        payload = msg.payload.decode()
        logger.debug(f"Received `{payload}` from `{topic}`")

        # Call all registered handlers for this topic
        if topic in self.message_handlers:
            for handler in self.message_handlers[topic]:
                handler(topic, payload)
        
        # Check for wildcard subscriptions
        for sub_topic, handlers in self.message_handlers.items():
            if '#' in sub_topic or '+' in sub_topic:
                # Basic wildcard matching (can be improved for full MQTT spec)
                if mqtt.topic_matches_sub(sub_topic, topic):
                    for handler in handlers:
                        handler(topic, payload)

    def connect(self):
        try:
            self.client.connect(self.broker_host, self.broker_port, 60)
            self.client.loop_start() # Start non-blocking loop
        except Exception as e:
            logger.error(f"Error connecting to MQTT broker: {e}")

    def disconnect(self):
        self.client.loop_stop()
        self.client.disconnect()
        logger.info("Disconnected from MQTT Broker.")

    def publish(self, topic, payload, qos=0, retain=False):
        # Convert non-string payloads to string (e.g., JSON dumps for dicts)
        if not isinstance(payload, str):
            try:
                payload = json.dumps(payload)
            except TypeError:
                logger.warning(f"Payload for topic '{topic}' is not string or JSON-serializable. Sending as-is.")
                payload = str(payload)
                
        self.client.publish(topic, payload, qos, retain)
        logger.debug(f"Published `{payload}` to `{topic}`")

    def subscribe(self, topic, callback_func):
        if topic not in self.subscriptions:
            self.client.subscribe(topic)
            self.subscriptions[topic] = True # Mark as subscribed
        
        if topic not in self.message_handlers:
            self.message_handlers[topic] = []
        self.message_handlers[topic].append(callback_func)
        logger.info(f"Registered callback for topic: {topic}")