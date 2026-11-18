"""Share the existing Argo CD admin login with all eight classroom teams.

Only username/password are copied to argocd-login, where Lens can list Secrets.
Run again after an explicit administrator password rotation. Values stay in
memory and are never printed or written to a manifest file.
"""
import argparse
import base64
import json
from pathlib import Path
import subprocess


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--kubeconfig", type=Path, required=True)
    parser.add_argument("--context", default="classroom-main-admin")
    args = parser.parse_args()
    identity = json.loads(subprocess.check_output(
        ["aws", "sts", "get-caller-identity", "--output", "json"]))
    if identity["Account"] != "950177940921":
        raise SystemExit("Refusing to modify a non-classroom AWS account")
    kube = ["kubectl", "--kubeconfig", str(args.kubeconfig), "--context", args.context]
    config = json.loads(subprocess.check_output(
        kube + ["config", "view", "--minify", "-o", "json"]))
    if config["contexts"][0]["context"]["cluster"] != (
        "arn:aws:eks:ap-southeast-2:950177940921:cluster/classroom-main"
    ):
        raise SystemExit("Refusing to modify a different Kubernetes cluster")
    source = json.loads(subprocess.check_output(kube + [
        "-n", "argocd", "get", "secret", "argocd-admin-credentials", "-o", "json"]))
    data = {key: source["data"][key] for key in ("username", "password")}
    if base64.b64decode(data["username"]).decode() != "admin" or not base64.b64decode(data["password"]):
        raise SystemExit("Administrator login Secret is incomplete")
    # Abort if the shared namespace already contains any other Secret.
    found = json.loads(subprocess.check_output(kube + [
        "get", "namespace", "argocd-login", "--ignore-not-found", "-o", "json"
    ]) or b"{}")
    if found:
        existing = json.loads(subprocess.check_output(kube + [
            "-n", "argocd-login", "get", "secrets", "-o", "json"]))
        if any(item["metadata"]["name"] != "argocd-admin-credentials" for item in existing["items"]):
            raise SystemExit("The shared namespace contains other Secrets; review before granting access")
    manifest = Path(__file__).parent / "templates/platform/argocd-login-reader.yaml"
    subprocess.run(kube + ["apply", "-f", str(manifest)], check=True)
    shared = {"apiVersion": "v1", "kind": "Secret", "type": "Opaque",
        "metadata": {"name": "argocd-admin-credentials", "namespace": "argocd-login"},
        "data": data}
    subprocess.run(kube + ["apply", "--server-side", "--field-manager=classroom-login-share", "-f", "-"],
        input=json.dumps(shared), text=True, check=True, stdout=subprocess.DEVNULL)
    print("Shared argocd-login/argocd-admin-credentials with team1~team8; values were not printed")


if __name__ == "__main__":
    main()
