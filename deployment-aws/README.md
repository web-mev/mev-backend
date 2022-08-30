Install [AWS CLI](https://aws.amazon.com/cli/) and [Terraform](https://www.terraform.io/)

Set up an AWS profile (use `us-east-2` region):
```shell
aws configure --profile webmev
export AWS_PROFILE=webmev
```
Download SSH keys:
```shell
aws s3 cp s3://webmev-terraform/secrets/dev-webmev.pem .
aws s3 cp s3://webmev-terraform/secrets/prod-webmev.pem .
```
Configure Terraform:
```shell
cd deployment-aws/terraform
terraform init
```
Create a new Terraform workspace, for example `dev`:
```shell
terraform workspace new dev
```
Note:
* workspace name will be used for:
  * naming AWS resources and Route53 records
  * Terraform state S3 object prefix
  * log bucket key prefix
* use workspace name `prod` for production deployments

Configure the site using `terraform.tfvars` file, for example:
```terraform
admin_email_csv = "admin@example.org"
backend_domain = "dev-mev-api.tm4.org"
django_superuser_email = "admin@example.org"
from_email = "WebMEV <noreply@mail.webmev.tm4.org>"
frontend_domain = "dev-mev.tm4.org"
ssh_key_pair_name = "dev-webmev"
storage_location = "local"
```

Create a CNAME record with the `tm4.org` domain registrar or DNS provider, for example:
```
dev-mev-api.tm4.org    CNAME    dev-mev-api.aws.tm4.org
```
where `dev` is your Terraform workspace name

Deploy the site:
```shell
terraform apply
```
Delete the site:
```shell
terraform destroy
```

## Initial setup
The following steps need to be done only once to bootstrap the project in your AWS account.

Create a private S3 bucket named `webmev-terraform` to store Terraform state and secrets:
```shell
aws s3 mb s3://webmev-terraform --region us-east-2
aws s3api put-bucket-tagging --bucket webmev-terraform --tagging 'TagSet=[{Key=Project,Value=WebMEV}]'
```
Create a private S3 bucket named `webmev-logs` to store access logs:
```shell
aws s3 mb s3://webmev-logs --region us-east-2
aws s3api put-bucket-tagging --bucket webmev-logs --tagging 'TagSet=[{Key=Project,Value=WebMEV}]'
```
Apply policy to the log bucket to [allow storing load balancer logs](https://docs.aws.amazon.com/elasticloadbalancing/latest/application/load-balancer-access-logs.html#access-logging-bucket-permissions):
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "AWS": "arn:aws:iam::033677994240:root"
      },
      "Action": "s3:PutObject",
      "Resource": "arn:aws:s3:::webmev-logs/*/AWSLogs/<aws-account-id>/*"
    }
  ]
}
```
(Note that `033677994240` above corresponds to the ELB account ID for `us-east-2`. Modify as required for different regions.)

[Create an HTTPS certificate](https://docs.aws.amazon.com/acm/latest/userguide/gs-acm-request-public.html) for `*.tm4.org` in Certificate Manager

[Create a public Route53 hosted zone](https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/CreatingHostedZone.html) `aws.tm4.org`

[Create an EC2 key pair](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/create-key-pairs.html) for each stack (e.g., `dev-webmev.pem`, `prod-webmev.pem`, etc) using AWS Console

[Create a service-linked role for AWS Batch](https://docs.aws.amazon.com/batch/latest/userguide/using-service-linked-roles.html#create-slr) - one per AWS account
