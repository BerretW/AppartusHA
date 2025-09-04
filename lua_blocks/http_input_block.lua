-- lua_blocks/http_input_block.lua
-- Tento blok reprezentuje HTTP endpoint. Když Python přijme data na tento
-- endpoint, zavolá funkci on_input tohoto bloku.

local block_id_g

function init(id, config, inputs, outputs)
    block_id_g = id
    log_from_lua("HTTP Input block '" .. id .. "' initialized for endpoint '" .. config.endpoint .. "'")
end

-- Tuto funkci zavolá přímo Python web server, když přijme data.
-- V tomto případě 'input_name' nebude mít velký význam.
function on_input(input_name, value)
    log_from_lua("HTTP Input '" .. block_id_g .. "' received value: " .. tostring(value))
    -- Hodnotu rovnou pošleme na jediný výstup bloku, typicky nazvaný "value"
    set_mqtt_output(block_id_g, "value", value)
end