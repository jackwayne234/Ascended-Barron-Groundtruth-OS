# Ascended Barron: GroundTruth OS — user shell profile.
#
# On the main console (tty1) the graphical dashboard starts automatically by
# launching X. On any other VT you just get a normal login shell, so there is
# always a plain escape hatch. The dashboard itself is started by ~/.xinitrc.
[[ -f ~/.bashrc ]] && . ~/.bashrc

if [[ -z "${DISPLAY:-}" && "$(tty)" == "/dev/tty1" ]]; then
  exec startx
fi
