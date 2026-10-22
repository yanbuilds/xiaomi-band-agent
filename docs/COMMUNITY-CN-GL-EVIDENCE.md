# Community CN→Global evidence (classification)

Two public write-ups describe replacing the Mi Fitness download file with an
officially signed `miwear.watch.n67gl` package while the app is transferring an
update. One gives the exact shared-storage directory and says the replacement
must preserve Mi Fitness' random filename; another describes using Notify for
Xiaomi to obtain the local pairing key and install a downloaded package.

- [Rubilnik procedure](https://xn--e1alhsoq4c.xn--p1ai/?p=1496)
- [BandBBS Notify procedure](https://www.bandbbs.cn/threads/13399/)

This is **community evidence only**. It does not prove that a current
`n67cn`/3.1.175 device accepts a global package, and it does not bypass the
firmware RSA signature. The described global file is an official signed image,
not a custom build. The procedure also risks a downgrade, model mismatch, loss
of NFC/region features, or a bricked device; no file swap is performed by this
project.

The actionable research result is that a future experiment must first preserve
the original downloaded filename, verify the candidate's official signature,
and capture the complete official recovery path. A locally modified candidate
still fails the RSA preflight and remains disallowed.
