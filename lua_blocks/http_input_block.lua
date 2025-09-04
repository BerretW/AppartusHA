--[[
@blockinfo
title = HTTP Vstup
color = #2980b9
inputs = 
outputs = value
fields = 
    endpoint; Endpoint; str; /pocasi/teplota
@endblockinfo
]]--

local M = {}

local block_id_g

function M.init(id, config, inputs, outputs)
    block_id_g = id
    py_log_from_lua("HTTP Input block '" .. id .. "' initialized for endpoint '" .. config.endpoint .. "'")
end

function M.on_input(input_name, value)
    py_log_from_lua("HTTP Input '" .. block_id_g .. "' received value: " .. tostring(value))
    py_set_mqtt_output(block_id_g, "value", value)
end

return M