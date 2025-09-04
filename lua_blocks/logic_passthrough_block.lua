--[[
@blockinfo
title = Logika: Rozdělovač
color = #8e44ad
inputs = trigger
outputs = output_1, output_2, output_3, output_4, output_5
fields = 
@endblockinfo
]]--

local M = {}

local block_id_g
local outputs_g

function M.init(id, config, inputs, outputs)
    block_id_g = id
    outputs_g = outputs
    py_log_from_lua("Logic Passthrough block '" .. id .. "' initialized.")
end

function M.on_input(input_name, value)
    py_log_from_lua("Passthrough block '" .. block_id_g .. "' received value: " .. tostring(value) .. ". Forwarding to all outputs.")
    
    for output_name, _ in pairs(outputs_g) do
        py_set_mqtt_output(block_id_g, output_name, value)
    end
end

return M