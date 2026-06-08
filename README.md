# AWS Price Tracker – Live API

Automated daily tracking of EC2 on‑demand prices using the **official AWS Price List API** via `boto3`.
Runs on GitHub Actions, logs historical prices to CSV.

## Architecture

- Scheduled GitHub Action (cron) runs daily at 09:00 UTC
- Python script uses `boto3` to query AWS Pricing API with filters
- YAML configuration for instances / regions / OS
- Output: timestamped CSV with prices
- AWS credentials stored as GitHub Secrets

## Why this is portfolio‑grade

- **Live data** – no static tables, real AWS API calls
- **Serverless automation** – full pipeline in GitHub Actions
- **Secure credentials** – using GitHub Secrets
- **FinOps ready** – easily extend to Cost Explorer, Slack alerts

## Setup for local testing

1. Clone the repo
2. Create a virtual environment and install dependencies
3. Configure AWS credentials (IAM user with `pricing:GetProducts`)
4. Run `python src/price_fetcher.py`

## AWS IAM policy required

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "pricing:GetProducts",
        "pricing:DescribeServices"
      ],
      "Resource": "*"
    }
  ]
}
```

## GitHub Secrets

Add these to your repository (Settings → Secrets and variables → Actions):

- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`

## Example output

```text
timestamp_utc,region_code,region_friendly,instance_type,os,tenancy,price_usd
2026-06-08T19:41:28+00:00,us-east-1,US East (N. Virginia),t3.micro,Linux,Shared,0.010400
...
```

## License

MIT
