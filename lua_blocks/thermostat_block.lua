--[[
@blockinfo
title = Termostat
color = #e67e22
inputs = current_temperature
outputs = heating_state
fields = 
    set_point; Cílová teplota; float; 21.5
@endblockinfo
]]--

local M = {}

local block_id_g
local set_point = 20
local heating_on = false

function M.init(id, config, inputs, outputs)
    block_id_g = id
    set_point = config.set_point or 20
    py_log_from_lua("Thermostat block '" .. id .. "' initialized with set point: " .. set_point .. " C.")
end

function M.on_input(input_name, value)
    if input_name == "current_temperature" then
        local temp = tonumber(value)
        if not temp then return end

        local should_be_on = (temp < set_point)

        if should_be_on ~= heating_on then
            heating_on = should_be_on
            py_log_from_lua("Heating state changed to: " .. tostring(heating_on))
            py_set_mqtt_output(block_id_g, "heating_state", heating_on)
        end
    end
end

return M