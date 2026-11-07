#!/usr/bin/env bash
# Build and deploy the Hive web app to Cloud Run behind IAP.
#   First deploy (admin):  HIVE_PROJECT=<project> HIVE_IAP_MEMBERS=domain:example.com,user:a@example.com deploy/deploy_web.sh
#   Later / CI:            HIVE_PROJECT=<project> [HIVE_WEB_IMAGE=<prebuilt image>] deploy/deploy_web.sh
# With HIVE_IAP_MEMBERS the script enables IAP and grants access; without it, it only rolls out a new revision and
# leaves IAP and IAM exactly as they are (that is all the CI deployer is allowed to do). It always checks that IAP
# still guards the URL afterwards.
set -euo pipefail
cd "$(dirname "$0")/.."

P=${HIVE_PROJECT:?set HIVE_PROJECT}
REGION=${HIVE_REGION:-us-central1}
ENGINE_REGION=${HIVE_ENGINE_REGION:-us-east4}
SERVICE=${HIVE_WEB_SERVICE:-agenthive-web}
MEMBERS=${HIVE_IAP_MEMBERS:-}
IMAGE=${HIVE_WEB_IMAGE:-}

ARGS=(--project "$P" --region "$REGION" --service-account "agenthive-web@$P.iam.gserviceaccount.com"
  --set-env-vars "HIVE_PROJECT=$P,HIVE_REGION=$REGION,HIVE_ENGINE_REGION=$ENGINE_REGION,HIVE_REQUIRE_IAP=1"
  --labels app=agenthive --cpu 1 --memory 512Mi --min-instances 0 --max-instances 3
  --concurrency 40 --timeout 900 --quiet)
if [ -n "$IMAGE" ]; then ARGS+=(--image "$IMAGE"); else ARGS+=(--source .); fi

if [ -n "$MEMBERS" ]; then
  gcloud beta run deploy "$SERVICE" "${ARGS[@]}" --no-allow-unauthenticated --iap
  NUMBER=$(gcloud projects describe "$P" --format='value(projectNumber)')
  # IAP's service agent invokes the service; people are authorised on IAP, not on Cloud Run.
  gcloud run services add-iam-policy-binding "$SERVICE" --project "$P" --region "$REGION" \
    --member "serviceAccount:service-$NUMBER@gcp-sa-iap.iam.gserviceaccount.com" --role roles/run.invoker \
    --quiet >/dev/null
  IFS=',' read -ra M <<< "$MEMBERS"
  for m in "${M[@]}"; do
    gcloud beta iap web add-iam-policy-binding --project "$P" --resource-type=cloud-run --service="$SERVICE" \
      --region="$REGION" --member="$m" --role=roles/iap.httpsResourceAccessor --quiet >/dev/null
    echo "IAP access: $m"
  done
else
  gcloud run deploy "$SERVICE" "${ARGS[@]}"
fi

URL=$(gcloud run services describe "$SERVICE" --project "$P" --region "$REGION" --format='value(status.url)')
# An anonymous request must be sent to Google sign-in by IAP, never served.
for i in 1 2 3 4 5 6; do
  read -r CODE LOCATION < <(curl -s -o /dev/null -w '%{http_code} %{redirect_url}\n' "$URL/" || true)
  case "$CODE $LOCATION" in
    "302 https://accounts.google.com/"*) echo "IAP guards $URL (anonymous request -> Google sign-in)"; exit 0 ;;
  esac
  sleep 10
done
echo "IAP check failed: anonymous request to $URL returned $CODE ${LOCATION:-}" >&2
exit 1
