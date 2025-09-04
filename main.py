import time
import json
import logging
import os

from mqtt_client import MQTTClient
from hardware_interface import HardwareInterface
from block_manager import BlockManager

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

    # 1. Načtení konfigurace
    config = load_config(CONFIG_FILE)
    if not config:
        logger