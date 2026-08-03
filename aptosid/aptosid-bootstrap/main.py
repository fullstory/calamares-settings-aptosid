#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# SPDX-FileCopyrightText: 2026 Kel Modderman <kelvmod@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
"""Bootstrap a minimal aptosid into the target.

The alternative to unpacking the live media's readonly filesystem: debootstrap
a bare system into the target, hand it the live session's own apt
configuration, and install nothing beyond essential utilities, a kernel and a
boot loader.

Everything that shapes the result is read from the running live system - apt
sources and their keyrings, the kernel metapackage, the initramfs tool, the
boot loader - so the installed system matches the medium it was installed
from and no build time state has to be baked into this module.

Mirrors what pyfll does when it builds the live media itself (pyfll/apt.py).
"""

import os
import re
import shutil
import subprocess

import libcalamares

import gettext
_ = gettext.translation("calamares-python",
                        localedir=libcalamares.utils.gettext_path(),
                        languages=libcalamares.utils.gettext_languages(),
                        fallback=True).gettext

# apt in a chroot: no recommends (this is a minimal system), no translations,
# and none of the interactive progress decoration.
APT_OPTIONS = [
    "-o", "APT::Install-Recommends=0",
    "-o", "Acquire::Languages=none",
    "-o", "Dpkg::Use-Pty=0",
    "-o", "Dpkg::Progress-Fancy=0",
    "-o", "APT::Color=0",
]

# The SSH public key pyfll bakes into the live medium, when one is configured.
SSH_AUTHORIZED_KEYS = "/var/lib/fll/ssh_authorized_keys"

# Where the bootloader module's own configuration is found, in search order:
# /etc takes precedence over the shipped defaults, as it does in calamares.
BOOTLOADER_CONF = (
    "/etc/calamares/modules/bootloader.conf",
    "/usr/share/calamares/modules/bootloader.conf",
)

# The smallest base each tool can lay down. These are not equivalent:
# cdebootstrap's "minimal" is Essential plus apt, while minbase is Essential
# plus Priority: required. The configured package list is padded for the
# smaller of the two, which is what makes the tools converge - measured against
# the sid indices, the only required-priority package a minbase has and this
# list does not pull in is an awk, so gawk is named there. (The archive also
# marks bsdutils required, but util-linux ships logger(1) these days and the
# live system does not install it either.)
#
# The consequence, and the reason the list is as long as it is: nothing arrives
# by priority. Anything an installed system needs - login(1), an init, zoneinfo,
# an editor - is named in the configuration or it is simply absent.
BASE_ARGS = {
    "debootstrap": ["--variant=minbase"],
    "cdebootstrap": ["--flavour=minimal"],
    "mmdebstrap": ["--variant=minbase"],
}

# grub's EFI package per architecture; the BIOS case is always grub-pc.
GRUB_EFI = {
    "amd64": "grub-efi-amd64",
    "i386": "grub-efi-ia32",
    "arm64": "grub-efi-arm64",
}

status = ""


def pretty_name():
    return _("Bootstrap a minimal system")


def pretty_status_message():
    return status or pretty_name()


def report(message, fraction):
    """Push a status message and progress fraction to the UI."""
    global status
    status = message
    libcalamares.utils.debug(message)
    libcalamares.job.setprogress(fraction)


class OutputProgress:
    """Show a command's output as the step's status message, creeping the
    progress bar from *start* towards *end* as lines arrive. Neither
    debootstrap nor apt report progress usefully, so this is the honest
    alternative to a bar that sits still for several minutes."""

    def __init__(self, start, end, step=0.002):
        self.value = start
        self.end = end
        self.step = step

    def __call__(self, line):
        line = line.strip()
        if not line:
            return
        global status
        status = line
        self.value = min(self.end, self.value + self.step)
        libcalamares.job.setprogress(self.value)


def host_output(args):
    """Run a command on the live system, returning its output lines."""
    lines = []
    libcalamares.utils.host_env_process_output(args, lines)
    return lines


def dpkg_installed(status):
    """True when a dpkg ${Status} field says the package is installed.

    Only the last two words are ours to judge: the selection in front of them
    is not always "install". The live medium holds its kernel packages (pyfll
    freezes them, calamares releases the hold on the installed system), and a
    held package reads "hold ok installed"."""
    fields = status.split()
    return len(fields) == 3 and fields[1:] == ["ok", "installed"]


def host_installed(package):
    """True when *package* is installed on the live system."""
    try:
        lines = host_output(["dpkg-query", "-W", "-f", "${Status}", package])
    except subprocess.CalledProcessError:
        return False
    return dpkg_installed(" ".join(lines))


def target_apt(command, packages=None, progress=None):
    """Run apt-get in the target. Non-interactive: the target's debconf has no
    terminal to ask questions on."""
    args = ["env", "DEBIAN_FRONTEND=noninteractive",
            "apt-get", "--yes", "-q"] + APT_OPTIONS + [command]
    if packages:
        args += packages
    libcalamares.utils.target_env_process_output(args, progress)


def deb822_stanzas(path):
    """Parse a deb822 apt sources file into a list of field mappings.

    Continuation lines are skipped: the only multi-line field pyfll writes is
    an embedded Signed-by key, which travels with the file when it is copied
    and needs no further handling here."""
    stanzas = []
    fields = {}
    with open(path) as sources:
        for line in sources:
            if not line.strip():
                if fields:
                    stanzas.append(fields)
                    fields = {}
                continue
            if line.startswith(("#", " ", "\t")):
                continue
            key, _colon, value = line.partition(":")
            fields[key.strip().lower()] = value.strip()
    if fields:
        stanzas.append(fields)
    return stanzas


def live_apt_sources():
    """Every deb822 stanza configured on the live system."""
    stanzas = []
    sources_dir = "/etc/apt/sources.list.d"
    for name in sorted(os.listdir(sources_dir)):
        if name.endswith(".sources"):
            stanzas += deb822_stanzas(os.path.join(sources_dir, name))
    return stanzas


def apt_keyrings(stanzas):
    """Signed-by keyring files referenced by the live system's apt sources."""
    keyrings = []
    for fields in stanzas:
        for path in fields.get("signed-by", "").split():
            if os.path.isfile(path) and path not in keyrings:
                keyrings.append(path)
    return keyrings


def keyring_packages(keyrings):
    """The archive-keyring packages owning *keyrings*, so that the installed
    system keeps following archive key rotations by itself."""
    packages = []
    for keyring in keyrings:
        package = re.sub(r"\.(gpg|asc)$", "", os.path.basename(keyring))
        if package.endswith("-archive-keyring") and package not in packages:
            packages.append(package)
    return packages


def kernel_metapackage(arch):
    """The live system's linux-image metapackage, e.g.
    linux-image-aptosid-amd64: the installed linux-image package that depends
    on the running kernel's versioned image."""
    running = "linux-image-" + os.uname().release
    candidates = []
    for line in host_output(["dpkg-query", "-W", "-f",
                             "${Package}|${Status}|${Depends}\n", "linux-image-*"]):
        package, _bar, rest = line.partition("|")
        state, _bar, depends = rest.partition("|")
        if not dpkg_installed(state) or package == running:
            continue
        if running in depends:
            return package
        # versioned images are not metapackages
        if not re.match(r"linux-image-\d", package):
            candidates.append(package)

    if candidates:
        return sorted(candidates, key=len)[0]

    libcalamares.utils.warning(
        "no linux-image metapackage found on the live system; "
        "falling back to Debian's linux-image-{}".format(arch))
    return "linux-image-" + arch


def initramfs_package():
    """The initramfs tool the live system uses, so the target's initrd is
    built by the same tool the dracut/initramfs module will drive later."""
    for package in ("dracut", "initramfs-tools"):
        if host_installed(package):
            return package
    libcalamares.utils.warning("no initramfs tool found on the live system")
    return None


def efi_boot_loader():
    """The loader the bootloader module is configured to install. pyfll bakes
    the live medium's own loader into that module's configuration at build
    time, so this is the authoritative answer - and the target needs packages
    for exactly the loader that module will go on to install."""
    for path in BOOTLOADER_CONF:
        if os.path.isfile(path):
            # load_yaml warns and returns an empty mapping on a broken file
            loader = libcalamares.utils.load_yaml(path).get("efiBootLoader")
            if loader:
                return loader
    return "grub"


def bootloader_packages(arch, efi):
    """Boot loader packages for the target, mimicking the live media's loader.

    The live medium only needs the EFI binaries (grub-efi-*-bin); the target
    gets the full package instead, so its maintainer script refreshes the
    loader on future upgrades. BIOS boot is grub-pc whatever the medium used,
    since neither systemd-boot nor rEFInd can boot it."""
    if not efi:
        return ["grub-pc"]
    loader = efi_boot_loader()
    if loader == "systemd-boot":
        return ["systemd-boot", "systemd-boot-efi"]
    if loader == "refind":
        return ["refind"]
    return [GRUB_EFI.get(arch, GRUB_EFI["amd64"])]


def bootstrapper(conf):
    """The bootstrap tool to use: the first of the preferred tools installed on
    the live system, unless the configuration names one explicitly."""
    named = conf.get("bootstrapper", "")
    if named in BASE_ARGS:
        return named
    if named:
        libcalamares.utils.warning(
            "unknown bootstrapper {!s} configured; ignoring it".format(named))
    for tool in ("cdebootstrap", "debootstrap"):
        if shutil.which(tool):
            return tool
    libcalamares.utils.warning("no bootstrap tool installed on the live system")
    return "debootstrap"


def bootstrap_command(tool, conf, arch, suite, mirror, root):
    """The bootstrapper command line, following pyfll's debbootstrap()."""
    include = ",".join(conf.get("bootstrapInclude", []))

    if tool == "mmdebstrap":
        command = ["mmdebstrap",
                   "--architectures=" + arch,
                   "--mode=root",
                   "--format=directory",
                   "--hook-dir=/usr/share/mmdebstrap/hooks/merged-usr"]
    elif tool == "cdebootstrap":
        command = ["cdebootstrap", "--arch=" + arch]
    else:
        command = ["debootstrap", "--arch=" + arch, "--merged-usr"]

    command += BASE_ARGS[tool]
    if include:
        command.append("--include=" + include)
    command += [suite, root, mirror]
    return command


def prime_apt(root, stanzas):
    """Give the target the live system's apt configuration: its sources, its
    pinning and the keyrings those sources are signed by.

    The bootstrapper's own one-line sources.list is dropped - the live media
    uses deb822 sources exclusively, and keeping both would configure the
    Debian mirror twice."""
    for relpath in ("etc/apt/sources.list.d", "etc/apt/preferences.d"):
        source_dir = os.path.join("/", relpath)
        if not os.path.isdir(source_dir):
            continue
        target_dir = os.path.join(root, relpath)
        os.makedirs(target_dir, exist_ok=True)
        for name in sorted(os.listdir(source_dir)):
            source = os.path.join(source_dir, name)
            if os.path.isfile(source):
                shutil.copy2(source, os.path.join(target_dir, name))

    sources_list = os.path.join(root, "etc/apt/sources.list")
    if os.path.isfile(sources_list):
        os.unlink(sources_list)

    for keyring in apt_keyrings(stanzas):
        target_keyring = os.path.join(root, keyring.lstrip("/"))
        os.makedirs(os.path.dirname(target_keyring), exist_ok=True)
        shutil.copy2(keyring, target_keyring)


def write_resolv_conf(root):
    """Give the target a resolver while packages are installed into it: apt
    runs there under chroot, which shares the live session's network but not
    its /run, so systemd-resolved's stub symlink would dangle. Prefer the
    upstream servers resolved knows about, else whatever the live system uses
    (copied, not linked, so the target sees the contents).

    Only for the install itself; the networkcfg module replaces this later with
    the live system's own /etc/resolv.conf, symlink and all."""
    for source in ("/run/systemd/resolve/resolv.conf", "/etc/resolv.conf"):
        if os.path.isfile(source):
            shutil.copy(source, os.path.join(root, "etc/resolv.conf"))
            return
    libcalamares.utils.warning("no resolv.conf to copy into the target")


def preserve_ssh_authorized_keys(root):
    """Carry the live medium's baked in SSH public key into the target.

    pyfll bakes a key into /var/lib/fll/ssh_authorized_keys when one is
    configured, and fll-live-initscripts' fll_sshd installs it for the live
    user. That initscript is no part of an installed system, so the key goes
    into the target's /etc/skel instead: the users module creates the account
    with `useradd -m`, which copies skel and chowns the home directory
    afterwards, so the new user gets the key whatever they called themselves.

    Root stays out of scope, exactly as on the live medium - sshd's
    prohibit-password plus sudo cover privileged access."""
    if not os.path.isfile(SSH_AUTHORIZED_KEYS) or not os.path.getsize(
            SSH_AUTHORIZED_KEYS):
        return

    ssh_dir = os.path.join(root, "etc/skel/.ssh")
    os.makedirs(ssh_dir, exist_ok=True)
    os.chmod(ssh_dir, 0o700)
    authorized_keys = os.path.join(ssh_dir, "authorized_keys")
    shutil.copy(SSH_AUTHORIZED_KEYS, authorized_keys)
    os.chmod(authorized_keys, 0o600)
    libcalamares.utils.debug(
        "preserved the live medium's authorized_keys in the target's /etc/skel")


def policy_rc_d(root, deny):
    """Deny (or allow again) service startup in the target while packages are
    installed there, as pyfll does for its build chroots: maintainer scripts
    must not start daemons in a chroot on the live system's behalf."""
    path = os.path.join(root, "usr/sbin/policy-rc.d")
    if not deny:
        if os.path.isfile(path):
            os.unlink(path)
        return
    with open(path, "w") as policy:
        policy.write("#!/bin/sh\n")
        policy.write('echo "$0 denied action: $1 $2" >&2\n')
        policy.write("exit 101\n")
    os.chmod(path, 0o755)


def target_packages(conf, arch, efi, partitions):
    """The full package list for a minimal target: the configured essentials,
    tools for the filesystems it is being installed onto, and the kernel,
    initramfs tool and boot loader taken from the live system."""
    packages = conf.get("packages", {})
    wanted = list(packages.get("essential", []))
    if efi:
        wanted += packages.get("efi", [])
    wanted += packages.get("firmware", [])
    wanted += packages.get("extra", [])

    initramfs = initramfs_package()

    # Filesystem tools, by the names the partition module puts in globalstorage
    # (KPMcore's, so fat32 rather than vfat). Without them the installed system
    # cannot fsck what it was installed onto, and an encrypted one cannot
    # unlock its root at all. A filesystem with no entry needs no tools.
    tools = packages.get("filesystems", {})
    for partition in partitions or []:
        wanted += tools.get((partition.get("fs") or "").lower(), [])
    if any(partition.get("luksMapperName") for partition in partitions or []):
        wanted += packages.get("luks", [])
        if initramfs == "initramfs-tools":
            # dracut reads crypttab natively; initramfs-tools needs the hooks
            wanted.append("cryptsetup-initramfs")

    wanted.append(kernel_metapackage(arch))
    if initramfs:
        wanted.append(initramfs)
    wanted += bootloader_packages(arch, efi)

    # apt would not mind the duplicates a two-ext4 layout produces, but the
    # log reads better without them
    return list(dict.fromkeys(wanted))


def run():
    """Bootstrap the target when a minimal install was chosen."""
    conf = libcalamares.job.configuration
    gs = libcalamares.globalstorage

    mode_key = conf.get("modeKey", "packagechooser_installmode")
    unpack_key = conf.get("unpackKey", "unpackfs")
    minimal_item = conf.get("minimalItem", "minimal")

    chosen = gs.value(mode_key) if gs.contains(mode_key) else ""
    minimal = minimal_item in [item.strip() for item in (chosen or "").split(",")]

    # unpackfsc reads this as its "condition", so exactly one of the two runs.
    gs.insert(unpack_key, not minimal)
    if not minimal:
        libcalamares.utils.debug(
            "live install: leaving the readonly filesystem to unpackfsc")
        return None

    root = gs.value("rootMountPoint")
    if not root or not os.path.isdir(root):
        return (_("Bootstrap failed"),
                _("There is no mounted target to bootstrap into."))

    if gs.contains("hasInternet") and not gs.value("hasInternet"):
        return (_("Bootstrap failed"),
                _("A minimal install downloads all of its packages and needs "
                  "a working internet connection."))

    efi = gs.value("firmwareType") == "efi"

    try:
        arch = host_output(["dpkg", "--print-architecture"])[0].strip()

        # the mirror and suite to bootstrap from: whatever the live session
        # installs its own Debian packages from
        source = conf.get("bootstrapSource", "debian")
        stanzas = deb822_stanzas(
            "/etc/apt/sources.list.d/{}.sources".format(source))
        mirror = stanzas[0]["uris"].split()[0]
        suite = stanzas[0]["suites"].split()[0]

        tool = bootstrapper(conf)
        report(_("Bootstrapping a minimal system ({!s} {!s})...")
               .format(suite, arch), 0.02)
        libcalamares.utils.host_env_process_output(
            bootstrap_command(tool, conf, arch, suite, mirror, root),
            OutputProgress(0.02, 0.55))

        if tool == "cdebootstrap":
            # cdebootstrap's runlevel helper has no place in an installed system
            libcalamares.utils.target_env_process_output(
                ["dpkg", "--purge", "cdebootstrap-helper-rc.d"])

        report(_("Configuring apt in the target system..."), 0.56)
        stanzas = live_apt_sources()
        prime_apt(root, stanzas)
        write_resolv_conf(root)

        policy_rc_d(root, True)
        try:
            target_apt("update")

            wanted = keyring_packages(apt_keyrings(stanzas))
            wanted += target_packages(conf, arch, efi, gs.value("partitions"))
            if "refind" in wanted:
                # rEFInd's maintainer script must not install itself to the
                # ESP here; the bootloader module and the aptosid-refind job
                # own the target's ESP.
                libcalamares.utils.target_env_process_output(
                    ["debconf-set-selections"], None,
                    "refind refind/install_to_esp boolean false\n")

            report(_("Installing the base system..."), 0.6)
            libcalamares.utils.debug("installing: {!s}".format(" ".join(wanted)))
            target_apt("install", wanted, OutputProgress(0.6, 0.99))
        finally:
            policy_rc_d(root, False)

        preserve_ssh_authorized_keys(root)
    except subprocess.CalledProcessError as error:
        return (_("Bootstrap failed"),
                _("The command <code>{!s}</code> returned error code {!s}.")
                .format(error.cmd, error.returncode))
    except (OSError, IndexError, KeyError) as error:
        return (_("Bootstrap failed"), str(error))

    report(_("Bootstrapped a minimal system"), 1.0)
    return None
