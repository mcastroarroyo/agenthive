#!/usr/bin/env bash
# One-time (idempotent) setup of the showcase web app — the version presented to Google and clients.
#   HIVE_PROJECT=<project> HIVE_GH_REPO=<owner>/<repo> HIVE_GOOGLE_CLIENT_ID=<oauth web client id> \
#   HIVE_ADMINS=a@example.com,b@example.com deploy/setup_showcase.sh
# Prerequisites: deploy/bootstrap.sh and deploy/setup_cicd.sh have run; the Firestore database "agenthive" exists;
# an OAuth web client (External consent screen, any project) lists the service URL as an authorised JS origin.
# Creates: session-signing secret, SA agenthive-showcase-web (call engines, write logs, read/write only the
# agenthive Firestore database, read only its secret), the public Cloud Run service (sign-in happens in the app),
# deployer rights to roll out new revisions, and the GitHub secrets the deploy workflow needs.
set -euo pipefail
cd "$(dirname "$0")/.."

P=${HIVE_PROJECT:?set HIVE_PROJECT}
REPO=${HIVE_GH_REPO:?set HIVE_GH_REPO}
CLIENT_ID=${HIVE_GOOGLE_CLIENT_ID:?set HIVE_GOOGLE_CLIENT_ID}
ADMINS=${HIVE_ADMINS:?set HIVE_ADMINS}
REGION=${HIVE_REGION:-us-central1}
SERVICE=agenthive-showcase
SECRET=agenthive-showcase-session
SA=agenthive-showcase-web@$P.iam.gserviceaccount.com
DEPLOYER=agenthive-deployer@$P.iam.gserviceaccount.com

echo "== Session-signing secret"
gcloud secrets describe "$SECRET" --project "$P" >/dev/null 2>&1 || \
  python3 -c "import secrets,sys; sys.stdout.write(secrets.token_urlsafe(48))" | \
  gcloud secrets create "$SECRET" --project "$P" --replication-policy=automatic --labels=app=agenthive --data-file=-

echo "== Service account"
gcloud iam service-accounts describe "$SA" --project "$P" >/dev/null 2>&1 || \
  gcloud iam service-accounts create agenthive-showcase-web --project "$P" --display-name "Agent Hive showcase web"
for r in roles/aiplatform.user roles/logging.logWriter; do
  gcloud projects add-iam-policy-binding "$P" --member "serviceAccount:$SA" --role "$r" --condition=None \
    --quiet >/dev/null && echo "  $r"
done
gcloud projects add-iam-policy-binding "$P" --member "serviceAccount:$SA" --role roles/datastore.user --quiet \
  --condition="expression=resource.name == \"projects/$P/databases/agenthive\",title=agenthive-firestore-only" \
  >/dev/null && echo "  datastore.user (agenthive database only)"
gcloud secrets add-iam-policy-binding "$SECRET" --project "$P" --member "serviceAccount:$SA" \
  --role roles/secretmanager.secretAccessor --quiet >/dev/null && echo "  secretAccessor on $SECRET"
gcloud iam service-accounts add-iam-policy-binding "$SA" --project "$P" --member "serviceAccount:$DEPLOYER" \
  --role roles/iam.serviceAccountUser --quiet >/dev/null && echo "  deployer may act as it"

echo "== First deploy (public service; the app requires Google sign-in)"
HIVE_EDITION=showcase HIVE_PUBLIC=1 HIVE_PROJECT="$P" HIVE_GOOGLE_CLIENT_ID="$CLIENT_ID" HIVE_ADMINS="$ADMINS" \
  deploy/deploy_web.sh
gcloud run services add-iam-policy-binding "$SERVICE" --project "$P" --region "$REGION" \
  --member "serviceAccount:$DEPLOYER" --role roles/run.developer --quiet >/dev/null && echo "  run.developer -> deployer"

echo "== GitHub secrets on $REPO"
gh secret set GCP_SHOWCASE_CLIENT_ID --repo "$REPO" --body "$CLIENT_ID"
gh secret set GCP_SHOWCASE_ADMINS --repo "$REPO" --body "$ADMINS"
echo "done: $(gcloud run services describe "$SERVICE" --project "$P" --region "$REGION" --format='value(status.url)')"
