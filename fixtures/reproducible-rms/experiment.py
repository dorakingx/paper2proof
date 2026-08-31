import json
import math
import statistics

observations = [3, 4]
observed = math.sqrt(statistics.fmean(value * value for value in observations))
print("PAPER2PROOF_RESULT=" + json.dumps({"observed": observed}, sort_keys=True))
