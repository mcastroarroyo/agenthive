#!/usr/bin/env bash
# One-time (idempotent) setup for GitHub Actions auto-deploy via Workload Identity Federation (no SA keys).
#   HIVE_PROJECT=<project> HIVE_GH_REPO=<owner>/<repo> deploy/setup_cicd.sh
# Run after deploy/bootstrap.sh and the first manual deploy_web.sh (the Cloud Run service must exist).
# Creates: SA agenthive-deployer with resource-scoped roles, Artifact Registry repo "agenthive", WIF pool + GitHub
# provider that only accepts tokens from refs/heads/main of that one repository. Stores the three values the deploy
# workflow needs as GitHub Actions secrets (masked in public logs).
set -euo pipefail

P=${HIVE_PROJECT:?set HIVE_PROJECT}
REPO=${HIVE_GH_REPO:?set HIVE_GH_REPO, e.g. owner/agenthive}
REGION=${HIVE_REGION:-us-central1}
ENGINE_REGION=${HIVE_ENGINE_REGION:-us-east4}
DATASET=${HIVE_BQ_DATASET:-agenthive_demo}
SERVICE=${HIVE_WEB_SERVICE:-agenthive-web}
POOL=agenthive-github
PROVIDER=github
NUMBER=$(gcloud projects describe "$P" --format='value(projectNumber)')
SA=agenthive-deployer@$P.iam.gserviceaccount.com
IDS=$(gh api "repos/$REPO" --jq '"\(.id) \(.owner.id)"')
REPO_ID=${IDS% *}
OWNER_ID=${IDS#* }

echo "== APIs"
gcloud services enable iamcredentials.googleapis.com sts.googleapis.com artifactregistry.googleapis.com --project "$P"

echo "== Deployer service account"
gcloud iam service-accounts describe "$SA" --project "$P" >/dev/null 2>&1 || \
  gcloud iam service-accounts create agenthive-deployer --project "$P" \
    --display-name "Agent Hive deployer (GitHub Actions)"

# Project-level only where the API has no resource-level IAM.
for r in roles/aiplatform.user roles/discoveryengine.editor roles/bigquery.jobUser; do
  gcloud projects add-iam-policy-binding "$P" --member "serviceAccount:$SA" --role "$r" --condition=None \
    --quiet >/dev/null && echo "  $r (project)"
done
# Act as the runtime SA (engines) and the web SA (Cloud Run) — nothing else.
for target in agenthive-runtime agenthive-web; do
  gcloud iam service-accounts add-iam-policy-binding "$target@$P.iam.gserviceaccount.com" --project "$P" \
    --member "serviceAccount:$SA" --role roles/iam.serviceAccountUser --quiet >/dev/null \
    && echo "  serviceAccountUser on $target"
done
# Objects in the Hive buckets only (engine staging + KB corpus).
for b in "gs://$P-agenthive" "gs://$P-agenthive-$ENGINE_REGION"; do
  for r in roles/storage.objectAdmin roles/storage.legacyBucketReader; do
    gcloud storage buckets add-iam-policy-binding "$b" --member "serviceAccount:$SA" --role "$r" >/dev/null
  done
  echo "  objectAdmin on ${b##*/}"
done
# The one Cloud Run service (new revisions, not IAM or IAP settings).
gcloud run services add-iam-policy-binding "$SERVICE" --project "$P" --region "$REGION" \
  --member "serviceAccount:$SA" --role roles/run.developer --quiet >/dev/null && echo "  run.developer on $SERVICE"

echo "== Artifact Registry repo agenthive ($REGION)"
gcloud artifacts repositories describe agenthive --project "$P" --location "$REGION" >/dev/null 2>&1 || \
  gcloud artifacts repositories create agenthive --project "$P" --location "$REGION" --repository-format docker \
    --description "Agent Hive web images" --labels app=agenthive
POLICY=$(mktemp)
cat > "$POLICY" <<'JSON'
[{"name": "keep-last-10", "action": {"type": "Keep"}, "mostRecentVersions": {"keepCount": 10}},
 {"name": "delete-older", "action": {"type": "Delete"}, "condition": {"olderThan": "604800s"}}]
JSON
gcloud artifacts repositories set-cleanup-policies agenthive --project "$P" --location "$REGION" \
  --policy "$POLICY" --no-dry-run --quiet >/dev/null
rm -f "$POLICY"
gcloud artifacts repositories add-iam-policy-binding agenthive --project "$P" --location "$REGION" \
  --member "serviceAccount:$SA" --role roles/artifactregistry.writer --quiet >/dev/null && echo "  writer on repo"

echo "== BigQuery dataset $DATASET (WRITER for the seed job)"
ACL=$(mktemp)
bq --project_id "$P" show --format=prettyjson "$P:$DATASET" > "$ACL"
python3 - "$ACL" "$SA" <<'PY'
import json, sys
path, sa = sys.argv[1], sys.argv[2]
d = json.load(open(path))
if not any(a.get("userByEmail") == sa and a.get("role") == "WRITER" for a in d["access"]):
    d["access"].append({"role": "WRITER", "userByEmail": sa})
json.dump({"access": d["access"]}, open(path, "w"))
PY
bq --project_id "$P" update --source "$ACL" "$P:$DATASET" >/dev/null && echo "  WRITER on dataset"
rm -f "$ACL"

echo "== Workload Identity pool $POOL / provider $PROVIDER"
gcloud iam workload-identity-pools describe "$POOL" --project "$P" --location global >/dev/null 2>&1 || \
  gcloud iam workload-identity-pools create "$POOL" --project "$P" --location global \
    --display-name "Agent Hive · GitHub Actions"
CONDITION="assertion.repository_id == '$REPO_ID' && assertion.repository_owner_id == '$OWNER_ID' && assertion.ref == 'refs/heads/main'"
MAPPING="google.subject=assertion.sub,attribute.repository_id=assertion.repository_id,attribute.repository=assertion.repository,attribute.ref=assertion.ref"
if gcloud iam workload-identity-pools providers describe "$PROVIDER" --project "$P" --location global \
     --workload-identity-pool "$POOL" >/dev/null 2>&1; then
  gcloud iam workload-identity-pools providers update-oidc "$PROVIDER" --project "$P" --location global \
    --workload-identity-pool "$POOL" --attribute-mapping "$MAPPING" --attribute-condition "$CONDITION" --quiet
else
  gcloud iam workload-identity-pools providers create-oidc "$PROVIDER" --project "$P" --location global \
    --workload-identity-pool "$POOL" --display-name "GitHub ($REPO main)" \
    --issuer-uri https://token.actions.githubusercontent.com \
    --attribute-mapping "$MAPPING" --attribute-condition "$CONDITION"
fi
gcloud iam service-accounts add-iam-policy-binding "$SA" --project "$P" --role roles/iam.workloadIdentityUser \
  --member "principalSet://iam.googleapis.com/projects/$NUMBER/locations/global/workloadIdentityPools/$POOL/attribute.repository_id/$REPO_ID" \
  --quiet >/dev/null && echo "  workloadIdentityUser for repo $REPO_ID"

echo "== GitHub secrets on $REPO"
gh secret set GCP_PROJECT --repo "$REPO" --body "$P"
gh secret set GCP_DEPLOYER_SA --repo "$REPO" --body "$SA"
gh secret set GCP_WIF_PROVIDER --repo "$REPO" \
  --body "projects/$NUMBER/locations/global/workloadIdentityPools/$POOL/providers/$PROVIDER"
echo "done."
