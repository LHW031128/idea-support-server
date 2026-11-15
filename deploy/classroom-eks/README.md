# 시드니 EKS · Argo CD · GitOps 수업 운영

2026-11-15 요청: 수업 계정 `950177940921`, 시드니 `ap-southeast-2`, `classroom-main`.
클러스터 하나에 `team`, `team1`~`team8`을 만들고 앱과 MySQL은 `team`에만 설치한다.
`argocd`, `kube-system`의 운영 Pod는 별도이며 팀 앱의 수에 포함하지 않는다.

**설치 절차와 샘플 구성. 실제 구축 결과는 비공개 Notion 설치 부록에서 관리한다.**
현재 PC 기본 AWS 계정은 다른 계정이므로 이 계정으로 생성하면 안 된다.
기존 Lightsail과 DB를 이 EKS로 자동 이전하거나 삭제하지 않는다.

강의 본문: [12주차 CD-2](../../docs/WEEK12_EKS_GITOPS.md).

Notion 개인 초안: [강의](https://app.notion.com/p/419b4057395f817bb96ad48b1e87c6dd) · [설치 부록](https://app.notion.com/p/419b4057395f81dab0d4d4246cc762b9).
준비 파일: [GitHub 설치 폴더](https://github.com/MinQDU014/idea-support-server/tree/codex/classroom-eks-preparation/deploy/classroom-eks).
프로젝트 상세에서 소유자 대학 Builder ID와 계정 번호를 대조했다. 이 프로젝트는 classic root 로그인 대상이 아니다.
사용자가 기존 ECR과 같은 시드니 리전 사용으로 변경했다. 실제 실행 상태와 검증 커밋은 비공개 설치 부록에 기록한다.

## 1. 계정·도구·네트워크 준비 (강사, Bash)

AWS CloudShell 또는 강사의 Bash에서 실행한다. 학생은 이 절을 실행하지 않는다.
`aws`, `kubectl`, `eksctl`, Helm, Python3, PyYAML, bcrypt가 필요하다.
공식 배포처만 사용하고 설치 버전은 수업 전 확인해 기록한다.

```bash
export AWS_PROFILE=classroom  # CloudShell의 수업 계정 세션이면 이 줄은 생략
export AWS_REGION=ap-southeast-2
aws sts get-caller-identity
aws eks describe-cluster-versions --region ap-southeast-2 --output table
```

Account가 반드시 `950177940921`인지 확인한다. `STANDARD_SUPPORT` 중 사용할 Kubernetes 버전을 고른다.
Free plan·리전 제한이 있으면 계정 소유자의 전환이 필요하며 자동 유료 전환하지 않는다.
`eksctl`의 default 버전이나 과거 초안의 버전을 무조건 재사용하지 않는다.

수업용 독립 VPC, 공인 subnet 두 개, t3.large 워커 두 대를 사용한다.
노드는 공인 IP로 이미지·AWS API에 나가며 SSH·NodePort는 공개하지 않는다.
NAT Gateway와 외부 LoadBalancer는 기본 구성에 없다. EKS API는 private+public이며
강의실의 고정 공인 IP가 없으므로 public API는 모든 IPv4 접속망에서 도달할 수 있게 하고,
AWS IAM 인증·EKS Access Entry·팀별 RBAC로 실제 접근을 통제한다. 노드와 제어부 사이는 private endpoint를 사용한다.
이는 인증 없는 앱·DB 공개와 다르다. 익명 쓰기·관리자 공용 키·장기 ServiceAccount token은 제공하지 않는다.
config의 `allow_public_api_from_anywhere: true`가 명시된 경우에만 `0.0.0.0/0`을 허용한다.
고정 출구나 VPN이 준비된 수업은 이 값을 false로 바꾸고 허용할 외부 CIDR만 넣는다.
근거: [EKS API endpoint와 IAM/RBAC](https://docs.aws.amazon.com/eks/latest/userguide/cluster-endpoint.html).
EKS 제어부·노드·EBS·IPv4 비용이 발생한다. 노드만 중지해도 제어부 비용은 남는다.

## 2. 공개 설치 파일 생성

```bash
mkdir -p .local/classroom-eks
cp deploy/classroom-eks/config.example.json .local/classroom-eks/config.json
python3 -m pip install PyYAML bcrypt
```

config의 버전·접속망 정책·기존 이미지 digest를 실제 값으로 채운다.
시드니 ECR 저장소 `idea-support-server`에 처음 실행할 이미지를 먼저 올려야 한다.
기존 시드니 ECR 저장소를 그대로 사용한다. main workflow의 기존 region·registry도 시드니이므로 유지한다.

```bash
aws ecr describe-repositories --repository-names idea-support-server --region ap-southeast-2
# RepositoryNotFoundException일 때만 생성한다. 다른 오류를 무시하고 진행하지 않는다.
aws ecr create-repository --repository-name idea-support-server --region ap-southeast-2 --image-scanning-configuration scanOnPush=true
```

기존 main CI의 ECR 업로드 부분은 아래와 같이 시드니 주소를 사용한다. 기존 test job 뒤에 둔다.
GitHub OIDC 역할 또는 현재의 수업용 인증 설정은 별도 계정 권한 검토 후 사용한다.

```bash
export AWS_REGION=ap-southeast-2
export CONTAINER_IMAGE=950177940921.dkr.ecr.ap-southeast-2.amazonaws.com/idea-support-server:latest
export REGISTRY_USER=AWS
export REGISTRY_PASSWORD=$(aws ecr get-login-password --region "$AWS_REGION")
./gradlew jib -PprojectDataImageTargetEnv=prod
unset REGISTRY_PASSWORD
aws ecr describe-images --repository-name idea-support-server --image-ids imageTag=latest --query imageDetails[0].imageDigest --output text
```

GitHub job은 테스트 통과 후에만 이 단계를 실행한다. workflow에 kubectl·관리자 kubeconfig는 넣지 않는다.
최초 digest를 config의 `bootstrap_digest`에 넣는다. `latest`는 덮어쓰는 별칭으로 사용한다.
태그 불변 정책을 켰다면 `latest` 예외 또는 별도 릴리스 태그 전략이 필요하다.

```bash
python3 deploy/classroom-eks/prepare.py --config .local/classroom-eks/config.json
eksctl create cluster -f .local/classroom-eks/rendered/cluster.yaml
export KUBECONFIG="$PWD/.local/classroom-eks/kubeconfig-admin"
aws eks update-kubeconfig --name classroom-main --region ap-southeast-2 --alias classroom-main-admin --kubeconfig "$KUBECONFIG"
kubectl config current-context
kubectl get nodes
aws eks list-addons --cluster-name classroom-main --region ap-southeast-2
```

이 별도 kubeconfig를 모든 강사 명령에 사용한다. PC의 기존 운영 클러스터 context를 사용하지 않는다.
EBS CSI·Pod Identity Agent가 ACTIVE, 노드 Ready가 된 뒤 진행한다.
EBS CSI의 Pod Identity IAM 역할은 cluster.yaml의 addon 설정으로 생성한다.
일반 EKS managed nodes 구성이다. EKS Auto Mode의 다른 StorageClass 예제를 섞지 않는다.

## 3. namespace·스토리지·앱 Secret

```bash
kubectl apply -f .local/classroom-eks/rendered/platform/namespaces.yaml
kubectl apply -f .local/classroom-eks/rendered/platform/storage.yaml
kubectl apply -f .local/classroom-eks/rendered/platform/observer.yaml
python3 deploy/classroom-eks/bootstrap-secrets.py app --kubeconfig "$KUBECONFIG"
```

`mysql-auth`에 DB 이름·사용자·암호, `spring-auth`에 JWT·SHA·AES 키가 저장된다.
값은 출력하거나 Git/Notion에 넣지 않는다. 기존 Secret은 재실행해도 덮어쓰지 않는다.
기존 PVC의 MySQL 암호를 Secret만 바꿔 회전할 수 없다. SQL 사용자 변경 절차가 별도로 필요하다.

## 4. Argo CD와 관리자 Secret

공식 차트로 확인한 고정 버전: argo-cd chart `10.18.0` / Argo CD `3.6.1`,
argocd-image-updater chart `1.4.2` / controller `1.4.0`.
공식 chart repo에서 해당 버전 존재를 확인하고 수업 중 임의 latest 업그레이드를 하지 않는다.

```bash
helm repo add argo https://argoproj.github.io/argo-helm
helm repo update
helm upgrade --install argocd argo/argo-cd --version 10.18.0 --namespace argocd --create-namespace -f .local/classroom-eks/rendered/argocd/values.yaml --wait --timeout 10m
python3 deploy/classroom-eks/bootstrap-secrets.py argocd --kubeconfig "$KUBECONFIG"
kubectl -n argocd port-forward svc/argocd-server 8443:443 --address 127.0.0.1
```

강사는 `https://localhost:8443`으로 접속한다. 설치 직후 자체 서명 인증서를 사용하므로
실제 외부 공개 시에는 신뢰하는 TLS 인증서·도메인·접근 통제를 따로 설정한다.
인증서 검증을 전체 비활성화한 설정을 배포 파일에 넣지 않는다.

관리자 암호의 **bcrypt 해시**는 Argo CD 표준 Secret `argocd/argocd-secret`의 `admin.password`다.
요청한 보관용 원문은 `argocd/argocd-admin-credentials`의 `password`에만 저장한다.
`argocd-initial-admin-secret`은 변경 후 삭제한다. 학생용 account `students`는 해당 앱 조회·로그만 허용한다.
`argocd-student-credentials`도 강사만 읽어 필요할 때 별도 전달한다.

강사 본인 화면에서만 원문을 확인하려면:

```bash
kubectl -n argocd get secret argocd-admin-credentials -o jsonpath='{.data.password}' | base64 -d
```

화면 공유 중 실행하지 않는다. Kubernetes Secret의 base64는 암호화가 아니며,
학생 Role에는 Secret 조회·Pod exec·쓰기·argocd namespace 권한을 주지 않는다.
Helm upgrade 때 기존 `argocd-secret` 관리 항목의 소유권 충돌이 없는지 확인한다.

## 5. Git 연결·GitOps 브랜치

이미지 업로드를 실행하는 **코드 main**과 배포 정의만 바뀌는 **codex/classroom-gitops**를 나눈다.
이렇게 해야 Image Updater의 Git 커밋이 다시 앱 빌드를 일으키는 루프를 피한다.

별도 깨끗한 checkout에서 `codex/classroom-gitops`를 만들고, 렌더링한
`apps/team/{mysql,spring,kustomization}.yaml` 세 파일을 해당 브랜치의
`deploy/classroom-eks/apps/team/`에 복사해 commit/push한다.
템플릿 폴더가 아니라 **자리표시자가 제거된 렌더 결과**를 올린다. Secret·kubeconfig는 올리지 않는다.
현재 작업 폴더를 강제로 reset하거나 기존 dev 수정 사항을 포함하지 않는다.
이미 브랜치가 있으면 새로 덮어쓰지 말고 최신 파일을 확인한다.

```bash
python3 deploy/classroom-eks/bootstrap-secrets.py git --kubeconfig "$KUBECONFIG"
kubectl apply -f .local/classroom-eks/rendered/argocd/project.yaml
kubectl apply -f .local/classroom-eks/rendered/argocd/application.yaml
kubectl -n argocd get applications classroom-team
kubectl -n team rollout status statefulset/mysql --timeout=5m
kubectl -n team rollout status deployment/spring --timeout=5m
```

Git 인증은 해당 저장소 Contents read/write만 가진 fine-grained token 또는 GitHub App을 사용한다.
read 전용 연결만으로는 Image Updater의 commit/push가 되지 않는다.
또는 해당 저장소에만 쓰기가 허용된 SSH deploy key를 사용한다. 이 경우 config의 git_repository를
`git@github.com:MinQDU014/idea-support-server.git`으로 바꿔 다시 렌더링하고,
`bootstrap-secrets.py git --repository git@github.com:MinQDU014/idea-support-server.git --ssh-key 개인키경로 --kubeconfig "$KUBECONFIG"`로 연결한다.
GitHub에 등록하는 것은 공개 키이고 개인 키는 argocd Secret에만 저장한다. Argo CD의 GitHub known-hosts 검증을 유지한다.
브랜치 보호가 직접 push를 막으면 write-back PR 방식으로 바꾸고 승인 뒤 합친다.
학생은 이 브랜치·관리자 토큰에 쓰기 권한을 받지 않는다.

## 6. ECR 읽기 역할·Image Updater

Image Updater용 role에는 ECR 조회만 준다. 노드의 ECR pull 역할과 별개다.
생성된 IAM YAML을 eksctl의 inline permissionPolicy로 사용해 Pod Identity association을 만든다.

```bash
python3 - <<'PY'
from pathlib import Path
import yaml
root = Path('.local/classroom-eks/rendered')
policy = yaml.safe_load((root/'iam/updater-ecr-read.yaml').read_text())
config = {'apiVersion':'eksctl.io/v1alpha5','kind':'ClusterConfig',
  'metadata':{'name':'classroom-main','region':'ap-southeast-2'},
  'iam':{'podIdentityAssociations':[{'namespace':'argocd',
    'serviceAccountName':'argocd-image-updater','createServiceAccount':True,
    'roleName':'classroom-main-image-updater','permissionPolicy':policy}]}}
(root/'updater-identity.yaml').write_text(yaml.safe_dump(config, sort_keys=False))
PY
eksctl create podidentityassociation -f .local/classroom-eks/rendered/updater-identity.yaml
helm upgrade --install argocd-image-updater argo/argocd-image-updater --version 1.4.2 --namespace argocd -f .local/classroom-eks/rendered/argocd/updater-values.yaml --set serviceAccount.create=false --wait --timeout 5m
kubectl apply -f .local/classroom-eks/rendered/argocd/image-updater.yaml
kubectl -n argocd logs deployment/argocd-image-updater-controller --tail=100
```

`1.4.0` controller에는 AWS CLI가 포함된다. `ecr-login.sh`가 Pod Identity로
ECR 토큰을 얻으며 토큰은 10시간 후 새로 읽는다. ECR 토큰은 12시간 유효하므로
영구 AWS access key나 고정 ECR 비밀번호를 YAML에 넣지 않는다.
이 스크립트를 직접 실행해 토큰 출력 결과를 강의에 붙이지 않는다.

CRD가 생긴 뒤 `ImageUpdater` 객체를 적용한다. 예전 0.x의 Application annotation만
붙이는 예제를 최신 1.x 설정과 섞지 않는다. 기본 폴링 1분, Argo Git 재조정 2분+jitter로
전체 반영은 즉시가 아니다. 필요하면 Argo UI의 Refresh를 강사가 사용한다.

이 설치의 Application.status.summary.images는 비어 있어 기본 감시에서 이미지가 건너뛰어졌다.
따라서 해당 Spring 이미지 한 개의 commonUpdateSettings.forceUpdate=true를 명시한다.
이는 상태 목록에 이미지가 없어도 추적한다는 뜻이며 readiness 실패를 무시한다는 뜻이 아니다.

## 7. 학생의 AWS 인증·Lens

실제 수업 계정에서 기존 IAM 사용자 `team1`~`team8`을 확인했다. 새 사용자나 AWS 키를 만들지 않고
각 팀이 이미 받은 ECR용 access key를 본인 PC의 제한된 profile로 재사용한다.
소속 계정·IAM 권한을 먼저 대조했고 기존 정책은 ECR PowerUser, IAM 그룹·추가 inline 정책은 없었다.
config에는 공개 principal ARN만 넣고 비밀번호·access key는 쓰지 않는다.
개인별 SSO를 운영 중인 수업은 그 role을 매핑하는 방식으로 대체할 수 있다.

config 예시에는 확인한 기존 team1~team8 principal이 이미 들어 있다. 학생 구성이 바뀌면 다음 형식으로 바꾼다.

```json
{"namespace":"team1","principal_arn":"arn:aws:iam::950177940921:user/team1"}
```

학생 IAM에는 최소한 해당 클러스터 ARN의 `eks:DescribeCluster`와 필요한 SSO/AssumeRole
접속 권한이 있어야 한다. Kubernetes 권한은 Access Entry → group → RoleBinding으로 준다.
추가 AmazonEKSAdminPolicy나 AmazonEKSClusterAdminPolicy를 학생에게 붙이지 않는다.
기존 ECR PowerUser에는 모든 저장소의 PutImage가 포함되어 있다. 예시 ECR을 덮어쓰면 GitOps 배포도 바뀌므로,
강사 예시 `idea-support-server` 저장소만 학생 업로드를 명시적으로 거절한다. 이미지 조회와 다른 저장소의 기존 권한은 유지한다.

```bash
python3 deploy/classroom-eks/prepare.py --config .local/classroom-eks/config.json
python3 deploy/classroom-eks/student-access.py --config .local/classroom-eks/config.json
# 계획의 principal과 팀 배정 확인 후:
python3 deploy/classroom-eks/student-access.py --config .local/classroom-eks/config.json --apply --grant-describe --protect-gitops-ecr
kubectl apply -f .local/classroom-eks/rendered/student-bindings.yaml
```

현재 student bindings는 **본인 teamN + 예시 team**에 읽기·로그만 허용한다.
Lens의 namespace 선택을 위해 namespace 이름 목록만 전역 조회를 허용한다.
노드·지표·argocd 리소스·다른 팀 앱은 금지하며 Lens 일부 메뉴의 Forbidden은 정상이다.
Lens에서 All namespaces 대신 `team`, `teamN`을 선택한다.

학생 PowerShell:

```powershell
aws configure --profile classroom-team1
aws sts get-caller-identity --profile classroom-team1
aws eks update-kubeconfig --region ap-southeast-2 --name classroom-main --alias classroom-team1 --profile classroom-team1
kubectl --context classroom-team1 -n team get pods
kubectl --context classroom-team1 -n team1 get pods
kubectl --context classroom-team1 auth can-i get secrets -n argocd
kubectl --context classroom-team1 auth can-i delete pods -n team
kubectl --context classroom-team1 auth can-i get pods -n team2
```

configure 프롬프트에는 이미 받은 자기 팀 access key ID·secret access key, region ap-southeast-2, output json을 입력한다.
새 AWS 계정을 가입하거나 강사 키를 입력하지 않는다. STS의 Account가 950177940921, Arn의 사용자가 자기 팀인지 확인한다.
SSO를 쓰는 학생만 별도 SSO profile로 로그인한다. 클러스터 region과 SSO region은 같다고 가정하지 않는다.
Lens는 로컬 `%USERPROFILE%\.kube\config`를 등록한다. 프리미엄 AWS 자동 검색은 필수가 아니다.
AWS CLI 실행 경로가 Lens의 PATH에 있어야 하고 SSO 만료 시 재로그인 후 다시 연결한다.
강사 kubeconfig·관리자 AWS key·ServiceAccount 영구 token을 학생에게 나눠 주지 않는다.

확인한 Lens 화면의 실제 순서:

1. Preferences → Kubernetes → Manage Kubeconfigs → Sync file(s)를 연다.
2. 자기 PC의 `%USERPROFILE%\.kube\config`를 선택한다. 최신 버전은 Preferences → Integrations → Local Kubeconfigs → Watch files & folders로 표시될 수 있다.
3. Navigator → Local Kubeconfigs → classroom-team1을 열고 Workloads → Pods를 선택한다.
4. namespace 선택에서 default·All namespaces를 해제하고 **team만** 선택한다. 최초 화면의 default는 학생 권한 범위가 아니므로 Failed to load items가 나올 수 있다.
5. mysql-0과 spring-…의 Running·Ready 상태를 확인한다. 자기 team1을 선택하면 빈 목록이 정상이다.

학생은 자기 팀 키로 연결한 뒤 예시 team의 Pod와 로그가 보이는지 확인한다. PC별 AWS CLI 설치와 학교 방화벽 조건도 대조한다.
근거: [Lens 로컬 클러스터 등록](https://docs.lenshq.io/k8slens/getting-started/add-clusters/add-local-cluster/).

예상 결과: 예시 team의 mysql-0·spring Pod 1개 조회, 본인 team1은 No resources found,
다른 팀·Secret·삭제 권한은 no. 인증 정보 없이 kubeconfig 파일만 복사해도 접속되지 않는다.
이번 수업은 고정 IP 없이 IAM 키로 접속하므로 publicAccessCIDRs는 0.0.0.0/0이다.
팀별 기존 키는 개별 전달하고, 유출되면 IAM에서 비활성화·회전한다. kubeconfig에는 비밀 키를 넣지 않는다.
IP를 제한하는 구성으로 바꾼 경우에는 학생의 실제 egress 공인 IP 또는 VPN 출구를 허용 목록에 추가해야 한다.

## 8. 수업 시연·판정·복구

1. Argo classroom-team이 Synced+Healthy, mysql PVC Bound, mysql-0/spring Ready인지 확인.
2. 강사가 `kubectl -n team port-forward svc/spring 18080:8080` 후 `/common/health` 확인.
3. 이 저장소는 prod에서 Swagger UI가 꺼져 있다. DB 쓰기/읽기는 `docs/API_SPEC.md`의 실제 인증·등록 API로 확인한다.
4. 수업용 AI_MODE=mock은 의도적이다. 실제 Gemini 호출 성공으로 기록하지 않는다.
5. 코드 main의 작은 응답 변경 → 검사 통과 → 시드니 ECR latest 갱신.
6. Image Updater 로그·GitOps 브랜치 kustomization digest 커밋·Argo revision·ReplicaSet·Lens imageID 순으로 기록.
7. Spring만 새 Pod로 교체되고 MySQL Pod/볼륨·team1~team8의 빈 상태는 유지되는지 확인.
8. 실패 이미지라면 자동 Git 롤백되지 않는다. 기존 Pod가 남더라도 DB migration의 부작용은 별도다.

긴급 고정 복구는 먼저 Image Updater를 멈춘 뒤 GitOps digest를 되돌린다.
`git revert`만 하면 updater가 latest를 다시 선택할 수 있다.

```bash
kubectl -n argocd scale deployment argocd-image-updater-controller --replicas=0
# GitOps 브랜치에서 실패한 digest 커밋을 git revert → push
kubectl -n team rollout status deployment/spring --timeout=5m
```

정상 코드로 main을 복구·빌드하여 ECR latest도 올바른 이미지로 만든 뒤 updater replicas=1로 재개한다.
`kubectl rollout undo`만 하면 selfHeal이 Git의 실패 설정을 다시 적용할 수 있다.
DB migration은 이미지 복구로 되돌아가지 않는다. StatefulSet/PVC 삭제를 복구 실습에 쓰지 않는다.
수업 종료 시 EKS·노드·EBS 등 과금 자원은 강사가 백업·보존 범위를 정한 뒤 정리한다.
Retain인 EBS는 클러스터 삭제 뒤에도 비용이 남는다. 기존 Lightsail/Registry는 별도다.

## 검증 기록

실제 계정의 배포·학생 접속 검증 기록은 [비공개 Notion 설치 부록](https://app.notion.com/p/419b4057395f81dab0d4d4246cc762b9)에서 관리한다. 공개 저장소에는 설치 절차와 구성만 보관한다.
