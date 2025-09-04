-- lua_blocks/digital_input_block.lua
-- Tento blok sleduje digitální vstup (např. tlačítko) a publikuje jeho stav.

local block_id_g
local block_config_g
local block_inputs_g
local block_outputs_g
local last_state = false
local last_press_time = 0
local double_click_timeout = 500 -- ms

function init(id, config, inputs, outputs)
    block_id_g = id
    block_config_g = config
    block_inputs_g = inputs
    block_outputs_g = outputs

    log_from_lua("Digital Input block " .. block_id_g .. " initialized for pin " .. block_config_g.input_pin)
    -- Nastavení pinu jako vstup (pouze simulace v Pythonu)
    -- hardware_interface.set_pin_mode(block_config_g.input_pin, 'INPUT')
end

-- Tato funkce je volána z Pythonu, když se detekuje změna na hardwarovém vstupu
function on_hardware_input_change(input_name, current_state)
    log_from_lua("Hardware input '" .. input_name .. "' on pin " .. block_config_g.input_pin .. " changed to: " .. tostring(current_state))
    
    if current_state ~= last_state then
        last_state = current_state
        set_mqtt_output(block_id_g, "state", current_state) -- Publikovat nový stav

        if current_state == true then -- Pokud je tlačítko stisknuto
            local current_time = os.clock() * 1000 -- current time in ms
            if current_time - last_press_time < double_click_timeout then
                log_from_lua("Double click detected!")
                set_mqtt_output(block_id_g, "double_click", true)
            end
            last_press_time = current_time
        end
    end
end

-- Funkce pro periodické zpracování (pokud by se dělal polling namísto event-driven)
function run()
    -- Zde by se mohlo dít polling pinu, ale pro demo předpokládáme on_hardware_input_change
    -- local current_hw_state = get_hardware_input(block_id_g, "digital", block_config_g.input_pin)
    -- if current_hw_state ~= last_state then
    --     on_hardware_input_change("hardware_input_state", current_hw_state)
    -- end
end