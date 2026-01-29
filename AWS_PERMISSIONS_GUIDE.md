# AWS Permissions Guide for Video Search Application

## Overview

This document outlines all AWS permissions required to successfully deploy and manage the Video Search Application infrastructure. You must have appropriate IAM permissions for all listed services before attempting deployment.

## ⚠️ Important Prerequisites

### Required AWS Account Access

To deploy this application, your AWS IAM user or role must have **full administrative access** or full permissions for the following AWS services:

- ✅ **CloudFormation** - Stack creation and management
- ✅ **IAM** - Role and policy creation
- ✅ **S3** - Bucket creation and management
- ✅ **Lambda** - Function deployment
- ✅ **ECS/Fargate** - Container orchestration
- ✅ **EC2** - VPC, subnets, security groups, and endpoints
- ✅ **OpenSearch** - Domain creation and configuration
- ✅ **CloudFront** - CDN distribution
- ✅ **Application Load Balancer** - Load balancer creation
- ✅ **Step Functions** - State machine orchestration
- ✅ **CloudWatch** - Logging and monitoring
- ✅ **Bedrock** - AI model access
- ✅ **STS** - Temporary credential management

### Recommended IAM Policy

For production deployments, we recommend using **AdministratorAccess** policy or creating a custom policy with the permissions listed below.

---

## Complete Resource List by AWS Service

### 1. AWS CloudFormation

**Resources Created:**
- Backend Stack: `{StackPrefix}-{Environment}-backend`
- Frontend Stack: `video-search-frontend-{Environment}`

**Required Permissions:**
```json
{
  "Effect": "Allow",
  "Action": [
    "cloudformation:CreateStack",
    "cloudformation:UpdateStack",
    "cloudformation:DeleteStack",
    "cloudformation:DescribeStacks",
    "cloudformation:DescribeStackEvents",
    "cloudformation:DescribeStackResources",
    "cloudformation:GetTemplate",
    "cloudformation:ValidateTemplate",
    "cloudformation:ListStacks",
    "cloudformation:GetTemplateSummary"
  ],
  "Resource": "*"
}
```

---

### 2. AWS Identity and Access Management (IAM)

**Resources Created:**
- `{StackPrefix}-{Environment}-ecs-task-execution-role`
- `{StackPrefix}-{Environment}-ecs-task-role`
- `{StackPrefix}-{Environment}-search-similar-videos-ecs-task-role`
- `{StackPrefix}-{Environment}-invoke-bedrock-marengo-role`
- `{StackPrefix}-{Environment}-invoke-video-processing-step-function-role`
- `{StackPrefix}-{Environment}-opensearch-snapshot-role`
- `{StackPrefix}-{Environment}-create-opensearch-snapshot-lambda-role`
- `{StackPrefix}-{Environment}-store-embeddings-opensearch-lambda-role`
- `{StackPrefix}-{Environment}-complete-video-processing-pipeline-role`
- `{StackPrefix}-{Environment}-opensearch-role-mapping-lambda-role`
- `{StackPrefix}-{Environment}-opensearch-admin`
- `{StackPrefix}-{Environment}-empty-bucket-lambda-role`
- `{ProjectName}-{Environment}-empty-bucket-lambda-role` (Frontend)

**Required Permissions:**
```json
{
  "Effect": "Allow",
  "Action": [
    "iam:CreateRole",
    "iam:DeleteRole",
    "iam:GetRole",
    "iam:PassRole",
    "iam:AttachRolePolicy",
    "iam:DetachRolePolicy",
    "iam:PutRolePolicy",
    "iam:DeleteRolePolicy",
    "iam:GetRolePolicy",
    "iam:ListRolePolicies",
    "iam:ListAttachedRolePolicies",
    "iam:UpdateAssumeRolePolicy",
    "iam:TagRole",
    "iam:UntagRole"
  ],
  "Resource": "*"
}
```

---

### 3. Amazon S3

**Resources Created:**
- `{StackPrefix}-{VideoBucketBaseName}-{Region}-{AccountId}-{Environment}` (Video uploads)
- `{StackPrefix}-processed-videos-{Region}-{AccountId}-{Environment}` (Processed videos)
- `{StackPrefix}-opensearch-snapshots-{Region}-{AccountId}-{Environment}` (OpenSearch backups)
- `{ProjectName}-frontend-{Environment}-{AccountId}` (Frontend hosting)
- `aws-cloudformation-templates-{AccountId}-{Region}` (Template storage)

**Required Permissions:**
```json
{
  "Effect": "Allow",
  "Action": [
    "s3:CreateBucket",
    "s3:DeleteBucket",
    "s3:ListBucket",
    "s3:ListBucketVersions",
    "s3:GetBucketLocation",
    "s3:GetBucketPolicy",
    "s3:PutBucketPolicy",
    "s3:DeleteBucketPolicy",
    "s3:GetBucketVersioning",
    "s3:PutBucketVersioning",
    "s3:GetBucketCORS",
    "s3:PutBucketCORS",
    "s3:GetBucketNotification",
    "s3:PutBucketNotification",
    "s3:GetBucketWebsite",
    "s3:PutBucketWebsite",
    "s3:GetBucketPublicAccessBlock",
    "s3:PutBucketPublicAccessBlock",
    "s3:GetObject",
    "s3:PutObject",
    "s3:DeleteObject",
    "s3:DeleteObjectVersion",
    "s3:GetObjectVersion",
    "s3:PutBucketTagging",
    "s3:GetBucketTagging"
  ],
  "Resource": "*"
}
```

---

### 4. AWS Lambda

**Resources Created:**
- `{StackPrefix}-{Environment}-invoke-bedrock-marengo`
- `{StackPrefix}-{Environment}-store-embeddings-opensearch`
- `{StackPrefix}-{Environment}-invoke-video-processing-step-function`
- `{StackPrefix}-{Environment}-create-opensearch-snapshot`
- `{StackPrefix}-{Environment}-opensearch-role-mapper`
- `{StackPrefix}-{Environment}-empty-bucket` (Backend)
- `{ProjectName}-{Environment}-empty-bucket` (Frontend)
- Lambda Layers for dependencies

**Required Permissions:**
```json
{
  "Effect": "Allow",
  "Action": [
    "lambda:CreateFunction",
    "lambda:DeleteFunction",
    "lambda:GetFunction",
    "lambda:GetFunctionConfiguration",
    "lambda:UpdateFunctionCode",
    "lambda:UpdateFunctionConfiguration",
    "lambda:InvokeFunction",
    "lambda:AddPermission",
    "lambda:RemovePermission",
    "lambda:GetPolicy",
    "lambda:PublishLayerVersion",
    "lambda:DeleteLayerVersion",
    "lambda:GetLayerVersion",
    "lambda:TagResource",
    "lambda:UntagResource",
    "lambda:ListTags"
  ],
  "Resource": "*"
}
```

---

### 5. Amazon ECS (Elastic Container Service)

**Resources Created:**
- ECS Cluster: `{StackPrefix}-{Environment}-cluster`
- Task Definitions:
  - `{StackPrefix}-{Environment}-video-preprocessing`
  - `{StackPrefix}-{Environment}-search-similar-videos-task`
- ECS Service: `{StackPrefix}-{Environment}-search-service`

**Required Permissions:**
```json
{
  "Effect": "Allow",
  "Action": [
    "ecs:CreateCluster",
    "ecs:DeleteCluster",
    "ecs:DescribeClusters",
    "ecs:RegisterTaskDefinition",
    "ecs:DeregisterTaskDefinition",
    "ecs:DescribeTaskDefinition",
    "ecs:CreateService",
    "ecs:DeleteService",
    "ecs:UpdateService",
    "ecs:DescribeServices",
    "ecs:RunTask",
    "ecs:StopTask",
    "ecs:DescribeTasks",
    "ecs:ListTasks",
    "ecs:TagResource",
    "ecs:UntagResource"
  ],
  "Resource": "*"
}
```

---

### 6. Amazon EC2 (VPC, Networking, Security)

**Resources Created:**
- VPC: `{StackPrefix}-{Environment}-vpc`
- Subnets: 4 subnets (2 public, 2 private)
- Internet Gateway: `{StackPrefix}-{Environment}-igw`
- NAT Gateway: `{StackPrefix}-{Environment}-nat-gateway`
- Elastic IP for NAT Gateway
- Route Tables: Public and Private
- Security Groups:
  - `{StackPrefix}-{Environment}-alb-sg`
  - `{StackPrefix}-{Environment}-ecs-sg`
  - `{StackPrefix}-{Environment}-lambda-sg`
  - `{StackPrefix}-{Environment}-vpc-endpoint-sg`
- VPC Endpoints:
  - ECR API, ECR DKR, Bedrock, Bedrock Runtime, Step Functions, STS

**Required Permissions:**
```json
{
  "Effect": "Allow",
  "Action": [
    "ec2:CreateVpc",
    "ec2:DeleteVpc",
    "ec2:DescribeVpcs",
    "ec2:ModifyVpcAttribute",
    "ec2:CreateSubnet",
    "ec2:DeleteSubnet",
    "ec2:DescribeSubnets",
    "ec2:CreateInternetGateway",
    "ec2:DeleteInternetGateway",
    "ec2:AttachInternetGateway",
    "ec2:DetachInternetGateway",
    "ec2:DescribeInternetGateways",
    "ec2:AllocateAddress",
    "ec2:ReleaseAddress",
    "ec2:DescribeAddresses",
    "ec2:CreateNatGateway",
    "ec2:DeleteNatGateway",
    "ec2:DescribeNatGateways",
    "ec2:CreateRouteTable",
    "ec2:DeleteRouteTable",
    "ec2:DescribeRouteTables",
    "ec2:CreateRoute",
    "ec2:DeleteRoute",
    "ec2:AssociateRouteTable",
    "ec2:DisassociateRouteTable",
    "ec2:CreateSecurityGroup",
    "ec2:DeleteSecurityGroup",
    "ec2:DescribeSecurityGroups",
    "ec2:AuthorizeSecurityGroupIngress",
    "ec2:AuthorizeSecurityGroupEgress",
    "ec2:RevokeSecurityGroupIngress",
    "ec2:RevokeSecurityGroupEgress",
    "ec2:CreateVpcEndpoint",
    "ec2:DeleteVpcEndpoints",
    "ec2:DescribeVpcEndpoints",
    "ec2:ModifyVpcEndpoint",
    "ec2:CreateNetworkInterface",
    "ec2:DeleteNetworkInterface",
    "ec2:DescribeNetworkInterfaces",
    "ec2:CreateTags",
    "ec2:DeleteTags",
    "ec2:DescribeTags",
    "ec2:DescribeAvailabilityZones"
  ],
  "Resource": "*"
}
```

---

### 7. Amazon OpenSearch Service

**Resources Created:**
- OpenSearch Domain: `{StackPrefix}-{Environment}-aos`

**Required Permissions:**
```json
{
  "Effect": "Allow",
  "Action": [
    "es:CreateDomain",
    "es:DeleteDomain",
    "es:DescribeDomain",
    "es:UpdateDomainConfig",
    "es:ESHttpGet",
    "es:ESHttpPost",
    "es:ESHttpPut",
    "es:ESHttpDelete",
    "es:ESHttpHead",
    "es:ListDomainNames",
    "es:DescribeDomainConfig",
    "es:AddTags",
    "es:RemoveTags",
    "es:ListTags"
  ],
  "Resource": "*"
}
```

---

### 8. Amazon CloudFront

**Resources Created:**
- API Distribution (Backend)
- Frontend Distribution
- Origin Access Control (OAC)

**Required Permissions:**
```json
{
  "Effect": "Allow",
  "Action": [
    "cloudfront:CreateDistribution",
    "cloudfront:DeleteDistribution",
    "cloudfront:GetDistribution",
    "cloudfront:GetDistributionConfig",
    "cloudfront:UpdateDistribution",
    "cloudfront:CreateOriginAccessControl",
    "cloudfront:DeleteOriginAccessControl",
    "cloudfront:GetOriginAccessControl",
    "cloudfront:CreateInvalidation",
    "cloudfront:GetInvalidation",
    "cloudfront:ListInvalidations",
    "cloudfront:TagResource",
    "cloudfront:UntagResource",
    "cloudfront:ListTagsForResource"
  ],
  "Resource": "*"
}
```

---

### 9. Elastic Load Balancing (ALB)

**Resources Created:**
- Application Load Balancer: `{StackPrefix}-{Environment}-alb`
- Target Group: `{StackPrefix}-{Environment}-tg`
- Listener on port 8000

**Required Permissions:**
```json
{
  "Effect": "Allow",
  "Action": [
    "elasticloadbalancing:CreateLoadBalancer",
    "elasticloadbalancing:DeleteLoadBalancer",
    "elasticloadbalancing:DescribeLoadBalancers",
    "elasticloadbalancing:ModifyLoadBalancerAttributes",
    "elasticloadbalancing:CreateTargetGroup",
    "elasticloadbalancing:DeleteTargetGroup",
    "elasticloadbalancing:DescribeTargetGroups",
    "elasticloadbalancing:ModifyTargetGroup",
    "elasticloadbalancing:ModifyTargetGroupAttributes",
    "elasticloadbalancing:CreateListener",
    "elasticloadbalancing:DeleteListener",
    "elasticloadbalancing:DescribeListeners",
    "elasticloadbalancing:ModifyListener",
    "elasticloadbalancing:RegisterTargets",
    "elasticloadbalancing:DeregisterTargets",
    "elasticloadbalancing:DescribeTargetHealth",
    "elasticloadbalancing:AddTags",
    "elasticloadbalancing:RemoveTags",
    "elasticloadbalancing:DescribeTags"
  ],
  "Resource": "*"
}
```

---

### 10. AWS Step Functions

**Resources Created:**
- State Machine: `{StackPrefix}-{Environment}-pipeline`

**Required Permissions:**
```json
{
  "Effect": "Allow",
  "Action": [
    "states:CreateStateMachine",
    "states:DeleteStateMachine",
    "states:DescribeStateMachine",
    "states:UpdateStateMachine",
    "states:StartExecution",
    "states:StopExecution",
    "states:DescribeExecution",
    "states:ListExecutions",
    "states:TagResource",
    "states:UntagResource",
    "states:ListTagsForResource"
  ],
  "Resource": "*"
}
```

---

### 11. Amazon CloudWatch

**Resources Created:**
- Log Groups for Lambda functions
- Log Groups for ECS tasks
- Metrics and alarms

**Required Permissions:**
```json
{
  "Effect": "Allow",
  "Action": [
    "logs:CreateLogGroup",
    "logs:DeleteLogGroup",
    "logs:DescribeLogGroups",
    "logs:CreateLogStream",
    "logs:DeleteLogStream",
    "logs:DescribeLogStreams",
    "logs:PutLogEvents",
    "logs:GetLogEvents",
    "logs:FilterLogEvents",
    "logs:PutRetentionPolicy",
    "logs:DeleteRetentionPolicy",
    "logs:TagLogGroup",
    "logs:UntagLogGroup",
    "logs:ListTagsLogGroup"
  ],
  "Resource": "*"
}
```

---

### 12. Application Auto Scaling

**Resources Created:**
- Scalable Target for ECS Service
- Scaling Policy

**Required Permissions:**
```json
{
  "Effect": "Allow",
  "Action": [
    "application-autoscaling:RegisterScalableTarget",
    "application-autoscaling:DeregisterScalableTarget",
    "application-autoscaling:DescribeScalableTargets",
    "application-autoscaling:PutScalingPolicy",
    "application-autoscaling:DeleteScalingPolicy",
    "application-autoscaling:DescribeScalingPolicies",
    "application-autoscaling:DescribeScalingActivities"
  ],
  "Resource": "*"
}
```

---

### 13. Amazon Bedrock

**Resources Used:**
- Foundation Models:
  - `twelvelabs.marengo-embed-2-7-v1:0`
  - `twelvelabs.marengo-embed-3-0-v1:0`
  - `amazon.nova-micro-v1:0`

**Required Permissions:**
```json
{
  "Effect": "Allow",
  "Action": [
    "bedrock:InvokeModel",
    "bedrock:InvokeModelWithResponseStream",
    "bedrock:GetAsyncInvoke",
    "bedrock:StartAsyncInvoke",
    "bedrock:ListFoundationModels",
    "bedrock:GetFoundationModel"
  ],
  "Resource": "*"
}
```

**⚠️ Important:** You must have access to Bedrock models in your AWS account. Some models require:
- Model access request approval
- AWS Marketplace subscription
- Regional availability

---

### 14. AWS STS (Security Token Service)

**Required Permissions:**
```json
{
  "Effect": "Allow",
  "Action": [
    "sts:GetCallerIdentity",
    "sts:AssumeRole"
  ],
  "Resource": "*"
}
```

---

### 15. Amazon EventBridge (Events)

**Resources Created:**
- Event rules for ECS task state changes

**Required Permissions:**
```json
{
  "Effect": "Allow",
  "Action": [
    "events:PutRule",
    "events:DeleteRule",
    "events:DescribeRule",
    "events:PutTargets",
    "events:RemoveTargets",
    "events:ListTargetsByRule"
  ],
  "Resource": "*"
}
```

---

## Complete IAM Policy Template

Here's a complete IAM policy that includes all required permissions:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "VideoSearchDeploymentPermissions",
      "Effect": "Allow",
      "Action": [
        "cloudformation:*",
        "iam:*",
        "s3:*",
        "lambda:*",
        "ecs:*",
        "ec2:*",
        "es:*",
        "cloudfront:*",
        "elasticloadbalancing:*",
        "states:*",
        "logs:*",
        "application-autoscaling:*",
        "bedrock:InvokeModel",
        "bedrock:InvokeModelWithResponseStream",
        "bedrock:GetAsyncInvoke",
        "bedrock:StartAsyncInvoke",
        "bedrock:ListFoundationModels",
        "bedrock:GetFoundationModel",
        "sts:GetCallerIdentity",
        "sts:AssumeRole",
        "events:*",
        "ecr:GetAuthorizationToken",
        "ecr:BatchCheckLayerAvailability",
        "ecr:GetDownloadUrlForLayer",
        "ecr:BatchGetImage"
      ],
      "Resource": "*"
    }
  ]
}
```

---

## Setup Instructions

### Option 1: Using AdministratorAccess (Recommended for Testing)

If you have `AdministratorAccess` policy attached to your IAM user/role, you already have all required permissions.

**To verify:**
```bash
aws iam list-attached-user-policies --user-name YOUR_USERNAME
```

Look for `AdministratorAccess` in the output.

---

### Option 2: Create Custom IAM Policy

1. **Go to AWS Console** → **IAM** → **Policies**
2. **Click "Create Policy"**
3. **Switch to JSON tab**
4. **Paste the complete IAM policy template** from above
5. **Name it**: `VideoSearchDeploymentPolicy`
6. **Click "Create Policy"**
7. **Attach to your IAM user/role**:
   - Go to **Users** or **Roles**
   - Select your user/role
   - Click **Add permissions** → **Attach policies directly**
   - Search for `VideoSearchDeploymentPolicy`
   - Click **Add permissions**

---

### Option 3: Using AWS CLI

Create the policy using AWS CLI:

```bash
# Save the policy to a file
cat > video-search-policy.json << 'EOF'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "VideoSearchDeploymentPermissions",
      "Effect": "Allow",
      "Action": [
        "cloudformation:*",
        "iam:*",
        "s3:*",
        "lambda:*",
        "ecs:*",
        "ec2:*",
        "es:*",
        "cloudfront:*",
        "elasticloadbalancing:*",
        "states:*",
        "logs:*",
        "application-autoscaling:*",
        "bedrock:InvokeModel",
        "bedrock:InvokeModelWithResponseStream",
        "bedrock:GetAsyncInvoke",
        "bedrock:StartAsyncInvoke",
        "bedrock:ListFoundationModels",
        "bedrock:GetFoundationModel",
        "sts:GetCallerIdentity",
        "sts:AssumeRole",
        "events:*",
        "ecr:GetAuthorizationToken",
        "ecr:BatchCheckLayerAvailability",
        "ecr:GetDownloadUrlForLayer",
        "ecr:BatchGetImage"
      ],
      "Resource": "*"
    }
  ]
}
EOF

# Create the policy
aws iam create-policy \
  --policy-name VideoSearchDeploymentPolicy \
  --policy-document file://video-search-policy.json

# Attach to your user (replace YOUR_USERNAME)
aws iam attach-user-policy \
  --user-name YOUR_USERNAME \
  --policy-arn arn:aws:iam::YOUR_ACCOUNT_ID:policy/VideoSearchDeploymentPolicy
```

---

## Verification Checklist

Before deploying, verify you have access to all required services:

```bash
# Test CloudFormation access
aws cloudformation list-stacks --region us-east-1

# Test S3 access
aws s3 ls

# Test IAM access
aws iam get-user

# Test Lambda access
aws lambda list-functions --region us-east-1

# Test ECS access
aws ecs list-clusters --region us-east-1

# Test EC2 access
aws ec2 describe-vpcs --region us-east-1

# Test OpenSearch access
aws opensearch list-domain-names --region us-east-1

# Test Bedrock access
aws bedrock list-foundation-models --region us-east-1

# Test CloudFront access
aws cloudfront list-distributions

# Test Step Functions access
aws stepfunctions list-state-machines --region us-east-1
```

If any command fails with "AccessDenied" or "UnauthorizedOperation", you need to add those permissions.

---

## Common Permission Issues

### Issue 1: "User is not authorized to perform: iam:CreateRole"

**Solution:** Add IAM permissions to your user/role.

### Issue 2: "InsufficientCapabilitiesException"

**Solution:** This is handled automatically by the GitHub Actions workflow with `--capabilities CAPABILITY_NAMED_IAM`.

### Issue 3: "Access Denied" for Bedrock models

**Solution:** 
1. Go to AWS Console → Bedrock → Model access
2. Request access to required models:
   - Twelve Labs Marengo Embed 2.7
   - Twelve Labs Marengo Embed 3.0
   - Amazon Nova Micro
3. Wait for approval (usually instant for most models)

### Issue 4: "VPC limit exceeded"

**Solution:** Request VPC limit increase in AWS Service Quotas.

### Issue 5: "OpenSearch domain creation failed"

**Solution:** Check OpenSearch service quotas and ensure you have capacity in your region.

---

## Security Best Practices

### For Production Deployments:

1. **Use Least Privilege**: Create a custom policy with only required permissions
2. **Enable MFA**: Require multi-factor authentication for IAM users
3. **Use IAM Roles**: Prefer IAM roles over IAM users for GitHub Actions
4. **Rotate Credentials**: Regularly rotate AWS access keys
5. **Enable CloudTrail**: Monitor all API calls for audit purposes
6. **Use AWS Organizations**: Manage multiple accounts with SCPs
7. **Tag Resources**: Apply consistent tagging for cost tracking

### For Development/Testing:

1. **AdministratorAccess** is acceptable for quick testing
2. **Use temporary credentials** (AWS SSO) when possible
3. **Delete resources** after testing to avoid costs
4. **Set billing alerts** to monitor spending

---

## Cost Considerations

Deploying this application will incur AWS costs. Estimated monthly costs (with moderate usage):

- **OpenSearch**: $50-150/month (t3.small.search instance)
- **ECS Fargate**: $20-50/month (based on task runtime)
- **Lambda**: $5-20/month (based on invocations)
- **S3**: $5-30/month (based on storage and requests)
- **CloudFront**: $5-20/month (based on data transfer)
- **NAT Gateway**: $30-45/month (fixed cost)
- **Other services**: $10-20/month

**Total estimated cost**: $125-335/month

**💡 Tip**: Use the cleanup workflow to delete all resources when not in use to avoid ongoing charges.

---

## Support

If you encounter permission issues:

1. **Check CloudFormation Events**: Look for specific error messages
2. **Review CloudWatch Logs**: Check Lambda and ECS logs
3. **Verify IAM Policies**: Use IAM Policy Simulator
4. **Contact AWS Support**: For quota increases or service-specific issues

---

## Summary

✅ **Before deployment, ensure you have:**
- Full access to all 15 AWS services listed above
- Bedrock model access approved
- Sufficient service quotas in your target region
- Valid AWS credentials configured in GitHub Secrets

✅ **Recommended approach:**
- Use `AdministratorAccess` for initial testing
- Create custom policy for production deployments
- Enable CloudTrail for audit logging
- Set up billing alerts

✅ **After deployment:**
- Monitor CloudWatch logs
- Review CloudFormation stack events
- Test all application features
- Clean up resources when done testing

---

**Ready to deploy?** Make sure you have all required permissions, then follow the [Quick Deploy guide](README.md#-quick-deploy-fork--deploy) in the main README.
