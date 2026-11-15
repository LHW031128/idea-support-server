"""Create private Kubernetes Secrets without files or printing credential values.

Requires PyYAML and bcrypt. Uses an explicitly named kubeconfig/context and checks
the AWS identity before mutations. Existing app secrets are preserved.
"""
import argparse
import base64
from datetime import datetime, timezone
import getpass
import json
from pathlib import Path
import secrets
import subprocess
import bcrypt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["app", "argocd", "git"])
    parser.add_argument("--kubeconfig", type=Path, required=True)
    parser.add_argument("--context", default="classroom-main-admin")
    parser.add_argument("--repository", default="https://github.com/MinQDU014/idea-support-server.git")
    parser.add_argument("--ssh-key", type=Path,
        help="Use a repository-scoped GitHub deploy key instead of a personal token")
    args = parser.parse_args()
    identity = json.loads(subprocess.check_output(["aws", "sts", "get-caller-identity", "--output", "json"]))
    if identity["Account"] != "950177940921":
        raise SystemExit("Refusing to modify a non-classroom AWS account")
    kube = ["kubectl", "--kubeconfig", str(args.kubeconfig), "--context", args.context]
    cluster_config = json.loads(subprocess.check_output(kube + ["config", "view", "--minify", "-o", "json"]))
    cluster_name = cluster_config["contexts"][0]["context"]["cluster"]
    if cluster_name != "arn:aws:eks:ap-southeast-2:950177940921:cluster/classroom-main":
        raise SystemExit("Refusing to modify a different Kubernetes cluster")

    def exists(namespace, name):
        found = subprocess.run(kube + ["-n", namespace, "get", "secret", name,
            "--ignore-not-found", "-o", "name"], capture_output=True, text=True, check=True)
        return bool(found.stdout.strip())

    def apply(namespace, name, values, labels=None):
        obj = {"apiVersion": "v1", "kind": "Secret", "type": "Opaque",
            "metadata": {"name": name, "namespace": namespace},
            "data": {k: base64.b64encode(v.encode()).decode() for k, v in values.items()}}
        if labels:
            obj["metadata"]["labels"] = labels
        subprocess.run(kube + ["apply", "--server-side", "--field-manager=classroom-secret-bootstrap", "-f", "-"],
                       input=json.dumps(obj), text=True, check=True, stdout=subprocess.DEVNULL)
        print(f"Stored {namespace}/{name}; values were not printed")

    if args.mode == "app":
        if not exists("team", "mysql-auth"):
            apply("team", "mysql-auth", {"MYSQL_DATABASE": "idea_support", "MYSQL_USER": "idea_support",
                "MYSQL_PASSWORD": secrets.token_urlsafe(32), "MYSQL_ROOT_PASSWORD": secrets.token_urlsafe(40)})
        else:
            print("Preserved existing team/mysql-auth; DB passwords are not rotated by this command")
        if not exists("team", "spring-auth"):
            apply("team", "spring-auth", {"JWT_SECRET": base64.b64encode(secrets.token_bytes(64)).decode(),
                "SHA_KEY": secrets.token_urlsafe(32), "AES_KEY": secrets.token_hex(16)})
        else:
            print("Preserved existing team/spring-auth")
    elif args.mode == "argocd":
        if exists("argocd", "argocd-admin-credentials"):
            raise SystemExit("Admin credential already exists; explicit rotation is a separate operation")
        if not exists("argocd", "argocd-secret"):
            raise SystemExit("Install Argo CD first")
        admin_password = secrets.token_urlsafe(32)
        student_password = secrets.token_urlsafe(24)
        now = datetime.now(timezone.utc).isoformat()
        hashes = {"admin.password": bcrypt.hashpw(admin_password.encode(), bcrypt.gensalt()).decode(),
            "admin.passwordMtime": now,
            "accounts.students.password": bcrypt.hashpw(student_password.encode(), bcrypt.gensalt()).decode(),
            "accounts.students.passwordMtime": now}
        # Only hashes are passed as command arguments; no plaintext credentials.
        subprocess.run(kube + ["-n", "argocd", "patch", "secret", "argocd-secret", "--type=merge",
            "-p", json.dumps({"data": {k: base64.b64encode(v.encode()).decode() for k, v in hashes.items()}})],
            check=True, stdout=subprocess.DEVNULL)
        apply("argocd", "argocd-admin-credentials", {"username": "admin", "password": admin_password})
        apply("argocd", "argocd-student-credentials", {"username": "students", "password": student_password})
        if exists("argocd", "argocd-initial-admin-secret"):
            subprocess.run(kube + ["-n", "argocd", "delete", "secret", "argocd-initial-admin-secret"],
                           check=True, stdout=subprocess.DEVNULL)
        print("Admin hash updated; private recovery credentials stored in argocd namespace only")
    else:
        if args.ssh_key:
            if not args.repository.startswith("git@github.com:"):
                raise SystemExit("Use the GitHub SSH repository URL with a deploy key")
            private_key = args.ssh_key.read_text(encoding="utf-8")
            if "PRIVATE KEY" not in private_key:
                raise SystemExit("The selected file is not an SSH private key")
            apply("argocd", "gitops-write", {"sshPrivateKey": private_key, "insecure": "false"})
            apply("argocd", "gitops-repository", {"type": "git", "url": args.repository,
                "sshPrivateKey": private_key, "insecure": "false"},
                {"argocd.argoproj.io/secret-type": "repository"})
            print("Repository deploy key stored; keep GitHub host verification enabled")
            return
        username = input("Git HTTPS username: ").strip()
        token = getpass.getpass("Repository-scoped Git write token (hidden): ").strip()
        if not username or not token:
            raise SystemExit("Empty credentials are not allowed")
        apply("argocd", "gitops-write", {"username": username, "password": token, "insecure": "false"})
        apply("argocd", "gitops-repository", {"type": "git", "url": args.repository,
            "username": username, "password": token, "insecure": "false"},
            {"argocd.argoproj.io/secret-type": "repository"})
        print("Use a credential limited to this GitOps repository; never enter it in Notion")


if __name__ == "__main__":
    main()
