import json
import statistics

observations = [1, 4, 16]
observed = statistics.geometric_mean(observations)
print("PAPER2PROOF_RESULT=" + json.dumps({"observed": observed}, sort_keys=True))
