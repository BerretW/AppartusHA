import paho.mqtt.client as mqtt
from paho.mqtt.client import CallbackAPIVersion
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MQTTClient:
    def __init__(self, broker_host, broker_port, state_cache, client_id="rpi_smarthome_backend"):
        self.client = mqtt.Client(CallbackAPIVersion.VERSION1, client_id)
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message
        self.broker_host = broker_host
        self.broker_port = broker_port
        self.subscriptions = {}
        self.message_handlers = {}
        self.state_cache = state_cache

    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            logger.info(f"Connected to MQTT Broker at {self.broker_host}:{self.broker_port}!")
            
            # <-- ZMĚNA: Přihlásíme se k odběru všech témat pro plnění cache
            client.subscribe("#")
            logger.info("Subscribed to wildcard topic '#' to populate state cache.")

            # Původní přihlašování k odběrům pro bloky stále zůstává
            for topic in self.subscriptions:
                self.client.subscribe(topic)
                logger.info(f"Subscribed to: {topic}")
        else:
            logger.error(f"Failed to connect, return code {rc}\n")

    def _on_message(self, client, userdata, msg):
        topic = msg.topic
        payload = msg.payload.decode()
        logger.debug(f"Received `{payload}` from `{topic}`")

        # Aktualizace cache se nyní provede pro každou zprávu
        if self.state_cache:
            self.state_cache.set(topic, payload)

        # Předání zprávy handlerům (logice bloků)
        if topic in self.message_handlers:
            for handler in self.message_handlers[topic]:
                handler(topic, payload)
        
        for sub_topic, handlers in self.message_handlers.items():
            if '#' in sub_topic or '+' in sub_topic:
                if mqtt.topic_matches_sub(sub_topic, topic) and sub_topic != topic:
                    for handler in handlers:
                        handler(topic, payload)
    
    # ... zbytek souboru je beze změny ...
    def connect(self):
        try:
            self.client.connect(self.broker_host, self.broker_port, 60)
            self.client.loop_start()
        except Exception as e:
            logger.error(f"Error connecting to MQTT broker: {e}")

    def disconnect(self):
        self.client.loop_stop()
        self.client.disconnect()
        logger.info("Disconnected from MQTT Broker.")

    def publish(self, topic, payload, qos=0, retain=False):
        if not isinstance(payload, str):
            try:
                payload = json.dumps(payload)
            except TypeError:
                payload = str(payload)
                
        self.client.publish(topic, payload, qos, retain)
        logger.debug(f"Published `{payload}` to `{topic}`")

    def subscribe(self, topic, callback_func):
        if topic not in self.subscriptions:
            # Stále si pamatujeme, co chtějí bloky, pro případ znovupřipojení
            self.subscriptions[topic] = True
            # Fyzické přihlášení k odběru se už děje v on_connect
        
        if topic not in self.message_handlers:
            self.message_handlers[topic] = []
        
        if callback_func not in self.message_handlers[topic]:
            self.message_handlers[topic].append(callback_func)
            
        logger.info(f"Registered callback for topic: {topic}")