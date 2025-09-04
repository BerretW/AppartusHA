-- lua_blocks/http_output_block.lua
-- Tento blok pošle HTTP požadavek na základě přijatého vstupu.

local M = {}

local block_id_g
local block_config_g

function M.init(id, config, inputs, outputs)
    block_id_g = id
    block_config_g = config
    py_log_from_lua("HTTP Output block '" .. id .. "' initialized for URL: " .. config.url)
end

function M.on_input(input_name, value)
    if input_name == "set_state" then
        local state_bool = (value == true or value == "true")
        local payload = ""
        
        if state_bool then
            payload = block_config_g.payload_on
        else
            payload = block_config_g.payload_off
        end

        py_log_from_lua("HTTP Output '" .. block_id_g .. "' sending request. Payload: " .. payload)
        
        -- Voláme novou Python funkci, která umí posílat HTTP požadavky
        py_send_http_request(block_id_g, block_config_g.method, block_config_g.url, payload)
    end
end

return M