#!/opt/storpool/python3/bin/python3

"""
Changes the default boot kernel for the system.
"""

from datetime import datetime
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

from typing import Optional

from sp_variant import variant

SAFEENC = "Latin-1"

GRUB_DEFAULT_PATH = pathlib.Path("/etc/default/grub")
_BACKUP_TIMESTAMP = datetime.strftime(datetime.now(), "%Y-%m-%d_%H-%M-%S")
GRUB_DEFAULT_BACKUP = f"{GRUB_DEFAULT_PATH}.{_BACKUP_TIMESTAMP}"

GRUB_EFI_BASE = pathlib.Path("/boot/efi/EFI/")
GRUB_CFG_PATHS = [
    *list(GRUB_EFI_BASE.glob("*/grub.cfg")),
    pathlib.Path("/boot/grub/grub.cfg"),
    pathlib.Path("/boot/grub2/grub.cfg"),
]
BOOT_LOADER_ENTRIES = pathlib.Path("/boot/loader/entries")

GRUB_MKCONFIG_CMDS = ["grub-mkconfig", "grub2-mkconfig"]

GRUB_LINE_FILTER = re.compile(r"^submenu|^menuentry|^\s+menuentry")


def variant_version(osvariant: variant.Variant) -> int:
    """Extract integer from string like ALMA9 or ROCKY10."""
    match = re.search(r'\d+', osvariant.name)
    assert match
    return int(match.group())

def get_grub_menu_title(menu: str) -> str:
    """Get a (sub)menu title out of a grub.conf menu entry."""
    menu_split = menu.split("'")
    if len(menu_split) < 2:
        return ""
    return menu_split[1]


def get_grubcfg_title(cfg_path: pathlib.Path, kernel: str) -> str:
    """
    Parses a grub.cfg and returns the menu and submenu name
    of the desired kernel version in the GRUB menu.
    """
    menu = ""
    submenu = ""

    if not cfg_path.exists():
        return ""

    with open(cfg_path, "r", encoding=SAFEENC) as cfg_file:
        for line in cfg_file.readlines():
            if not GRUB_LINE_FILTER.match(line):
                continue
            line_lower = line.lower()
            if "(recovery mode)" in line_lower or "rescue" in line_lower:
                continue
            line = line.rstrip()

            if line.startswith("menuentry"):
                if kernel in line:
                    menu = get_grub_menu_title(line)
                    break
            elif line.startswith("submenu"):
                menu = get_grub_menu_title(line)
                submenu = ""
                continue
            else:
                if kernel in line:
                    submenu = get_grub_menu_title(line)
                    break

    if not menu:
        return ""
    if not submenu:
        return menu if kernel in menu else ""
    return menu + ">" + submenu


def get_boot_loader_title(kernel: str) -> str:
    """
    Parses /boot/loader/entries files to get the
    bootloader title for the desired kernel.
    """
    title = ""

    if not BOOT_LOADER_ENTRIES.exists():
        return title

    for entry in BOOT_LOADER_ENTRIES.glob(f"*{kernel}*.conf"):
        with open(entry, "r", encoding=SAFEENC) as entry_file:
            for line in entry_file.readlines():
                if not line.startswith("title "):
                    continue
                line = line.rstrip()
                title = line.lstrip("title ")
                break

    return title


def _copy_meta(src: pathlib.Path, dst: pathlib.Path):
    """
    Ensure the destination file has the same owner,
    group, and permissions as the source.
    """
    try:
        src_meta = os.stat(src)
    except OSError:
        return

    try:
        dst_meta = os.stat(dst)
    except OSError as err:
        sys.exit(f"Could not read metadata for {dst}: {err}")

    if dst_meta.st_mode != src_meta.st_mode:
        os.chmod(dst, src_meta.st_mode)

    new_gid, new_uid = -1, -1
    if dst_meta.st_gid != src_meta.st_gid:
        new_gid = src_meta.st_gid
    if dst_meta.st_uid != src_meta.st_uid:
        new_uid = src_meta.st_uid
    if new_gid > -1 or new_uid > -1:
        os.chown(dst, new_uid, new_gid)


def _safe_write(path: pathlib.Path, content: str):
    with tempfile.NamedTemporaryFile(
        mode="w",
        prefix=os.path.basename(path) + ".",
        dir=os.path.dirname(path),
        encoding=SAFEENC,
        delete=False,
    ) as tmpf:
        moved = False
        try:
            tmpf.write(content)
            _copy_meta(path, pathlib.Path(tmpf.name))
            os.rename(tmpf.name, path)
            moved = True
        finally:
            if not moved:
                os.unlink(tmpf.name)
        return moved


def find_grub_cfg(osvariant: variant.Variant) -> Optional[str]:
    if osvariant.name.startswith("ALMA"):
        # # /usr/sbin/grub2-mkconfig -o /boot/efi/EFI/almalinux/grub.cfg
        # Running `grub2-mkconfig -o /boot/efi/EFI/almalinux/grub.cfg' will overwrite the GRUB wrapper.
        # Please run `grub2-mkconfig -o /boot/grub2/grub.cfg' instead to update grub.cfg.
        # GRUB configuration file was not updated.
        # the /etc/grub2*.cfg is always a symlink to /boot/grub2/grub2*.cfg in RHEL8+ based distros
        # $ ls -l /etc/grub2.cfg
        # lrwxrwxrwx. 1 root root 22 Jun  4 10:39 /etc/grub2.cfg -> ../boot/grub2/grub.cfg
        if pathlib.Path("/sys/firmware/efi/runtime").exists() and pathlib.Path("/etc/grub2-efi.cfg").exists():
            return "/etc/grub2-efi.cfg"
        elif pathlib.Path("/etc/grub2.cfg").exists():
            return "/etc/grub2.cfg"
        print(f"Could not find /etc/grub2(-efi).cfg on ALMA9")
        return None

    grub_cfg_path = next(path for path in GRUB_CFG_PATHS if path.exists())
    if grub_cfg_path:
        assert isinstance(grub_cfg_path, pathlib.Path)
        print(f"Found GRUB config path {grub_cfg_path}")
        return str(grub_cfg_path)

    print(f"Could not find any of the following GRUB config files: {GRUB_CFG_PATHS}")
    return None


def replace_grub_default(title: str) -> bool:
    """
    Replace the GRUB default boot kernel in /etc/default/grub.
    """
    shutil.copy(GRUB_DEFAULT_PATH, GRUB_DEFAULT_BACKUP)
    grub_cfg = ""
    with open(GRUB_DEFAULT_PATH, "r", encoding=SAFEENC) as grub_file:
        for line in grub_file.readlines():
            if line.startswith("GRUB_DEFAULT="):
                line = f'GRUB_DEFAULT="{title}"\n'
            grub_cfg += line

    if not _safe_write(GRUB_DEFAULT_PATH, grub_cfg):
        return False

    grub_mkcfg = next(cmd for cmd in GRUB_MKCONFIG_CMDS if shutil.which(cmd))
    if not grub_mkcfg:
        print(f"Could not find any of the following GRUB tools: {GRUB_MKCONFIG_CMDS}")
        return False
    osvariant = variant.detect_variant()
    grub_cfg_path = find_grub_cfg(osvariant)
    if not grub_cfg_path:
        return False

    grub_cmd = [grub_mkcfg, "-o", grub_cfg_path]
    if osvariant.family == "redhat" and variant_version(osvariant) >= 9:
        grub_cmd.append("--update-bls-cmdline")
    return subprocess.call(grub_cmd, timeout=120) == 0


def get_kernel_title(kernel: str) -> str:
    """Look for the title of the desired kernel in various locations."""
    kernel_title = ""

    for cfg_path in GRUB_CFG_PATHS:
        kernel_title = get_grubcfg_title(cfg_path, kernel)
        if kernel_title:
            return kernel_title
    kernel_title = get_boot_loader_title(kernel)

    return kernel_title


def main() -> None:
    """
    Find the GRUB title for the desired kernel and
    replace it in the GRUB default configuration.
    """
    if len(sys.argv) != 2:
        sys.exit(
            f"Usage: {sys.argv[0]} <new_kernel_version>\n"
            "Sets the default kernel version to boot from"
        )
    new_kernel = sys.argv[1]
    print(new_kernel)

    kernel_title = get_kernel_title(new_kernel)
    if not kernel_title:
        sys.exit(f"Could not find GRUB kernel title for {new_kernel}, exiting")
    print(f"Found title '{kernel_title}' for kernel '{new_kernel}'")
    if os.getenv("SP_SET_KERNEL_DUMMY"):
        sys.exit(0)

    if not replace_grub_default(kernel_title):
        sys.exit(
            "Could not set new kernel as default, backup of "
            f"'{GRUB_DEFAULT_PATH}' is available at '{GRUB_DEFAULT_BACKUP}'"
        )
    print("GRUB default boot option replaced successfully")


if __name__ == "__main__":
    main()
