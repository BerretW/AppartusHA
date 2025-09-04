import lupa
import os
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BlockManager:
    def __init__(self, mqtt_client, hardware_interface, lua_block_dir="lua_blocks"):
        self.mqtt_client = mqtt_client
        self.hardware_interface = hardware_interface
        self.lua_block_dir = lua_block_dir
        self.blocks = {} # block_id -> BlockInstance
        self.block_instances = {} # block_id -> {lua_runtime, config, inputs, outputs, etc.}
        self.lua_runtime = lupa.LuaRuntime(unpack_returned_tuples=True) # Global Lua runtime instance

        # Exponování Python funkcí do Lua prostředí
        # Tímto se Lua bloky mohou "zeptat" Pythonu na stav hardwaru nebo publikovat MQTT zprávy.
        self.lua_runtime.globals().set_mqtt_output = self._lua_set_mqtt_output
        self.lua_runtime.globals().get_hardware_input = self._lua_get_hardware_input
        self.lua_runtime.globals().set_hardware_output = self._lua_set_hardware_output
        self.lua_runtime.globals().log_from_lua = lambda msg: logger.info(f"[LUA_BLOCK] {msg}")
        
    def _lua_set_mqtt_output(self, block_id, output_name, value):
        # Voláno z Lua bloku, aby publikoval na MQTT
        block_info = self.block_instances.get(block_id)
        if block_info and output_name in block_info['outputs']:
            topic = block_info['outputs'][output_name]
            self.mqtt_client.publish(topic, value)
        else:
            logger.warning(f"Lua block {block_id} tried to publish on unknown output '{output_name}'")

    def _lua_get_hardware_input(self, block_id, input_type, pin_or_addr):
        # Voláno z Lua bloku, aby četl z hardwaru
        # input_type: "digital", "analog", "dali_status", etc.
        if input_type == "digital":
            return self.hardware_interface.read_digital_input(pin_or_addr)
        elif input_type == "analog":
            return self.hardware_interface.read_analog_input(pin_or_addr)
        # Další typy vstupů (např. DALI stav, teplota z RS485) by se přidaly zde
        else:
            logger.warning(f"Lua block {block_id} requested unknown hardware input type: {input_type}")
            return None

    def _lua_set_hardware_output(self, block_id, output_type, pin_or_addr, value):
        # Voláno z Lua bloku, aby ovládal hardware
        # output_type: "digital", "dali_brightness", etc.
        if output_type == "digital":
            self.hardware_interface.write_digital_output(pin_or_addr, value)
        elif output_type == "dali_brightness":
            self.hardware_interface.set_dali_brightness(pin_or_addr, value)
        # Další typy výstupů (např. RS485 data) by se přidaly zde
        else:
            logger.warning(f"Lua block {block_id} requested unknown hardware output type: {output_type}")


    def load_blocks_from_config(self, config_data):
        for block_data in config_data.get("blocks", []):
            block_id = block_data['id']
            block_type = block_data['type']
            lua_script_file = block_data.get('lua_script')
            block_config = block_data.get('config', {})
            block_inputs = block_data.get('inputs', {})
            block_outputs = block_data.get('outputs', {})

            if not lua_script_file:
                logger.warning(f"Block {block_id} has no 'lua_script' specified. Skipping Lua initialization.")
                continue

            lua_path = os.path.join(self.lua_block_dir, lua_script_file)
            if not os.path.exists(lua_path):
                logger.error(f"Lua script '{lua_path}' for block {block_id} not found.")
                continue

            try:
                with open(lua_path, 'r') as f:
                    lua_code = f.read()
                
                # Vytvoříme samostatné Lua prostředí pro každý blok (sandbox)
                # Důležité pro izolaci bloků a bezpečnost
                block_lua_env = self.lua_runtime.execute(lua_code) # Executes the script, populating a new global table
                
                # Inicializujeme blok, pokud má funkci 'init'
                if hasattr(block_lua_env, 'init'):
                    block_lua_env.init(block_id, block_config, block_inputs, block_outputs)
                
                self.block_instances[block_id] = {
                    'type': block_type,
                    'lua_env': block_lua_env, # Reference to the Lua environment of this block
                    'config': block_config,
                    'inputs': block_inputs,
                    'outputs': block_outputs
                }
                logger.info(f"Loaded Lua block '{block_id}' from '{lua_path}'")

                # Pro každý výstup bloku, pokud je to MQTT topic, se přihlásíme (i když publikujeme my)
                # a pro vstupy se přihlásíme k jejich zdrojovým topicům
                for output_name, topic in block_outputs.items():
                    # Zde se přihlašujeme k výstupním tématům, abychom mohli monitorovat nebo zpracovávat publikované hodnoty
                    # A také se to hodí pro to, když si blok "přeje" být upozorněn, že něco publikoval on sám.
                    self.mqtt_client.subscribe(topic, self._handle_mqtt_message_for_block)
                
                for input_name, input_info in block_inputs.items():
                    if "source_block_id" in input_info:
                        # Vstupy propojené z jiných bloků (interní MQTT komunikace)
                        source_block = self.block_instances.get(input_info["source_block_id"])
                        if source_block and input_info["source_output"] in source_block['outputs']:
                            topic = source_block['outputs'][input_info["source_output"]]
                            self.mqtt_client.subscribe(topic, self._handle_mqtt_message_for_block)
                        else:
                             logger.warning(f"Input '{input_name}' for block {block_id} refers to non-existent source.")
                    elif "hardware_input" in input_info:
                        # Hardwarové vstupy - zde se bude dít polling nebo event-driven
                        pass # Polling bude v hlavní smyčce

            except Exception as e:
                logger.error(f"Error loading Lua script for block {block_id}: {e}")

    def _handle_mqtt_message_for_block(self, topic, payload):
        # Tato callback funkce je volána, když dorazí MQTT zpráva
        # Musíme zjistit, který blok je tím ovlivněn (jako vstup nebo pro interní logiku)
        for block_id, block_info in self.block_instances.items():
            # Check if this topic is one of its inputs from another block
            for input_name, input_def in block_info['inputs'].items():
                if "source_block_id" in input_def:
                    source_block_info = self.block_instances.get(input_def["source_block_id"])
                    if source_block_info and input_def["source_output"] in source_block_info['outputs']:
                        source_topic = source_block_info['outputs'][input_def["source_output"]]
                        if source_topic == topic:
                            self._call_lua_input_handler(block_id, input_name, payload)
                            break # Assume one input connection per topic for now
            
            # Check if this topic is one of its own outputs (for internal state updates or logging)
            # This allows blocks to react to their own published outputs if needed.
            for output_name, output_topic in block_info['outputs'].items():
                if output_topic == topic:
                    # Not strictly an input, but a notification that this block's output topic received a message
                    # Could trigger a 'on_output_received' or similar Lua function if defined.
                    pass # Or handle specific cases

    def _call_lua_input_handler(self, block_id, input_name, value):
        block_instance = self.block_instances.get(block_id)
        if block_instance and hasattr(block_instance['lua_env'], 'on_input'):
            try:
                block_instance['lua_env'].on_input(input_name, value)
            except Exception as e:
                logger.error(f"Error calling on_input for block {block_id}, input {input_name}: {e}")

    def process_block_logic(self):
        # Tato funkce se volá pravidelně (např. v hlavní smyčce)
        # Zde se zpracovává logika bloků, které nejsou čistě event-driven z MQTT
        # Např. čtení hardwarových vstupů, časové události atd.
        for block_id, block_info in self.block_instances.items():
            # Zde můžeme kontrolovat hardwarové vstupy
            for input_name, input_def in block_info['inputs'].items():
                if "hardware_input" in input_def:
                    hw_type = input_def["hardware_input"]["type"]
                    hw_pin_or_addr = input_def["hardware_input"]["address"]
                    
                    # Implementace pro detekci změny hardwarového vstupu
                    # V reálném systému by to bylo složitější (detekce hran, debouncing)
                    # Zde jen načteme aktuální hodnotu a pošleme ji jako "input" do Lua bloku
                    current_value = None
                    if hw_type == "digital":
                        current_value = self.hardware_interface.read_digital_input(hw_pin_or_addr)
                    elif hw_type == "analog":
                        current_value = self.hardware_interface.read_analog_input(hw_pin_or_addr)
                    
                    if current_value is not None:
                        # Zde by se měla implementovat logika pro detekci ZMĚNY
                        # a jen při změně volat on_input. Pro jednoduchost voláme vždy
                        # a logika detekce změny může být v Lua bloku nebo v HardwareInterface
                        if hasattr(block_info['lua_env'], 'on_hardware_input_change'):
                            block_info['lua_env'].on_hardware_input_change(input_name, current_value)
                        
                        # Můžeme také předat jako standardní on_input
                        self._call_lua_input_handler(block_id, input_name, current_value)


            # Volání hlavní logiky bloku (pokud má funkci 'run' nebo 'update')
            if hasattr(block_info['lua_env'], 'run'):
                try:
                    block_info['lua_env'].run()
                except Exception as e:
                    logger.error(f"Error calling run for block {block_id}: {e}")