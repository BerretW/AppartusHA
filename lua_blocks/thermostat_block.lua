-- lua_blocks/thermostat_block.lua

local block_id_g
local set_point = 20 -- Teplota, pod kterou se má topit
local heating_on = false

function init(id, config, inputs, outputs)
    block_id_g = id
    -- Umožníme nastavit teplotu v config.json, jinak použijeme výchozí
    set_point = config.set_point or 20
    log_from_lua("Thermostat block '" .. id .. "' initialized with set point: " .. set_point .. " C.")
end

function on_input(input_name, value)
    if input_name == "current_temperature" then
        local temp = tonumber(value)
        if not temp then return end -- Pokud hodnota není číslo, ignorujeme ji

        log_from_lua("Thermostat received temperature: " .. temp .. " C.")

        local should_be_on = (temp < set_point)

        -- Změníme stav a publikujeme, pouze pokud došlo ke změně
        if should_be_on ~= heating_on then
            heating_on = should_be_on
            log_from_lua("Heating state changed to: " .. tostring(heating_on))
            set_mqtt_output(block_id_g, "heating_state", heating_on)
        end
    end
end