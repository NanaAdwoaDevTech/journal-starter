#!/usr/bin/env bash
# One-time cluster add-ons: cert-manager (TLS certificates) and Traefik (ingress).
# Run from the repo root after `terraform apply`, with AWS credentials active.
set -euo pipefail

CLUSTER="${CLUSTER:-journal-cluster}"
REGION="${AWS_REGION:-us-east-1}"

EIP_ALLOC="$(terraform -chdir=infra output -raw ingress_eip_allocation_id)"
SUBNET_ID="$(terraform -chdir=infra output -raw ingress_subnet_id)"

aws eks update-kubeconfig --name "$CLUSTER" --region "$REGION"

helm repo add jetstack https://charts.jetstack.io
helm repo add traefik https://traefik.github.io/charts
helm repo update

helm upgrade --install cert-manager jetstack/cert-manager \
  --namespace cert-manager --create-namespace \
  --set crds.enabled=true --wait

cat > /tmp/traefik-values.yaml <<EOF
service:
  type: LoadBalancer
  annotations:
    service.beta.kubernetes.io/aws-load-balancer-type: "nlb"
    service.beta.kubernetes.io/aws-load-balancer-subnets: "${SUBNET_ID}"
    service.beta.kubernetes.io/aws-load-balancer-eip-allocations: "${EIP_ALLOC}"
    service.beta.kubernetes.io/aws-load-balancer-cross-zone-load-balancing-enabled: "true"
EOF

helm upgrade --install traefik traefik/traefik \
  --namespace traefik --create-namespace \
  -f /tmp/traefik-values.yaml --wait

kubectl apply -f k8s/namespace.yaml

# The cert-manager webhook can take a few seconds to become ready
for i in 1 2 3 4 5 6; do
  kubectl apply -f k8s/cluster-issuer.yaml && break || sleep 10
done

echo "Load balancer:"
kubectl -n traefik get svc traefik
