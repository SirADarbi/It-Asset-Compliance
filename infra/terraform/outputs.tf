output "elastic_ip" {
  description = "Public Elastic IP address of the compliance server"
  value       = aws_eip.compliance_eip.public_ip
}

output "api_url" {
  description = "FastAPI base URL"
  value       = "http://${aws_eip.compliance_eip.public_ip}:8000"
}

output "grafana_url" {
  description = "Grafana dashboard URL"
  value       = "http://${aws_eip.compliance_eip.public_ip}:3000"
}
