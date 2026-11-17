"""Grant the eight classroom groups port-forward access to current Argo server Pods."""
import argparse
import json
import subprocess

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--kubeconfig', required=True)
parser.add_argument('--context', default='classroom-main-admin')
args = parser.parse_args()
if args.context != 'classroom-main-admin':
    parser.error('Use the explicit classroom-main-admin context')
kubectl = ['kubectl', '--kubeconfig', args.kubeconfig, '--context', args.context]
pods = json.loads(subprocess.check_output(kubectl + ['-n', 'argocd', 'get', 'pods',
    '-l', 'app.kubernetes.io/name=argocd-server,app.kubernetes.io/instance=argocd', '-o', 'json']))
names = sorted(p['metadata']['name'] for p in pods['items'] if not p['metadata'].get('deletionTimestamp'))
if not names:
    raise SystemExit('No Argo CD server Pod found; no permissions changed')
role = {'apiVersion': 'rbac.authorization.k8s.io/v1', 'kind': 'Role',
    'metadata': {'namespace': 'argocd', 'name': 'classroom-argocd-portforward'},
    'rules': [{'apiGroups': [''], 'resources': ['pods/portforward'],
               'resourceNames': names, 'verbs': ['get', 'create']}]}
binding = {'apiVersion': 'rbac.authorization.k8s.io/v1', 'kind': 'RoleBinding',
    'metadata': {'namespace': 'argocd', 'name': 'classroom-argocd-portforward'},
    'subjects': [{'kind': 'Group', 'name': f'classroom:team{i}',
                  'apiGroup': 'rbac.authorization.k8s.io'} for i in range(1, 9)],
    'roleRef': {'kind': 'Role', 'name': 'classroom-argocd-portforward',
                'apiGroup': 'rbac.authorization.k8s.io'}}
subprocess.run(kubectl + ['apply', '-f', '-'],
    input=json.dumps({'apiVersion': 'v1', 'kind': 'List', 'items': [role, binding]}),
    text=True, check=True)
print('Argo CD server port-forward granted to team1 through team8.')
print('Run this again after Argo CD server Pods are replaced.')
