import threading
from flask import Flask, jsonify, request
import logging
from block_parser import get_all_block_definitions # <-- PŘIDAT IMPORT

log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

def run_web_server(block_manager, all_blocks_config, state_cache, lua_block_dir):
    """
    Spustí Flask server, který dynamicky vytvoří endpointy na základě konfigurace.
    """
    app = Flask(__name__)

    # --- Dynamické vytváření POST endpointů ---
    def create_post_handler(block_id):
        """
        Vytvoří a vrátí funkci, která bude obsluhovat POST request pro konkrétní blok.
        Toto je potřeba, aby se správně 'uzavřela' proměnná block_id.
        """
        def post_handler():
            data = request.get_json()
            if not data or 'value' not in data:
                return jsonify({"status": "error", "message": "Missing 'value' in JSON payload"}), 400
            
            value = data['value']
            
            # Místo publikování na MQTT zavoláme přímo handler v BlockManageru
            # 'http_input' je fiktivní název vstupu, protože Lua skript ho nepotřebuje
            block_manager._call_lua_input_handler(block_id, 'http_input', value)
            
            logging.getLogger(__name__).info(f"[HTTP] Injected value '{value}' into block '{block_id}'")
            return jsonify({"status": "success", "block_id": block_id, "value": value})
        return post_handler

    for block in all_blocks_config:
        if block.get('type') == 'HttpInput':
            endpoint_url = block.get('config', {}).get('endpoint')
            block_id = block.get('id')

            if not endpoint_url or not block_id:
                logging.warning(f"Skipping HttpInput block due to missing 'endpoint' or 'id'. Block data: {block}")
                continue
            
            # Ujistíme se, že endpoint začíná lomítkem
            if not endpoint_url.startswith('/'):
                endpoint_url = '/' + endpoint_url
            
            full_url = f"/api/input{endpoint_url}"
            
            # Zaregistrujeme novou URL cestu v aplikaci
            app.add_url_rule(
                full_url, 
                endpoint=block_id,  # Každý endpoint musí mít unikátní název
                view_func=create_post_handler(block_id), 
                methods=['POST']
            )
            logging.getLogger(__name__).info(f"Created HTTP endpoint: POST {full_url} for block '{block_id}'")

    # --- GET endpointy pro monitorování zůstávají stejné ---
    @app.route('/api/status', methods=['GET'])
    def get_all_statuses():
        return jsonify(state_cache.get_all())

    @app.route('/api/status/<path:topic>', methods=['GET'])
    def get_topic_status(topic):
        """Vrátí poslední známý stav konkrétního MQTT tématu z cache."""
        
        # --- LADICÍ VÝPIS ---
        all_cache_content = state_cache.get_all()
        print(f"DEBUG: Obsah cache v momentě dotazu na '{topic}': {all_cache_content}")
        
        value = state_cache.get(topic)
        if value is not None:
            return jsonify({"topic": topic, "value": value})
        else:
            return jsonify({"status": "error", "message": "Topic not found in cache"}), 404

    @app.route('/api/block-definitions', methods=['GET'])
    def get_definitions():
        try:
            definitions = get_all_block_definitions(lua_block_dir)
            return jsonify(definitions)
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    # --- Spuštění serveru ---
    def start_server():
        app.run(host='0.0.0.0', port=5001)

    server_thread = threading.Thread(target=start_server, daemon=True)
    server_thread.start()
    logging.getLogger(__name__).info("HTTP server is running on http://localhost:5001")