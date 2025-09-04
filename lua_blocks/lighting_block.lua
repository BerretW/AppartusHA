-- lua_blocks/lighting_block.lua
-- Tento blok ovládá osvětlení v místnosti
-- Volá Python funkce:
--   py_set_mqtt_output(block_id, output_name, value)
--   py_get_hardware_input(block_id, input_type, pin_or_addr)
--   py_set_hardware_output(block_id, output_type, pin_or_addr, value)
--   py_log_from_lua(message)

local M = {} -- Vytvoříme tabulku pro náš modul

-- Globální proměnné pro tento Lua blok
local current_brightness = 0
local block_id_g
local block_config_g
-- local block_inputs_g -- Již nepotřebujeme držet přímo v lokální proměnné, můžeme přistupovat přes config_g.inputs
local block_outputs_g

-- Funkce pro inicializaci bloku
function M.init(id, config, inputs, outputs)
    block_id_g = id
    block_config_g = config
    -- block_inputs_g = inputs -- Není potřeba lokální, vstupní témata jsou v block_config_g.inputs
    block_outputs_g = outputs
    
    current_brightness = block_config_g.default_brightness or 0
    py_log_from_lua("Lighting block " .. block_id_g .. " initialized with default brightness: " .. current_brightness)
    
    -- Nastavíme počáteční stav výstupu
    if block_config_g.output_pin then
        py_set_hardware_output(block_id_g, "digital", block_config_g.output_pin, current_brightness > 0)
    end
    -- Pokud podporuje stmívání přes DALI nebo PWM, bylo by to zde
    -- Aplikujeme počáteční jas, což také publikuje stav
    M.apply_brightness()
end

-- Funkce volaná, když dorazí MQTT zpráva pro vstup tohoto bloku
function M.on_input(input_name, value)
    py_log_from_lua("Input " .. input_name .. " received value: " .. tostring(value))

    if input_name == "power_button" then
        if value == true or value == "true" then -- Předpokládáme digitální stav ON
            if current_brightness > 0 then
                current_brightness = 0 -- Zhasnout
            else
                current_brightness = block_config_g.default_brightness -- Rozsvítit na výchozí
            end
            M.apply_brightness()
        end
    elseif input_name == "motion_sensor" then
        if value == true or value == "true" then
            py_log_from_lua("Motion detected in " .. block_id_g .. ", turning on light.")
            current_brightness = block_config_g.default_brightness or 100
            M.apply_brightness()
        else
            py_log_from_lua("Motion ceased in " .. block_id_g .. ", turning off light after delay (simulated).")
            -- Zde by se implementovala logika zhasnutí po určité době neaktivity
            -- Pro jednoduchost hned zhasneme
            current_brightness = 0
            M.apply_brightness()
        end
    elseif input_name == "daylight_sensor" then
        local lux = tonumber(value)
        if lux then
            py_log_from_lua("Daylight sensor reading: " .. lux .. " lux")
            -- Zde by se mohla implementovat logika automatického stmívání/rozsvěcování
            -- podle denního světla. Např. pokud je dost světla, zhasnout, jinak rozsvítit.
            -- Pro jednoduchost jen logujeme.
        end
    elseif input_name == "master_switch" then
        if value == false or value == "false" then
            py_log_from_lua("Master switch OFF for " .. block_id_g .. ", turning off light.")
            current_brightness = 0
            M.apply_brightness()
        else -- Pokud master_switch je true a světlo by mělo svítit
             -- Můžeme buď ignorovat, nebo se pokusit nastavit na default
            py_log_from_lua("Master switch ON for " .. block_id_g .. ", allowing light control.")
            -- Pro teď to necháme tak, aby master switch jen vypínal
        end
    elseif input_name == "temperature_check" then
        local temp = tonumber(value)
        if temp then
            py_log_from_lua("Received temperature for " .. block_id_g .. ": " .. temp .. " C.")
            -- Zde byste mohli implementovat logiku související s teplotou, např.
            -- pokud je moc teplo, snížit jas, aby se netopilo.
            -- Prozatím jen logujeme.
        end
    end
end

-- Funkce pro periodické zpracování (např. čtení hardwaru, časovače)
function M.run()
    -- Publikace aktuálního stavu na MQTT
    py_set_mqtt_output(block_id_g, "status", current_brightness > 0)
    -- Publikujeme i aktuální jas, pokud je to potřeba
    if block_config_g.supports_dimming == true then
        py_set_mqtt_output(block_id_g, "current_brightness", current_brightness)
    end
end

-- Pomocná funkce pro aplikaci jasu
function M.apply_brightness()
    py_log_from_lua("Applying brightness: " .. current_brightness .. " to " .. block_id_g)
    if block_config_g.supports_dimming == true then
        -- V reálu by zde byla logika pro DALI, PWM atd.
        -- Pro simulaci použijeme digitální výstup pro on/off podle jasu
        py_set_hardware_output(block_id_g, "digital", block_config_g.output_pin, current_brightness > 0)
        -- Pokud máte DALI, zde by bylo: py_set_hardware_output(block_id_g, "dali_brightness", block_config_g.dali_address, current_brightness)
    else
        py_set_hardware_output(block_id_g, "digital", block_config_g.output_pin, current_brightness > 0)
    end
end

return M