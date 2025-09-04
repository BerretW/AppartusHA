import requests
import json
import sys

# Adresa, na které běží váš backend
BASE_URL = "http://localhost:5001/api"

def set_http_input(endpoint, value):
    """Sends a POST request to a specific HttpInput block endpoint."""
    if not endpoint.startswith('/'):
        endpoint = '/' + endpoint
    
    url = f"{BASE_URL}/input{endpoint}"
    payload = {"value": value}
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status() # Zkontroluje, zda nenastala HTTP chyba (jako 4xx nebo 5xx)
        print("OK. Odpověď serveru:")
        print(json.dumps(response.json(), indent=2))
    except requests.exceptions.RequestException as e:
        print(f"Chyba při odesílání požadavku na {url}: {e}")

def get_status(topic=None):
    """Sends a GET request to retrieve the status."""
    if topic:
        url = f"{BASE_URL}/status/{topic}"
    else:
        url = f"{BASE_URL}/status"
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        print("OK. Odpověď serveru:")
        print(json.dumps(response.json(), indent=2))
    except requests.exceptions.RequestException as e:
        print(f"Chyba při odesílání požadavku na {url}: {e}")

def print_help():
    print("\n--- HTTP Tester příkazy ---")
    print("  post <endpoint> <value>  - Pošle hodnotu na HTTP vstup (např. 'post /pocasi/teplota 21.5')")
    print("  get                      - Získá stav všech témat")
    print("  get <topic>              - Získá stav konkrétního tématu (např. 'get smarthome/light/hall/1/status')")
    print("  help                     - Zobrazí tuto nápovědu")
    print("  exit                     - Ukončí tester")
    print("----------------------------\n")

def main():
    print_help()
    while True:
        try:
            # Použijeme sys.stdout.flush() pro zajištění správného zobrazení promptu
            print("> ", end='', flush=True)
            user_input = sys.stdin.readline().strip().split()
            
            if not user_input:
                continue

            command = user_input[0].lower()

            if command == 'exit':
                break
            elif command == 'help':
                print_help()
            elif command == 'post':
                if len(user_input) < 3:
                    print("Chyba: 'post' vyžaduje endpoint a hodnotu. Příklad: post /pocasi/teplota 25")
                else:
                    endpoint = user_input[1]
                    value = " ".join(user_input[2:])
                    set_http_input(endpoint, value)
            elif command == 'get':
                if len(user_input) > 1:
                    topic = user_input[1]
                    get_status(topic)
                else:
                    get_status()
            else:
                print(f"Neznámý příkaz: '{command}'. Napište 'help' pro nápovědu.")

        except (KeyboardInterrupt, EOFError):
            print("\nUkončuji...")
            break

if __name__ == '__main__':
    main()