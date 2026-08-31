"""AWS Lambda adapter for the Paper2Proof FastAPI application."""

from mangum import Mangum
from paper2proof.api import app

handler = Mangum(app, lifespan="off")
