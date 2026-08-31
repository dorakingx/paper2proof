import json
import pandas

observed = pandas.Series([1, 3, 5, 7, 9]).median()
print("PAPER2PROOF_RESULT=" + json.dumps({"observed": float(observed)}, sort_keys=True))
