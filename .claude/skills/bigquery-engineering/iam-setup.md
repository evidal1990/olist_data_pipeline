# IAM & Access Setup — Reference

## Principle of Least Privilege

Each system component gets only the roles it needs. Never use an Owner or Editor account for automated jobs.

---

## Service Account for Airbyte

### Required Roles

| Role | Scope | Why |
|---|---|---|
| `roles/bigquery.dataEditor` | Dataset level (`postgres_raw`) | Read/write tables in destination dataset |
| `roles/bigquery.jobUser` | Project level | Submit load jobs |
| `roles/storage.objectCreator` | GCS bucket level | Write staging files (GCS Staging mode) |
| `roles/storage.objectViewer` | GCS bucket level | Read and delete staging files after load |

### Create Service Account (gcloud CLI)

```bash
# 1. Create the service account
gcloud iam service-accounts create airbyte-ingestion \
  --display-name="Airbyte Ingestion SA" \
  --project=YOUR_PROJECT_ID

# 2. Grant BigQuery job submission at project level
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
  --member="serviceAccount:airbyte-ingestion@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/bigquery.jobUser"

# 3. Grant data editor on destination dataset only
bq update \
  --set_label="" \
  YOUR_PROJECT_ID:postgres_raw

# Use bq or Terraform to set dataset-level IAM (not project-level)
# Dataset IAM via bq CLI:
bq add-iam-policy-binding \
  --member="serviceAccount:airbyte-ingestion@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/bigquery.dataEditor" \
  YOUR_PROJECT_ID:postgres_raw

# 4. Grant GCS staging bucket access
gsutil iam ch \
  serviceAccount:airbyte-ingestion@YOUR_PROJECT_ID.iam.gserviceaccount.com:roles/storage.objectCreator \
  gs://airbyte-staging-supply-chain

gsutil iam ch \
  serviceAccount:airbyte-ingestion@YOUR_PROJECT_ID.iam.gserviceaccount.com:roles/storage.legacyBucketReader \
  gs://airbyte-staging-supply-chain

# 5. Generate JSON key for Airbyte
gcloud iam service-accounts keys create airbyte-sa-key.json \
  --iam-account=airbyte-ingestion@YOUR_PROJECT_ID.iam.gserviceaccount.com
```

### Upload Key to Airbyte

In Airbyte BigQuery destination settings:
- **Authentication method:** Service Account Key JSON
- **Service Account Key JSON:** paste the contents of `airbyte-sa-key.json`

**Never commit the key file to git.** Store it in a secrets manager or environment variable.

---

## Dataset-Level Access Control

Grant read access to analysts without exposing the full project:

```bash
# Read-only access to raw dataset for data team
bq add-iam-policy-binding \
  --member="group:data-team@yourcompany.com" \
  --role="roles/bigquery.dataViewer" \
  YOUR_PROJECT_ID:postgres_raw

# Read-only for a specific analyst
bq add-iam-policy-binding \
  --member="user:analyst@yourcompany.com" \
  --role="roles/bigquery.dataViewer" \
  YOUR_PROJECT_ID:postgres_raw
```

---

## Verify Permissions

```bash
# List service account roles at project level
gcloud projects get-iam-policy YOUR_PROJECT_ID \
  --flatten="bindings[].members" \
  --filter="bindings.members:airbyte-ingestion@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
  --format="table(bindings.role)"

# Test BigQuery access as service account
gcloud auth activate-service-account --key-file=airbyte-sa-key.json
bq query --use_legacy_sql=false \
  'SELECT COUNT(*) FROM `YOUR_PROJECT_ID.postgres_raw.orders`'

# Revert to default credentials
gcloud auth application-default login
```

---

## Common IAM Errors

| Error message | Missing role | Where to add |
|---|---|---|
| `Access Denied: BigQuery: Permission bigquery.jobs.create denied` | `roles/bigquery.jobUser` | Project level |
| `Access Denied: BigQuery: Permission bigquery.tables.create denied` | `roles/bigquery.dataEditor` | Dataset level |
| `Access Denied: Storage: Permission storage.objects.create denied` | `roles/storage.objectCreator` | GCS bucket level |
| `The caller does not have permission` on dataset | Not a member of dataset IAM | Add `dataViewer` or `dataEditor` on dataset |
