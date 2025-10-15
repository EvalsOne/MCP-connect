#!/bin/bash
# Setup desktop environment configuration files for Fluxbox, PCManFM, and tint2
set -e

TEMPL=/opt/mcp-desktop
install -d -o 1000 -g 1000 "$TEMPL/fluxbox" "$TEMPL/fluxbox/styles" "$TEMPL/tint2" "$TEMPL/pcmanfm/default"

cat > "$TEMPL/fluxbox/init" <<'FILE'
session.configVersion:    13
session.screen0.toolbar.tools:  RootMenu, WorkspaceName, Iconbar, Clock
session.screen0.toolbar.autoHide:    false
session.screen0.toolbar.placement:   BottomCenter
session.screen0.toolbar.widthPercent: 100
session.screen0.toolbar.height: 28
session.screen0.toolbar.layer:  Dock
session.screen0.toolbar.visible:  false
session.screen0.toolbar.maxOver:  False
session.screen0.toolbar.alpha:   255
session.screen0.iconbar.mode:    Workspace
session.screen0.iconbar.focused: true
session.screen0.iconbar.unfocused:  true
session.screen0.menu.delay:  150
session.screen0.rootCommand:  pcmanfm --desktop --profile=default
session.styleFile: ~/.fluxbox/styles/MCP-Grey
session.screen0.workspaceNames: Workspace 1, Workspace 2, Workspace 3, Workspace 4
session.autoRaiseDelay:   250
session.slitlistFile: ~/.fluxbox/slitlist
session.appsFile: ~/.fluxbox/apps
session.tabsAttachArea:   0
session.tabFocusModel:    Follow
session.focusTabMinWidth: 0
session.clickRaises:  True
session.focusModel:   ClickFocus
session.clientMenu.usePixmap:    true
session.tabPadding:    0
session.ignoreBorder:  false
session.styleOverlay:  ~/.fluxbox/overlay
FILE

cat > "$TEMPL/fluxbox/overlay" <<'FILE'
window.focus.alpha: 255
window.unfocus.alpha: 220
toolbar.alpha: 255
menu.alpha: 255
FILE

cat > "$TEMPL/fluxbox/menu" <<'FILE'
[begin] (MCP)
  [exec] (Chrome) {/usr/bin/google-chrome --no-sandbox}
  [exec] (Terminal) {x-terminal-emulator}
  [exec] (File Manager) {pcmanfm}
  [separator]
  [exit] (Logout)
[end]
FILE

cat > "$TEMPL/fluxbox/keys" <<'FILE'
OnDesktop Mouse1 :HideMenus
Mod1 Tab :NextWindow {static groups}
Mod1 Shift Tab :PrevWindow {static groups}
Mod4 d :RootMenu
Mod4 Return :ExecCommand x-terminal-emulator
Mod4 c :ExecCommand google-chrome --no-sandbox
FILE

cat > "$TEMPL/fluxbox/styles/MCP-Grey" <<'FILE'
! minimal neutral style
toolbar: flat gradient vertical
  toolbar.color: #2b303b
  toolbar.colorTo: #232832
  toolbar.borderColor: #1c1f26
  toolbar.borderWidth: 1
window.title.focus: flat gradient vertical
  window.title.focus.color: #3b4252
  window.title.focus.colorTo: #2e3440
window.title.unfocus: flat gradient vertical
  window.title.unfocus.color: #434c5e
  window.title.unfocus.colorTo: #3b4252
window.button.focus: flat solid
  window.button.focus.color: #d8dee9
window.button.unfocus: flat solid
  window.button.unfocus.color: #a7adba
menu.frame: flat solid
  menu.frame.color: #2e3440
menu.title: flat solid
  menu.title.color: #3b4252
handle: flat solid
  handle.color: #2e3440
borderColor: #1c1f26
borderWidth: 2
FILE

:>"$TEMPL/fluxbox/slitlist"
:>"$TEMPL/fluxbox/apps"

cat > "$TEMPL/pcmanfm/default/desktop-items-0.conf" <<'FILE'
[*]
wallpaper_mode=color
wallpaper=
desktop_bg=#1d1f21
desktop_shadow=#000000
desktop_font=Sans 11
desktop_folder=$HOME/Desktop
show_desktop_bg=1
show_trash=1
show_mounts=1
show_documents=1
show_wm_menu=0
sort=name;ascending;
FILE

cat > "$TEMPL/tint2/tint2rc" <<'FILE'
# Minimal tint2 panel
panel_items = LTS
panel_monitor = all
panel_position = bottom center horizontal
panel_size = 100% 30
panel_margin = 0 0
panel_padding = 8 4 8
panel_background_id = 0
wm_menu = 1

rounded = 6
border_width = 1
border_color = #1c1f26 100
background_color = #2b303b 95
background_color_hover = #343b48 95

launcher_padding = 4 4 4
launcher_item_size = 28
launcher_icon_theme = Adwaita

# Taskbar
task_text = 1
urgent_nb_of_blink = 7
mouse_middle = none
mouse_right = close
mouse_scroll_up = toggle
mouse_scroll_down = iconify

time1_format = %H:%M
clock_font_color = #eceff4 100
clock_padding = 8 0

backgrounds = 1
background_id = 0
  background_color = #2b303b 95
  border_color = #1c1f26 100
  border_width = 1
  border_radius = 6
FILE

chown -R 1000:1000 "$TEMPL"
