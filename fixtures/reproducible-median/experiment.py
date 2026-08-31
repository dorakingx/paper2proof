import json
import statistics

observations = [1, 3, 5, 7, 9]
observed = statistics.median(observations)
print("PAPER2PROOF_RESULT=" + json.dumps({"observed": observed}, sort_keys=True))
