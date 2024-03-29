# RF Blind Home Assistant Control

## Background

Various blinds of various brands use motors that have an RF remote control.

These blinds can be made "smart" by using one of a number of Wi-Fi to RF
bridges ([Sonoff RFBridgeR2](https://sonoff.tech/product/gateway-and-sensors/rf-bridger2/),
[Bond Bridge](https://bondhome.io/product/bond-bridge/), 
[Broadlink Universal Remote RM4 pro](https://ebroadlink.com/products/universal-remote-rm4-pro)) 
to record the blinds' remotes' open/close/stop commands and replay them in
response to commands a user sends using the bridge's app.

The bridges can also then be added to Home Assistant (Bond and Broadlink have
native integratoins, Sonoff requires some extra work).

These RF blinds, bridges, and Home Assistant integrations do not maintain any
internal state regarding the current position of the blinds, so, if the blinds
are exposed to HomeKit or Google Home, the blinds are hard to control.

With pyscript and some templating, it's possible to control the blinds and
track their current position.

## Overview

At a high level:
1. Record the RF blinds' remotes' commands using the RF bridge's app
1. Add the RF bridge to Home Assistant.
1. Rename the Home Assistant entity for the RF bridge's blind cover to end in
"_rf_bridge"
1. Add entries to configuration.yaml for the blind and some supporting sensors
to store values.
1. Add a pyscript that is used to implement open and close functions that take:
   1. The shade that should move
   1. The new position the shade should be set to
1. When called, the pyscript function then:
   1. Stops the shade in case it's already moving
   1. Calculates:
      1. Whether the new position is more or less than the current position
         and whether the shade needs to be opened or closed to reach the new
         position.
      1. How many seconds the shade needs to move for to reach the new position.
      1. What percentage movement occurs in one tenth of a second.
   1. Begins opening or closing the shade.
   1. Waits the appropriate number of seconds in a while loop that:
      1. Sleeps one tenth of a second.
      1. Calculates the new current position
      1. Sets the current_position on the shade.
   1. Stops the blind
      1. There are edge cases where the blind entity's current_position gets
         out of sync. To account for this, if the entity's current_position 
         is < 1 or > 99, the pyscript sends the command to fully close or open
         the blind.

The RF motor blind is represented as a template cover that calls the pyscript
open, close, and stop functions.

There's three sensors needed to track:
1. Whether the blind is currently moving;
1. The blind's current position; and
1. The blind's time to open/close.

### Setting up Template Entities for RF shades

Copy and paste the contents of [configuration_entries.yaml](configuration_entries.yaml)
into your configuration.yaml and follow the instructions at the top as to
what needs to be changed for your blinds.

### Setting up pyscript for RF shades

Install [Home Assistant Community Store (HACS)](https://hacs.xyz/) if you
haven't previously.

Install [hacs-pyscript](https://github.com/custom-components/pyscript/) using
hacs if you havne't previously.

Download [rf_blind_control.py](rf_blind_control.py) into your pyscript directory. 
