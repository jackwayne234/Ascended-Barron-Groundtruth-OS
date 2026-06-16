import os
import shlex
import shutil


def x11_env():
    """Env that forces apps onto X11 (Qt/GTK/SDL)."""
    env = dict(os.environ)
    env["QT_QPA_PLATFORM"] = "xcb"
    env["GDK_BACKEND"] = "x11"
    env["SDL_VIDEODRIVER"] = "x11"
    return env


def xterm_args(shell_command, into=None, geometry="110x32"):
    """Readable xterm fallback only."""
    args = ["xterm"]
    if into is not None:
        args += ["-into", str(into)]
    args += [
        "-bg", "#020912", "-fg", "#a7f3d0",
        "-fa", "DejaVu Sans Mono", "-fs", "12",
        "-geometry", geometry,
        "-xrm", "XTerm*selectToClipboard: true",
        "-e", "bash", "-lc", shell_command,
    ]
    return args


def find_terminal(shell_command):
    candidates = [
        ("lxterminal", ["lxterminal", "--title=Ascended Barron", "-e",
                        f"bash -lc {shlex.quote(shell_command)}"]),
        ("ptyxis", ["ptyxis", "-s", "--", "bash", "-lc", shell_command]),
        ("x-terminal-emulator", ["x-terminal-emulator", "-e", "bash", "-lc", shell_command]),
        ("gnome-terminal", ["gnome-terminal", "--", "bash", "-lc", shell_command]),
        ("konsole", ["konsole", "-e", "bash", "-lc", shell_command]),
        ("xfce4-terminal", ["xfce4-terminal", "--command", f"bash -lc {shlex.quote(shell_command)}"]),
        ("mate-terminal", ["mate-terminal", "-e", f"bash -lc {shlex.quote(shell_command)}"]),
        ("xterm", xterm_args(shell_command)),
    ]
    for exe, args in candidates:
        if shutil.which(exe):
            return args
    return None
