import json
import os

observed = float(len(os.environ))
print("PAPER2PROOF_RESULT=" + json.dumps({"observed": observed}, sort_keys=True))
