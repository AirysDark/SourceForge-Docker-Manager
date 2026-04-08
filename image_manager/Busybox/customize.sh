# Set permissions for the binary
set_perm $MODPATH/system/bin/busybox 0 2000 0755

# Create symlinks (applets)
# This makes BusyBox commands work without typing 'busybox' first
ui_print "- Creating BusyBox applets..."
$MODPATH/system/bin/busybox --install -s $MODPATH/system/bin
