variable "project" {
  description = "Prefix for every resource name."
  type        = string
  default     = "kalavigyan"
}

variable "aws_region" {
  description = "Region for the box, the bucket and the parameters."
  type        = string
  default     = "ap-south-1"
}

variable "bucket_name" {
  description = "Private media bucket."
  type        = string
  default     = "kalavigyan-media-626159998512"
}

variable "repo_slug" {
  description = "Repository folder name used under backups/."
  type        = string
  default     = "science-behind-craft"
}

variable "github_repo" {
  description = "owner/name of the repository allowed to assume the deploy role."
  type        = string
  default     = "ankits1802/science-behind-craft"
}

variable "github_deploy_ref" {
  description = "Git ref whose workflows may assume the deploy role."
  type        = string
  default     = "refs/heads/main"
}

variable "cors_allowed_origins" {
  description = "Browser origins allowed to PUT and GET media with presigned URLs."
  type        = list(string)
  default = [
    "https://kalavigyan.vercel.app",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
  ]
}

variable "instance_type" {
  description = "API box size."
  type        = string
  default     = "t3.large"
}

variable "root_volume_gb" {
  description = "Root volume size in GiB."
  type        = number
  default     = 40
}

variable "noncurrent_version_days" {
  description = "Days an overwritten or deleted object version is kept."
  type        = number
  default     = 90
}

variable "nightly_dump_days" {
  description = "Days a nightly database dump is kept."
  type        = number
  default     = 30
}

variable "weekly_dump_days" {
  description = "Days a weekly database dump is kept."
  type        = number
  default     = 365
}

variable "export_days" {
  description = "Days a generated export under exports/ is kept."
  type        = number
  default     = 7
}

variable "deploy_artifact_days" {
  description = "Days a release tarball or deploy log under deploy/ is kept."
  type        = number
  default     = 30
}

variable "cloudfront_price_class" {
  description = "CloudFront edge set. PriceClass_200 includes India."
  type        = string
  default     = "PriceClass_200"
}
