import time
import json
import logging
import os

from mqtt_client import MQTTClient
from hardware_interface import HardwareInterface
from block_manager import BlockManager
from state_cache import StateCache
from web_server import run_web_server

# Nastavení formátu logování pro lepší přehlednost
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

CONFIG_FILE = "config.json"
LUA_BLOCK_DIR = "lua_blocks"

def load_config(filepath):
    """Načte konfiguraci ze souboru JSON."""
    if not os.path.exists(filepath):
        logger.error(f"Configuration file not found: {filepath}")
        return None
    try:
        with open(filepath, 'r') as f:
            config = json.load(f)
        logger.info(f"Configuration loaded from {filepath}")
        return config
    except json.JSONDecodeError as e:
        logger.error(f"Error decoding JSON from {filepath}: {e}")
        return None

def main():
    logger.info("Starting Smart Home Backend...")

    # Načtení centrální konfigurace
    config = load_config(CONFIG_FILE)
    if not config:
        logger.critical("Could not load configuration. Exiting.")
        return

    # 1. Vytvoření cache, která bude držet poslední stavy MQTT témat pro monitorování (GET požadavky)
    state_cache = StateCache()

    # 2. Inicializace hardwarového rozhraní (simulovaného)
    hw_interface = HardwareInterface()
    
    # 3. Inicializace MQTT klienta
    # Předáme mu referenci na cache, aby ji mohl automaticky plnit
    mqtt_broker_host = config.get("mqtt_broker_host", "localhost")
    mqtt_broker_port = config.get("mqtt_broker_port", 1883)
    
    mqtt_client = MQTTClient(mqtt_broker_host, mqtt_broker_port, state_cache)
    mqtt_client.connect()

    # 4. Inicializace správce bloků, který je srdcem logiky
    block_manager = BlockManager(mqtt_client, hw_interface, LUA_BLOCK_DIR)
    block_manager.load_blocks_from_config(config)

    # 5. Spuštění webového serveru v samostatném vlákně
    # Předáme mu správce bloků a konfiguraci, aby mohl dynamicky vytvořit HTTP vstupy (POST endpointy)
    # Také mu předáme cache pro monitorovací endpointy (GET)
    run_web_server(block_manager, config.get("blocks", []), state_cache)

    # 6. Hlavní smyčka aplikace
    # Tato smyčka se neustále opakuje a volá logiku bloků (např. pro polling hardwaru)
    logger.info("Backend is running. Press Ctrl+C to exit.")
    try:
        while True:
            block_manager.process_block_logic()
            time.sleep(0.1)  # Krátká pauza pro snížení zátěže CPU

    except KeyboardInterrupt:
        logger.info("Shutting down...")
    finally:
        # Čisté ukončení MQTT klienta
        mqtt_client.disconnect()
        logger.info("Backend stopped.")

if __name__ == '__main__':
    main()