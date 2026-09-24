/*
 * Xtobe Final Guardian - starter YARA ruleset.
 * Extend this file; the guardian hot-loads it at startup.
 */

rule Suspicious_PowerShell_Download {
    meta:
        description = "PowerShell download cradle pattern"
        severity = "high"
    strings:
        $a = "DownloadString" nocase
        $b = "IEX" nocase
        $c = "-enc" nocase
    condition:
        2 of them
}

rule Embedded_PE_In_Script {
    meta:
        description = "PE header embedded in a non-PE file"
        severity = "medium"
    strings:
        $mz = { 4D 5A 90 00 }
        $ps = "powershell" nocase
    condition:
        $mz at 0 and $ps
}

rule Known_Ransomware_Note_Keywords {
    meta:
        description = "Common ransom-note phrasing dropped by executables"
        severity = "critical"
    strings:
        $a = "your files have been encrypted" nocase
        $b = "bitcoin" nocase
        $c = ".onion" nocase
    condition:
        all of them
}

rule Xtobe_Test_Payload {
    meta:
        description = "Xtobe Guardian end-to-end test payload marker"
        severity = "critical"
    strings:
        $marker = "XTOBE-GUARDIAN-TEST-PAYLOAD-7f3a9b" ascii wide
    condition:
        $marker
}
