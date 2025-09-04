--[[
@blockinfo
title = Logika: Osvětlení
color = #f1c40f
inputs = power_button, motion_sensor, daylight_sensor, master_switch
outputs = state, brightness
fields = 
    default_on; Výchozí stav ZAPNUTO; bool
    default_brightness; Výchozí jas (%); int; 100
@endblockinfo
]]--

local M = {}

local block_id_g
local config_g
local is_on = false
local brightness = 100

function M.init(id, config, inputs, outputs)
    block_id_g = id
    config_g = config -- Uložíme si celou config tabulku
    
    --[[
        Bezpečný přístup k hodnotám.
        'config_g.default_on' může být nil. Pokud je, 'or false' zajistí,
        že 'is_on' bude mít vždy platnou hodnotu.
    ]]--
    is_on = (config_g.default_on == true) -- Explicitní kontrola na true
    brightness = config_g.default_brightness or 100

    py_log_from_lua("Lighting Logic block '" .. id .. "' initialized. State: " .. tostring(is_on))
    
    -- Publikujeme počáteční stav
    py_set_mqtt_output(block_id_g, "state", is_on)
    py_set_mqtt_output(block_id_g, "brightness", brightness)
end

function M.on_input(input_name, value)
    if input_name == "power_button" then
        if value == true or value == "true" then
            is_on = not is_on
            py_log_from_lua("Lighting Logic '" .. block_id_g .. "' toggled. New state: " .. tostring(is_on))
            py_set_mqtt_output(block_id_g, "state", is_on)
        end
    end
end

return M