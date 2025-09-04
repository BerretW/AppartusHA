-- lua_blocks/logic_passthrough_block.lua
-- Tento blok jednoduše vezme hodnotu ze svého vstupu a přepošle ji
-- na všechny své definované výstupy. Funguje jako rozdvojka.

local M = {}

local block_id_g
local outputs_g

function M.init(id, config, inputs, outputs)
    block_id_g = id
    outputs_g = outputs -- Uložíme si tabulku výstupů
    py_log_from_lua("Logic Passthrough block '" .. id .. "' initialized.")
end

function M.on_input(input_name, value)
    py_log_from_lua("Passthrough block '" .. block_id_g .. "' received value: " .. tostring(value) .. ". Forwarding to all outputs.")
    
    -- Projdeme všechny definované výstupy a pošleme na ně přijatou hodnotu
    for output_name, _ in pairs(outputs_g) do
        py_set_mqtt_output(block_id_g, output_name, value)
    end
end

return M