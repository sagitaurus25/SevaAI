# 🚀 SevaAI Enhanced AWS Agent

A comprehensive AI-powered AWS assistant that supports multiple AWS services including S3, EC2, Lambda, IAM, RDS, CloudWatch, VPC, Route53, CloudFormation, and more.

## 🌟 Features

### Supported AWS Services

| Service | Capabilities |
|---------|-------------|
| **S3** | List/create/delete buckets, manage objects, bucket policies |
| **EC2** | List/start/stop instances, security groups, key pairs |
| **Lambda** | List/invoke functions, view logs, manage triggers |
| **IAM** | List users/roles/policies, permission management |
| **RDS** | Monitor database instances, manage snapshots |
| **CloudWatch** | View metrics/alarms, monitor performance |
| **VPC** | Manage virtual networks, subnets, routing |
| **Route53** | DNS management, hosted zones |
| **CloudFormation** | Stack management, infrastructure as code |
| **Cost & Billing** | Usage monitoring, cost optimization |

### Key Capabilities

- 🤖 **Natural Language Interface** - Ask questions in plain English
- 🔧 **Real-time AWS Operations** - Execute AWS commands directly
- 📊 **Comprehensive Monitoring** - View metrics, logs, and performance data
- 💰 **Cost Optimization** - Track usage and spending
- 🔒 **Security Management** - IAM policies, security groups, best practices
- 🏗️ **Infrastructure Management** - EC2, VPC, networking, storage

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- AWS CLI configured OR AWS credentials
- AWS Bedrock access (for Claude models)

### 1. Automated Setup

```bash
cd /Users/tar/Desktop/SevaAI/seva-agent
python setup_enhanced_agent.py
```

### 2. Manual Setup

```bash
# Install dependencies
pip install -r enhanced_requirements.txt

# Configure AWS credentials (choose one method)
aws configure
# OR set environment variables
export AWS_ACCESS_KEY_ID=your_access_key
export AWS_SECRET_ACCESS_KEY=your_secret_key
export AWS_REGION=us-east-1

# Start the agent
python enhanced_aws_agent.py
```

### 3. Access the Interface

Open your browser to: `http://localhost:8086`

## 💬 Example Conversations

### S3 Management
```
You: "List my S3 buckets"
Agent: "I'll list your S3 buckets for you..."
[Shows bucket list with creation dates]

You: "Show me objects in my-data-bucket"
Agent: "Here are the objects in my-data-bucket..."
[Lists objects with sizes and modification dates]
```

### EC2 Management
```
You: "Show my EC2 instances"
Agent: "Here are your EC2 instances..."
[Lists instances with states, IPs, and types]

You: "Start instance i-1234567890abcdef0"
Agent: "Starting instance i-1234567890abcdef0..."
[Confirms instance start operation]
```

### Lambda Functions
```
You: "List my Lambda functions"
Agent: "Here are your Lambda functions..."
[Shows functions with runtimes and memory settings]

You: "Show logs for my-function from the last 2 hours"
Agent: "Retrieving logs for my-function..."
[Displays recent log entries]
```

### Cost Monitoring
```
You: "Show my AWS costs for the last 30 days"
Agent: "Here's your cost breakdown..."
[Shows daily costs by service]
```

## 🛠️ Available Tools

### S3 Operations
- `list_s3_buckets` - List all S3 buckets
- `create_s3_bucket` - Create new S3 bucket
- `delete_s3_bucket` - Delete S3 bucket (must be empty)
- `list_s3_objects` - List objects in bucket

### EC2 Operations
- `list_ec2_instances` - List EC2 instances
- `start_ec2_instance` - Start EC2 instance
- `stop_ec2_instance` - Stop EC2 instance
- `list_security_groups` - List security groups

### Lambda Operations
- `list_lambda_functions` - List Lambda functions
- `invoke_lambda_function` - Invoke Lambda function
- `get_lambda_logs` - Get function logs

### IAM Operations
- `list_iam_users` - List IAM users
- `list_iam_roles` - List IAM roles
- `list_iam_policies` - List IAM policies

### Monitoring & Cost
- `list_cloudwatch_alarms` - List CloudWatch alarms
- `get_cloudwatch_metrics` - Get CloudWatch metrics
- `get_cost_and_usage` - Get cost and usage data

### Network & Infrastructure
- `list_vpcs` - List VPCs
- `list_subnets` - List subnets
- `list_hosted_zones` - List Route53 hosted zones
- `list_cloudformation_stacks` - List CloudFormation stacks

### Utility
- `get_account_info` - Get AWS account information
- `list_regions` - List available AWS regions

## 🔧 Configuration

### Environment Variables

Create a `.env` file or set environment variables:

```bash
# AWS Credentials
AWS_ACCESS_KEY_ID=your_access_key_here
AWS_SECRET_ACCESS_KEY=your_secret_key_here
AWS_REGION=us-east-1

# Bedrock Configuration
BEDROCK_MODEL_ID=anthropic.claude-3-5-sonnet-20241022-v2:0
BEDROCK_REGION=us-east-1

# Agent Configuration
AGENT_PORT=8086
AGENT_HOST=0.0.0.0
```

### AWS Permissions

The agent requires appropriate AWS permissions. Here's a sample IAM policy:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "s3:ListAllMyBuckets",
                "s3:ListBucket",
                "s3:GetObject",
                "s3:PutObject",
                "ec2:DescribeInstances",
                "ec2:StartInstances",
                "ec2:StopInstances",
                "ec2:DescribeSecurityGroups",
                "lambda:ListFunctions",
                "lambda:InvokeFunction",
                "logs:FilterLogEvents",
                "iam:ListUsers",
                "iam:ListRoles",
                "iam:ListPolicies",
                "rds:DescribeDBInstances",
                "cloudwatch:DescribeAlarms",
                "cloudwatch:GetMetricStatistics",
                "ce:GetCostAndUsage",
                "route53:ListHostedZones",
                "cloudformation:DescribeStacks",
                "sts:GetCallerIdentity"
            ],
            "Resource": "*"
        }
    ]
}
```

## 🚀 Advanced Usage

### Custom Tool Integration

Add new AWS services by extending `enhanced_aws_tools.py`:

```python
def list_custom_service(self) -> str:
    """List resources from custom AWS service"""
    try:
        client = self.session.client('custom-service')
        response = client.list_resources()
        return json.dumps({"resources": response['Resources']})
    except Exception as e:
        return json.dumps({"error": str(e)})
```

### API Integration

Use the REST API directly:

```bash
# Health check
curl http://localhost:8086/health

# List available tools
curl http://localhost:8086/tools

# Chat with the agent
curl -X POST http://localhost:8086/chat \
  -H "Content-Type: application/json" \
  -d '{"messages": [{"role": "user", "content": "List my S3 buckets"}]}'
```

## 🔍 Troubleshooting

### Common Issues

1. **AWS Credentials Not Found**
   ```bash
   aws configure
   # OR
   export AWS_ACCESS_KEY_ID=your_key
   export AWS_SECRET_ACCESS_KEY=your_secret
   ```

2. **Bedrock Access Denied**
   - Ensure your AWS account has Bedrock access
   - Check if Claude models are available in your region

3. **Permission Denied Errors**
   - Review IAM permissions
   - Ensure your user/role has necessary AWS service permissions

4. **Port Already in Use**
   ```bash
   # Change port in enhanced_aws_agent.py
   uvicorn.run(app, host="0.0.0.0", port=8087)
   ```

### Debug Mode

Enable debug logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## 📈 Performance Tips

1. **Use IAM Roles** instead of access keys when running on EC2
2. **Enable CloudTrail** for audit logging
3. **Set up CloudWatch** for monitoring agent performance
4. **Use VPC endpoints** for private AWS API access

## 🔒 Security Best Practices

1. **Principle of Least Privilege** - Grant minimal required permissions
2. **Rotate Credentials** regularly
3. **Use IAM Roles** when possible
4. **Enable MFA** for sensitive operations
5. **Monitor API Usage** with CloudTrail

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Add new AWS service support
4. Test thoroughly
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License.

## 🆘 Support

For issues and questions:
1. Check the troubleshooting section
2. Review AWS documentation
3. Check CloudWatch logs
4. Open an issue with detailed error information

---

**Happy AWS Management with SevaAI! 🚀**