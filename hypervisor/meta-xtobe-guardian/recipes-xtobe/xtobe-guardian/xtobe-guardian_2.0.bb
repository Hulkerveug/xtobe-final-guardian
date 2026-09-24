SUMMARY = "Xtobe guardian core — Python sidecar + token ledger for the microVM"
LICENSE = "CLOSED"

# Ship the same audited sources as the PC build. Point SRC_URI at the repo.
SRC_URI = " \
    file://guardian.py \
    file://token_ledger.py \
    file://xtobe-guardian.service \
"

S = "${WORKDIR}"

inherit systemd
SYSTEMD_SERVICE:${PN} = "xtobe-guardian.service"
SYSTEMD_AUTO_ENABLE:${PN} = "enable"

RDEPENDS:${PN} = "python3 python3-json"

do_install() {
    install -d ${D}${libexecdir}/xtobe
    install -m 0755 ${WORKDIR}/guardian.py ${D}${libexecdir}/xtobe/guardian.py
    install -m 0755 ${WORKDIR}/token_ledger.py ${D}${libexecdir}/xtobe/token_ledger.py

    # Local-only data dirs: feelings + dual ledger live INSIDE the guest.
    install -d ${D}${localstatedir}/lib/xtobe/data

    install -d ${D}${systemd_system_unitdir}
    install -m 0644 ${WORKDIR}/xtobe-guardian.service \
        ${D}${systemd_system_unitdir}/xtobe-guardian.service
}

FILES:${PN} += "${libexecdir}/xtobe ${localstatedir}/lib/xtobe"
