# Controlled Technical Note: Tight Tolerance Breach

This MIT-licensed negative control reports the mean of `4, 5, 6` as **4.99
units** with a tight absolute tolerance of 0.001. The unrounded observed mean
is 5.0, so a correct verifier must return `MISMATCH`.
