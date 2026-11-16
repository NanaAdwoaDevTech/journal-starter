resource "aws_ecr_repository" "journal_api" {
  name                 = "journal-api"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  encryption_configuration {
    encryption_type = "AES256"
  }
}

# Adopt the repository that CI already pushes to, so its images are kept
import {
  to = aws_ecr_repository.journal_api
  id = "journal-api"
}