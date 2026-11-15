# Classroom GitOps deployment record

- Scope: account 950177940921, Sydney ap-southeast-2, EKS classroom-main, namespace team.
- The application source remains on main. This branch stores desired Kubernetes state.
- Initial image: sha256:330b00bcb5e1adf68924dd47137a9d5ad968bebddf45e0bcd99b4b7813217e86.
- Built from the existing classroom backend after 189 tests passed. Secrets are created separately in Kubernetes and never committed here.
- MySQL uses its own retained PVC. Argo automatic pruning is disabled for the classroom.
- Argo CD Image Updater will commit later ECR latest digest changes to apps/team/kustomization.yaml.
- The initial commit prepares desired state; it is not proof of a live deployment.

Update apps/team/kustomization.yaml through Image Updater for image releases. Update the workload definitions here for configuration changes. Installation sources are on codex/classroom-eks-preparation.
