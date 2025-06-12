#!/bin/bash
set -e

# Script to provision AWS buckets (raw, processed), S3 Bucket Notification and SQS queue.
# ACTION REQUIRED: After running this aws-init.sh script, it outputs the resource names.
# Please copy it into .env.aws

# --- LOAD ENVIRONMENT VARIABLES ---
if [ -f .env.aws ]; then
  set -o allexport  # or `set -a`
  source <(grep -v '^#' .env.aws | grep -v '^$')
  set +o allexport # or `set +a`
else
  echo "Error: .env.aws file not found. Please create it from the template."
  exit 1
fi
# ---

if [ -z "$1" ]; then
  echo "Error: Please provide a unique suffix for the S3 buckets."
  echo "Usage: $0 <my-unique-suffix>"
  exit 1
fi

UNIQUE_SUFFIX=$1
# Use the region from the .env.aws file, defaulting to ap-southeast-1 if not set
AWS_REGION=${AWS_REGION:-ap-southeast-1}
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query "Account" --output text)

RAW_BUCKET_NAME="transcode-raw-files-${UNIQUE_SUFFIX}"
PROCESSED_BUCKET_NAME="transcode-processed-files-${UNIQUE_SUFFIX}"
QUEUE_NAME="transcode-queue-${UNIQUE_SUFFIX}"
SQS_POLICY_FILE="policy.json"

echo "---"
echo "Starting AWS resource provisioning in region: ${AWS_REGION}"
echo "Using unique suffix: ${UNIQUE_SUFFIX}"
echo "---"

## 1. Create S3 buckets
echo "Creating S3 bucket: ${RAW_BUCKET_NAME}"
aws s3api create-bucket --bucket "${RAW_BUCKET_NAME}" --create-bucket-configuration LocationConstraint="${AWS_REGION}"
echo "Creating S3 bucket: ${PROCESSED_BUCKET_NAME}"
aws s3api create-bucket --bucket "${PROCESSED_BUCKET_NAME}" --create-bucket-configuration LocationConstraint="${AWS_REGION}"

# 2. Create SQS queue with permissions
echo "Creating SQS queue: ${QUEUE_NAME}"
QUEUE_URL=$(aws sqs create-queue --queue-name "${QUEUE_NAME}" --attributes VisibilityTimeout=720 --region "${AWS_REGION}" --query "QueueUrl" --output text)
QUEUE_ARN=$(aws sqs get-queue-attributes --queue-url "${QUEUE_URL}" --attribute-names QueueArn --region "${AWS_REGION}" --query "Attributes.QueueArn" --output text)

# help because of nested json and shell quoting
SQS_POLICY='{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "s3.amazonaws.com"
      },
      "Action": "sqs:SendMessage",
      "Resource": "'${QUEUE_ARN}'",
      "Condition": {
        "ArnEquals": {
          "aws:SourceArn": "arn:aws:s3:::'${RAW_BUCKET_NAME}'"
        }
      }
    }
  ]
}'
SQS_POLICY_ESCAPED=$(echo ${SQS_POLICY} | perl -pe 's/"/\\"/g')
SQS_ATTRIBUTES='{"Policy":"'${SQS_POLICY_ESCAPED}'"}'

echo "SQS_ATTRUBUTES: \n ${SQS_ATTRIBUTES}"
echo "---------------------------------------------------------"

echo "Applying SQS policy to allow S3 notifications..."
aws sqs set-queue-attributes --queue-url "${QUEUE_URL}" --region "${AWS_REGION}" --attributes "${SQS_ATTRIBUTES}"
# validate
echo "Validate SQS attributes set"
aws sqs get-queue-attributes --queue-url "${QUEUE_URL}" --attribute-names All

# 3. Configure S3 bucket notification to trigger SQS
echo "Configuring S3 event notifications for bucket: ${RAW_BUCKET_NAME}"

# filter only .mp4 and .mov files to trigger Event Notification"
NOTIFICATION_CONFIG='{
  "QueueConfigurations": [
    {
      "Id": "s3-event-to-sqs-transcoder",
      "QueueArn": "'${QUEUE_ARN}'",
      "Events": ["s3:ObjectCreated:*"],
      "Filter": {
        "Key": {
          "FilterRules": [
            {"Name": "suffix", "Value": ".mp4"}
          ]
        }
      }
    },
    {
      "Id": "s3-event-to-sqs-transcoder-mov",
      "QueueArn": "'${QUEUE_ARN}'",
      "Events": ["s3:ObjectCreated:*"],
      "Filter": {
        "Key": {
          "FilterRules": [
            {"Name": "suffix", "Value": ".mov"}
          ]
        }
      }
    }
  ]
}'

aws s3api put-bucket-notification-configuration \
  --bucket "${RAW_BUCKET_NAME}" \
  --notification-configuration "${NOTIFICATION_CONFIG}" \
  --region "${AWS_REGION}"

echo "---"
echo "AWS Resources provisioning complete!"
echo "---"
echo "ACTION REQUIRED: Copy the following lines and paste them into your .env.aws file:"
echo ""
echo "S3_RAW_BUCKET=${RAW_BUCKET_NAME}"
echo "S3_PROCESSED_BUCKET=${PROCESSED_BUCKET_NAME}"
echo "SQS_QUEUE_URL=${QUEUE_URL}"
echo ""
