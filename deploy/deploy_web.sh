#!/usr/bin/env bash
# Build and deploy the Hive web app to Cloud Run behind IAP.
#   HIVE_PROJECT=<project> [HIVE_IAP_MEMBERS=domain:example.com,user:a@example.com] deploy/deploy_web.sh
set -euo pipefail
cd "$(dirname "$0")/.."

P=${HIVE_PROJECT:?set HIVE_PROJECT}
REGION=${HIVE_REGION:-us-central1}
ENGINE_REGION=${HIVE_ENGINE_REGION:-us-east4}
SERVICE=${HIVE_WEB_SERVICE:-agenthive-web}
MEMBERS=${HIVE_IAP_MEMBERS:?set HIVE_IAP_MEMBERS, e.g. domain:example.com}
NUMBER=$(gcloud projects describe "$P" --format='value(projectNumber)')

gcloud beta run deploy "$SERVICE" --source . --project "$P" --region "$REGION" \
  --service-account "agenthive-web@$P.iam.gserviceaccount.com" \
  --no-allow-unauthenticated --iap \
  --set-env-vars "HIVE_PROJECT=$P,HIVE_REGION=$REGION,HIVE_ENGINE_REGION=$ENGINE_REGION,HIVE_REQUIRE_IAP=1" \
  --labels app=agenthive --cpu 1 --memory 512Mi --min-instances 0 --max-instances 3 \
  --concurrency 40 --timeout 900 --quiet

# IAP's service agent invokes the service; people are authorised on IAP, not on Cloud Run.
gcloud run services add-iam-policy-binding "$SERVICE" --project "$P" --region "$REGION" \
  --member "serviceAccount:service-$NUMBER@gcp-sa-iap.iam.gserviceaccount.com" --role roles/run.invoker --quiet >/dev/null
IFS=',' read -ra M <<< "$MEMBERS"
for m in "${M[@]}"; do
  gcloud beta iap web add-iam-policy-binding --project "$P" --resource-type=cloud-run --service="$SERVICE" \
    --region="$REGION" --member="$m" --role=roles/iap.httpsResourceAccessor --quiet >/dev/null
  echo "IAP access: $m"
done
gcloud run services describe "$SERVICE" --project "$P" --region "$REGION" --format='value(status.url)'
