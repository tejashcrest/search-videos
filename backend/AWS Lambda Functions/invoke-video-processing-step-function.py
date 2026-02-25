import json
import boto3
import os
from datetime import datetime
import re

from urllib.parse import unquote_plus

# Initialize Step Functions client
sfn_client = boto3.client('stepfunctions')

# Get state machine ARN from environment variable
STATE_MACHINE_ARN = os.environ['STATE_MACHINE_ARN']

############ Updated for new input
def parse_categories_from_key(key: str) -> list:
    """Parse categories from S3 key. Key format: {categories}/{filename} or {filename}"""
    parts = key.split('/', 1)  # Split on first '/' only
    if len(parts) == 1:
        return ['Uncategorized']
    prefix = parts[0].strip()
    if not prefix:
        return ['Uncategorized']
    # Support both comma and pipe delimiters for backward compatibility
    categories = [c.strip() for c in re.split(r'[|,]', prefix) if c.strip()]
    return categories if categories else ['Uncategorized']

def lambda_handler(event, context):
    """
    Triggered by S3 upload, starts Step Functions execution
    """
    
    # Parse S3 event
    for record in event['Records']:
        bucket = record['s3']['bucket']['name']
        key = unquote_plus(record['s3']['object']['key'])
        dst_bucket = 'demo-raw-useast1-943143228843-dev'
        timestamp = str(datetime.now().strftime('%m-%d-%Y_%H-%M-%S'))
        # Only process video files
        if not key.lower().endswith(('.mp4', '.mov', '.avi')):
            print(f"Skipping non-video file: {key}")
            continue
        
        categories = parse_categories_from_key(key) ############ Updated for new input
        # Prepare input for Step Functions
        sfn_input = {
            "detail": {
                "bucket": {
                    "name": bucket
                },
                "object": {
                    "key": key,
                    "categories": categories ############ Updated for new input
                },
                "dst_bucket": {
                    "key": dst_bucket
                }
            }
        }
        
        # Start Step Functions execution
        try:
            response = sfn_client.start_execution(
                stateMachineArn=STATE_MACHINE_ARN,
                name=f"video-process-{re.sub(r'[^a-zA-Z0-9_-]', '-', key)[:28]}-{timestamp}",
                input=json.dumps(sfn_input)
            )
            
            print(f"Started Step Functions execution: {response['executionArn']}")
            
        except Exception as e:
            print(f"Error starting Step Functions: {str(e)}")
            raise
    
    return {
        'statusCode': 200,
        'body': json.dumps('Step Functions triggered successfully')
    }
