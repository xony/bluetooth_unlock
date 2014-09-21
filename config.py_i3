### CHANGE THESE PARAMETERS
#
# Assume:
#   userstr = "su xony -c"
#   unlockstr = ["cmd1" , "cmd2"]
#   lockstr = "cmd3"
#
# Then upon unlocking these commands will be executed:
#   su xony -c cmd1
#   su xony -c cmd2
#
# and upon locking:
#   su xony -c cmd3
#
# Other Parameters:
#   lock_threshold:     How low must RSSI go before screen will be locked (inclusive)
#   unlock_threshold:   How high the RSSI must be before screen will be unlocked (inclusive)
#   count_threshold:    How often the RSSI must be below lock_threshold before the screen may be locked
#   refresh_time:       Between checking, sleep so long in seconds
#   client_file:        This file holds the ID of the unlocking bluetooth address
#
userstr         = "su xony -c"
unlockstr       = ["killall i3lock","xset dpms force on"]
lockstr         = "i3lock -d -c 111111"

lock_threshold  = -11
unlock_threshold= 0
count_threshold = 2
refresh_time    = 2

client_file     = "known_clients"
###
