--[[
@blockinfo
title = Digitální Vstup
color = #27ae60
inputs = 
outputs = state, double_click
fields = 
    input_pin; Hardware Pin; int; 5
@endblockinfo
]]--

local M = {}

local block_id_g
local block_config_g
local last_state = false
local last_press_time = 0
local double_click_timeout = 500

function M.init(id, config, inputs, outputs)
    block_id_g = id
    block_config_g = config
    py_log_from_lua("Digital Input block " .. block_id_g .. " initialized for pin " .. block_config_g.input_pin)
end

function M.on_hardware_input_change(input_name, current_state)
    if current_state ~= last_state then
        last_state = current_state
        py_set_mqtt_output(block_id_g, "state", current_state)

        if current_state == true then
            local current_time = os.clock() * 1000
            if current_time - last_press_time < double_click_timeout then
                py_log_from_lua("Double click detected!")
                py_set_mqtt_output(block_id_g, "double_click", true)
            end
            last_press_time = current_time
        end
    end
end

return M