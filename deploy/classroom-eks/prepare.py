"""Render public deployment config. Never reads credentials or contacts AWS.

python deploy/classroom-eks/prepare.py --config .local/classroom-eks/config.json
Requires PyYAML (python -m pip install PyYAML).
"""
import argparse
import ipaddress
import json
from pathlib import Path
import re
import yaml

HERE = Path(__file__).resolve().parent


def render(config, output):
    if config["account_id"] != "950177940921":
        raise ValueError("This bundle is restricted to the classroom account 950177940921")
    if config["region"] != "ap-northeast-2" or config["cluster_name"] != "classroom-main":
        raise ValueError("This lesson targets classroom-main in Seoul only")
    if not re.fullmatch(r"1\.\d+", config["eks_version"]):
        raise ValueError("Set a currently STANDARD_SUPPORT EKS version")
    if not re.fullmatch(r"sha256:[0-9a-f]{64}", config["bootstrap_digest"]):
        raise ValueError("bootstrap_digest must be an existing ECR sha256 digest")
    cidrs = config["api_allowed_cidrs"]
    if not cidrs:
        raise ValueError("At least one administrator/classroom public CIDR is required")
    for cidr in cidrs:
        if ipaddress.ip_network(cidr).prefixlen == 0:
            raise ValueError("Do not expose the EKS API to the entire Internet")
    students = config.get("students", [])
    for student in students:
        if student["namespace"] not in [f"team{i}" for i in range(1, 9)]:
            raise ValueError("Student namespaces must be team1 through team8")
        if not re.fullmatch(r"arn:aws:iam::950177940921:(role|user)/.+", student["principal_arn"]):
            raise ValueError("Use a classroom IAM principal ARN, not an STS session ARN")
    if len({s["principal_arn"] for s in students}) != len(students):
        raise ValueError("Every principal must have exactly one team mapping")
    output = output.resolve()
    if output == HERE or HERE in output.parents:
        raise ValueError("Render into a separate .local folder, not the source templates")
    output.mkdir(parents=True, exist_ok=True)
    registry = f'{config["account_id"]}.dkr.ecr.{config["region"]}.amazonaws.com'
    values = {
        "__REGISTRY__": registry,
        "__IMAGE__": f'{registry}/{config["ecr_repository"]}',
        "__ECR_REPOSITORY__": config["ecr_repository"],
        "__BOOTSTRAP_DIGEST__": config["bootstrap_digest"],
        "__GIT_REPOSITORY__": config["git_repository"],
        "__GIT_BRANCH__": config["git_branch"],
        "__GIT_PATH__": config["git_path"],
        "__REGION__": config["region"],
    }
    count = 0
    for source in sorted((HERE / "templates").rglob("*.yaml")):
        content = source.read_text(encoding="utf-8")
        for key, value in values.items():
            content = content.replace(key, value)
        if re.search(r"__[A-Z_]+__", content):
            raise ValueError(f"Unresolved placeholder in {source}")
        list(yaml.safe_load_all(content))
        target = output / source.relative_to(HERE / "templates")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8", newline="\n")
        count += 1
    cluster = {
        "apiVersion": "eksctl.io/v1alpha5", "kind": "ClusterConfig",
        "metadata": {"name": config["cluster_name"], "region": config["region"],
                     "version": config["eks_version"], "tags": {"purpose": "classroom-gitops"}},
        "availabilityZones": ["ap-northeast-2a", "ap-northeast-2c"],
        "accessConfig": {"authenticationMode": "API_AND_CONFIG_MAP"},
        "vpc": {"nat": {"gateway": "Disable"},
                "clusterEndpoints": {"privateAccess": True, "publicAccess": True},
                "publicAccessCIDRs": cidrs},
        "iam": {"withOIDC": True},
        "managedNodeGroups": [{"name": "classroom-workers", "instanceType": "t3.large",
            "amiFamily": "AmazonLinux2023", "desiredCapacity": 2, "minSize": 2, "maxSize": 2,
            "privateNetworking": False, "volumeSize": 30, "volumeEncrypted": True,
            "disableIMDSv1": True, "ssh": {"allow": False},
            "iam": {"withAddonPolicies": {"imageBuilder": False}}}],
        "addons": [{"name": "vpc-cni"}, {"name": "coredns"}, {"name": "kube-proxy"},
                   {"name": "eks-pod-identity-agent"},
                   {"name": "aws-ebs-csi-driver", "podIdentityAssociations": [{
                       "namespace": "kube-system",
                       "serviceAccountName": "ebs-csi-controller-sa",
                       "permissionPolicyARNs": ["arn:aws:iam::aws:policy/service-role/AmazonEBSCSIDriverPolicy"]}]}],
    }
    (output / "cluster.yaml").write_text(yaml.safe_dump(cluster, sort_keys=False), encoding="utf-8")
    bindings = []
    for student in students:
        for namespace in ["team", student["namespace"]]:
            safe_name = re.sub(r"[^a-z0-9-]", "-", student["namespace"].lower())
            binding = {"apiVersion": "rbac.authorization.k8s.io/v1", "kind": "RoleBinding",
                "metadata": {"name": f"lens-{safe_name}", "namespace": namespace},
                "subjects": [{"kind": "Group", "name": f'classroom:{student["namespace"]}',
                              "apiGroup": "rbac.authorization.k8s.io"}],
                "roleRef": {"kind": "ClusterRole", "name": "classroom-observer",
                            "apiGroup": "rbac.authorization.k8s.io"}}
            if binding not in bindings:
                bindings.append(binding)
    if students:
        bindings.append({"apiVersion": "rbac.authorization.k8s.io/v1", "kind": "ClusterRoleBinding",
            "metadata": {"name": "classroom-namespace-discovery"},
            "subjects": [{"kind": "Group", "name": f"classroom:{namespace}",
                          "apiGroup": "rbac.authorization.k8s.io"}
                         for namespace in sorted({s["namespace"] for s in students})],
            "roleRef": {"kind": "ClusterRole", "name": "classroom-namespace-discovery",
                        "apiGroup": "rbac.authorization.k8s.io"}})
    (output / "student-bindings.yaml").write_text(
        yaml.safe_dump_all(bindings, sort_keys=False), encoding="utf-8")
    (output / "student-principals.json").write_text(json.dumps(students, indent=2), encoding="utf-8")
    print(f"Rendered {count} YAML files plus cluster and student mappings to {output}")
    print("No AWS resource, Kubernetes Secret, credential or live deployment was changed.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=HERE.parents[1] / ".local/classroom-eks/rendered")
    args = parser.parse_args()
    render(json.loads(args.config.read_text(encoding="utf-8-sig")), args.output)
