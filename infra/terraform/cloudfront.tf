resource "random_password" "origin_verify" {
  length  = 48
  special = false
}

locals {
  origin_id                   = "${var.project}-ec2-origin"
  cache_policy_disabled       = "4135ea2d-6df8-44a3-9df3-4b5a84be39ad"
  origin_request_all_but_host = "b689b0a8-53d0-40ab-baf2-68738e2966ac"
}

resource "aws_cloudfront_distribution" "api" {
  enabled         = true
  comment         = "KalaVigyan API: HTTPS front for the EC2 origin"
  price_class     = var.cloudfront_price_class
  http_version    = "http2and3"
  is_ipv6_enabled = true

  origin {
    origin_id   = local.origin_id
    domain_name = aws_eip.api.public_dns

    custom_origin_config {
      http_port                = 80
      https_port               = 443
      origin_protocol_policy   = "http-only"
      origin_ssl_protocols     = ["TLSv1.2"]
      origin_read_timeout      = 120
      origin_keepalive_timeout = 60
    }

    custom_header {
      name  = "X-Origin-Verify"
      value = random_password.origin_verify.result
    }
  }

  default_cache_behavior {
    target_origin_id         = local.origin_id
    viewer_protocol_policy   = "redirect-to-https"
    allowed_methods          = ["GET", "HEAD", "OPTIONS", "PUT", "POST", "PATCH", "DELETE"]
    cached_methods           = ["GET", "HEAD"]
    compress                 = false
    cache_policy_id          = local.cache_policy_disabled
    origin_request_policy_id = local.origin_request_all_but_host
  }

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  viewer_certificate {
    cloudfront_default_certificate = true
  }

  tags = { Name = "${var.project}-api" }
}
