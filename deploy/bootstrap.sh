#!/usr/bin/env bash
# One-time (idempotent) project setup for the Agent Hive.
#   HIVE_PROJECT=<project> deploy/bootstrap.sh
# Creates: staging/corpus bucket, runtime + web service accounts with least-privilege roles, BigQuery dataset,
# one Vertex AI Search data store per realm. Nothing project-specific is stored in the repo.
set -euo pipefail

P=${HIVE_PROJECT:?set HIVE_PROJECT}
REGION=${HIVE_REGION:-us-central1}
ENGINE_REGION=${HIVE_ENGINE_REGION:-us-east4}
DATASET=${HIVE_BQ_DATASET:-agenthive_demo}
KB_PREFIX=${HIVE_KB_PREFIX:-agenthive-kb}
BUCKET=gs://${P}-agenthive
RUNTIME_SA=agenthive-runtime@${P}.iam.gserviceaccount.com
WEB_SA=agenthive-web@${P}.iam.gserviceaccount.com
REALMS=(platform government enterprise smb delivery workforce)

echo "== APIs"
gcloud services enable aiplatform.googleapis.com discoveryengine.googleapis.com bigquery.googleapis.com \
  run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com iap.googleapis.com \
  storage.googleapis.com logging.googleapis.com --project "$P"

echo "== Bucket $BUCKET"
gcloud storage buckets describe "$BUCKET" --project "$P" >/dev/null 2>&1 || \
  gcloud storage buckets create "$BUCKET" --project "$P" --location "$REGION" --uniform-bucket-level-access
gcloud storage buckets update "$BUCKET" --update-labels=app=agenthive >/dev/null
STAGING=gs://${P}-agenthive-${ENGINE_REGION}   # Agent Engine staging bucket, co-located with the engines
gcloud storage buckets describe "$STAGING" --project "$P" >/dev/null 2>&1 || \
  gcloud storage buckets create "$STAGING" --project "$P" --location "$ENGINE_REGION" --uniform-bucket-level-access
gcloud storage buckets update "$STAGING" --update-labels=app=agenthive >/dev/null

echo "== Service accounts"
for sa in agenthive-runtime agenthive-web; do
  gcloud iam service-accounts describe "$sa@$P.iam.gserviceaccount.com" --project "$P" >/dev/null 2>&1 || \
    gcloud iam service-accounts create "$sa" --project "$P" --display-name "Agent Hive ${sa#agenthive-}"
done

bind() { gcloud projects add-iam-policy-binding "$P" --member "serviceAccount:$1" --role "$2" --condition=None \
  --quiet >/dev/null && echo "  $2 -> ${1%%@*}"; }
for r in roles/aiplatform.user roles/logging.logWriter roles/cloudtrace.agent roles/monitoring.metricWriter \
         roles/bigquery.jobUser roles/discoveryengine.viewer; do bind "$RUNTIME_SA" "$r"; done
for r in roles/aiplatform.user roles/logging.logWriter; do bind "$WEB_SA" "$r"; done
gcloud storage buckets add-iam-policy-binding "$BUCKET" --member "serviceAccount:$RUNTIME_SA" \
  --role roles/storage.objectViewer >/dev/null && echo "  objectViewer on bucket -> runtime"

echo "== BigQuery dataset $DATASET"
bq --project_id "$P" show "$P:$DATASET" >/dev/null 2>&1 || \
  bq --project_id "$P" mk --dataset --location "$REGION" --label app:agenthive \
     --description "Agent Hive synthetic demo warehouse" "$P:$DATASET"
ACL=$(mktemp)
bq --project_id "$P" show --format=prettyjson "$P:$DATASET" > "$ACL"
python3 - "$ACL" "$RUNTIME_SA" <<'PY'
import json, sys
path, sa = sys.argv[1], sys.argv[2]
d = json.load(open(path))
if not any(a.get("userByEmail") == sa for a in d["access"]):
    d["access"].append({"role": "READER", "userByEmail": sa})
json.dump({"access": d["access"]}, open(path, "w"))
PY
bq --project_id "$P" update --source "$ACL" "$P:$DATASET" >/dev/null && echo "  READER on dataset -> runtime"
rm -f "$ACL"

echo "== Vertex AI Search data stores"
TOKEN=$(gcloud auth print-access-token)
BASE="https://discoveryengine.googleapis.com/v1/projects/$P/locations/global/collections/default_collection/dataStores"
for realm in "${REALMS[@]}"; do
  id="$KB_PREFIX-$realm"
  code=$(curl -s -o /dev/null -w "%{http_code}" -H "Authorization: Bearer $TOKEN" -H "X-Goog-User-Project: $P" "$BASE/$id")
  if [ "$code" = 200 ]; then echo "  $id exists"; continue; fi
  curl -s -X POST -H "Authorization: Bearer $TOKEN" -H "X-Goog-User-Project: $P" -H "Content-Type: application/json" \
    "$BASE?dataStoreId=$id" -d "{\"displayName\": \"Agent Hive KB · $realm\", \"industryVertical\": \"GENERIC\",
      \"solutionTypes\": [\"SOLUTION_TYPE_SEARCH\"], \"contentConfig\": \"CONTENT_REQUIRED\"}" | head -c 300
  echo "  created $id"
done
echo "done."
