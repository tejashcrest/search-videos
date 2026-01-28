# 🎬 Video Search Application

A complete AI-powered video search application that lets you upload videos and search through them using natural language queries. Built with AWS services, React, and powered by Amazon Bedrock's Marengo models.

## ✨ Features

- 🎥 **Video Upload**: Upload videos directly through the web interface
- 🔍 **AI-Powered Search**: Search videos using natural language descriptions
- 🖼️ **Thumbnail Generation**: Automatic thumbnail creation for uploaded videos
- ⚡ **Real-time Processing**: Videos are processed automatically upon upload
- 🌐 **Global CDN**: Fast content delivery via CloudFront
- 🔒 **Secure**: Built with AWS security best practices

## 🚀 Quick Deploy (Fork & Deploy)

**Perfect for anyone who wants to try this application - no local setup required!**

### 1. Fork this repository
Click the "Fork" button at the top of this page (GitHub web interface)

### 2. Set up AWS credentials
In your forked repository, go to **Settings → Secrets and variables → Actions** and add:

**For Regular IAM Users:**
- `AWS_ACCESS_KEY_ID` - Your AWS access key
- `AWS_SECRET_ACCESS_KEY` - Your AWS secret key

**For AWS SSO Users:**
- `AWS_ACCESS_KEY_ID` - Your temporary access key (starts with `ASIA`)
- `AWS_SECRET_ACCESS_KEY` - Your temporary secret key  
- `AWS_SESSION_TOKEN` - Your session token (long string)

💡 **SSO Users**: Get these from `aws configure export-credentials --profile your-profile` or your AWS console

### 3. Deploy with one click
1. Go to the **Actions** tab in your forked repository
2. Click **Deploy Video Search Infrastructure**
3. Click **Run workflow**
4. Choose your settings (defaults work great for testing):
   - **Environment**: `demo`
   - **Stack prefix**: `vs-1` 
   - **AWS Region**: `us-east-1`
   - **Deploy frontend**: ✅ (checked)
   - **Action**: `deploy`
5. Click **Run workflow**

> 💡 **Pro Tip**: Write down your settings (environment, stack prefix, region)!  
> You'll need these EXACT values later for cleanup to avoid charges.

⏱️ **Deployment takes 15-25 minutes**.

🌐 **Everything happens in GitHub** - no local tools or setup required!

### 4. View Deployment Outputs

After the workflow completes successfully:

1. **Go to the Actions tab** in your repository
2. **Click on the completed workflow run** (green checkmark ✅)
3. **Scroll down below the workflow diagram** to find the **"deployment-summary"** job
4. **Click on "deployment-summary"** to expand it
5. You'll see a detailed summary with:
   - ✅ **Backend Deployment**
     - **API URL**: Your backend API endpoint (CloudFront URL)
     - **Video Bucket**: S3 bucket name for uploading videos
     - **OpenSearch**: OpenSearch domain endpoint
   - ✅ **Frontend Deployment**
     - **Frontend URL**: Your live application URL (click to open!)
   - 🎉 **Ready to Use!** section with your application link

**Example Output:**
![alt text](image.png)

💡 **Tip**: Save these URLs! You'll need the API URL for local frontend development.


📖 **[Full Deployment Guide](DEPLOYMENT_GUIDE.md)** - Detailed instructions and troubleshooting

## 🏗️ Architecture

### Backend (AWS)
- **Amazon Bedrock**: AI video understanding with Marengo models
- **OpenSearch**: Vector search for video embeddings
- **ECS Fargate**: Scalable video processing
- **Lambda**: Serverless API functions
- **S3**: Video and asset storage
- **CloudFront**: Global content delivery

### Frontend (React)
- **React**: Modern UI framework
- **Tailwind CSS**: Utility-first styling
- **Vite**: Fast build tooling
- **S3 + CloudFront**: Static hosting

### File Structure
```
.
├── .github/workflows/          # GitHub Actions deployment
│   └── deploy-infrastructure.yml
├── backend/                    # Backend services
│   ├── AWS Lambda Functions/   # Lambda function code
│   ├── landingzone to raw - ECS Fargate/
│   └── search-similar-videos - ECS Fargate/
├── frontend/                   # React frontend
│   ├── src/
│   ├── package.json
│   └── vite.config.js
├── video-search-cloudformation-stack.yaml  # Backend infrastructure
├── frontend-cloudformation-stack.yaml      # Frontend infrastructure
├── README.md                   # This file
├── LOCAL_DEVELOPMENT.md        # Local development guide
└── DEPLOYMENT_GUIDE.md         # Detailed deployment guide
```

## 💻 Local Development

**Want to develop locally?** Check out the **[Local Development Guide](LOCAL_DEVELOPMENT.md)** for:
- Running frontend locally with deployed backend
- Direct AWS CLI deployment
- Manual frontend build and deployment
- Debugging tips and troubleshooting
- Backend development (Lambda, ECS, infrastructure)

**Quick start for frontend development:**
```bash
# Deploy backend via GitHub Actions first, then:
cd frontend
npm install
# Add your API URL to .env
npm run dev  # Opens at http://localhost:5173
```

See the [full guide](LOCAL_DEVELOPMENT.md) for detailed instructions.

## 📊 Monitoring & Logs

After deployment, monitor your application:
- **CloudWatch Logs**: Application logs and errors
- **CloudFormation**: Infrastructure status in AWS Console
- **S3**: Uploaded videos and processed content
- **OpenSearch**: Search indices and performance

**View logs via AWS CLI:**
```bash
# API logs
aws logs tail /ecs/vs-1-demo-search-similar-videos-task --follow

# Processing logs
aws logs tail /aws/lambda/vs-1-demo-invoke-bedrock-marengo --follow
```

## 🧹 Cleanup

> **⚠️ IMPORTANT - Avoid Unexpected Charges**  
> Always cleanup your AWS resources when done testing to avoid ongoing charges.  
> **Use the EXACT SAME settings (environment, stack prefix, region) that you used for deployment!**

**⚠️ Important**: To avoid ongoing AWS charges, delete all resources when you're done testing.

### Cleanup via GitHub Actions (Recommended)

Use the same workflow that deployed your infrastructure:

1. **Go to Actions tab** in your repository
2. **Click "Deploy Video Search Infrastructure"**
3. **Click "Run workflow"**
4. **⚠️ CRITICAL: Use the EXACT SAME settings you used for deployment:**
   - **Environment**: Same as deployment (e.g., `demo`)
   - **Stack prefix**: Same as deployment (e.g., `vs-1`)
   - **AWS Region**: Same as deployment (e.g., `us-east-1`)
   - **Action**: Select `cleanup` ⬅️ **This is the only change!**
5. **Click "Run workflow"**

⏱️ **Cleanup takes 10-15 minutes**.

**What gets deleted:**
- ✅ All S3 buckets (videos, processed files, snapshots) - **automatically emptied before deletion**
- ✅ OpenSearch domain
- ✅ Lambda functions
- ✅ ECS services and tasks
- ✅ VPC and networking resources
- ✅ CloudFront distributions
- ✅ IAM roles and policies
- ✅ All CloudFormation stacks

**After cleanup completes:**
- All AWS resources are deleted
- Billing stops within 24 hours
- You can safely delete your forked repository if desired

> 💡 **Note**: S3 buckets are automatically emptied by a custom Lambda function before deletion, so you won't encounter the "bucket not empty" error (409).

### Cleanup via AWS CLI (Alternative)

If you prefer using AWS CLI:

```bash
# Set the SAME variables you used for deployment
export STACK_PREFIX="vs-1"           # ⚠️ Must match deployment
export ENVIRONMENT="demo"            # ⚠️ Must match deployment
export AWS_REGION="us-east-1"        # ⚠️ Must match deployment

# Delete frontend stack first
aws cloudformation delete-stack \
  --stack-name "video-search-frontend-${ENVIRONMENT}" \
  --region "${AWS_REGION}"

# Wait for frontend deletion
aws cloudformation wait stack-delete-complete \
  --stack-name "video-search-frontend-${ENVIRONMENT}" \
  --region "${AWS_REGION}"

# Delete backend stack
aws cloudformation delete-stack \
  --stack-name "${STACK_PREFIX}-${ENVIRONMENT}-backend" \
  --region "${AWS_REGION}"

# Wait for backend deletion (10-15 minutes)
aws cloudformation wait stack-delete-complete \
  --stack-name "${STACK_PREFIX}-${ENVIRONMENT}-backend" \
  --region "${AWS_REGION}"

echo "✅ Cleanup complete!"
```

### Verify Cleanup

Check that all resources are deleted:

```bash
# Check CloudFormation stacks
aws cloudformation list-stacks \
  --stack-status-filter DELETE_COMPLETE \
  --region "${AWS_REGION}" \
  | grep -E "(vs-1|video-search)"

# Check S3 buckets (should return empty)
aws s3 ls | grep -E "(vs-1|video-search)"

# Check OpenSearch domains (should return empty)
aws opensearch list-domain-names --region "${AWS_REGION}"
```

### Troubleshooting Cleanup

**If cleanup fails:**

1. **Check the workflow logs** in GitHub Actions for error messages
2. **Retry the cleanup workflow** - sometimes temporary AWS issues resolve on retry
3. **Delete stacks manually** in AWS Console:
   - Go to CloudFormation
   - Select the stack
   - Click "Delete"
4. **Contact AWS Support** if resources remain stuck

**Common Issues:**
- **OpenSearch domain deletion**: Takes 10-15 minutes, be patient
- **VPC deletion**: Waits for all resources to be deleted first
- **IAM roles in use**: Ensure no other services are using the roles
- **CloudFront distribution**: Takes 15-20 minutes to fully delete

## 🔧 Configuration

The application supports multiple environments:
- **demo**: Testing and demos
- **dev**: Development
- **stage**: Staging
- **prod**: Production

Each environment is isolated with its own resources.

## 🎯 What's Next?

After deploying:
1. **Find your application URL** in the deployment summary (Actions tab)
2. **Upload test videos** through the web interface
3. **Try different search queries** to test AI-powered search
4. **Monitor in CloudWatch** to see processing in action
5. **Customize for your needs** using local development
6. **Build something amazing!**

## 📚 Quick Reference

### Important URLs After Deployment
- **Frontend URL**: `https://[cloudfront-id].cloudfront.net` (from deployment summary)
- **API URL**: `https://[cloudfront-id].cloudfront.net` (from deployment summary)
- **AWS Console**: Check CloudFormation, S3, OpenSearch, Lambda, ECS

### Common Commands

**View Deployment Outputs:**
```bash
aws cloudformation describe-stacks \
  --stack-name vs-1-demo-backend \
  --query 'Stacks[0].Outputs' \
  --region us-east-1
```

**Check Stack Status:**
```bash
aws cloudformation describe-stacks \
  --stack-name vs-1-demo-backend \
  --query 'Stacks[0].StackStatus' \
  --region us-east-1
```

**List Uploaded Videos:**
```bash
aws s3 ls s3://vs-1-videos-us-east-1-[account-id]-demo/
```

**View Application Logs:**
```bash
# API logs
aws logs tail /ecs/vs-1-demo-search-similar-videos-task --follow

# Processing logs
aws logs tail /aws/lambda/vs-1-demo-invoke-bedrock-marengo --follow
```

### Support & Resources
- **Local Development**: See [LOCAL_DEVELOPMENT.md](LOCAL_DEVELOPMENT.md)
- **Deployment Guide**: See [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)
- **Issues**: Open an issue in this repository
- **AWS Documentation**: [AWS Bedrock](https://docs.aws.amazon.com/bedrock/), [OpenSearch](https://docs.aws.amazon.com/opensearch-service/)

---

**Ready to get started?** 👆 Fork this repo and deploy in minutes!
