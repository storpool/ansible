#!/opt/storpool/python2/bin/python2
"""
Automates tasks involving installing and updating StorPool modules
"""

from __future__ import print_function
import argparse
import ConfigParser
import cPickle as pickle
from collections import defaultdict
from contextlib import closing
from distutils.version import LooseVersion
import filecmp
import fnmatch
import glob
import itertools
import logging
import logging.handlers
import os
import platform
import re
import subprocess
import sys
import tarfile


def which(exe_name):
    """
    Checks if exe_name in PATH, similar to which
    exe_path: str name of executable
    return None or exe_path
    """
    res = None
    for path in os.environ["PATH"].split(os.pathsep):
        exepath = os.path.join(path, exe_name)
        if os.path.isfile(exepath) and os.access(exepath, os.X_OK):
            res = exe_name
    return res


SP_MANIFEST = "storpool_manifest"
SP_VARIANT = "storpool_variant"
HAVE_STORPOOL = False
if all(which(x) for x in (SP_MANIFEST, SP_VARIANT)):
    HAVE_STORPOOL = True


DEFAULTWORKDIR = os.path.expanduser("~/storpool")
FLEXVOLPATH = (
    "/usr/libexec/kubernetes/kubelet-plugins/volume/exec/"
    "storpool.com~flexvol/flexvol"
)
EXT_BL_LIST = (".bz2", ".efi.signed")


def getlogger():
    """returns logger instance object"""
    logger = logging.getLogger(sys.argv[0])
    logger.setLevel(logging.INFO)
    dhandler = logging.handlers.SysLogHandler(address="/dev/log")
    formatter = logging.Formatter("%(name)s[%(process)d]: %(message)s")
    dhandler.setFormatter(formatter)
    logger.addHandler(dhandler)
    if sys.stdout.isatty():
        # initialises output to stdout as well
        clogger = logging.StreamHandler(sys.stdout)
        clogger.setLevel(logging.INFO)
        logger.addHandler(clogger)
    return logger


def getargs():
    """parses arguments"""
    parser = argparse.ArgumentParser(
        description="""
    Lists available packages in working directory (default: {d})

    Helps in updating changes for the different releases, by default attempts
    to find and install the latest available StorPool package in {d},
    autodetects installed modules and attempts to update only them.
    Does some additional consistency checks and validations, prior to and after
    the installation.
    """.format(
            d=DEFAULTWORKDIR
        )
    )
    parser.add_argument(
        "-w",
        "--workdir",
        help=(
            "Directory to search for release files into (default: {d})"
        ).format(d=DEFAULTWORKDIR),
        default=DEFAULTWORKDIR,
    )
    parser.add_argument(
        "-g",
        "--gid",
        help=(
            "Glob for searching latest package (default: unset)\n"
            "Example: 19.01 will search for storpool-19.01*.tar.gz\n"
            "17775 will search for storpool-*17775*.tar.gz, etc."
        ),
        type=str,
    )
    parser.add_argument(
        "-l",
        "--list",
        help=("Just list all packages found in workdir and exit"),
        action="store_true",
    )
    parser.add_argument(
        "-i",
        "--install",
        help="Install this package, instead the latest in workdir",
        type=str,
    )
    parser.add_argument(
        "--uninstall",
        help=(
            "Uninstall the selected or all autodected modules "
            "(requires '--gid'/'--modules' if none could be autodetected)"
        ),
        action="store_true",
    )
    parser.add_argument(
        "-r",
        "--reinstall",
        help="Skip install checks and reinstall anyway",
        action="store_true",
    )
    parser.add_argument(
        "-m",
        "--modules",
        help=("Install these modules, instead of autodetecting the installed"),
        type=str,
        default="",
    )
    parser.add_argument(
        "--retry",
        help=("Number of times to retry install (helpful for automations)"),
        type=int,
        default=1,
    )
    parser.add_argument(
        "--inplace-reinstall",
        help=(
            "Experimental feature to run yum erase or apt purge on storpool "
            "packages if versions match. Use with caution."
        ),
        action="store_true",
    )
    args = parser.parse_args()
    if args.inplace_reinstall and not HAVE_STORPOOL:
        sys.exit(
            "--inplace-reinstall selected, but StorPool does not seem to be"
            "installed."
        )
    return args


def getpackages(workdir, pat="*"):
    """
    workdir: str path to directory to search release files into
    pat: pattern to search for
    returns list of path to each package found sorted from least to last"""
    return sorted(
        glob.glob("{w}/storpool-{p}.tar.gz".format(w=workdir, p=pat)),
        key=LooseVersion,
    )


def cmdexec(cmd, stdout=None, stderr=None, retry=1):
    """cmd: list of str command arguments
    stdout, stderr: file objects
    retry: int number of times to retry executing cmd in case of failure
    executes cmd, returns tuple (exit-status, stdout, stderr)
    """
    if not stdout:
        stdout = subprocess.PIPE
    if not stderr:
        stderr = subprocess.PIPE
    count = 0
    while count < retry:
        subproc = subprocess.Popen(cmd, stdout=stdout, stderr=stderr)
        out, err = subproc.communicate()
        res = subproc.wait()
        if res == 0:
            break
        print("Command failed: {cmd} -- stdout {out} stderr {err}".format(
            cmd = cmd, out = repr(out), err = repr(err)
            ))
        count += 1
        print(
            "Command count/retry {count}/{retry} (exit {res}): {cmd}".format(
                count=count, retry=retry, res=res, cmd=cmd
            )
        )
    return (subproc.wait(), out, err)


def getrevision(binary):
    """returns the revision string from binary"""
    revision = ""
    with open(binary, "rb") as rtgt:
        stream = rtgt.read()
    sppattern = re.compile(r"storpool_revision=[a-z0-9\.]+")
    results = set(sppattern.findall(stream))
    if results:
        assert len(results) == 1, "More than one storpool_revision found"
        return results.pop().split("=")[1]
    return revision


def getinstalledmodules():
    """
    returns name(path) and revision for all
    /usr/sbin/storpool_*bin files
    """
    revisions = []
    tocheck = itertools.chain(
        *[
            glob.glob(i)
            for i in [
                "/usr/sbin/storpool_*.bin",
                "/usr/lib/debug/usr/sbin/storpool_*.bin",
            ]
        ]
    )
    for binary in tocheck:
        revisions.append((binary, getrevision(binary)))
    return revisions


def detectmodules(modules):
    """
    modules: list of names of the installed StorPool binaries
    returns list of string args for install.sh
    based on the detected installed modules
    """
    resargs = ["@block", "@cli"]
    if os.path.exists(FLEXVOLPATH):
        resargs.append("kubernetes")
    if "/usr/sbin/storpool_server.bin" in modules:
        resargs.append("@block_server")
    for pttn in ["mgmt", "bridge", "iscsi"]:
        if "/usr/sbin/storpool_{s}.bin".format(s=pttn) in modules:
            resargs.append(pttn)
    if [i for i in modules if "debug" in i]:
        resargs.append("debug")
    return list(resargs)


def extract(pkg):
    """
    Extracts pkg in its directory
    """

    def _extracted(allmembers):
        res = []
        for member in allmembers:
            mpath = os.path.join(pkgdir, member.name)
            res.append(os.path.exists(mpath) or os.path.islink(mpath))
        return all(res)

    pkgdir, pkgname = os.path.split(pkg)
    listname = os.path.join(pkgdir, ".{p}.pkl".format(p=pkgname))
    with closing(tarfile.open(pkg, "r:gz")) as tar:
        if os.path.exists(listname):
            with open(listname, "rb") as tgt:
                allmembers = pickle.load(tgt)
        else:
            allmembers = tar.getmembers()  # pylint: disable=no-member
            with open(listname, "wb") as tgt:
                pickle.dump(allmembers, tgt)
        topdir = allmembers[0].name
        if not pkgname.startswith(topdir):
            sys.exit("Unexpected dir {t} in tar archive".format(t=topdir))
        extractdir = os.path.join(pkgdir, topdir)
        if _extracted(allmembers):
            LOGGER.info(
                "%s already seems to be extracted, %s exists",
                os.path.basename(pkg),
                os.path.basename(extractdir),
            )
        else:
            LOGGER.info("Extracting %s in %s", topdir, pkgdir)
            # pylint: disable=no-member
            tar.extractall(path=pkgdir)
    return (extractdir, allmembers)


def getinifile(pkg, allfiles):
    """
    searches for inifile in pkg and does basic validation
    returns str version"""
    pkgdir, pkgname = os.path.split(pkg)
    inifiles = [i for i in allfiles if i.endswith(".ini") and "debug" not in i]
    if not inifiles:
        sys.exit("Could not find ini file for {p}".format(p=pkg))
    elif len(inifiles) > 1:
        sys.exit(
            "More than one inifile found:\n{i}".format(i=" ".join(inifiles))
        )
    inifile = inifiles.pop()
    config = ConfigParser.ConfigParser()
    config.readfp(open(os.path.join(pkgdir, inifile)))
    revision = config.get("source", "version")
    if revision not in pkgname:
        sys.exit(
            "Revision {r} not in package name {p}, bailing out".format(
                r=revision, p=pkgname
            )
        )
    return revision


def getinstshlines(inst, cmd):
    """
    inst: path to install.sh
    cmd: list - command to execute to get list of modules out of inst
    returns semi-validated output from cmd or pre-saved output if the package
    is no longer available, but a saved output exists
    """
    dirname, instname = os.path.split(os.path.dirname(inst))
    defstgt = os.path.join(dirname, ".{n}.defs".format(n=instname))
    if os.path.exists(defstgt):
        with open(defstgt) as dtgt:
            out = dtgt.read()
    else:
        exst, out, err = cmdexec(cmd)
        if exst != 0:
            LOGGER.critical(
                "%s failed with exit status %d\nout:\n%serr:\n%s",
                " ".join(cmd),
                exst,
                out,
                err,
            )
            sys.exit(exst)
        elif err != "":
            LOGGER.critical("Got unexpected error output %s, bailing out", err)
        with open(defstgt, "w") as tgt:
            tgt.write(out)
    return [l for l in out.split("\n") if l.startswith("-")]


def getmoduledefs(inst):
    """
    inst: path to install.sh
    gets modules from install.sh -l, returns dict with module defs
    """
    result = {}
    cmd = [inst, "-l"]
    moduledeflines = getinstshlines(inst, cmd)
    for line in moduledeflines:
        spl = line.split()
        if spl.pop(0) != "-":
            sys.exit(
                "Unexpected line {ln}, please check {c}".format(ln=line, c=cmd)
            )
        result[spl.pop(0)] = spl
    return result


def getkerneltocheck(pkg, allfiles):
    """
    pkg: str path to package
    exits if support for an installed kernel is missing
    returns list of kernels to be checked for installed modules
    """
    runningkernel = platform.release()
    target = os.path.join(
        os.path.dirname(pkg), allfiles[0], "kernel-versions.txt"
    )
    with open(target) as kfile:
        kernelversions = set(k.rstrip("\n") for k in kfile)
    ptpref = r"/boot/vmlinu[zx]-"
    installedkernels = sorted(
        [
            re.sub(ptpref, "", k)
            for k in glob.glob(ptpref + "*")
            if "rescue" not in k
            and not any(k.endswith(i) for i in EXT_BL_LIST)
        ],
        key=(lambda x: LooseVersion(re.sub(r"\.el[67].x86_64$", "", x))),
    )
    kernelstocheck = installedkernels[installedkernels.index(runningkernel) :]
    missing = set(kernelstocheck).difference(kernelversions)
    if missing:
        sys.exit(
            "Support for the following installed kernels missing: {m}".format(
                m="\n".join(missing)
            )
        )
    return kernelstocheck


def kmodinstalled(pkg, allfiles):
    """
    pkg: str path to package file
    allfiles: list of str files from tar archive
    returns True if kernel modules from this package are already installed
    False otherwise"""
    for kernel in getkerneltocheck(pkg, allfiles):
        kdir = os.path.join("/lib/modules/{k}/extra/".format(k=kernel))
        if not os.path.exists(kdir):
            return False
        modules = [
            os.path.basename(i)
            for i in glob.glob(os.path.join(kdir, "storpool_*.ko"))
        ]
        if not modules:
            return False
        manifest = os.path.join(
            os.path.dirname(pkg), allfiles[0], "manifest.json"
        )
        if os.path.exists(manifest):
            # New-style packages do not have file checksums yet
            return False
        for mod in modules:
            pattern = "*/*/lib/modules/{k}/extra/{m}".format(k=kernel, m=mod)
            modfiles = [i for i in allfiles if fnmatch.fnmatch(i, pattern)]
            if not modfiles:
                sys.exit(
                    "Failed to find {m} for installed kernel {k}".format(
                        m=mod, k=kernel
                    )
                )
            elif len(modfiles) > 1:
                sys.exit(
                    (
                        "Found more than one {m} module files for {k}, "
                        "files:\n{f}"
                    ).format(m=mod, k=kernel, f="\n".join(modfiles))
                )
            modfile = os.path.join(os.path.dirname(pkg), modfiles.pop())
            instkmodfile = os.path.join(kdir, modfile)
            if not filecmp.cmp(modfile, instkmodfile):
                return False
    return True


def installed(pkg, allfiles, instmodulesdetails, revision):
    """
    pkg: path to the package file
    instmodulesdetails: list with tuple details for the installed modules
    return True if the package is already installed, False otherwise
    revision: str revision name
    """
    initramfs_flagfile = "/var/run/storpool-skipped-initramfs"
    if os.path.exists(initramfs_flagfile):
        LOGGER.info(
            "%s spotted, a step from previous installation was skipped",
            initramfs_flagfile,
        )
        return False
    if not instmodulesdetails:
        return False
    diff = [d for d in instmodulesdetails if d[1] and d[1] != revision]
    if diff:
        LOGGER.info("Modules different than %s detected:", revision)
        logmodules(diff)
        return False
    if not kmodinstalled(pkg, allfiles):
        return False
    return True


def logmodules(details):
    """Just log what is presently installed"""
    for binary, revision in details:
        LOGGER.info("%-50s%s", binary, revision)


def postinstallchecks():
    """Runs post-install checks"""
    chks = [
        "/usr/lib/storpool/pre-upgrade-checks",
        "/usr/lib/storpool/update_checks",
    ]
    for chk in chks:
        if os.path.isfile(chk) and os.access(chk, os.X_OK):
            exstatus, out, err = cmdexec(chk)
            msgfmt = "%s exited with exit status %d, stdout:\n%s"
            logfunc = LOGGER.info
            if exstatus != 0:
                logfunc = LOGGER.critical
            logfunc(msgfmt, chk, exstatus, out)
            if err:
                logfunc("stderr:\n%s", err)
    checkoldhugepagesleftovers()


def expandmodules(moduleparams, moduledefs):
    """
    moduleparams: list of str names for the install.sh options
    moduledefs: dict with definitions as returned by getmoduledefs
    returns list of all expanded modules behind the alias
    """
    modules = []
    for mdef in moduleparams:
        if mdef in moduledefs:
            modules.extend(moduledefs[mdef])
        else:
            modules.append(mdef)
    return list(set(modules))


def getspdep(mod, allfiles, basedir):
    """
    mod: str name of the module
    allfiles: list of files in the tar
    basedir: str name of the root directory where the tar file is extracted
    does few validations
    returns the contents of the expected spdep
    """
    result = False
    pat = "*/sp-dep/storpool-dep/package-{m}-dep.txt".format(m=mod)
    spdeps = [depfile for depfile in allfiles if fnmatch.fnmatch(depfile, pat)]
    if not spdeps:
        LOGGER.critical("Could not find sp-dep file for %s", mod)
    elif len(spdeps) > 1:
        LOGGER.critical(
            "Found more than one sp-dep file for %s:\n%s",
            mod,
            "\n".join(spdeps),
        )
    else:
        try:
            spdepfile = os.path.join(basedir, spdeps.pop())
            with open(spdepfile) as spdeptgt:
                result = spdeptgt.read().rstrip("\n")
        except IOError as err:
            LOGGER.critical(
                "Failed to get spdep info for %s, error %s", spdepfile, err
            )
    return result


def getdeplist(cmd):
    """
    returns list of all OS packages installed on the node or None in case
    of failure
    """
    result = []
    exst, out, err = cmdexec(cmd)
    if exst != 0:
        LOGGER.critical("%s failed", " ".join(cmd))
        return None
    if err != "":
        LOGGER.critical("Unexpected error output: %s", " ".join(cmd))
        return None
    result.extend([i for i in out.split("\n") if "storpool" in i])
    return result


def getdepcmd(distro):
    """returns None or proper cmd for collecting dependency package names"""
    cmd = None
    if any(distro.lower().startswith(d) for d in ["centos", "virtuozzo"]):
        cmd = ["rpm", "-q", "-a"]
    elif any(distro.lower().startswith(d) for d in ["debian", "ubuntu"]):
        cmd = [
            "dpkg-query",
            "-f=${binary:Package}_${source:Version}_${architecture}.deb\n",
            "-W",
            "storpool-*",
        ]
    return cmd


def depinstalled(allfiles, moduleparams, inst):
    """
    allfiles: list of str path to extracted files
    moduleparams: list of str names for the install.sh options
    inst: path to install.sh
    returns True if dependencies are installed, False otherwise
    """
    modules = expandmodules(moduleparams, getmoduledefs(inst))
    basedir = os.path.dirname(os.path.dirname(inst))
    distro = platform.linux_distribution()[0]
    cmd = getdepcmd(distro)
    if not cmd:
        LOGGER.critical(
            "Distribution %s not supported, skipping check", distro
        )
        return False
    deplist = getdeplist(cmd)
    if deplist is None:
        LOGGER.critical("Failed to collect installed packages")
        return False
    for mod in modules:
        pname = getspdep(mod, allfiles, basedir)
        if not pname:
            return False
        if not [i for i in deplist if pname.startswith(i)]:
            return False
    return True


def get_features(inst):
    """
    inst: str path to install.sh
    return dict with key feature, value feature version
    """

    res = {}
    fcmd = [inst, "--features"]
    exst, fout, _ = cmdexec(fcmd)
    if exst == 0:
        res = dict(
            f.split("=", 1)
            for f in fout.strip("\n").split(":", 1)[1].strip().split()
        )
    return res


def if_needed(inst):
    """
    inst: str path to install.sh
    return: bool whether check_installed is supported or not
    """
    return get_features(inst).get("if-needed")


def tup_version_match(revision, instmodulesdetails):
    """
    revision: str revision name
    check whether the package being installed matches the exact version part
    only.
    return bool
    """
    return tuple(revision.split(".")[0:3]) in set(
        tuple(v[1].split(".")[0:3]) for v in instmodulesdetails if v[1]
    )


def inplace_uninstall():
    """
    attempts to detect apt or yum and uninstall all storpool-*-19.01 detected
    from the node
    """

    lines = subprocess.check_output(
        ["storpool_manifest", "list"], shell=False
    ).splitlines()
    cmd = [
        "storpool_variant",
        "command",
        "run",
        "-N",
        "--",
        "package.purge",
    ] + lines
    if not subprocess.check_call(
        cmd,
        shell=False,
    ):
        LOGGER.error("'%s' failed, please check", " ".join(cmd))


def install(pkg, moduleparams, instmodulesdetails, reinstall, retry, inplace):
    """
    pkg: str path to release revision
    moduleparams: args for StorPool install.sh
    instmodulesdetails: list of tuples with info for installed packages
    reinstall: bool whether to skip the check if package already installed
    retry: int number of times to retry install
    inplace: attempt to uninstall if same version installed
    """
    logmodules(instmodulesdetails)
    try:
        directory, allmembers = extract(pkg)
    except (tarfile.TarError, IOError, pickle.PickleError) as err:
        sys.exit(err)
    allfiles = [i.name for i in allmembers]
    revision = getinifile(pkg, allfiles)
    inplace_install_required = tup_version_match(revision, instmodulesdetails)

    if inplace_install_required and inplace:
        LOGGER.info("Version match detected, and inplace_uninstall")
        inplace_uninstall()
    if (
        installed(pkg, allfiles, instmodulesdetails, revision)
        and not reinstall
    ):
        LOGGER.info(
            "Package already installed, please use --uninstall or --reinstall"
            "if you need a different set of services than the installed"
        )
        return True
    inst = os.path.join(directory, "install.sh")
    instargs = moduleparams[:]
    if if_needed(inst) and not reinstall:
        LOGGER.info(
            "Feature if-needed supported, adding '--if-needed' argument "
            "to install.sh command"
        )
        instargs.insert(0, "--if-needed")
    elif depinstalled(allfiles, moduleparams, inst):
        LOGGER.info("Dependencies already installed, skipping dep install")
        instargs.insert(0, "--skip-os-dep-install")
    cmd = [inst] + instargs
    LOGGER.info("Executing:\n%s", " ".join(cmd))
    exstatus, out, err = cmdexec(cmd, retry=retry)
    if exstatus != 0:
        LOGGER.critical("%s failed, stdout:\n%sstderr:\n%s", inst, out, err)
        sys.exit(exstatus)
    LOGGER.info("%s success, stdout:\n%s", inst, out)
    if err:
        LOGGER.info("stderr:\n%s", err)
    logmodules(getinstalledmodules())
    postinstallchecks()
    return True


def checkoldhugepagesleftovers():
    """Prints a warning if an old hugepages"""
    configurations = []
    if os.path.exists("/etc/default/grub"):
        configurations.append("/etc/default/grub")
    configurations.extend(glob.glob("/boot/*/grub.conf"))
    reg = re.compile(r"hugepages=")
    for cfg in configurations:
        with open(cfg) as rtgt:
            stream = rtgt.read()
            if reg.match(stream):
                LOGGER.warning(
                    "Leftover hugepages configuration spotted in %s", cfg
                )


def refuseifnotonrelease():
    """Exit if a custom change is installed"""
    revfile = "/etc/storpool_revision"
    # 'Revision: 18.02.1104.9d1719e (1574963792:sp-release-18.02)\n'
    if os.path.exists(revfile):
        with open(revfile) as tgt:
            rlist = tgt.read().split()
            rev = rlist[-1].strip("()\n").split(":")[-1]
        if not re.match(r"^sp-release-[12][890]\.0[1-9]$", rev):
            sys.exit(
                (
                    'Installed release "{r}" with revision "{rv}" might not be'
                    ' on the release branch, bailing out (use "--gid" to omit)'
                ).format(r=rlist[1], rv=rev)
            )


def listpkg(packages):
    """just print packages and exit"""
    print("\n".join(packages))
    sys.exit()


def usedbins(details):
    """
    details: list of str path to bin files found on this node
    checks if any pids are existing in /var/run/storpool*.pid and if
    any process with this pid are existing
    returns a list with everything matching
    """

    def _getcontents(ftgt):
        with open(ftgt) as tgt:
            return tgt.read().rstrip("\n")

    def _working(binpath, ftgt):
        result = False
        if os.path.exists(ftgt):
            procpidexe = "/proc/{p}/exe".format(p=_getcontents(ftgt))
            try:
                exepath = os.path.realpath(procpidexe)
                if exepath.endswith(" (deleted)"):
                    exepath = exepath.replace(" (deleted)", "")
                result = os.path.exists(procpidexe) and exepath == binpath
            except (IOError, OSError):
                pass
        return result

    res = []
    for binpath in details:
        pidpath = os.path.join("/var/run", os.path.basename(binpath) + ".pid")
        if _working(binpath, pidpath):
            res.append(os.path.basename(binpath).replace(".bin", ""))
    return res


def getmembers(listname):
    """
    listname: str path to list file
    returns list of str filenames from tar
    """
    with open(listname, "rb") as tgt:
        return pickle.load(tgt)


def getmodfilesdata(workdir, pkllist, moduleparams):
    """
    workdir: path to workdir
    pkllist: path to pkllist to get uninstall data from
    returns dict with key module directories, value list of all files
    found in filelist for this module
    """
    res = defaultdict(list)
    tarmembers = getmembers(pkllist)
    topdir = tarmembers.pop(0).name
    inst = os.path.join(workdir, topdir, "install.sh")
    modules = expandmodules(moduleparams, getmoduledefs(inst))
    for mod in modules:
        dirprefix = os.path.join(topdir, mod)
        pat = dirprefix + "/*"
        matches = [
            i.name
            for i in tarmembers
            if fnmatch.fnmatch(i.name, pat) and i.isfile()
        ]
        for match in matches:
            fmatch = re.sub(dirprefix, "", match)
            if os.path.exists(fmatch):
                res[mod].append(fmatch)
    return res


def overhaul_check_uninstall():
    """
    Performs the new way to uninstall a package post-install-overhaul
    """
    if not os.path.exists("/usr/sbin/storpool_manifest"):
        return
    res = cmdexec(["storpool_manifest", "list"])
    if res[0] != 0:
        sys.exit(res[0])
    mcleanup_command = [
        "storpool_variant",
        "command",
        "run",
        "package.purge",
    ] + res[1].splitlines()
    rescleanup = cmdexec(mcleanup_command)
    sys.exit(rescleanup[0])


def uninstall(args, moduleparams, instmodulesdetails):
    """args: argparse.ArgumentParser instance object
    moduleparams: args for StorPool install.sh
    instmodulesdetails: list of tuples with info for installed packages
    Uninstalls all files installed by the selected modules
    """

    def _getrevisions(args, instmodulesdetails):
        revisions = set(
            i[1]
            for i in instmodulesdetails
            if i[1] and not i[1].endswith(".dirty")
        )
        if len(revisions) > 1 and args.gid is None:
            LOGGER.critical(
                (
                    'Different revisions found, please use "--gid" to specify'
                    " what revision (and modules) should be uninstalled"
                )
            )
            return None
        if not revisions:
            LOGGER.critical(
                "No revision could be autodetected, is StorPool installed?"
            )
            return None
        return revisions

    def _getpkl(args, revisions):
        fmt = ".storpool-*{r}*.pkl"
        pkgfmt = "storpool-*{r}*.tar.gz"
        if args.gid:
            revisionglob = fmt.format(r=args.gid)
            pkgglob = pkgfmt.format(r=args.gid)
        else:
            rev = revisions.pop()
            revisionglob = fmt.format(r=rev)
            pkgglob = pkgfmt.format(r=rev)
        pattern = os.path.join(args.workdir, revisionglob)
        pkgpattern = os.path.join(args.workdir, pkgglob)
        pklnames = glob.glob(pattern)
        pkgnames = glob.glob(pkgpattern)
        if not pklnames:
            if pkgnames:
                try:
                    extract(pkgnames[-1])
                except (
                    tarfile.TarError,
                    IOError,
                    OSError,
                    pickle.PickleError,
                ) as err:
                    sys.exit(
                        "Could not extract {p}, error: {e}".format(
                            p=pkgnames[-1], e=err
                        )
                    )
            pklnames = glob.glob(pattern)
            if not pklnames:
                LOGGER.critical(
                    "Could not find uninstall data for %s", pattern
                )
                return None
        if len(pklnames) > 1:
            LOGGER.info(
                (
                    "More than one pickle found with pattern %s, using the "
                    "last one:\n%s"
                ),
                pattern,
                "\n".join(pklnames),
            )
        return pklnames.pop()

    working = usedbins([i[0] for i in instmodulesdetails])
    if working:
        LOGGER.critical(
            "The following services seem to be working, please check:\n%s",
            "\n".join(working),
        )
        return False
    revisions = _getrevisions(args, instmodulesdetails)
    overhaul_check_uninstall()
    if not revisions:
        return False
    pklname = _getpkl(args, revisions)
    if not pklname:
        return False
    modfilesdata = getmodfilesdata(args.workdir, pklname, moduleparams)
    if not modfilesdata:
        LOGGER.info("No files to cleanup.")
        return True
    for mod in modfilesdata:
        for filetgt in modfilesdata[mod]:
            os.unlink(filetgt)
    os.unlink(pklname)
    LOGGER.info("Success")
    return True


def boolexit(result):
    """inverts bool to exit code"""
    sys.exit(not result)


def main(args):
    """Main function"""
    packages = getpackages(args.workdir)
    if not packages:
        sys.exit(
            "No packages found, please upload a package in {w}".format(
                w=args.workdir
            )
        )
    if args.list:
        listpkg(packages)
    instmodulesdetails = getinstalledmodules()
    moduleparams = args.modules.split()
    if not moduleparams:
        LOGGER.info("No modules specified, autodetecting...")
        moduleparams = detectmodules([i[0] for i in instmodulesdetails])
    if args.uninstall:
        LOGGER.info("Modules to uninstall: %s", " ".join(moduleparams))
        return uninstall(args, moduleparams, instmodulesdetails)
    LOGGER.info("Modules to install: %s", " ".join(moduleparams))
    if args.install:
        if args.gid:
            sys.exit('Please use either "--gid" or "--install"')
        return install(
            args.install,
            moduleparams,
            instmodulesdetails,
            args.reinstall,
            args.retry,
            args.inplace_reinstall,
        )
    pattern = os.path.join(args.workdir, "storpool-1[89].0*")
    if args.gid:
        reg = re.compile(r"[0-9]+\-[0-9]+")
        fmt = "storpool-{g}*"
        if reg.match(args.gid):
            fmt = "storpool-*{g}*"
        pattern = os.path.join(args.workdir, fmt.format(g=args.gid))
    matches = fnmatch.filter(packages, pattern)
    if matches:
        if args.gid is None:
            refuseifnotonrelease()
        return install(
            matches[-1],
            moduleparams,
            instmodulesdetails,
            args.reinstall,
            args.retry,
            args.inplace_reinstall,
        )
    sys.exit("No matching package with {p}".format(p=pattern))


if __name__ == "__main__":
    LOGGER = getlogger()
    ARGS = getargs()
    # check user not root and update PATH
    if os.getuid() != 0:
        sys.exit("Please run this as root (i.e. use sudo)")
    SUDOUSER = os.environ.get("SUDO_USER")
    if SUDOUSER and ARGS.workdir == DEFAULTWORKDIR:
        ARGS.workdir = os.path.expanduser("~{s}/storpool".format(s=SUDOUSER))
        LOGGER.info("Invoked through sudo, path is now %s", ARGS.workdir)
    boolexit(main(ARGS))
