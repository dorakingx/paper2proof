import json
import numpy

observed = numpy.mean([2, 4, 4, 4, 5, 5, 7, 9])
print("PAPER2PROOF_RESULT=" + json.dumps({"observed": float(observed)}, sort_keys=True))
