#!/usr/bin/python
#
# Copyright 2024 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Code to control a blind via RF while tracking position in Home Assistant"""

# Persist the state of positions in the pyscript domain.
state.persist("pyscript.family_room_east_blind_position")
state.persist("pyscript.primary_bedroom_north_blind_position")
state.persist("pyscript.primary_bedroom_east_blind_position")

# On startup, restore the state of the sensors tracking positions
# as well as the current position on blinds.
# This handles the case where HA is rebooted and the blinds aren't closed.
@time_trigger("startup")
def restore_blind_positions():
    log.error("restore_blind_positions: restoring positions on startup")
    sensor.family_room_east_blind_position = pyscript.family_room_east_blind_position
    cover.family_room_east_blind.current_position = pyscript.family_room_east_blind_position

    sensor.primary_bedroom_north_blind_position = pyscript.primary_bedroom_north_blind_position
    cover.primary_bedroom_north_blind.current_position = pyscript.primary_bedroom_north_blind_position

    sensor.primary_bedroom_east_blind_position = pyscript.primary_bedroom_east_blind_position
    cover.primary_bedroom_east_blind.current_position = pyscript.primary_bedroom_east_blind_position

# A service to call to stop the blinds' movement.
# If the shade's current position is < 1 or > 99,
# then do a full open or close using the rf device to account for drift.
@service
def stop_rf_blind(shade_entity):
    shade_current_position = exec("float(%s.current_position)" % shade_entity)
    rf_bridge_cover_entity = "%s_rf_bridge" % shade_entity
    if shade_current_position <= 1.0:
        log.error("stop_rf_blind: Closing the blind fully because <= 1.0")
        service.call("cover", 
                     "close_cover", 
                     entity_id = rf_bridge_cover_entity)
    elif shade_current_position >= 99.00:
        log.error("stop_rf_blind: Opening the blind fully because >= 99.00")
        service.call("cover", 
                     "open_cover", 
                     entity_id = rf_bridge_cover_entity)
    else:
        service.call("cover", 
                     "stop_cover", 
                     entity_id = rf_bridge_cover_entity)
    shade_name = shade_entity.split(".")[1]
    # Because a blind can be stopped while it is being moved
    # use binary_sensor.shade_name_moving as a way to indicate the shade
    # has stopped to break the while loop of set_rf_blind_pos early.
    exec_str = "binary_sensor.%s_moving = \"Off\"" % shade_name
    exec(exec_str)    


@service
def set_rf_blind_pos(shade_entity,
                     desired_shade_position):
    # Set up this task so it is killable as you can call move multiple times.
    task_name = "set_rf_blind_pos-%s" % shade_entity
    task.unique(task_name, kill_me=True)
    rf_bridge_cover_entity = "%s_rf_bridge" % shade_entity
    shade_current_position = float(exec("%s.current_position" % shade_entity))
    shade_name = shade_entity.split(".")[1]
    log.error("set_rf_blind_pos: called to move %s to %s" % (shade_entity, desired_shade_position))
    log.error("set_rf_blind_pos: %s current position is %s" % (shade_entity, shade_current_position))
    
    # Stop the shade in case it's already moving.
    stop_rf_blind(shade_entity)
    
    # The time it takes for a shade to open/close will grow over time as the
    # battery gets discharged.
    # Fully charge the battery, measure the time, stick the value in a sensor
    # in configuration.yaml.
    # When the shade starts to not align with position clearly, charge the
    # battery.
    shade_total_time_sensor = "sensor.%s_span" % shade_name
    shade_total_time = float(exec(shade_total_time_sensor))

    one_percent_in_seconds = shade_total_time/100.0
    tenth_second_percent = 100/shade_total_time * .1

    percent_to_move = abs(desired_shade_position-shade_current_position)

    # Determine if the shade needs to move up or down based on the current
    # position vs. the desired position.

    if desired_shade_position < shade_current_position:
        direction_to_move = "close_cover"
    else:
        direction_to_move = "open_cover"

    move_duration_sec = one_percent_in_seconds * percent_to_move

    # Set the binary sensor for moving for the shade to On
    exec_str = "binary_sensor.%s_moving = \"On\"" % shade_name
    exec(exec_str)

    # Move the shade
    service.call("cover", direction_to_move, entity_id = rf_bridge_cover_entity)
    
    if direction_to_move == "open_cover":
        calc_new_current_position = "float(%s.current_position) + tenth_second_percent" % shade_entity
    elif direction_to_move == "close_cover":
        calc_new_current_position = "float(%s.current_position) - tenth_second_percent" % shade_entity

#    shadeMovingVar = exec("binary_sensor.%s_moving" % shade_name)

    # Determine the state of whether the blind is moving.
    # It needs to be a calculated variable.
    # This has to be part of the while loop because a shade can be stopped
    # independently of its moving window.
    exec_str_moving = "binary_sensor.%s_moving == \"On\"" % shade_name

    while move_duration_sec > 0 and \
          exec(exec_str_moving):
        task.sleep(0.1)
        new_current_position = exec(calc_new_current_position)
        # These are all exec'ed because the names are derived from the shade.
        exec_str = "%s.current_position = %s" % (shade_entity, new_current_position)
        exec(exec_str)
        exec_str = "sensor.%s_position = %s" % (shade_name, new_current_position)
        exec(exec_str)
        exec_str = "pyscript.%s_position = %s" % (shade_name, new_current_position)
        exec(exec_str)
        move_duration_sec -= 0.1

    # Close the blind if it isn't already closed.
    if exec(exec_str_moving):
        stop_rf_blind(shade_entity)

    return
