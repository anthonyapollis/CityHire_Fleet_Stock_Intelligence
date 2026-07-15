"""
Provision a minimal Azure ML workspace, submit ONE training job on serverless
compute (no persistent cluster - pay only for the job's actual runtime), wait
for it to finish, and print the results. Cleanup (resource group deletion) is
a separate deliberate step run after this succeeds, not part of this script.
"""
import sys
import time
from pathlib import Path

from azure.identity import AzureCliCredential
from azure.ai.ml import MLClient, command, Input
from azure.ai.ml.entities import Workspace, ManagedIdentityConfiguration

SUBSCRIPTION_ID = "cea67e6f-62b2-4b2f-83e8-9af31093d8c8"
RESOURCE_GROUP = "rg-cityhire-ml-temp"
WORKSPACE_NAME = "mlw-cityhire-temp"
LOCATION = "uksouth"

ROOT = Path(__file__).resolve().parent.parent.parent
DATA_PATH = ROOT / "data" / "raw" / "stock_master.csv"
CODE_DIR = Path(__file__).resolve().parent

credential = AzureCliCredential()

print("Step 1/4: creating (or reusing) the Azure ML workspace...")
ml_client_rg = MLClient(credential, SUBSCRIPTION_ID, RESOURCE_GROUP)
ws = Workspace(name=WORKSPACE_NAME, location=LOCATION,
                description="Temporary workspace for CityHire ML demo - delete after use")
ws_poller = ml_client_rg.workspaces.begin_create(ws)
ws_result = ws_poller.result()
print(f"Workspace ready: {ws_result.name}")

ml_client = MLClient(credential, SUBSCRIPTION_ID, RESOURCE_GROUP, WORKSPACE_NAME)

print("Step 2/4: picking a curated environment...")
envs = list(ml_client.environments.list())
sklearn_envs = [e.name for e in envs if "sklearn" in e.name.lower()]
env_name = sklearn_envs[0] if sklearn_envs else None
if env_name is None:
    # fall back to any curated AzureML- environment with sklearn-capable base
    fallback = [e.name for e in envs if e.name.startswith("AzureML-")]
    env_name = fallback[0] if fallback else None
if env_name is None:
    print("No curated environment found - aborting.")
    sys.exit(1)
env_versions = list(ml_client.environments.list(name=env_name))
env_latest = sorted(env_versions, key=lambda e: e.version)[-1]
env_ref = f"azureml:{env_name}:{env_latest.version}"
print(f"Using environment: {env_ref}")

print("Step 3/4: submitting the training job on serverless compute...")
job = command(
    code=str(CODE_DIR),
    command="python train_azure.py --data ${{inputs.data}}",
    inputs={"data": Input(type="uri_file", path=str(DATA_PATH))},
    environment=env_ref,
    compute="serverless",
    display_name="cityhire-day-rate-pricing-model",
    experiment_name="cityhire-fleet-intelligence",
    description="Day-rate pricing model (RandomForest) - CityHire Fleet & Stock Intelligence portfolio build",
)

submitted = ml_client.jobs.create_or_update(job)
print(f"Job submitted: {submitted.name}")
print(f"Studio URL: {submitted.studio_url}")

print("Step 4/4: streaming job logs until completion (this can take a few minutes)...")
ml_client.jobs.stream(submitted.name)

final = ml_client.jobs.get(submitted.name)
print(f"\nFinal status: {final.status}")
print(f"Job name (for cleanup / reference): {submitted.name}")
