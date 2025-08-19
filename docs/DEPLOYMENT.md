📚 Now let's create DEPLOYMENT.md
bashcd ~/dataquest-bls-pipeline/docs
nano DEPLOYMENT.md
Copy this content into DEPLOYMENT.md:
markdown# Deployment Guide - DataQuest BLS Pipeline

> **Complete step-by-step deployment instructions for the economic intelligence platform**

## 🎯 Prerequisites

### 🔧 Required Tools & Accounts

| Requirement | Version | Purpose |
|-------------|---------|---------|
| **AWS Account** | Active | Infrastructure deployment |
| **AWS CLI** | v2.0+ | AWS service interaction |
| **Python** | 3.9+ | Lambda runtime and scripts |
| **Node.js** | 18+ | CDK framework |
| **AWS CDK** | v2.100+ | Infrastructure as Code |
| **Git** | Latest | Source code management |

### 💳 AWS Permissions Required

**IAM Permissions Needed:**
- `AWSLambdaFullAccess`
- `AmazonS3FullAccess`
- `AmazonEventBridgeFullAccess`
- `IAMFullAccess`
- `CloudFormationFullAccess`
- `AmazonSageMakerFullAccess`

---

## 🚀 Quick Deployment (Production)

### 1️⃣ Environment Setup

```bash
# Clone repository
git clone <repository-url>
cd dataquest-bls-pipeline

# Configure AWS CLI (if not already done)
aws configure
# Enter: Access Key, Secret Key, Region (us-east-2), Output (json)

# Verify AWS access
aws sts get-caller-identity
2️⃣ Install Dependencies
bash# Install CDK globally
npm install -g aws-cdk

# Install Python dependencies
cd infrastructure
pip install -r requirements.txt

# Verify CDK installation
cdk --version
3️⃣ Bootstrap CDK Environment
bash# Bootstrap CDK (first time only per account/region)
cdk bootstrap

# Expected output: CDK toolkit stack deployed successfully
4️⃣ Deploy Infrastructure
bash# Deploy the complete stack
cdk deploy

# Confirm deployment when prompted
# Deployment time: 3-5 minutes
5️⃣ Verify Deployment
bash# Test BLS data collection
aws lambda invoke \
    --function-name rearc-data-ingestion \
    --payload '{}' \
    response.json

# Check response
cat response.json

# Verify S3 bucket exists
aws s3 ls s3://dataquest-gov-bls-timeseries/

# Check SageMaker notebook
aws sagemaker describe-notebook-instance \
    --notebook-instance-name rearc-quest-notebook

🔧 Troubleshooting
❌ Common Issues & Solutions
1. CDK Bootstrap Errors
bash# Error: "Unable to resolve AWS account"
# Solution: Configure AWS CLI properly
aws configure list
aws sts get-caller-identity

# Error: "Region not specified"
# Solution: Set default region
export AWS_DEFAULT_REGION=us-east-2
2. Lambda Deployment Errors
bash# Error: "Code size too large"
# Solution: Check handler.py size and dependencies
ls -la data-collection/bls-ingestion/

# Error: "Permission denied"
# Solution: Verify IAM permissions
aws iam get-user
3. S3 Access Issues
bash# Error: "Access Denied"
# Solution: Check bucket policy and IAM roles
aws s3api get-bucket-acl --bucket dataquest-gov-bls-timeseries

# Error: "Bucket already exists"
# Solution: Use unique bucket name or different region

🧹 Cleanup & Removal
🗑️ Complete Environment Cleanup
1. Stop Ongoing Services
bash# Stop SageMaker notebook
aws sagemaker stop-notebook-instance \
    --notebook-instance-name rearc-quest-notebook
2. Remove CDK Stack
bash# Destroy all infrastructure
cdk destroy

# Confirm deletion when prompted
3. Manual Cleanup (if needed)
bash# Delete S3 bucket contents (if not empty)
aws s3 rm s3://dataquest-gov-bls-timeseries --recursive

# Delete bucket
aws s3 rb s3://dataquest-gov-bls-timeseries

📊 Monitoring & Maintenance
📈 Operational Monitoring
Daily Health Checks:
bash# Check Lambda execution status
aws lambda get-function --function-name rearc-data-ingestion

# Verify recent data collection
aws s3 ls s3://dataquest-gov-bls-timeseries/bls-data/ --recursive | tail -10

# Monitor costs
aws ce get-cost-and-usage \
    --time-period Start=2025-08-01,End=2025-08-31 \
    --granularity MONTHLY \
    --metrics BlendedCost

🎯 Success Criteria
✅ Deployment Complete When:

Lambda function deploys successfully
S3 bucket created with proper permissions
EventBridge rule schedules daily execution
SageMaker notebook accessible
First data collection run succeeds
All AWS services communicating properly

Expected Timeline: 15-30 minutes for complete deployment

For additional support or advanced configuration options, refer to the System Architecture documentation.

