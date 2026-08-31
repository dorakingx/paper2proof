import json
import statistics

observations = [1, 2, 3]
observed = statistics.pstdev(observations)
print("PAPER2PROOF_RESULT=" + json.dumps({"observed": observed}, sort_keys=True))
