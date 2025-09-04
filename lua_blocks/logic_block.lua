-- lua_blocks/logic_block.lua
-- Tento blok implementuje jednoduchou logiku. Například "master switch".
-- Pokud obdrží na vstupu 'toggle' hodnotu 'true', změní svůj stav a publikuje ho.

local block_id_g
local is_on = false -- Vnitřní stav bloku

function init(id, config, inputs, outputs)
    block_id_g = id
    -- Načteme výchozí stav z konfigurace, pokud existuje
    is_on = config.default_state or false
    log_from_lua("Logic block '" .. block_id_g .. "' initialized with state: " .. tostring(is_on))
    -- Publikujeme počáteční stav
    set_mqtt_output(block_id_g, "state", is_on)
end

function on_input(input_name, value)
    if input_name == "toggle" then
        -- Očekáváme, že z tlačítka přijde 'true' při stisku
        if value == true or value == "true" then
            is_on = not is_on
            log_from_lua("Logic block '" .. block_id_g .. "' toggled. New state: " .. tostring(is_on))
            set_mqtt_output(block_id_g, "state", is_on)
        end
    end
end

-- Funkce run se volá periodicky a může sloužit např. k publikaci stavu
function run()
    -- Pro tento jednoduchý příklad není potřeba, stav se publikuje při změně.
end