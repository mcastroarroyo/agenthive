#!/usr/bin/env bash
# Build and deploy the Hive web app to Cloud Run.
#
# Internal edition (Wursta only, behind IAP):
#   First deploy (admin):  HIVE_PROJECT=<p> HIVE_IAP_MEMBERS=domain:example.com deploy/deploy_web.sh
#   Later / CI:            HIVE_PROJECT=<p> [HIVE_WEB_IMAGE=<image>] deploy/deploy_web.sh
# Showcase edition (Google + clients; any Google account signs in, app-level auth):
#   HIVE_EDITION=showcase HIVE_PROJECT=<p> HIVE_GOOGLE_CLIENT_ID=<id> HIVE_ADMINS=a@x.com,b@y.com \
#     [HIVE_PUBLIC=1 on the first, admin deploy] [HIVE_WEB_IMAGE=<image>] deploy/deploy_web.sh
#
# Without HIVE_IAP_MEMBERS / HIVE_PUBLIC the script only rolls out a new revision and leaves IAM and IAP as they are
# (that is all the CI deployer may do). It always checks the access model afterwards: internal = anonymous request
# goes to Google sign-in (IAP); showcase = the page is public and the API answers 401 without the app's sign-in.
set -euo pipefail
cd "$(dirname "$0")/.."

P=${HIVE_PROJECT:?set HIVE_PROJECT}
EDITION=${HIVE_EDITION:-internal}
REGION=${HIVE_REGION:-us-central1}
ENGINE_REGION=${HIVE_ENGINE_REGION:-us-east4}
IMAGE=${HIVE_WEB_IMAGE:-}

if [ "$EDITION" = internal ]; then
  SERVICE=${HIVE_WEB_SERVICE:-agenthive-web}
  SA=agenthive-web@$P.iam.gserviceaccount.com
  ENV="HIVE_PROJECT=$P,HIVE_REGION=$REGION,HIVE_ENGINE_REGION=$ENGINE_REGION,HIVE_REQUIRE_IAP=1"
  EXTRA=()
else
  SERVICE=${HIVE_WEB_SERVICE:-agenthive-$EDITION}
  SA=agenthive-$EDITION-web@$P.iam.gserviceaccount.com
  CLIENT_ID=${HIVE_GOOGLE_CLIENT_ID:?set HIVE_GOOGLE_CLIENT_ID (OAuth web client of the login project)}
  ADMINS=${HIVE_ADMINS:?set HIVE_ADMINS (comma-separated admin emails)}
  ENV="^|^HIVE_PROJECT=$P|HIVE_REGION=$REGION|HIVE_ENGINE_REGION=$ENGINE_REGION|HIVE_EDITION=$EDITION|HIVE_AUTH=google"
  ENV="$ENV|HIVE_FIRESTORE_DB=agenthive|HIVE_GOOGLE_CLIENT_ID=$CLIENT_ID|HIVE_ADMINS=$ADMINS"
  EXTRA=(--set-secrets "HIVE_SESSION_SECRET=agenthive-$EDITION-session:latest")
fi

ARGS=(--project "$P" --region "$REGION" --service-account "$SA" --set-env-vars "$ENV" ${EXTRA[@]+"${EXTRA[@]}"}
  --labels app=agenthive,edition=$EDITION --cpu 1 --memory 512Mi --min-instances 0 --max-instances 3
  --concurrency 40 --timeout 900 --quiet)
if [ -n "$IMAGE" ]; then ARGS+=(--image "$IMAGE"); else ARGS+=(--source .); fi

if [ "$EDITION" = internal ] && [ -n "${HIVE_IAP_MEMBERS:-}" ]; then
  gcloud beta run deploy "$SERVICE" "${ARGS[@]}" --no-allow-unauthenticated --iap
  NUMBER=$(gcloud projects describe "$P" --format='value(projectNumber)')
  # IAP's service agent invokes the service; people are authorised on IAP, not on Cloud Run.
  gcloud run services add-iam-policy-binding "$SERVICE" --project "$P" --region "$REGION" \
    --member "serviceAccount:service-$NUMBER@gcp-sa-iap.iam.gserviceaccount.com" --role roles/run.invoker \
    --quiet >/dev/null
  IFS=',' read -ra M <<< "$HIVE_IAP_MEMBERS"
  for m in "${M[@]}"; do
    gcloud beta iap web add-iam-policy-binding --project "$P" --resource-type=cloud-run --service="$SERVICE" \
      --region="$REGION" --member="$m" --role=roles/iap.httpsResourceAccessor --quiet >/dev/null
    echo "IAP access: $m"
  done
elif [ "$EDITION" != internal ] && [ "${HIVE_PUBLIC:-}" = 1 ]; then
  gcloud run deploy "$SERVICE" "${ARGS[@]}" --allow-unauthenticated   # sign-in happens in the app
else
  gcloud run deploy "$SERVICE" "${ARGS[@]}"   # keeps the service's IAM and IAP settings
fi

URL=$(gcloud run services describe "$SERVICE" --project "$P" --region "$REGION" --format='value(status.url)')
for i in 1 2 3 4 5 6; do
  if [ "$EDITION" = internal ]; then
    read -r CODE LOCATION < <(curl -s -o /dev/null -w '%{http_code} %{redirect_url}\n' "$URL/" || true)
    case "$CODE $LOCATION" in
      "302 https://accounts.google.com/"*) echo "IAP guards $URL (anonymous request -> Google sign-in)"; exit 0 ;;
    esac
  else
    PAGE=$(curl -s -o /dev/null -w '%{http_code}' "$URL/" || true)
    API=$(curl -s -o /dev/null -w '%{http_code}' "$URL/api/catalog" || true)
    if [ "$PAGE" = 200 ] && [ "$API" = 401 ]; then echo "$URL is public; its API requires the app's Google sign-in"; exit 0; fi
    CODE="page $PAGE, api $API"
  fi
  sleep 10
done
echo "Access check failed for $URL ($EDITION): $CODE ${LOCATION:-}" >&2
exit 1
