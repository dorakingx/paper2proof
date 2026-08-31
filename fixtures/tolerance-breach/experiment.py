import json
import statistics

observations = [4, 5, 6]
observed = statistics.fmean(observations)
print("PAPER2PROOF_RESULT=" + json.dumps({"observed": observed}, sort_keys=True))
