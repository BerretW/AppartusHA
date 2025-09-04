-- lua_blocks/digital_output_block.lua
-- Tento blok reprezentuje fyzický digitální výstup (např. GPIO pin).

local M = {}

local block_id_g
local block_config_g

function M.init(id, config, inputs, outputs)
    block_id_g = id
    block_config_g = config
    py_log_from_lua("Digital Output block '" .. id .. "' initialized for pin " .. config.output_pin)
end

function M.on_input(input_name, value)
    -- Očekáváme boolean hodnotu (true/false) na vstupu 'set_state'
    if input_name == "set_state" then
        local state_bool = (value == true or value == "true")
        py_log_from_lua("Digital Output '" .. block_id_g .. "' setting pin " .. block_config_g.output_pin .. " to " .. tostring(state_bool))
        py_set_hardware_output(block_id_g, "digital", block_config_g.output_pin, state_bool)
    end
end

return M