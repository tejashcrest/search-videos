# Video Search Demo - AI-Powered Video Search Platform

A video search platform using AWS services, Amazon Bedrock's Marengo embedding models, and OpenSearch for semantic video search. Users can search through video content using natural language queries with hybrid search combining vector similarity and text matching.

## 🏗️ Architecture Overview

```
User Upload → S3 → Lambda Trigger → Step Functions → ECS (Video Split) 
→ Lambda (Bedrock Marengo) → Lambda (Store Embeddings) → OpenSearch

User Search → CloudFront → ALB → ECS (Search API) → OpenSearch → Results
```

## 📁 Repository Structure

```
.
├── .env
├── .gitignore
├── README.md
├── cf-stack-custom.yaml
├── cloudfront-test-stack.yaml
├── video-search-cloudformation-stack.yaml
├── backend/
│   ├── AWS Lambda Functions/
│   │   ├── Lambda Layers/
│   │   │   ├── ffmpeg-video-processing-dependencies-697fac5e-fb3f-4814-b610-f0d2d3812616.zip
│   │   │   ├── ffprobe-video-processing-dependencies-be43225a-83d9-410a-a3e3-85d0d3fea83c.zip
│   │   │   ├── opensearch-query-dependencies-2fb22b80-caf2-4d3f-84a6-3f863bf3c409.zip
│   │   │   └── store-embeddings-lambda.zip
│   │   ├── create_opensearch_snapshot.py
│   │   ├── invoke-bedrock-marengo.py
│   │   ├── invoke-video-processing-step-function.py
│   │   ├── search-lambda.py
│   │   └── store-embeddings-opensearch-lambda.py
│   ├── landingzone to raw - ECS Fargate/
│   │   ├── Dockerfile
│   │   ├── main.py
│   │   ├── requirements.txt
│   │   └── video_processor.py
│   └── search-similar-videos - ECS Fargate/
│       ├── .env
│       ├── .env.example
│       ├── docker-compose.yml
│       ├── Dockerfile
│       ├── main.py
│       └── requirements.txt
└── frontend/
    ├── .env
    ├── .env.example
    ├── .gitignore
    ├── README.md
    ├── dist/
    ├── node_modules/
    └── src/
        ├── App.jsx
        ├── main.jsx
        ├── components/
        ├── config/
        ├── hooks/
        ├── services/
        └── utils/
```

## 🚀 Local Setup Guide

### Prerequisites

1. **AWS Account** with appropriate permissions
2. **AWS CLI** configured with credentials
3. **Docker** installed
4. **Node.js 18+**
5. **Python 3.11+**

### Required AWS Services Access

- Amazon Bedrock (Marengo models subscription)
- Amazon OpenSearch Service
- Amazon ECS/Fargate
- AWS Lambda, Step Functions, S3
- Amazon CloudFront, ALB
- VPC with NAT Gateway

### Step 1: Clone and Setup

```bash
# Clone repository
git clone <repository-url>
cd video-search-demo

# Copy environment files
cp .env.example .env
cp frontend/.env.example frontend/.env
```

### Step 2: Build Docker Images

Create ECR repositories and build images:

```bash
# Create ECR repositories
aws ecr create-repository --repository-name video-preprocessing --region us-east-1
aws ecr create-repository --repository-name condenast/search-similar-videos --region us-east-1

# Get ECR login
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com

# Build and push video preprocessing image
cd backend/landingzone\ to\ raw\ -\ ECS\ Fargate/
docker build -t video-preprocessing:latest .
docker tag video-preprocessing:latest <ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/video-preprocessing:latest
docker push <ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/video-preprocessing:latest

# Build and push search API image
cd ../search-similar-videos\ -\ ECS\ Fargate/
docker build -t search-similar-videos:latest .
docker tag search-similar-videos:latest <ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/condenast/search-similar-videos:latest
docker push <ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/condenast/search-similar-videos:latest
```

### Step 3: Prepare Lambda Layers

The CloudFormation stack requires Lambda layers that are already included in this repository. Upload these layers to S3:

**Required Lambda Layers:**
1. **OpenSearch Dependencies Layer** - Contains `opensearchpy` and related libraries
2. **FFmpeg Video Processing Layer** - Contains `ffmpeg` binaries and video processing libraries  
3. **Klayers Requests Layer** - Pre-built layer from Klayers (automatically referenced)

**Upload the local layers to S3:**
```bash
# Upload OpenSearch dependencies layer
aws s3 cp "backend/AWS Lambda Functions/Lambda Layers/opensearch-query-dependencies-2fb22b80-caf2-4d3f-84a6-3f863bf3c409.zip" \
  s3://{env}-aihouse-dist-{AccountId}/lambda-artifacts/

# Upload FFmpeg video processing layer  
aws s3 cp "backend/AWS Lambda Functions/Lambda Layers/ffmpeg-video-processing-dependencies-697fac5e-fb3f-4814-b610-f0d2d3812616.zip" \
  s3://{env}-aihouse-dist-{AccountId}/lambda-artifacts/
```

**Note:** The stack also uses Klayers (arn:aws:lambda:${AWS::Region}:770693421928:layer:Klayers-p312-requests:18) which is automatically available and doesn't need manual upload.

### Step 4: Deploy Infrastructure

```bash
aws cloudformation create-stack \
  --stack-name video-search-demo \
  --template-body file://video-search-cloudformation-stack.yaml \
  --parameters \
    ParameterKey=env,ParameterValue=dev \
    ParameterKey=StackPrefix,ParameterValue=vs-1 \
  --capabilities CAPABILITY_NAMED_IAM \
  --region us-east-1
```

**Deployment time**: ~25-30 minutes

### Step 5: Setup Frontend

```bash
cd frontend

# Install dependencies
npm install

# Update .env with deployed API URL
# Get CloudFront URL from stack outputs
aws cloudformation describe-stacks \
  --stack-name video-search-demo \
  --query 'Stacks[0].Outputs[?OutputKey==`CloudFrontURL`].OutputValue' \
  --output text

# Add to frontend/.env:
# VITE_API_BASE_URL=https://your-api-cloudfront-url.cloudfront.net
# VITE_AWS_REGION=us-east-1

# Start development server
npm run dev
```

### Step 6: Test the Application

```bash
# Health check
curl https://your-api-url.cloudfront.net/health

# Upload a video through the frontend
# Search for content using natural language
```

## 🔧 Environment Configuration

### Backend (.env)
```env
AWS_REGION=us-east-1
OPENSEARCH_CLUSTER_HOST=your-domain.us-east-1.es.amazonaws.com
THUMBNAIL_BUCKET=vs-1-processed-videos-us-east-1-123456789012-dev
AWS_S3_BUCKET=vs-1-videos-us-east-1-123456789012-dev
STATE_MACHINE_ARN=arn:aws:states:us-east-1:123456789012:stateMachine:vs-1-dev-pipeline
```

### Frontend (.env)
```env
VITE_API_BASE_URL=https://your-api-cloudfront-url.cloudfront.net
VITE_AWS_REGION=us-east-1
```

## 🔧 Development

### Frontend Development
```bash
cd frontend
npm install
npm run dev          # Development server
npm run build        # Production build
```

### Backend Testing
```bash
# Test API endpoints
curl https://your-api-url.cloudfront.net/health
curl https://your-api-url.cloudfront.net/list

# Search test
curl -X POST https://your-api-url.cloudfront.net/search \
  -H "Content-Type: application/json" \
  -d '{"query_text": "person walking", "top_k": 10, "search_type": "hybrid"}'
```

## 🗑️ Cleanup

```bash
# Delete CloudFormation stack (includes automatic cleanup)
aws cloudformation delete-stack --stack-name video-search-demo

# Delete ECR repositories
aws ecr delete-repository --repository-name video-preprocessing --force
aws ecr delete-repository --repository-name condenast/search-similar-videos --force
```

## � License

This project is licensed under the MIT License.
