# Troubleshooting Guide

Common issues and solutions discovered during development and testing of this integration.

## Table of Contents

1. [Modbus Connection Issues](#modbus-connection-issues)
2. [Battery/Backup Register Errors](#batterybackup-register-errors)
3. [Control Register Not Working](#control-register-not-working)
4. [Configuration File Structure Errors](#configuration-file-structure-errors)
5. [Template Sensor Issues](#template-sensor-issues)
6. [Duplicate Sensors with "_2" Suffix](#duplicate-sensors-with-_2-suffix)
7. [Automation Not Triggering](#automation-not-triggering)

---

## Modbus Connection Issues

### Problem: Cannot connect to inverter

**Symptoms:**
- Modbus integration shows "unavailable"
- Error: "Connection refused" or "Connection timeout"

**Solution:**
1. Verify inverter IP address hasn't changed:
   ```bash
   # Check router DHCP table
   # Or scan network for port 502
   nmap -p 502 192.168.1.0/24
   ```

2. Test connection manually:
   ```yaml
   # Developer Tools → Services
   service: modbus.write_register
   data:
     hub: SungrowSHx
     slave: 1
     address: 5005
     value: 207
   ```

3. Check firewall isn't blocking port 502

4. Reboot WiNet-S dongle if necessary

---

## Battery/Backup Register Errors

### Problem: Hundreds of modbus errors for registers 13058, 13073, 13074, 13086, 13099

**Symptoms:**
```
Error reading register 13058: Modbus Error: [Input/Output] Modbus Error
Error reading register 13073: Illegal Address
```

**Root Cause:**
SG5.0RS is a **string inverter** (not hybrid). These registers are for battery/backup systems which don't exist on string inverters.

**Solution:**
Remove all battery-related registers from `modbus_sungrow.yaml`. The SG5.0RS only supports:
- 5000-series registers (production, grid, control)
- Limited 13000-series registers

**Working registers for SG5.0RS:**
- 5000-5148: Production, power, energy, control
- Avoid: 13000+ battery/backup registers (for SH-series hybrid inverters only)

---

## Control Register Not Working

### Problem: Writing to modbus doesn't shut down inverter

**Symptoms:**
- Input select changes but inverter stays on
- Register write succeeds but no effect
- Wrong register values don't work

**Solution:**

**Correct register for SG5.0RS:**
- **Register**: 5006 (Modbus address: 5005)
- **Values**:
  - `206` = Shutdown
  - `207` = Enabled

**Test command:**
```yaml
# Shutdown
service: modbus.write_register
data:
  hub: SungrowSHx
  slave: 1
  address: 5005
  value: 206

# Enable
service: modbus.write_register
data:
  hub: SungrowSHx
  slave: 1
  address: 5005
  value: 207
```

**Note:** Different inverter models may use different registers:
- SG5.0RS: Register 5006 (address 5005)
- SH-series: May use register 13000 (address 12999)

**Verification:**
After sending shutdown command:
- Check `sensor.inverter_total_dc_power` → should drop to 0W
- Check `sensor.inverter_run_state_register` → should show 206

---

## Configuration File Structure Errors

### Problem: "Invalid config" or "required key not provided"

**Symptoms:**
```
Invalid config for 'input_select' at sungrow_control.yaml, line 15:
required key 'options' not provided
```

**Root Cause:**
Trying to use direct `!include` for files containing multiple component types (input_select, automation, template in one file).

**Solution:**

**❌ WRONG - Don't do this:**
```yaml
# configuration.yaml
input_select: !include sungrow_control.yaml
input_number: !include sungrow_control.yaml
automation: !include sungrow_control.yaml
```

**✅ CORRECT - Use packages:**
```yaml
# configuration.yaml
homeassistant:
  packages:
    sungrow: !include packages/sungrow_control.yaml
```

**Package file structure:**
```yaml
# packages/sungrow_control.yaml
input_select:
  set_sg_inverter_run_mode:
    name: "Sungrow Inverter Run Mode"
    options:
      - "Enabled"
      - "Shutdown"

automation:
  - id: sungrow_shutdown
    # automation config

template:
  - sensor:
      - name: MPPT1 Power
        # template config
```

---

## Template Sensor Issues

### Problem: Template sensors show "unavailable"

**Symptoms:**
```
binary_sensor.pv_generating: unavailable
Error: sensor.total_dc_power unavailable
```

**Root Cause:**
Template references sensor name that doesn't exist.

**Solution:**

1. **Find actual sensor names:**
   - Go to **Developer Tools → States**
   - Search for the sensor (e.g., "dc_power")
   - Note exact entity_id

2. **Update template to match:**
   ```yaml
   # If template references:
   {{ states('sensor.total_dc_power') }}

   # But actual sensor is:
   sensor.inverter_total_dc_power

   # Update template to:
   {{ states('sensor.inverter_total_dc_power') }}
   ```

3. **Reload templates:**
   - **Developer Tools → YAML → Template Entities → Reload**

**Common mismatches:**
- `sensor.total_dc_power` vs `sensor.inverter_total_dc_power`
- `sensor.meter_power` vs `sensor.inverter_meter_power`
- `sensor.total_active_power` vs `sensor.inverter_total_active_power`

---

## Duplicate Sensors with "_2" Suffix

### Problem: Sensors appear with "_2" appended

**Symptoms:**
- `sensor.inverter_total_dc_power_2`
- `sensor.inverter_meter_power_2`
- Original sensors unavailable

**Root Cause:**
Multiple modbus configurations loaded (duplicate integration or old config files).

**Solution:**

1. **Check for duplicate modbus configs:**
   ```bash
   # Search for modbus config files
   find /config -name "*modbus*.yaml"
   ```

2. **Check integrations:**
   - **Settings → Devices & Services**
   - Look for duplicate "Modbus" integrations
   - Remove old/duplicate ones

3. **Clean up configuration.yaml:**
   ```yaml
   # Make sure modbus is only included ONCE
   modbus: !include integrations/modbus_sungrow.yaml

   # NOT multiple times like:
   # modbus: !include modbus_old.yaml  ← Remove
   # modbus: !include modbus_sungrow.yaml
   ```

4. **Restart Home Assistant**

5. **Delete unavailable entities:**
   - **Settings → Entities**
   - Filter: "Status: Unavailable"
   - Delete old entities with no "_2"

6. **Rename "_2" entities (if needed):**
   - Click entity → ⚙️ Settings
   - Change entity_id to remove "_2"

---

## Automation Not Triggering

### Problem: Curtailment automation doesn't run

**Symptoms:**
- Battery full, price negative, but inverter stays on
- Automation trace shows "Stopped: condition failed"

**Troubleshooting Steps:**

### 1. Check Automation is Enabled

- **Settings → Automations** → Find "Sungrow: Shutdown when..."
- Verify toggle is **ON**
- Check `input_boolean.sungrow_curtailment_enabled` is **ON**

### 2. Verify All Sensors Exist

```yaml
# Required sensors must NOT be "unavailable"
sensor.powerwall_percentage_charged
sensor.inverter_meter_power
sensor.sandhurst_estate_feed_in_price
```

**Check in Developer Tools → States** - all should have valid numeric values.

### 3. Check Condition Values

View automation trace:
- **Settings → Automations** → Click automation → **⋮ → Traces**
- Look at "Conditions" section
- See which condition failed

**Common issues:**
- Battery sensor shows "unknown" → Teslemetry integration issue
- Price sensor shows "unavailable" → Amber integration issue
- Meter power is negative (importing) → Not exporting

### 4. Verify Trigger Duration

Automation requires conditions sustained for **3 minutes**:

```yaml
trigger:
  - platform: template
    value_template: "{{ conditions }}"
    for:
      minutes: 3  # Must be true for 3 full minutes
```

If conditions fluctuate, trigger won't fire.

### 5. Check Time Conditions

Some automations only run:
- Between sunrise and sunset
- During daylight hours

Verify it's currently daytime when testing.

### 6. Test Manual Trigger

Force-run automation:
- **Settings → Automations** → Click automation
- Click **▶ RUN** button
- Check trace for errors

---

## Inverter Not Responding to Commands

### Problem: Manual control doesn't work

**Symptoms:**
- Change input_select to "Shutdown" but inverter stays on
- `sensor.inverter_run_state_register` doesn't change

**Solution:**

### 1. Test Direct Modbus Write

```yaml
# Developer Tools → Services
service: modbus.write_register
data:
  hub: SungrowSHx
  slave: 1
  address: 5005
  value: 206
```

**Expected result:**
- `sensor.inverter_total_dc_power` drops to 0W within 10 seconds
- `sensor.inverter_run_state_register` changes to 206

**If this works:** Problem is in automation trigger
**If this fails:** Problem is modbus connection

### 2. Check WiNet-S Write Permissions

Some WiNet-S dongles require enabling write access:
1. Connect to WiNet-S web interface (usually http://[ip]:8080)
2. Look for "Modbus Settings" or "Advanced Settings"
3. Enable "Allow Modbus Write" or similar option
4. Save and reboot dongle

### 3. Verify Automation Trigger

Check automation trace:
- **Settings → Automations** → "Sungrow: Write run mode to modbus"
- **⋮ → Traces**
- Verify it triggered when `input_select` changed
- Check action was called
- Look for any errors in modbus write

### 4. Check Hub Name

Automation must use exact hub name from modbus config:

```yaml
# modbus_sungrow.yaml
- name: SungrowSHx  # ← This name

# automation
service: modbus.write_register
data:
  hub: SungrowSHx  # ← Must match exactly
```

---

## JavaScript Frontend Errors

### Problem: "Error in describing trigger: undefined is not an object"

**Symptoms:**
- Error appears in browser console when viewing automation
- Occurs when testing Enable/Shutdown commands

**Root Cause:**
Frontend UI bug when rendering template triggers.

**Solution:**
- **Ignore this error** - it's cosmetic only
- Automation still works correctly
- Verify by checking:
  - `sensor.inverter_total_dc_power` changes
  - `sensor.inverter_run_state_register` updates
  - Inverter actually responds

**This does NOT affect functionality.**

---

## Sensor Name Mismatches

### Problem: Dashboard shows "Entity not available"

**Symptoms:**
- Dashboard cards show "Entity not available"
- Looking for sensors that don't exist

**Solution:**

### 1. Find Your Actual Sensor Names

**Developer Tools → States** → Search for keywords:
- "inverter"
- "power"
- "meter"
- "dc"

### 2. Common Name Patterns

This integration creates sensors with `inverter_` prefix:
- ✅ `sensor.inverter_total_dc_power`
- ❌ NOT `sensor.total_dc_power`

- ✅ `sensor.inverter_meter_power`
- ❌ NOT `sensor.meter_power`

### 3. Update References

Search all files for old names:
```bash
grep -r "sensor.total_dc_power" /config/
```

Replace with correct names in:
- Templates (`packages/sungrow_control.yaml`)
- Customize (`sungrow_customize.yaml`)
- Dashboard (`dashboard.yaml`)

---

## Configuration Validation Errors

### Problem: "Configuration invalid" after restart

**Common causes and fixes:**

### 1. YAML Indentation

**Must use spaces, NOT tabs:**
```yaml
# ✅ CORRECT
sensor:
  - name: Test
    unit_of_measurement: W

# ❌ WRONG
sensor:
	- name: Test  # ← Tab character
```

### 2. Missing Colon

```yaml
# ✅ CORRECT
sensor:
  - name: Test

# ❌ WRONG
sensor
  - name: Test  # ← Missing colon after sensor
```

### 3. Wrong Quote Style

```yaml
# ✅ CORRECT
name: "Test Sensor"

# ❌ WRONG
name: 'Test Sensor'  # ← Use double quotes for consistency
```

### 4. Validate Before Restart

Always check config before restarting:
```bash
ha core check
```

Expected output: **"Configuration valid!"**

---

## Getting Help

If you encounter issues not covered here:

1. **Check logs:**
   - **Settings → System → Logs**
   - Search for "sungrow", "modbus", or error keywords

2. **Check automation traces:**
   - **Settings → Automations → [automation] → ⋮ → Traces**
   - Shows exactly why automation didn't trigger

3. **Test components individually:**
   - Test modbus write directly
   - Test template sensors in Template Editor
   - Check sensor values in Developer Tools

4. **Open an issue:**
   - [GitHub Issues](https://github.com/Artic0din/sungrow-sg5-price-curtailment/issues)
   - Include:
     - Home Assistant version
     - Error logs
     - Configuration (redact secrets)
     - Steps to reproduce

---

## Resources

- [Modbus Register Reference](MODBUS_REGISTERS.md)
- [Installation Guide](INSTALLATION.md)
- [Integration Setup](INTEGRATIONS.md)
- [mkaiser's Sungrow Integration](https://github.com/mkaiser/Sungrow-SHx-Inverter-Modbus-Home-Assistant)
- [Home Assistant Modbus Docs](https://www.home-assistant.io/integrations/modbus/)

---

**Last updated**: 2024-12-23
