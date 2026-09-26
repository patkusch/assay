# Paired comparisons

Made with `bench/compare.py`: only items both runs share, 2,000 resamples for each interval. Gaps are B minus A.

## Word scoring against letter scoring, gemma3 4B, calibrated

| Slice | Items | Right answers A → B | Gap | 95% interval | Outside noise? | Confidence error A → B | Gap | 95% interval | Outside noise? |
|---|---|---|---|---|---|---|---|---|---|
| all tasks | 912 | 74.6% → 78.0% | +0.034 | +0.011 to +0.056 | yes | 0.096 → 0.062 | -0.033 | -0.060 to -0.002 | yes |
| command_safety | 280 | 74.6% → 77.9% | +0.032 | +0.000 to +0.068 | no | 0.138 → 0.024 | -0.114 | -0.145 to -0.042 | yes |
| phishing | 232 | 84.5% → 92.2% | +0.078 | +0.043 to +0.116 | yes | 0.083 → 0.070 | -0.013 | -0.062 to +0.020 | no |
| routing | 214 | 58.4% → 65.4% | +0.070 | +0.033 to +0.107 | yes | 0.188 → 0.154 | -0.034 | -0.086 to +0.024 | no |
| urgency | 186 | 80.6% → 74.7% | -0.059 | -0.124 to +0.011 | no | 0.089 → 0.108 | +0.019 | -0.029 to +0.088 | no |

## Word scoring (B, shuffled) against the plain generate-and-parse answer (A) from the letter run, gemma3 4B

| Slice | Items | Right answers A → B | Gap | 95% interval | Outside noise? | Confidence error A → B | Gap | 95% interval | Outside noise? |
|---|---|---|---|---|---|---|---|---|---|
| all tasks | 912 | 81.7% → 78.0% | -0.037 | -0.069 to -0.005 | yes | 0.110 → 0.189 | +0.079 | +0.050 to +0.110 | yes |
| command_safety | 280 | 75.4% → 77.9% | +0.025 | -0.025 to +0.071 | no | 0.163 → 0.199 | +0.036 | -0.007 to +0.085 | no |
| phishing | 232 | 75.4% → 92.2% | +0.168 | +0.121 to +0.220 | yes | 0.181 → 0.074 | -0.107 | -0.152 to -0.057 | yes |
| routing | 214 | 95.8% → 65.4% | -0.304 | -0.369 to -0.243 | yes | 0.017 → 0.313 | +0.296 | +0.229 to +0.365 | yes |
| urgency | 186 | 82.8% → 74.7% | -0.081 | -0.156 to -0.005 | yes | 0.086 → 0.191 | +0.106 | +0.039 to +0.182 | yes |

## gemma3 12B (B) against gemma3 4B (A), letter scoring, shuffled, on the 12B's 320-item subset

| Slice | Items | Right answers A → B | Gap | 95% interval | Outside noise? | Confidence error A → B | Gap | 95% interval | Outside noise? |
|---|---|---|---|---|---|---|---|---|---|
| all tasks | 320 | 74.1% → 90.0% | +0.159 | +0.113 to +0.206 | yes | 0.169 → 0.058 | -0.111 | -0.157 to -0.064 | yes |
| command_safety | 80 | 75.0% → 80.0% | +0.050 | -0.025 to +0.125 | no | 0.214 → 0.143 | -0.071 | -0.170 to +0.037 | no |
| phishing | 80 | 82.5% → 92.5% | +0.100 | +0.037 to +0.175 | yes | 0.089 → 0.036 | -0.053 | -0.130 to +0.007 | no |
| routing | 80 | 60.0% → 92.5% | +0.325 | +0.225 to +0.438 | yes | 0.352 → 0.060 | -0.292 | -0.407 to -0.199 | yes |
| urgency | 80 | 78.8% → 95.0% | +0.162 | +0.062 to +0.263 | yes | 0.103 → 0.090 | -0.013 | -0.112 to +0.042 | no |

Answers that changed when the options were reversed: 10.3% → 3.1% (gap -0.072, 95% interval -0.106 to -0.037, outside noise).

## gemma3 12B (B) against gemma3 4B (A), letter scoring, calibrated, same subset

| Slice | Items | Right answers A → B | Gap | 95% interval | Outside noise? | Confidence error A → B | Gap | 95% interval | Outside noise? |
|---|---|---|---|---|---|---|---|---|---|
| all tasks | 320 | 74.1% → 90.0% | +0.159 | +0.113 to +0.206 | yes | 0.084 → 0.029 | -0.055 | -0.091 to -0.007 | yes |
| command_safety | 80 | 75.0% → 80.0% | +0.050 | -0.025 to +0.125 | no | 0.155 → 0.078 | -0.077 | -0.165 to +0.018 | no |
| phishing | 80 | 82.5% → 92.5% | +0.100 | +0.037 to +0.175 | yes | 0.083 → 0.036 | -0.046 | -0.131 to -0.015 | yes |
| routing | 80 | 60.0% → 92.5% | +0.325 | +0.225 to +0.438 | yes | 0.265 → 0.056 | -0.209 | -0.290 to -0.123 | yes |
| urgency | 80 | 78.8% → 95.0% | +0.162 | +0.062 to +0.263 | yes | 0.077 → 0.081 | +0.004 | -0.081 to +0.064 | no |
