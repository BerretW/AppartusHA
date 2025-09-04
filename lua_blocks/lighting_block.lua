-- lua_blocks/lighting_block.lua
-- Tento blok ovládá osvětlení v místnosti
-- Exponované Python funkce:
--   set_mqtt_output(block_id, output_name, value)
--   get_hardware_input(block_id, input_type, pin_or_addr)
--   set_hardware_output(block_id, output_type, pin_or_addr, value)
--   log_from_lua(message)

-- Globální proměnné pro tento Lua blok
local current_brightness = 0
local block_id_g
local block_config_g
local block_inputs_g
local block_outputs_g

-- Funkce pro inicializaci bloku
function init(id, config, inputs, outputs)
    block_id_g = id
    block_config_g = config
    block_inputs_g = inputs
    block_outputs_g = outputs
    
    current_brightness = block_config_g.default_brightness or 0
    log_from_lua("Lighting block " .. block_id_g .. " initialized with default brightness: " .. current_brightness)
    
    -- Nastavíme počáteční stav výstupu
    if block_config_g.output_pin then
        set_hardware_output(block_id_g, "digital", block_config_g.output_pin, current_brightness > 0)
    end
    -- Pokud podporuje stmívání přes DALI nebo PWM, bylo by to zde
end

-- Funkce volaná, když dorazí MQTT zpráva pro vstup tohoto bloku
function on_input(input_name, value)
    log_from_lua("Input " .. input_name .. " received value: " .. tostring(value))

    if input_name == "power_button" then
        if value == true or value == "true" then -- Předpokládáme digitální stav ON
            if current_brightness > 0 then
                current_brightness = 0 -- Zhasnout
            else
                current_brightness = block_config_g.default_brightness -- Rozsvítit na výchozí
            end
            apply_brightness()
        end
    elseif input_name == "motion_sensor" then
        if value == true or value == "true" then
            log_from_lua("Motion detected in " .. block_id_g .. ", turning on light.")
            current_brightness = block_config_g.default_brightness or 100
            apply_brightness()
        else
            log_from_lua("Motion ceased in " .. block_id_g .. ", turning off light after delay (simulated).")
            -- Zde by se implementovala logika zhasnutí po určité době neaktivity
            -- Pro jednoduchost hned zhasneme
            current_brightness = 0
            apply_brightness()
        end
    elseif input_name == "daylight_sensor" then
        local lux = tonumber(value)
        if lux then
            log_from_lua("Daylight sensor reading: " .. lux .. " lux")
            -- Zde by se mohla implementovat logika automatického stmívání/rozsvěcování
            -- podle denního světla. Např. pokud je dost světla, zhasnout, jinak rozsvítit.
            -- Pro jednoduchost jen logujeme.
        end
    end
end

-- Funkce pro periodické zpracování (např. čtení hardwaru, časovače)
function run()
    -- Zde se může dít polling hardwarových vstupů, pokud nejsou event-driven
    -- Například kontrola stavu fyzického vypínače, pokud by to nebylo řešeno MQTT
    -- local hw_button_state = get_hardware_input(block_id_g, "digital", block_config_g.input_pin)
    -- If hw_button_state changed, call on_input("power_button", hw_button_state)

    -- Publikace aktuálního stavu na MQTT
    set_mqtt_output(block_id_g, "status", current_brightness > 0)
    set_mqtt_output(block_id_g, "current_brightness", current_brightness)
end

-- Pomocná funkce pro aplikaci jasu
function apply_brightness()
    log_from_lua("Applying brightness: " .. current_brightness .. " to " .. block_id_g)
    if block_config_g.supports_dimming == true then
        -- Předpokládejme DALI ovládání, pokud je k dispozici
        -- V reálu by potřebovalo DALI adresu
        -- set_hardware_output(block_id_g, "dali_brightness", block_config_g.dali_address, current_brightness)
        -- Pro simulaci použijeme digitální výstup
        set_hardware_output(block_id_g, "digital", block_config_g.output_pin, current_brightness > 0)
    else
        set_hardware_output(block_id_g, "digital", block_config_g.output_pin, current_brightness > 0)
    end
end