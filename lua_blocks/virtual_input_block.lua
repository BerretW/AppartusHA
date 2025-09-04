-- lua_blocks/virtual_input_block.lua
-- Tento blok slouží jako brána pro externí MQTT zprávy.
-- Jednoduše vezme hodnotu ze svého vstupu a publikuje ji na svém výstupu.

local block_id_g

function init(id, config, inputs, outputs)
    block_id_g = id
    log_from_lua("Virtual Input block '" .. block_id_g .. "' initialized.")
end

function on_input(input_name, value)
    log_from_lua("Virtual Input '" .. block_id_g .. "' received '" .. tostring(value) .. "' on input '" .. input_name .. "'. Forwarding to output.")
    -- Předpokládáme, že má právě jeden výstup nazvaný "value"
    set_mqtt_output(block_id_g, "value", value)
end