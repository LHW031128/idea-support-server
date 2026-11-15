<p color="blue">이번 주 핵심 질문</p>

[강사용 설치 부록](https://app.notion.com/p/419b4057395f81dab0d4d4246cc762b9) · [전체 배포 파일](https://github.com/MinQDU014/idea-support-server/tree/codex/classroom-eks-preparation/deploy/classroom-eks)

**ECR에 새 이미지가 올라왔다는 사실만으로, 실행 중인 서버는 어떻게 새 버전으로 바뀔까요.**

지난 시간에는 Lightsail 한 대에서 Docker Compose로 서버를 교체했습니다. 이번에는 같은 Spring Boot 패키지를 EKS에서 실행합니다. 서버마다 접속해서 명령을 내리는 대신, Git에 원하는 상태를 적고 Argo CD가 실제 상태를 맞추게 하겠습니다.

오늘은 코드가 ECR을 거쳐 Pod가 될 때까지의 길을 봅니다. 그다음 새 버전이 실패했을 때 어디서 멈추는지, Git으로 어떻게 복구하는지, Lens에서 무엇을 확인해야 하는지 직접 따라가 보겠습니다.

## 오늘의 3시간 운영표

| 시간 | 분량 | 내용 |
| --- | --- | --- |
| 00:00~00:10 | 10분 | 지난주 복습, 예시 서버와 Lens 준비 확인 |
| 00:10~00:40 | 30분 | 1부. Kubernetes와 EKS, 우리가 만들 리소스 |
| 00:40~00:50 | 10분 | 휴식 |
| 00:50~01:25 | 35분 | 2부. Argo CD와 GitOps, ECR 변경이 배포되는 과정 |
| 01:25~01:35 | 10분 | 휴식 |
| 01:35~02:00 | 25분 | 3부. MySQL·Spring 배포, Secret·스토리지·학생 권한 |
| 02:00~02:40 | 40분 | 활동. Lens 연결, 새 버전 관찰, 실패와 Git 복구 |
| 02:40~02:55 | 15분 | 팀별 공유, 어떤 단계에서 멈췄는지 설명하기 |
| 02:55~03:00 | 5분 | 오늘 남길 문장과 정리 |

EKS 생성과 도구 설치는 강사가 수업 전에 끝냅니다. 수업 중에는 준비된 클러스터에서 한 번의 배포를 천천히 추적합니다. 팀마다 클러스터를 만들지 않습니다.

---

# 오프닝. 지난주와 무엇이 달라질까

| 구분 | 지난 시간 | 이번 시간 |
| --- | --- | --- |
| 이미지 저장 | docker.minq.live | 시드니 ECR |
| 실행 환경 | Lightsail VM + Compose | 공유 EKS + Kubernetes |
| 배포의 기준 | 배포 요청을 받은 서버의 교체 명령 | Git에 기록한 원하는 상태 |
| 실제 교체 | Compose로 컨테이너 교체 | Deployment가 ReplicaSet과 Pod 교체 |
| 확인 도구 | Actions·브라우저·서버 로그 | Actions·Git·Argo CD·Lens |
| 복구 | 코드 Revert 후 재빌드·배포 | 이미지 갱신을 멈추고 Git 배포 정의 복구, 또는 코드 Revert 후 정상 이미지 재발행 |

이번 수업은 **수업 계정 950177940921, 시드니 ap-southeast-2, classroom-main**을 사용하도록 준비합니다. 기존 시드니 Lightsail 서버·학생 DB를 이번 EKS 실습이 자동으로 이전하는 것은 아닙니다. EKS의 team MySQL은 새 수업용 데이터베이스입니다.

손을 들어 보세요.

1. ECR에 이미지가 저장된 것과 서버가 실행된 것은 다르다고 설명할 수 있다.
2. Git에서 합친 PR을 Revert해 본 적이 있다.
3. Lens와 AWS CLI를 설치했고, 강사에게 본인 AWS 접속 안내를 받았다.

퀴즈입니다. 답은 2부 끝에서 확인하겠습니다.

1. Argo CD는 ECR을 직접 계속 검색한다.
2. latest가 바뀌면 Kubernetes가 실행 중인 Pod를 알아서 다시 만든다.
3. namespace만 나누면 다른 팀의 Secret을 읽을 수 없다.
4. Argo CD의 Synced는 서비스가 정상이라는 뜻이다.
5. Git에서 예전 이미지를 지정하면 DB 데이터도 예전으로 돌아간다.

---

# 1부. Kubernetes와 EKS, 우리가 만들 리소스

## 1. 컨테이너를 실행하는 명령에서 원하는 상태로

Compose에서는 파일에 앱과 DB를 적고 서버에서 실행했습니다. Kubernetes에서도 파일을 씁니다. 차이는 파일을 적용한 뒤에도 컨트롤러가 계속 실제 상태를 확인한다는 점입니다.

Spring Pod가 1개여야 하는데 사라지면 새 Pod를 만듭니다. 새 버전으로 바꾸라고 적으면 새 Pod를 준비한 뒤 기존 Pod를 내립니다. 하지만 잘못된 비밀번호나 잘못 만든 API까지 도구가 알아서 고쳐 주지는 않습니다.

| 용어 | 맡은 일 | 이번 수업 |
| --- | --- | --- |
| EKS | Kubernetes 제어부를 AWS가 운영 | classroom-main 한 개 |
| Node | 실제 컨테이너를 실행할 컴퓨터 | 수업용 EC2 워커 두 대 |
| Namespace | 리소스를 묶는 이름 공간 | team, team1~team8 |
| Pod | 함께 실행되는 컨테이너의 최소 단위 | Spring Pod, MySQL Pod |
| Deployment | 앱 Pod 수와 버전 교체를 관리 | spring |
| ReplicaSet | 해당 Pod 템플릿의 개수를 유지 | Deployment가 자동 생성 |
| StatefulSet | 일정한 이름·스토리지와 연결한 실행 관리 | mysql-0 |
| Service | 바뀌는 Pod 앞에 고정된 접속 경로 제공 | spring, mysql |
| PVC / PV | 저장공간 요청 / 연결된 저장공간 | MySQL의 EBS 데이터 디스크 |
| Secret | 비밀번호·키를 주입하는 리소스 | mysql-auth, spring-auth, Argo 관리자 암호 |
| Argo CD Application | Git 경로와 배포 대상을 연결 | classroom-team |

Pod는 없어져도 다시 생길 수 있어야 합니다. 데이터베이스 파일을 Pod 안에만 두면 새로 생긴 Pod에는 그 파일이 없습니다. 그래서 MySQL은 Pod와 수명이 다른 EBS 디스크를 연결합니다.

## 2. 오늘의 배치도

```text
AWS 수업 계정 950177940921 / 시드니 ap-southeast-2
└─ EKS classroom-main
   ├─ argocd: Argo CD + Image Updater
   ├─ kube-system: DNS·네트워크·EBS 드라이버·Pod Identity Agent
   ├─ team: Spring Deployment 1개 + MySQL StatefulSet 1개 + EBS
   ├─ team1: 학생 권한만 준비, 앱 Pod 없음
   ├─ team2~team7: 학생 권한만 준비, 앱 Pod 없음
   └─ team8: 학생 권한만 준비, 앱 Pod 없음
```

**학생 namespace에 아직 Pod가 없는 것은 정상입니다.** 이번에는 강사 예시 team을 모두 함께 관찰합니다. 이후 자기 팀 앱을 올릴 때는 별도 DB·Secret·이미지 경로·Application·배포 권한을 준비해야 합니다. team의 DB 암호를 복사해서 나누지 않습니다.

namespace는 폴더처럼 묶어 주지만, 그 이름만으로 접근 권한·네트워크·CPU가 격리되지는 않습니다. 오늘은 학생에게 읽기 권한만 부여해 관찰 범위를 제한합니다. 여러 팀이 실제 앱을 운영하는 단계에서는 ResourceQuota·LimitRange·NetworkPolicy를 별도로 적용하고 CNI의 정책 실행도 확인해야 합니다.

## 3. Service와 외부 접속은 다르다

Spring은 mysql.team.svc.cluster.local:3306으로 DB에 접속합니다. 이 주소는 클러스터 안에서 쓰는 Service DNS입니다. 학생 노트북 브라우저에서 직접 열리는 주소가 아닙니다.

이번 수업의 Spring·MySQL·Argo 서비스는 ClusterIP로 시작합니다. 강사는 port-forward로 Argo CD와 Spring을 확인합니다. 학생 Lens는 Kubernetes API에 인증해서 상태와 로그를 읽습니다. MySQL 3306을 인터넷에 공개하지 않습니다.

강의실에는 고정 공인 IP가 없습니다. EKS의 공개 API에는 어느 접속망에서도 도달할 수 있게 하고, 기존 팀별 AWS 키 → 짧은 수명의 EKS 인증 토큰 → Access Entry → RBAC 순서로 접근을 확인합니다. SSH 개인 키로 노드에 로그인하는 방식이 아닙니다. kubeconfig에는 클러스터 주소·인증서·AWS CLI 실행 설정이 있고 비밀 access key 자체를 넣지 않습니다.

학생의 AWS 키는 자기 팀에만 개별 전달합니다. 다른 팀 키나 관리자 키를 복사하지 않습니다. 예시 ECR을 학생이 덮어써 배포를 바꾸지 못하도록 그 저장소의 업로드도 제한합니다. [EKS 공개 API의 IAM·RBAC 인증](https://docs.aws.amazon.com/eks/latest/userguide/cluster-endpoint.html).

실제 사용자에게 웹서비스를 공개하려면 Ingress 또는 LoadBalancer, 도메인, TLS 인증서, CORS 주소 설정을 추가해야 합니다. Lens 접속이 되는 것과 일반 사용자가 앱을 여는 것은 별개입니다.

---

# 2부. Argo CD와 GitOps, ECR 변경이 배포되는 과정

## 1. GitOps는 Git을 배포 상태의 기준으로 삼는다

GitOps에서는 배포할 이미지와 Pod 개수 같은 설정을 Git에 적습니다. Argo CD는 Git에 적힌 상태와 Kubernetes에 있는 상태를 비교하고 차이가 생기면 맞춥니다.

누가 어떤 이미지로 바꿨는지 Git에서 볼 수 있고, 이전 상태도 커밋으로 남습니다. CI에게 Kubernetes 관리자 권한을 줘서 서버에 직접 들어오게 할 필요도 줄어듭니다.

| 담당 | 보는 곳 | 바꾸는 것 |
| --- | --- | --- |
| GitHub Actions + Jib | 코드 main의 변경 | 테스트한 앱 이미지를 ECR에 업로드 |
| Argo CD Image Updater | ECR latest의 실제 digest | GitOps 브랜치의 이미지 digest를 commit/push |
| Argo CD | GitOps 브랜치의 배포 파일 | Kubernetes Deployment·Service·StatefulSet |
| Kubernetes | 적용된 원하는 상태 | 실제 ReplicaSet·Pod·Service 연결 |
| Lens | Kubernetes API | 이번 수업에서는 조회만 |

**Argo CD만 설치했다고 ECR의 새 이미지를 찾는 것은 아닙니다.** 그 역할을 하는 Image Updater가 필요합니다. 다른 설계로 CI가 GitOps 파일을 직접 수정할 수도 있지만, 오늘은 ECR 감지 과정을 보기 위해 Image Updater를 사용합니다.

## 2. ECR에서 Pod까지 여덟 단계

```text
코드 main에 merge
  → Actions 테스트 통과
  → Jib이 시드니 ECR의 latest를 새 이미지로 갱신
  → Image Updater가 ECR latest의 digest를 주기적으로 비교
  → GitOps 브랜치 kustomization.yaml에 새 digest commit/push
  → Argo CD가 Git 변경을 발견하고 OutOfSync 표시
  → 자동 Sync가 Kubernetes Deployment의 이미지 변경
  → 새 Pod가 Ready가 된 뒤 기존 Pod 종료
```

여기서 GitOps 브랜치는 codex/classroom-gitops입니다. 코드 main과 분리했기 때문에 이미지 기록 커밋이 다시 앱 빌드를 시작하는 루프를 만들지 않습니다. 학생은 코드 main의 변경과 GitOps의 변경 커밋이 서로 다른 기록이라는 것을 보세요.

ECR을 1분마다 확인하고, Argo CD는 Git을 2분과 추가 jitter 간격으로 재확인하도록 준비합니다. 빌드·Git 쓰기·동기화·앱 기동 시간이 더해져 즉시 배포되지 않습니다. Git webhook은 대기 시간을 줄이는 방법이며 이미지 감지 기능을 대신하지 않습니다.

근거: [Argo CD 자동 동기화](https://argo-cd.readthedocs.io/en/stable/user-guide/auto_sync/), [Image Updater Git write-back](https://argocd-image-updater.readthedocs.io/en/stable/basics/update-methods/).

## 3. latest 이름이 같아도 새 버전을 알 수 있는 이유

latest는 사람이 붙인 이름입니다. 같은 이름을 다른 이미지에 다시 붙일 수 있습니다. digest는 이미지 내용에 대응하는 식별값입니다.

| 구분 | 바뀌기 전 | 바뀐 뒤 |
| --- | --- | --- |
| ECR 태그 | latest | latest |
| 실제 이미지 digest | sha256:AAA… | sha256:BBB… |
| Git 배포 파일 | digest: sha256:AAA… | digest: sha256:BBB… |
| Deployment Pod 템플릿 | 이전 이미지 고정 | 새 이미지 고정 |

오늘은 **digest 전략**으로 latest 뒤의 실제 내용 변화를 감지합니다. Image Updater는 Git에 digest를 기록하고 Kustomize가 정확한 이미지 주소를 만듭니다. Deployment의 Pod 템플릿이 바뀌므로 새 ReplicaSet과 Pod가 생깁니다.

반대로 YAML이 계속 image:latest로 같고, 다른 변경도 없으면 새 ECR 이미지가 올라와도 기존 Pod는 그대로입니다. imagePullPolicy:Always는 Pod가 시작될 때의 pull 동작이지 실행 중인 Pod를 자동 교체하는 감시기가 아닙니다.

Jib은 amd64·arm64 멀티아키텍처 이미지를 만들 수 있습니다. ECR의 최상위 index digest와 노드가 실행한 amd64 하위 manifest의 imageID는 다를 수 있습니다. Pod spec의 고정 digest와 ECR index의 플랫폼별 manifest까지 따라가 확인하며, 두 문자열이 다르다는 이유만으로 실패라고 판단하지 않습니다.

근거: [Image Updater 이미지 선택·digest 전략](https://argocd-image-updater.readthedocs.io/en/stable/configuration/images/), [Kubernetes 이미지 pull 동작](https://kubernetes.io/docs/concepts/containers/images/).

## 4. 설정 파일은 무엇을 말하나

전체 설치 파일은 강사용 설치 안내에 있습니다. 수업에서는 두 파일을 먼저 읽겠습니다.

```yaml
# Application 일부: 무엇을 어디에 배포할까
source:
  repoURL: git@github.com:MinQDU014/idea-support-server.git
  targetRevision: codex/classroom-gitops
  path: deploy/classroom-eks/apps/team
destination:
  server: https://kubernetes.default.svc
  namespace: team
syncPolicy:
  automated:
    prune: false
    selfHeal: true
```

repoURL은 저장소, targetRevision은 감시할 브랜치, path는 Kubernetes 파일이 있는 폴더입니다. destination은 실제 클러스터와 namespace입니다. 다른 폴더나 main을 감시하면 우리가 기대한 Git 커밋을 보지 못합니다.

selfHeal은 누군가 서버 설정을 직접 바꿨을 때 Git 상태로 맞추는 기능입니다. 잘못 만든 앱 기능까지 고친다는 뜻은 아닙니다. 이번 DB 수업은 prune:false로 두어 Git에서 파일을 지웠다는 이유만으로 DB 리소스를 자동 삭제하지 않습니다. 지워진 리소스 정리는 강사가 직접 판단합니다.

```yaml
apiVersion: argocd-image-updater.argoproj.io/v1alpha1
kind: ImageUpdater
metadata:
  name: classroom-team
  namespace: argocd
spec:
  writeBackConfig:
    method: git:secret:gitops-write
    gitConfig:
      branch: codex/classroom-gitops
      writeBackTarget: kustomization
  applicationRefs:
    - namePattern: classroom-team
      images:
        - alias: spring
          imageName: 950177940921.dkr.ecr.ap-southeast-2.amazonaws.com/idea-support-server:latest
          commonUpdateSettings:
            updateStrategy: digest
            platforms: [linux/amd64]
```

Git에 쓸 인증은 argocd namespace의 gitops-write Secret에서 읽습니다. ECR 조회 권한은 별도 AWS Pod Identity 역할로 받습니다. 둘은 서로 다른 인증입니다. 하나만 맞아도 전체 배포가 되지는 않습니다.

이 예시는 Image Updater 1.x CRD 방식입니다. 예전 0.x의 Application annotation 예제와 섞지 않습니다. 설치 CRD가 생기기 전에 ImageUpdater 파일을 적용하면 리소스 종류를 모른다는 오류가 납니다.

## 5. Synced와 Healthy는 서로 다른 질문이다

| 표시 | 뜻 | 다음에 볼 것 |
| --- | --- | --- |
| OutOfSync | Git과 클러스터 정의가 다름 | Git 경로·자동 Sync·권한 |
| Synced | 배포 정의가 Git과 맞음 | Pod와 서비스 건강 상태 |
| Progressing | 새 Pod가 준비되는 중 | 이미지 pull·기동·readiness |
| Degraded | 리소스의 건강 상태가 나쁨 | Pod Events·로그·rollout |
| Healthy | 해당 리소스의 건강 판정 통과 | 실제 API와 DB 쓰기·읽기 |

Synced여도 비밀번호가 틀려 앱은 죽을 수 있습니다. Healthy여도 특정 API 기능은 잘못됐을 수 있습니다. 마지막 확인은 우리가 바꾼 응답과 실제 DB 저장 결과입니다.

오프닝 퀴즈의 답은 **다섯 개 모두 틀림**입니다. Argo CD와 Image Updater, 이미지 이름과 digest, namespace와 권한, 동기화와 건강, 앱 복구와 데이터 복구를 구분해 보세요.

---

# 3부. MySQL·Spring 배포, Secret·스토리지·학생 권한

## 1. 강사가 설치하는 순서

| 순서 | 작업 | 다음으로 넘어가기 전 확인 |
| --- | --- | --- |
| 1 | 수업 계정·시드니 확인, ECR에 시작 이미지 준비 | 계정 950177940921, 시드니 URI·digest 존재 |
| 2 | EKS·노드·EBS CSI·Pod Identity Agent 준비 | Node Ready, add-on ACTIVE |
| 3 | team과 team1~team8 생성, StorageClass 준비 | 9개 namespace, gp3 설정 |
| 4 | team에 DB·Spring Secret 생성 | Secret 이름·필수 key 존재, 값은 비공개 |
| 5 | Argo CD 설치·관리자 암호 Secret 보관 | 관리자 로그인, 학생은 조회만 |
| 6 | GitOps 브랜치와 Git 읽기·쓰기 인증 연결 | 실제 브랜치·경로, read/write 가능 |
| 7 | Application으로 MySQL·Spring 첫 Sync | PVC Bound, mysql-0·spring Ready |
| 8 | Image Updater 설치·ECR 조회 연결 | ECR 인증·Git commit 성공 |
| 9 | 학생 Access Entry·RBAC·Lens 연결 | 본인 팀·예시 조회, Secret·쓰기·다른 팀 거절 |
| 10 | 새 이미지·실패 이미지·복구 시연 | ECR→Git→Argo→Pod→API 기록 |

이번 처음 띄우기는 kubectl로 앱을 계속 관리하는 과정이 아닙니다. 강사는 플랫폼과 Secret을 먼저 준비하고, MySQL·Spring의 선언은 Git에서 Argo CD가 적용하게 합니다.

## 2. MySQL을 올리는 방법

MySQL은 StatefulSet으로 한 개만 실행합니다. 이름은 mysql-0이고 /var/lib/mysql을 PVC에 연결합니다. PVC는 10GiB gp3 EBS를 요청합니다. Service 이름은 mysql입니다.

StorageClass의 WaitForFirstConsumer는 Pod가 어느 가용영역에 배치되는지 정한 뒤 그 영역에 볼륨을 만듭니다. 아직 소비할 Pod가 없다면 Pending일 수 있습니다. Pod가 생긴 뒤에도 계속 Pending이면 EBS CSI·IAM·가용영역·이벤트를 확인합니다.

EBS는 가용영역에 묶인 저장장치입니다. 워커가 두 대라고 MySQL이 여러 영역에서 자동 고가용성이 되는 것은 아닙니다. 이번은 교육용 단일 DB이며 실제 운영의 RDS·복제·백업 설계와 구분합니다. Retain은 자동 삭제를 줄일 뿐 백업을 만들어 주지는 않습니다.

강사가 MySQL을 먼저 Ready로 만든 뒤 Spring이 올라오는지 봅니다. 앱의 Liquibase가 DB 스키마를 준비하고 JPA가 이를 검증합니다. MySQL root 계정은 Spring에 주입하지 않고 별도 앱 사용자를 씁니다.

## 3. Spring을 올리는 방법

기존 패키지를 Jib으로 이미지로 만들고 prod profile로 실행합니다. DB_HOST는 전체 JDBC URL, DB_USERNAME·DB_PASSWORD는 mysql-auth의 앱 사용자 값입니다. JWT_SECRET·SHA_KEY·AES_KEY는 spring-auth에서 읽습니다.

Deployment는 maxUnavailable:0, maxSurge:1로 준비합니다. 기존 앱을 남긴 채 새 Pod를 하나 더 띄울 수 있어야 하므로 교체 중에는 두 Pod의 메모리가 필요합니다. startupProbe는 느린 첫 기동을 기다리고 readinessProbe는 요청을 받을 준비를 확인합니다.

이번 저장소의 health 경로는 /common/health입니다. 실제 DB 저장·조회는 별도로 검사합니다. prod에서는 Swagger UI가 꺼져 있으므로 /swagger-ui가 안 열린다고 배포 실패로 단정하지 않습니다. AI_MODE=mock은 배포 흐름에 집중하기 위한 실습 설정입니다.

## 4. Argo CD admin 암호는 어디에 저장할까

| Secret | 보관하는 것 | 누가 읽나 |
| --- | --- | --- |
| argocd/argocd-secret | Argo CD가 인증에 쓰는 admin.password bcrypt 해시 | Argo CD·강사 |
| argocd/argocd-admin-credentials | 강사 복구용 admin 사용자명·임의 생성 암호 | 강사만 |
| argocd/argocd-student-credentials | 조회 전용 students 사용자명·암호 | 강사가 필요할 때 전달 |
| team/mysql-auth | DB 이름·사용자·암호 | DB·Spring·강사 |
| team/spring-auth | JWT·SHA·AES 키 | Spring·강사 |

실제 암호는 강의 페이지·Git·로그에 쓰지 않습니다. 설치 도구가 임의 생성해 Kubernetes Secret에 저장하고 출력하지 않습니다. 설치 초기에 생기는 argocd-initial-admin-secret은 새 암호 설정 뒤 지웁니다.

Kubernetes Secret의 base64는 암호화가 아닙니다. Lens에서 Secret을 읽을 수 있는 사람이 곧 비밀번호를 읽을 수 있는 사람입니다. 그래서 학생에게 관리자 role이나 Secret 조회를 주지 않습니다. 학생은 Argo CD의 관리자 계정도 공유하지 않습니다.

근거: [Argo CD 관리자 암호와 Secret](https://argo-cd.readthedocs.io/en/stable/faq/), [Kubernetes Secret 주의점](https://kubernetes.io/docs/concepts/configuration/secret/).

## 5. 학생이 EKS에 들어가는 두 개의 문

첫 번째 문은 AWS 인증입니다. 기존 수업 계정에 team1~team8 IAM 사용자가 있으므로, 각 팀이 이미 받은 AWS 키를 자기 PC의 profile로 등록합니다. 강사는 해당 클러스터의 DescribeCluster 권한만 추가합니다. 두 번째 문은 Kubernetes 권한입니다. EKS Access Entry로 연결한 classroom:team1 그룹에 RoleBinding을 주면 team1과 team의 Pod·로그만 볼 수 있습니다. 새 AWS 계정을 만들거나 강사 키를 공유하지 않습니다.

| 학생 team1의 작업 | 결과 |
| --- | --- |
| namespace 이름 목록 보기 | 가능, Lens 선택용 |
| team의 MySQL·Spring 상태와 로그 보기 | 가능 |
| team1의 리소스 보기 | 가능, 지금은 비어 있음 |
| team2~team8의 Pod 보기 | 거절 |
| argocd의 Secret 보기 | 거절 |
| Pod 삭제·수정·터미널 exec·port-forward | 거절 |
| 노드·클러스터 관리자 화면·일부 지표 보기 | 거절될 수 있음 |

Lens에 클러스터가 등록된 것만으로 권한이 생기지 않습니다. kubeconfig에는 연결 주소와 인증 실행 방법이 들어 있습니다. 강사의 관리자 kubeconfig나 AWS 키를 복사해 학생에게 주지 않습니다.

근거: [AWS EKS Access Entries](https://docs.aws.amazon.com/eks/latest/userguide/access-entries.html), [Lens 로컬 kubeconfig 연결](https://docs.lenshq.io/k8slens/getting-started/add-clusters/add-local-cluster/).

---

# 활동. Lens 연결, 새 버전 관찰, 실패와 Git 복구

## STEP 1. 본인 계정으로 Lens 연결하기 (10분)

이전에 자기 팀에 발급된 AWS access key ID와 secret access key를 준비하세요. 새로 발급하거나 강사의 키를 복사하지 않습니다. SSO를 별도로 사용하는 분만 해당 SSO profile로 바꾸세요.

학생 PowerShell에서 실행합니다. team1은 자기 팀 번호로 바꾸세요.

```powershell
aws configure --profile classroom-team1
aws sts get-caller-identity --profile classroom-team1
aws eks update-kubeconfig --region ap-southeast-2 --name classroom-main --alias classroom-team1 --profile classroom-team1
kubectl --context classroom-team1 -n team get pods
kubectl --context classroom-team1 -n team1 get pods
```

1. configure에는 자기 팀의 키, region ap-southeast-2, output json을 입력합니다. STS의 Account가 950177940921이고 Arn이 자기 team1 사용자인지 확인합니다. 다른 계정이면 손을 들어 주세요.
2. Lens의 로컬 kubeconfig 추가에서 %USERPROFILE%\.kube\config를 등록합니다. 기본 자동 감지로 보이면 해당 context를 선택합니다.
3. classroom-team1을 연결하고 namespace를 team으로 선택합니다. Workloads → Pods에서 mysql-0과 spring을 확인합니다.
4. 자기 namespace team1을 선택합니다. No resources found가 정상입니다.
5. team의 Spring Pod → Logs에서 기동 결과를 확인합니다. 비밀번호나 token을 화면에 붙이지 않습니다.

Lens의 유료 AWS 자동 검색 기능은 이번 수업의 필수 조건이 아닙니다. 로컬 kubeconfig 방식으로 연결합니다. 노드·지표 화면이 Forbidden이어도 Pod와 로그가 보이는지부터 확인하세요.

접속이 막힐 때는 아래 순서로 봅니다.

| 현상 | 먼저 확인 |
| --- | --- |
| aws executable not found | AWS CLI 설치·PATH, Lens 다시 실행 |
| SSO 세션 만료·Unauthorized | aws sso login, 본인 profile·Access Entry |
| eks:DescribeCluster AccessDenied | 본인 IAM에 해당 클러스터 조회 권한 |
| Forbidden | 선택 namespace와 RBAC, 앱 Pod 조회 자체도 막혔는지 |
| timeout | AWS 리전·클러스터 주소·학교 방화벽의 443 연결·DNS, IP 제한형 구성이라면 허용 CIDR |
| 팀 앱이 비어 있음 | 이번은 team에만 앱이 있는지 |

## STEP 2. 권한 경계를 확인하기 (5분)

team1 학생의 예상 답은 앞의 두 개 yes, 나머지 no입니다. 다른 팀은 본인 namespace와 비교할 다른 팀 번호를 바꾸세요.

```powershell
kubectl --context classroom-team1 auth can-i get pods -n team
kubectl --context classroom-team1 auth can-i get pods -n team1
kubectl --context classroom-team1 auth can-i get pods -n team2
kubectl --context classroom-team1 auth can-i get secrets -n argocd
kubectl --context classroom-team1 auth can-i delete pods -n team
kubectl --context classroom-team1 auth can-i create pods/exec -n team
```

강사는 관리자 권한으로 대신 검사하는 것과 학생 본인 계정으로 실제 인증하는 것을 구분합니다. 학생의 실제 profile·Lens 연결까지 확인해야 접속 준비가 끝납니다.

## STEP 3. 한 번의 배포를 끝까지 추적하기 (15분)

강사가 코드 main의 응답 한 곳을 바꾸고 배포합니다. 학생은 동시에 Lens를 열고 이 표를 채워 보세요. 팀별 main을 공유 예시 ECR에 동시에 올리지 않습니다.

| 관찰 위치 | 기록할 것 |
| --- | --- |
| GitHub Actions | 코드 변경 SHA, 테스트·빌드 성공 |
| 시드니 ECR | latest의 이전·새 digest |
| GitOps 브랜치 | Image Updater가 만든 커밋, kustomization의 변경 |
| Argo CD | 감지한 Git revision, OutOfSync→Synced, Progressing→Healthy |
| Lens | 이전·새 ReplicaSet, 새 Pod 이름, Ready·Events·로그 |
| 실제 API | 변경한 응답과 DB 저장·조회 결과 |

Spring Pod가 새로 만들어지는 동안 mysql-0의 이름·PVC가 유지되는지 봅니다. Pod가 잠깐 두 개가 되는 이유도 설명해 보세요. 새 Pod의 image와 imageID를 보되 멀티아키텍처 digest 차이를 구분합니다.

## STEP 4. 실패했을 때 멈춘 위치와 복구를 보기 (10분)

강사가 실패하는 수업용 이미지를 배포합니다. 학생은 Events와 로그에서 다음 구분을 찾아보세요.

| 위치 | 예시 실패 | 뒤 단계 |
| --- | --- | --- |
| CI | 테스트 실패 | 새 이미지를 올리지 않음 |
| ECR 감지 | Image Updater IAM·토큰 갱신 실패 | Git digest 변경 없음 |
| Git 쓰기 | 저장소 권한·브랜치 보호 | Argo는 기존 Git 상태 유지 |
| Argo Sync | 경로·YAML·AppProject 권한 오류 | 새 선언 적용 실패 |
| Pod 시작 | ImagePullBackOff·PVC Pending·Secret 없음 | 새 Pod Ready 실패 |
| 앱 실행 | DB 연결 실패·CrashLoopBackOff | rollout 정지·건강 이상 |
| 실제 기능 | 잘못된 API 응답 | Healthy여도 사용자 기능 실패 |

실패한 rollout이 자동으로 Git을 되돌려 주지는 않습니다. maxUnavailable:0으로 기존 Pod를 남기더라도 DB 변경까지 보호하는 것은 아닙니다.

강사는 먼저 Image Updater를 멈추고 GitOps의 잘못된 digest 커밋을 Revert해 push합니다. Argo CD가 정상 이미지를 다시 적용하는지 봅니다. latest가 아직 실패 이미지인데 updater를 켜 두면 방금 되돌린 설정이 다시 실패 이미지로 바뀔 수 있기 때문입니다.

정상 코드로 main을 복구해 ECR latest도 정상으로 만든 뒤 updater를 재개합니다. 코드 Revert→정상 이미지 재빌드 방식도 지난주와 연결됩니다. kubectl rollout undo만으로 끝내면 selfHeal이 Git의 설정을 다시 적용할 수 있습니다. DB 스키마·데이터 복원은 별도 절차입니다.

---

# 팀별 공유

팀당 2분 안에 다음 세 가지를 설명해 보세요.

1. ECR 변경을 누가 감지했고, Git에는 무엇이 남았나요.
2. Argo CD가 바꾼 리소스와 Kubernetes가 만든 리소스는 각각 무엇인가요.
3. 우리 계정은 어디까지 볼 수 있고, 배포 실패는 어느 단계에서 멈췄나요.

# 오늘 남길 문장

**CI는 검사한 이미지를 만들고, Image Updater는 ECR 변화를 Git에 기록하고, Argo CD는 Git의 상태를 Kubernetes에 맞춥니다.**

**Synced·Healthy·실제 기능 정상은 각각 확인해야 합니다. 앱 복구와 데이터 복구도 구분해야 합니다.**

강사용 설치 부록에는 실제 순서대로 namespace, EBS, MySQL, Spring, 관리자 Secret, ECR 인증, Git write-back, Lens 권한을 만드는 명령과 전체 배포 파일 위치를 정리했습니다.

# 준비·검증 상태

이 자료는 시드니 classroom-main 구축을 위한 강의 초안입니다. 실제 클러스터 주소·Lens 접속·배포 커밋·암호 저장 완료 여부는 구축 후 검증 기록에서 확인합니다. 준비 파일이 존재하는 것과 실제로 배포된 것은 구분합니다.
