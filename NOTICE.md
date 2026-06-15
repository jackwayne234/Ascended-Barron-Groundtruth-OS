# Notices & Credits

The **MIT license** in [LICENSE](LICENSE) covers only the original work created
for Ascended Barron: GroundTruth OS — the dashboard (`ai-os-dashboard.py`), the
`ai_big_log` logging/export library, the helper CLIs (`ai-os-*`), the build
profile and scripts, the branding, and the sample content.

GroundTruth OS is an **Arch-based Linux distribution**. It bundles and builds on
a great deal of third-party software, **each of which keeps its own license.**
GroundTruth OS does not relicense any of it. The major components include:

| Component | Role | License (summary) |
| --- | --- | --- |
| Arch Linux (base system, pacman, `releng`/`archiso`) | Base distribution & build tooling | Mostly GPL/MIT/BSD per package |
| Linux kernel | Kernel | GPL-2.0 |
| GNU coreutils, bash, glibc, GRUB, etc. | Core userland & bootloader | GPL-2.0 / GPL-3.0 / LGPL |
| Xorg (xorg-server, xinit) | Display server | MIT |
| Openbox | Window manager | GPL-2.0 |
| Python + Tk/tkinter | Dashboard runtime & GUI toolkit | PSF / BSD-style |
| Chromium | Web browser | BSD-3-Clause (+ bundled components' licenses) |
| lxterminal | Terminal emulator | GPL-2.0 |
| NetworkManager | Networking | GPL-2.0 |
| PipeWire / WirePlumber | Audio | MIT |
| polkit | Privilege management | LGPL-2.0 |
| DejaVu / system fonts | Fonts | Bitstream Vera / various permissive |

This list summarizes the most visible components; it is not exhaustive. The
authoritative license for any bundled package is the one shipped with that
package (typically under `/usr/share/licenses/` on the installed system) and in
each project's upstream source.

Trademarks (e.g. "Arch Linux", "Chromium") belong to their respective owners and
are used only to identify the bundled software.
