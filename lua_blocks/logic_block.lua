local M = {}

local block_id_g
local is_on = false

function M.init(id, config, inputs, outputs)
    block_id_g = id
    is_on = config.default_state or false
    py_log_from_lua("Logic block '" .. block_id_g .. "' initialized with state: " .. tostring(is_on))
    py_set_mqtt_output(block_id_g, "state", is_on)
end

function M.on_input(input_name, value)
    if input_name == "toggle" then
        if value == true or value == "true" then
            is_on = not is_on
            py_log_from_lua("Logic block '" .. block_id_g .. "' toggled. New state: " .. tostring(is_on))
            py_set_mqtt_output(block_id_g, "state", is_on)
        end
    end
end

return M