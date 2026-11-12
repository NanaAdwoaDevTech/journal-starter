output "cluster_name" {
  value = aws_eks_cluster.main.name
}

output "database_endpoint" {
  value = aws_db_instance.main.address
}

output "ingress_public_ip" {
  value = aws_eip.ingress.public_ip
}

output "ingress_eip_allocation_id" {
  value = aws_eip.ingress.id
}

output "ingress_subnet_id" {
  value = aws_subnet.public[0].id
}