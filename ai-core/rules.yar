/*
 * Xtobe Final Guardian - starter YARA ruleset.
 * Extend this file; the guardian hot-loads it at startup.
 */

rule Suspicious_PowerShell_Download {
    meta:
        description = "PowerShell download cradle: remote fetch piped into execution"
        severity = "high"
    strings:
        $fetch1 = "DownloadString" nocase
        $fetch2 = "DownloadFile" nocase
        $fetch3 = "Invoke-WebRequest" nocase
        $fetch4 = "Net.WebClient" nocase
        $fetch5 = "Invoke-RestMethod" nocase
        $run1 = "Invoke-Expression" nocase
        $run2 = "-EncodedCommand" nocase
        $run3 = "iex" fullword nocase
    condition:
        // A cradle has to fetch AND execute. The old 2-of(DownloadString|IEX|-enc)
        // form fired on any file that merely contained the substrings "iex" and
        // "-enc" - including this application's own EXE - so the fetch half is
        // now mandatory and the 3-letter marker must be word-bounded.
        ($fetch1 or $fetch2 or $fetch3 or $fetch4 or $fetch5) and
        ($run1 or $run2 or $run3)
}

rule Embedded_PE_In_Script {
    meta:
        description = "PE image embedded inside a script/text dropper"
        severity = "high"
    strings:
        $mz = { 4D 5A 90 00 }
        $ps = "powershell" nocase
        $b64 = "FromBase64String" nocase
        $iex = "IEX" nocase
        $amsi = "AmsiScanBuffer" nocase
        $cmd = "cmd.exe" nocase
    condition:
        // The PE has to be *embedded*: a file that is itself an executable
        // (MZ at offset 0, i.e. powershell.exe) is not an embedded payload.
        uint16(0) != 0x5A4D and
        $mz in (1..filesize) and
        // ...and it must sit inside script staging code, not an application
        // that merely ships a PE resource alongside the word "powershell".
        2 of ($ps, $b64, $iex, $amsi, $cmd)
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
