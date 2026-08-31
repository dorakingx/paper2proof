import json
import statistics

observations = [2, 4, 4, 4, 5, 5, 7, 9]
observed = statistics.fmean(observations)
print("PAPER2PROOF_RESULT=" + json.dumps({"observed": observed}, sort_keys=True))
