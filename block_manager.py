import lupa
import os
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BlockManager:
    def __init__(self, mqtt_client, hardware_interface, state_cache, lua_block_dir="lua_blocks"):
        """
        Inicializuje správce bloků.

        Args:
            mqtt_client: Instance MQTT klienta.
            hardware_interface: Instance hardwarového rozhraní.
            state_cache: Instance sdílené cache pro ukládání stavů MQTT témat.
            lua_block_dir: Cesta ke složce s Lua skripty.
        """
        self.mqtt_client = mqtt_client
        self.hardware_interface = hardware_interface
        self.lua_block_dir = lua_block_dir
        self.state_cache = state_cache
        self.blocks = {}
        self.block_instances = {}
        self.topic_map = {} # Pro rychlé mapování MQTT témat na bloky
        self.last_hw_states = {} # Pro detekci změn na hardwarových vstupech
        self.lua_runtime = lupa.LuaRuntime(unpack_returned_tuples=True)

        # Zpřístupnění Python funkcí pro volání z Lua skriptů
        self.lua_runtime.globals().set_mqtt_output = self._lua_set_mqtt_output
        self.lua_runtime.globals().get_hardware_input = self._lua_get_hardware_input
        self.lua_runtime.globals().set_hardware_output = self._lua_set_hardware_output
        self.lua_runtime.globals().log_from_lua = lambda msg: logger.info(f"[LUA_BLOCK] {msg}")

    def _lua_set_mqtt_output(self, block_id, output_name, value):
        """Voláno z Lua. Publikuje zprávu na MQTT a aktualizuje interní cache."""
        
        # --- LADICÍ VÝPIS 1 ---
        print(f"DEBUG: _lua_set_mqtt_output voláno pro blok '{block_id}' s hodnotou '{value}'. Pokus o zápis do cache.")
        
        block_info = self.block_instances.get(block_id)
        if block_info and output_name in block_info['outputs']:
            topic = block_info['outputs'][output_name]
            
            # --- LADICÍ VÝPIS 2 ---
            print(f"DEBUG: Aktualizuji cache pro téma '{topic}' s hodnotou '{value}'")
            
            self.state_cache.set(topic, str(value))
            self.mqtt_client.publish(topic, value)
        else:
            # --- LADICÍ VÝPIS 3 ---
            print(f"DEBUG: CHYBA - Nepodařilo se najít výstup '{output_name}' pro blok '{block_id}'")

    def _lua_get_hardware_input(self, block_id, input_type, pin_or_addr):
        """Voláno z Lua. Čte hodnotu z hardwarového rozhraní."""
        if input_type == "digital":
            return self.hardware_interface.read_digital_input(pin_or_addr)
        elif input_type == "analog":
            return self.hardware_interface.read_analog_input(pin_or_addr)
        else:
            logger.warning(f"Lua block {block_id} requested unknown hardware input type: {input_type}")
            return None

    def _lua_set_hardware_output(self, block_id, output_type, pin_or_addr, value):
        """Voláno z Lua. Nastavuje hodnotu na hardwarovém rozhraní."""
        if output_type == "digital":
            self.hardware_interface.write_digital_output(pin_or_addr, value)
        elif output_type == "dali_brightness":
            self.hardware_interface.set_dali_brightness(pin_or_addr, value)
        else:
            logger.warning(f"Lua block {block_id} requested unknown hardware output type: {output_type}")
    
    def _call_lua_input_handler(self, block_id, input_name, value):
        """
        Interní metoda pro bezpečné zavolání funkce 'on_input' v Lua skriptu bloku.
        Používá se pro předání dat z MQTT nebo přímo z HTTP serveru.
        """
        block_instance = self.block_instances.get(block_id)
        if block_instance and hasattr(block_instance['lua_env'], 'on_input'):
            try:
                # Pokus o konverzi běžných stringových reprezentací boolean hodnot
                if isinstance(value, str):
                    if value.lower() == 'true': value = True
                    elif value.lower() == 'false': value = False
                block_instance['lua_env'].on_input(input_name, value)
            except Exception as e:
                logger.error(f"Error calling on_input for block {block_id}, input {input_name}: {e}")

    def load_blocks_from_config(self, config_data):
        """Načte a inicializuje všechny bloky definované v konfiguračním objektu."""
        # První průchod: vytvoříme instance všech bloků a jejich Lua prostředí
        for block_data in config_data.get("blocks", []):
            block_id = block_data['id']
            lua_script_file = block_data.get('lua_script')
            
            if not lua_script_file:
                logger.warning(f"Block {block_id} has no 'lua_script' specified. Skipping.")
                continue

            lua_path = os.path.join(self.lua_block_dir, lua_script_file)
            if not os.path.exists(lua_path):
                logger.error(f"Lua script '{lua_path}' for block {block_id} not found.")
                continue
            
            try:
                with open(lua_path, 'r', encoding='utf-8') as f:
                    lua_code = f.read()

                block_lua_env = self.lua_runtime.execute(lua_code)
                self.block_instances[block_id] = {
                    'type': block_data.get('type'),
                    'lua_env': block_lua_env,
                    'config': block_data.get('config', {}),
                    'inputs': block_data.get('inputs', {}),
                    'outputs': block_data.get('outputs', {})
                }
            except Exception as e:
                logger.error(f"Error creating Lua environment for block {block_id}: {e}")

        # Druhý průchod: zavoláme 'init' funkce a propojíme vstupy/výstupy přes MQTT
        for block_id, block_info in self.block_instances.items():
            try:
                if hasattr(block_info['lua_env'], 'init'):
                    block_info['lua_env'].init(block_id, block_info['config'], block_info['inputs'], block_info['outputs'])
                
                logger.info(f"Loaded and initialized Lua block '{block_id}'")

                # Propojíme vstupy bloku s výstupy jiných bloků
                for input_name, input_info in block_info['inputs'].items():
                    if "source_block_id" in input_info:
                        source_block = self.block_instances.get(input_info["source_block_id"])
                        if source_block and input_info["source_output"] in source_block['outputs']:
                            topic = source_block['outputs'][input_info["source_output"]]
                            self.mqtt_client.subscribe(topic, self._handle_mqtt_message_for_block)
                            
                            if topic not in self.topic_map: self.topic_map[topic] = []
                            self.topic_map[topic].append({'block_id': block_id, 'input_name': input_name})
                        else:
                            logger.warning(f"Input '{input_name}' for block {block_id} refers to non-existent source.")
            
            except Exception as e:
                logger.error(f"Error initializing or wiring Lua script for block {block_id}: {e}")

    def _handle_mqtt_message_for_block(self, topic, payload):
        """Callback pro MQTT. Najde správný blok a předá mu zprávu."""
        if topic in self.topic_map:
            for target in self.topic_map[topic]:
                self._call_lua_input_handler(target['block_id'], target['input_name'], payload)

    def process_block_logic(self):
        """
        Hlavní logická smyčka, volaná periodicky. Zpracovává hardwarové vstupy
        a volá 'run' funkce v blocích.
        """
        for block_id, block_info in self.block_instances.items():
            # Zpracování hardwarových vstupů s detekcí změny
            for input_name, input_def in block_info['inputs'].items():
                if "hardware_input" in input_def:
                    hw_type = input_def["hardware_input"]["type"]
                    hw_pin_or_addr = input_def["hardware_input"]["address"]
                    
                    current_value = self._lua_get_hardware_input(block_id, hw_type, hw_pin_or_addr)
                    
                    if current_value is not None:
                        state_key = (block_id, input_name)
                        last_value = self.last_hw_states.get(state_key)
                        
                        if current_value != last_value:
                            self.last_hw_states[state_key] = current_value
                            if hasattr(block_info['lua_env'], 'on_hardware_input_change'):
                                block_info['lua_env'].on_hardware_input_change(input_name, current_value)
                            else:
                                self._call_lua_input_handler(block_id, input_name, current_value)

            # Volání periodické 'run' funkce v Lua skriptu, pokud existuje
            if hasattr(block_info['lua_env'], 'run'):
                try:
                    block_info['lua_env'].run()
                except Exception as e:
                    logger.error(f"Error calling run for block {block_id}: {e}")