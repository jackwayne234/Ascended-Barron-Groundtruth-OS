#!/usr/bin/env bash
# shellcheck disable=SC2034
#
# Ascended Barron: GroundTruth OS — archiso profile definition (v1).
#
# This makes the repo a valid `mkarchiso` profile overlay. The build derives
# its bootloader configs (syslinux/grub/efiboot) and the base live-boot package
# set from archiso's `releng` profile (version-matched inside the builder VM),
# then layers THIS profile's airootfs, packages, and customizations on top.
# See BUILD.md for the exact build contract.

iso_name="ascended-barron-groundtruth-os"
iso_label="GROUNDTRUTH_$(date +%Y%m)"
iso_publisher="Ascended Barron: GroundTruth OS <https://github.com/jackwayne234/Ascended-Barron-Groundtruth-OS>"
iso_application="Ascended Barron: GroundTruth OS — your AI workflow operating system"
iso_version="$(date +%Y.%m.%d)"
install_dir="arch"
buildmodes=('iso')
# UEFI (x64 + ia32) and legacy BIOS — Q11 (no Secure Boot in v1).
bootmodes=(
  'bios.syslinux.mbr'
  'bios.syslinux.eltorito'
  'uefi-ia32.grub.esp'
  'uefi-x64.grub.esp'
  'uefi-ia32.grub.eltorito'
  'uefi-x64.grub.eltorito'
)
arch="x86_64"
pacman_conf="pacman.conf"
airootfs_image_type="squashfs"
airootfs_image_tool_options=('-comp' 'xz' '-Xbcj' 'x86' '-b' '1M' '-Xdict-size' '1M')
bootstrap_tarball_compression=('zstd' '-c' '-T0' '--auto-threads=logical' '--long' '-19')

# Ownership/permissions applied to the airootfs. The single user is `barron`
# (uid/gid 1000); /home/barron is also chowned recursively in customize_airootfs.sh.
declare -A file_permissions=(
  ["/etc/shadow"]="0:0:400"
  ["/etc/gshadow"]="0:0:400"
  ["/root"]="0:0:750"
  ["/root/customize_airootfs.sh"]="0:0:755"
  ["/home/barron"]="1000:1000:755"
  ["/usr/local/bin/ai-os-browser"]="0:0:755"
  ["/usr/local/bin/ai-os-firstboot-info"]="0:0:755"
  ["/usr/local/bin/ai-os-internet-check"]="0:0:755"
  ["/usr/local/bin/ai-os-open-terminal"]="0:0:755"
  ["/usr/local/bin/ai-os-router-check"]="0:0:755"
  ["/usr/local/bin/ai-os-terminal-dashboard"]="0:0:755"
  ["/usr/local/bin/ai-os-wifi-setup"]="0:0:755"
  ["/usr/local/bin/start-ai-os-gui-dashboard"]="0:0:755"
  ["/usr/local/bin/ai-os-install-to-disk"]="0:0:755"
)
