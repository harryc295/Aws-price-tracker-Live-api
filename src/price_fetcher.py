#!/usr/bin/env python3
"""
AWS Price Tracker – Live API version using boto3.
Queries the official AWS Price List API for on‑demand prices.
Requires AWS credentials with pricing:GetProducts permission.
"""

import csv
import sys
import boto3
import yaml
from datetime import datetime, timezone
from pathlib import Path
from botocore.exceptions import ClientError

from logger import setup_logger

logger = setup_logger("price_fetcher", log_file="logs/fetcher.log")

def get_price(region_friendly: str, instance_type: str, os: str, tenancy: str) -> float | None:
    """
    Query AWS Price List API for a specific product.
    Returns hourly on‑demand price in USD or None.
    """
    # Map friendly name to AWS region code
    region_code_map = {
        "US East (N. Virginia)": "us-east-1",
        "US West (Oregon)": "us-west-2",
        "EU (Ireland)": "eu-west-1",
        "Asia Pacific (Singapore)": "ap-southeast-1",
    }
    region_code = region_code_map.get(region_friendly, region_friendly)

    client = boto3.client('pricing', region_name='us-east-1')  # Pricing API only available in us-east-1

    filters = [
        {'Type': 'TERM_MATCH', 'Field': 'instanceType', 'Value': instance_type},
        {'Type': 'TERM_MATCH', 'Field': 'location', 'Value': region_friendly},
        {'Type': 'TERM_MATCH', 'Field': 'operatingSystem', 'Value': os},
        {'Type': 'TERM_MATCH', 'Field': 'tenancy', 'Value': tenancy},
        {'Type': 'TERM_MATCH', 'Field': 'preInstalledSw', 'Value': 'NA'},
        {'Type': 'TERM_MATCH', 'Field': 'capacitystatus', 'Value': 'Used'},
    ]

    try:
        response = client.get_products(
            ServiceCode='AmazonEC2',
            Filters=filters,
            FormatVersion='aws_v1'
        )
        price_list = response.get('PriceList', [])
        if not price_list:
            logger.warning(f"No product found for {instance_type} in {region_friendly}")
            return None

        # Parse the first product (JSON string)
        import json
        product = json.loads(price_list[0])
        on_demand = product.get('terms', {}).get('OnDemand', {})
        for term in on_demand.values():
            price_dimensions = term.get('priceDimensions', {})
            for dim in price_dimensions.values():
                price_per_unit = dim.get('pricePerUnit', {})
                usd = price_per_unit.get('USD')
                if usd:
                    return float(usd)
        return None
    except ClientError as e:
        logger.error(f"AWS API error: {e}")
        return None

def append_to_csv(csv_path: Path, row: list) -> None:
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    headers = ["timestamp_utc", "region_code", "region_friendly", "instance_type", "os", "tenancy", "price_usd"]
    write_header = not csv_path.exists()
    with open(csv_path, 'a', newline='') as f:
        writer = csv.writer(f)
        if write_header:
            writer.writerow(headers)
        writer.writerow(row)

def main():
    config_path = Path("config/instances.yaml")
    if not config_path.exists():
        logger.error("config/instances.yaml not found")
        sys.exit(1)

    with open(config_path) as f:
        config = yaml.safe_load(f)

    instances = config.get("instances", [])
    output_csv = Path(config.get("output", {}).get("csv_path", "data/cost_log.csv"))

    if not instances:
        logger.warning("No instances defined")
        sys.exit(0)

    now_iso = datetime.now(timezone.utc).isoformat(timespec='seconds')
    success = 0

    for inst in instances:
        region_friendly = inst["region"]
        region_code = inst.get("region_code", region_friendly)
        instance_type = inst["instance_type"]
        os_name = inst.get("os", "Linux")
        tenancy = inst.get("tenancy", "Shared")

        logger.info(f"Querying live price for {instance_type} in {region_friendly}...")
        price = get_price(region_friendly, instance_type, os_name, tenancy)

        if price is None:
            price_str = "NOT_FOUND"
            logger.warning(f"No live price found")
        else:
            price_str = f"{price:.6f}"
            success += 1
            logger.info(f"Price: ${price:.4f}/hour")

        row = [now_iso, region_code, region_friendly, instance_type, os_name, tenancy, price_str]
        append_to_csv(output_csv, row)

    logger.info(f"Retrieved {success}/{len(instances)} prices")
    sys.exit(0 if success == len(instances) else 1)

if __name__ == "__main__":
    main()
