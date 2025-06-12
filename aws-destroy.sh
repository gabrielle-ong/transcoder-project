#!/bin/bash
set -e

# Script to de-provision AWS resources for the transcoding application.
# It requires the same unique suffix used during initialization.
# Example usage: ./aws-destroy.sh my-unique-suffix

if [ -z "$1" ]; then
  echo "Error: Please provide the unique suffix used to create the resources."
  echo "Usage: $0 <your-unique-suffix>"
  exit 1
fi

UNIQUE_SUFFIX=$1
AWS_REGION=${AWS_REGION:-ap-southeast-1}
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query "Account" --output text)

RAW_BUCKET_NAME="transcode-raw-files-${UNIQUE_SUFFIX}"
PROCESSED_BUCKET_NAME="transcode-processed-files-${UNIQUE_SUFFIX}"
QUEUE_NAME="transcode-queue-${UNIQUE_SUFFIX}"
QUEUE_URL="https://sqs.${AWS_REGION}.amazonaws.com/${AWS_ACCOUNT_ID}/${QUEUE_NAME}"

echo "---"
echo "Starting AWS resource DESTRUCTION in region: ${AWS_REGION}"
echo "This will permanently delete resources associated with suffix: ${UNIQUE_SUFFIX}"
echo "---"

# 1. Empty and delete S3 buckets
echo "Force-deleting all objects in bucket: ${RAW_BUCKET_NAME}"
aws s3 rb "s3://${RAW_BUCKET_NAME}" --force

echo "Force-deleting all objects in bucket: ${PROCESSED_BUCKET_NAME}"
aws s3 rb "s3://${PROCESSED_BUCKET_NAME}" --force

echo "S3 buckets deleted."

# 2. Delete SQS queue
echo "Deleting SQS queue: ${QUEUE_NAME}"
aws sqs delete-queue --queue-url "${QUEUE_URL}"

echo "SQS queue deleted."

echo "---"
echo "Destruction Complete!"
echo "---"