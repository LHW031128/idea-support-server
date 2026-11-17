"""Register already-existing classroom IAM principals for Lens (no AWS keys created).

AWS_PROFILE must select the classroom administrator. RBAC bindings are rendered
by prepare.py. Every call is fixed to the Sydney classroom cluster.
"""
import argparse
import json
from pathlib import Path
import subprocess


def aws(*args):
    return json.loads(subprocess.check_output(["aws", *args, "--region", "ap-southeast-2", "--output", "json"]))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--grant-describe", action="store_true",
        help="Add only eks:DescribeCluster to the verified existing team1~team8 IAM users")
    parser.add_argument("--protect-gitops-ecr", action="store_true",
        help="Deny student writes only to the instructor's GitOps release repository")
    args = parser.parse_args()
    config = json.loads(args.config.read_text(encoding="utf-8-sig"))
    students = config.get("students", [])
    if not students:
        raise SystemExit("No student principals configured; nothing was created")
    if config["account_id"] != "950177940921" or config["region"] != "ap-southeast-2" or config["cluster_name"] != "classroom-main":
        raise SystemExit("Only the Sydney classroom cluster is supported")
    for s in students:
        if s["namespace"] not in [f"team{i}" for i in range(1, 9)] or not s["principal_arn"].startswith("arn:aws:iam::950177940921:"):
            raise SystemExit("Invalid student mapping")
    if aws("sts", "get-caller-identity")["Account"] != "950177940921":
        raise SystemExit("Wrong AWS account")
    if args.grant_describe or args.protect_gitops_ecr:
        for s in students:
            if s["principal_arn"] != f'arn:aws:iam::950177940921:user/{s["namespace"]}':
                raise SystemExit("Describe policy automation is limited to existing classroom team users")
    if args.protect_gitops_ecr and config.get("ecr_repository") != "idea-support-server":
        raise SystemExit("ECR protection is limited to the verified instructor repository")
    cluster = aws("eks", "describe-cluster", "--name", "classroom-main")["cluster"]
    if cluster["status"] != "ACTIVE":
        raise SystemExit("Wait for the Sydney classroom cluster to become ACTIVE")
    entries = set(aws("eks", "list-access-entries", "--cluster-name", "classroom-main")["accessEntries"])
    for s in students:
        principal = s["principal_arn"]
        group = f'classroom:{s["namespace"]}'
        if principal in entries:
            existing = aws("eks", "describe-access-entry", "--cluster-name", "classroom-main", "--principal-arn", principal)["accessEntry"]
            policies = aws("eks", "list-associated-access-policies", "--cluster-name", "classroom-main", "--principal-arn", principal)["associatedAccessPolicies"]
            if existing.get("kubernetesGroups", []) != [group] or policies:
                raise SystemExit(f"Existing principal has other permissions; audit manually: {principal}")
            print(f"Preserved existing limited mapping: {s['namespace']}")
        elif args.apply:
            aws("eks", "create-access-entry", "--cluster-name", "classroom-main", "--principal-arn", principal,
                "--type", "STANDARD", "--kubernetes-groups", group)
            print(f"Created access entry for {s['namespace']}; apply RoleBindings next")
        else:
            print(f"Would map {principal} to {group}")
        if args.grant_describe and args.apply:
            policy = {"Version": "2012-10-17", "Statement": [{"Effect": "Allow",
                "Action": "eks:DescribeCluster", "Resource": cluster["arn"]}]}
            subprocess.run(["aws", "iam", "put-user-policy", "--user-name", s["namespace"],
                "--policy-name", "ClassroomEksDescribeOnly", "--policy-document", json.dumps(policy),
                "--region", "ap-southeast-2"], check=True, stdout=subprocess.DEVNULL)
            print(f"Added classroom cluster DescribeCluster only: {s['namespace']}")
        if args.protect_gitops_ecr and args.apply:
            policy = {"Version": "2012-10-17", "Statement": [{"Effect": "Deny",
                "Action": ["ecr:InitiateLayerUpload", "ecr:UploadLayerPart", "ecr:CompleteLayerUpload", "ecr:PutImage"],
                "Resource": "arn:aws:ecr:ap-southeast-2:950177940921:repository/idea-support-server"}]}
            subprocess.run(["aws", "iam", "put-user-policy", "--user-name", s["namespace"],
                "--policy-name", "ClassroomGitOpsEcrProtection", "--policy-document", json.dumps(policy),
                "--region", "ap-southeast-2"], check=True, stdout=subprocess.DEVNULL)
            print(f"Protected instructor release image from student writes: {s['namespace']}")


if __name__ == "__main__":
    main()
