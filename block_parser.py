# FILE: block_parser.py
import os
import re

def parse_lua_block_info(file_path):
    """ Přečte a naparsuje speciální @blockinfo komentář z Lua souboru. """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        match = re.search(r'--\[\[\s*@blockinfo(.*?)@endblockinfo\s*\]\]--', content, re.DOTALL)
        if not match:
            return None

        info_str = match.group(1)
        info = {'inputs': [], 'outputs': [], 'fields': []}
        
        for line in info_str.strip().split('\n'):
            if '=' in line:
                key, value = [p.strip() for p in line.split('=', 1)]
                if key in ['inputs', 'outputs']:
                    if value: info[key] = [v.strip() for v in value.split(',')]
                else:
                    info[key] = value

            elif line.strip().startswith((' ' * 4)): # Detekce pole
                parts = [p.strip() for p in line.strip().split(';')]
                if len(parts) >= 3:
                    field = {'name': parts[0], 'label': parts[1], 'type': parts[2]}
                    if len(parts) > 3: field['placeholder'] = parts[3]
                    info['fields'].append(field)
        
        return info

    except Exception:
        return None

def get_all_block_definitions(lua_dir):
    """ Projde složku a vytvoří slovník definic pro všechny platné Lua bloky. """
    definitions = {}
    for filename in os.listdir(lua_dir):
        if filename.endswith('.lua'):
            block_name = filename.replace('.lua', '')
            info = parse_lua_block_info(os.path.join(lua_dir, filename))
            if info:
                # Interní jméno typu bloku odvodíme od názvu souboru bez "_block"
                type_name = ''.join(word.capitalize() for word in block_name.replace('_block','').split('_'))
                info['lua'] = filename
                definitions[type_name] = info
    return definitions