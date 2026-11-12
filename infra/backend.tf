terraform {
  backend "s3" {
    bucket       = "journal-tfstate-011237053925"
    key          = "journal/terraform.tfstate"
    region       = "us-east-1"
    encrypt      = true
    use_lockfile = true
  }
}