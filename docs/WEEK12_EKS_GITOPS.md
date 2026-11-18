# 12주차 - 서버 설정 및 배포 (CD-2): EKS·Argo CD·GitOps

## 오늘은 서버가 바뀌는 순간을 봅니다

코드를 수정해 `main`에 반영한 뒤 Argo CD와 Lens를 열어 봅시다. 새 Spring Pod가 하나 생기고, 준비가 끝나면 기존 Pod가 내려갑니다. 그동안 같은 주소로 요청을 보내 서비스가 계속 응답하는지 확인합니다.

1. GitHub 배포 설정과 Lens 접속을 등록합니다.
2. 버전 표시를 바꾸고 `dev`에서 확인한 뒤 `main`에 반영합니다.
3. **기존 Pod 1개 → 기존·새 Pod 2개 → 새 Pod 1개**를 직접 봅니다.
4. 배포하는 동안 health 응답을 확인하고, 새 버전의 화면을 엽니다.

## 1. 우리 서버는 지금 어떻게 나뉘어 있을까

9주차의 Spring Boot 프로젝트를 그대로 사용합니다. 코드가 올라간 브랜치에 따라 실행하는 곳이 달라집니다.

| 구분 | dev | main |
| --- | --- | --- |
| 용도 | 개발한 내용을 먼저 확인 | 확인한 내용을 최종 반영 |
| 이미지 보관 | `docker.minq.live` | AWS ECR |
| 서버 실행 | Lightsail의 Docker Compose | EKS의 Kubernetes |
| 배포 연결 | GitHub Actions가 배포 요청 | Image Updater → Git → Argo CD |
| 확인할 곳 | 팀별 웹 주소 | Argo CD, Lens, health 응답 |

dev 예시 주소는 **https://daelim.minq.live/example/** 입니다. 팀별 주소는 `/team1/`부터 `/team8/`까지 있습니다.

main은 시드니의 EKS 클러스터 **classroom-main**에서 실행합니다. 이번에는 **team**을 공통 실습 공간으로 사용합니다.

| EKS 안의 공간 | 들어 있는 것 |
| --- | --- |
| `team` | Spring Pod 1개, MySQL Pod 1개 |
| `team1` ~ `team8` | 팀별로 나눈 공간 |
| `argocd` | Argo CD와 Image Updater |

이 공간을 **namespace**라고 부릅니다. Lens에서는 먼저 `team`을 선택하세요. 여기서 이번 배포를 함께 봅니다. dev와 main의 MySQL은 각각 따로 사용합니다.

## 2. Kubernetes는 무엇을 해 줄까

Compose에서 컨테이너를 실행했던 것처럼 Kubernetes도 서버 프로그램을 실행합니다. 여기에 **몇 개를 유지할지, 새 버전으로 어떻게 바꿀지, 어디로 요청을 보낼지**를 함께 적을 수 있습니다.

| 이름 | 우리 예제에서 하는 일 |
| --- | --- |
| 클러스터 | Kubernetes가 관리하는 서버들의 묶음. 이름은 `classroom-main` |
| Node | Pod가 실제로 실행되는 컴퓨터 |
| Pod | Spring 같은 프로그램이 실행되는 자리 |
| Deployment | Spring Pod를 1개 유지하고 새 버전으로 교체하는 설정 |
| Service | 준비된 Spring Pod로 요청을 보내는 고정된 연결 창구 |

AWS가 Kubernetes의 관리 부분을 운영해 주는 서비스가 **EKS**입니다. 우리는 EKS 안에 Spring과 MySQL을 올려 사용합니다.

Spring Pod 이름이 바뀌어도 Service 이름은 `spring`으로 유지됩니다. 요청을 보내는 쪽은 새 Pod 이름을 알아서 바꿀 필요가 없습니다.

### 새 버전이 켜진 뒤 기존 버전을 끄기

| 순서 | 기존 Spring Pod | 새 Spring Pod | 요청을 받는 곳 |
| --- | --- | --- | --- |
| 배포 전 | Ready 1/1 | 아직 없음 | 기존 Pod |
| 새 버전 시작 | Ready 1/1 | 준비 중 0/1 | 기존 Pod |
| 새 버전 준비 완료 | Ready 1/1 | Ready 1/1 | 준비된 Pod들 |
| 교체 완료 | Terminating → 사라짐 | Ready 1/1 | 새 Pod |

이렇게 조금씩 교체하는 방식을 **롤링 업데이트**라고 부릅니다. 교체 중에는 Spring Pod가 잠시 2개가 됩니다. MySQL Pod는 그대로 있습니다.

**파일:** [deploy/classroom-eks/apps/team/spring.yaml](https://github.com/MinQDU014/idea-support-server/blob/main/deploy/classroom-eks/apps/team/spring.yaml)

**브랜치:** `main`

**설정 위치:** `kind: Deployment`에 속한 최상위 `spec` 안입니다. 아래 코드는 그 `spec` 내부에서 롤링 업데이트에 필요한 부분을 발췌한 것입니다.

이 파일은 Argo CD가 Git에서 읽어 EKS의 Kubernetes API에 등록합니다. Deployment 컨트롤러가 이 설정을 보고 Spring Pod를 만들고 교체합니다.

```yaml
replicas: 1
minReadySeconds: 10
strategy:
  type: RollingUpdate
  rollingUpdate:
    maxSurge: 1
    maxUnavailable: 0
```

- `replicas: 1` — 평소 Spring Pod 1개를 유지합니다.
- `maxSurge: 1` — 교체할 때 새 Pod를 1개 더 띄웁니다.
- `maxUnavailable: 0` — 교체 중에도 필요한 1개를 사용할 수 있게 유지합니다.
- `minReadySeconds: 10` — 새 Pod가 Ready 상태로 10초 유지된 뒤 교체를 진행합니다.

### Running과 Ready 읽기

Spring은 실행을 시작한 뒤 DB 연결 등 기동 과정을 거칩니다. Kubernetes는 `/common/health`에 요청을 보내 HTTP **200**이 오는지 확인합니다. 이 검사가 **readinessProbe**입니다.

**파일:** [deploy/classroom-eks/apps/team/spring.yaml](https://github.com/MinQDU014/idea-support-server/blob/main/deploy/classroom-eks/apps/team/spring.yaml)

**브랜치:** `main`

**설정 위치:** `Deployment.spec.template.spec.containers`에서 `name: spring`인 컨테이너 안의 `readinessProbe`입니다.

```yaml
readinessProbe:
  httpGet:
    path: /common/health
    port: http
  periodSeconds: 5
```

우리 health API는 정상일 때 `status: "ok"`, `database: "up"`을 응답합니다. Lens의 **Running**은 실행 중이라는 뜻이고, **Ready 1/1**은 요청을 받을 준비까지 됐다는 뜻입니다.

[Kubernetes 롤링 업데이트](https://kubernetes.io/docs/concepts/workloads/controllers/deployment/) · [준비 상태 검사](https://kubernetes.io/docs/concepts/workloads/pods/probes/)

### 이 YAML은 누가 읽고 어디에 적용할까

`spring.yaml`은 **Spring 서버를 어떤 모습으로 실행할지 적은 Kubernetes 설정 파일**입니다. GitHub에는 파일로 보관되고, Argo CD가 읽어 EKS에 적용합니다. Spring 프로그램이 이 파일을 읽는 구조가 아닙니다.

한 파일 안에 `---`로 구분한 두 문서가 있습니다.

| spring.yaml의 문서 | EKS에 만들어지는 리소스 | 하는 일 |
| --- | --- | --- |
| `kind: Deployment`, 이름 `spring` | Spring Deployment | 실행할 이미지, 유지할 Pod 수, 교체 순서, 준비 상태 검사 설정 |
| `kind: Service`, 이름 `spring` | Spring Service | `app: spring` 표시가 붙은 준비된 Pod로 요청 연결 |

`apiVersion`은 Kubernetes API의 규격, `kind`는 만들 리소스 종류, `metadata.name`은 리소스 이름입니다. `spec`에는 그 리소스가 유지해야 할 상태를 적습니다. 그래서 `replicas: 1`은 Kubernetes에 “Spring Pod가 1개 실행되는 상태를 유지해 줘”라고 전달하는 설정입니다.

이 파일이 EKS까지 전달되는 순서를 실제 파일로 따라가 봅시다.

**1. Argo CD의 연결 설정** — [deploy/classroom-eks/argocd/application.yaml](https://github.com/MinQDU014/idea-support-server/blob/main/deploy/classroom-eks/argocd/application.yaml)

   이 파일을 등록해 만든 `classroom-team` Application이 이미 클러스터에 있습니다. Argo CD는 여기에 저장된 저장소·브랜치·폴더를 보고 Git을 계속 확인합니다.

   ```yaml
   spec:
     source:
       repoURL: git@github.com:MinQDU014/idea-support-server.git
       targetRevision: main
       path: deploy/classroom-eks/apps/team
     destination:
       server: https://kubernetes.default.svc
       namespace: team
   ```

   `targetRevision: main`은 읽을 브랜치, `path`는 읽을 폴더입니다. `destination`은 적용할 클러스터와 namespace입니다. Application 파일은 처음 연결할 때 등록하는 설정이고, 배포 때마다 확인하는 대상은 `path`에 적힌 폴더입니다.

**2. 그 폴더에서 묶을 파일 선택** — [deploy/classroom-eks/apps/team/kustomization.yaml](https://github.com/MinQDU014/idea-support-server/blob/main/deploy/classroom-eks/apps/team/kustomization.yaml)

   ```yaml
   apiVersion: kustomize.config.k8s.io/v1beta1
   kind: Kustomization
   namespace: team
   resources:
     - mysql.yaml
     - spring.yaml
   ```

   Argo CD는 이 파일을 보고 `mysql.yaml`과 `spring.yaml`을 함께 조합합니다. 파일 이름이 `spring.yaml`이라서 자동 실행되는 것이 아니라, `resources` 목록에 이 파일이 들어 있기 때문에 읽힙니다.

   실제 파일 아래쪽의 `images.digest`에는 사용할 이미지의 고유 번호도 들어 있습니다. Kustomize가 이 값을 Spring Deployment의 이미지에 반영해 최종 YAML을 만듭니다.

**3. Kubernetes API에 등록** — Argo CD가 최종 YAML을 EKS의 Kubernetes API에 전달합니다. API 서버는 `kind: Deployment` 문서를 Spring Deployment로, `kind: Service` 문서를 Spring Service로 저장합니다.

**4. Pod 만들기** — Deployment 컨트롤러가 현재 Pod와 설정을 비교합니다. 새 이미지가 들어간 Pod 설정이 생기면 새 ReplicaSet을 만들고, ReplicaSet 컨트롤러가 새 Pod를 만듭니다. 스케줄러가 실행할 Node를 고르면 그 Node의 kubelet이 이미지를 받아 Spring을 시작합니다.

**5. 새 Pod로 요청 연결하기** — `/common/health` 검사에 통과한 새 Pod가 Ready가 되면 Service의 연결 대상에 들어갑니다. 새 Pod가 Ready 상태를 10초 유지하면 Deployment가 기존 ReplicaSet의 Pod 수를 줄이고 기존 Pod가 종료됩니다.

Spring의 새 이미지가 바뀌어도 MySQL StatefulSet의 설정은 그대로여서 MySQL Pod와 저장 공간은 계속 사용합니다.

### Argo CD가 조합한 YAML을 직접 보기

**실행 위치:** 저장소를 내려받은 PC의 PowerShell, `gradlew`가 있는 프로젝트 최상위 폴더입니다.

```powershell
git switch main
git pull --ff-only origin main
kubectl kustomize deploy/classroom-eks/apps/team
```

이 명령은 Argo CD가 조합하는 최종 YAML을 출력합니다. 출력에서 `kind: Deployment`, `namespace: team`, `replicas: 1`, `image:`를 찾아보세요. `spring.yaml`의 이미지 이름에 `kustomization.yaml`의 digest가 반영된 모습을 볼 수 있습니다.

### 설정을 바꾸면 무엇이 달라질까

| 바꾼 곳 | main에 반영한 뒤 일어나는 일 |
| --- | --- |
| Spring 소스 코드 | GitHub Actions가 새 이미지 생성 → ECR 업로드 → 이미지 번호 갱신 → 새 Pod로 교체 |
| `spring.yaml`의 `replicas` | Argo CD가 Pod 수 설정 적용 → Deployment가 필요한 Pod 수 조정 |
| `spring.yaml`의 교체·readiness 설정 | Argo CD가 설정 적용 → 이후 Pod 교체·준비 상태 검사에 사용 |
| `kustomization.yaml`의 `images.digest` | 최종 Deployment의 이미지가 변경 → 새 ReplicaSet과 새 Pod 생성 |


## 3. Argo CD는 무엇을 보고 배포할까

Argo CD는 Git의 배포 설정과 EKS의 현재 상태를 비교하고, 차이가 생기면 그 설정을 적용합니다. Git을 기준으로 배포하는 이 방식을 **GitOps**라고 부릅니다.


### main에 코드를 올린 뒤 새 Pod가 생기기까지

이번 구성은 **코드와 배포 YAML을 모두 main에서 관리**합니다. 실행 주체는 다음처럼 나뉩니다.

| 읽는 도구 | 읽는 파일·대상 | 만드는 결과 |
| --- | --- | --- |
| GitHub Actions | `.github/workflows/deploy.yaml`과 Spring 소스 | 테스트한 앱 이미지 → ECR |
| Image Updater | ECR의 `latest`와 `argocd/image-updater.yaml`로 등록한 설정 | `main`의 `kustomization.yaml`에 새 digest 커밋 |
| Argo CD | Application에 등록된 `main`의 `apps/team` 폴더 | 조합한 Deployment·Service·StatefulSet 설정을 EKS에 적용 |
| Kubernetes 컨트롤러 | API 서버에 등록된 리소스 설정 | Pod 생성·준비 상태 확인·기존 Pod 종료 |

```text
main의 Spring 코드 변경
  → GitHub Actions가 새 이미지 생성
  → ECR의 latest가 새 이미지로 변경
  → Image Updater가 새 digest를 main에 커밋
  → Argo CD가 main의 apps/team 폴더를 다시 조합
  → 최종 Deployment의 image 값 변경
  → 새 ReplicaSet과 Pod 생성
  → Ready 확인, 10초 유지
  → 기존 Pod 종료
```

**왜 Image Updater의 커밋에서 빌드가 다시 돌지 않을까?** `.github/workflows/deploy.yaml`에 `deploy/classroom-eks/**`와 `docs/**`의 변경만 있는 경우를 제외하도록 설정했습니다. 따라서 새 digest를 기록한 커밋은 Argo CD가 읽고, Spring 코드가 포함된 커밋은 GitHub Actions가 검사·빌드합니다.

예전에는 코드 `main`과 배포 설정 `codex/classroom-gitops`를 분리했습니다. 이는 자동 이미지 커밋을 코드 빌드와 나누는 구성 방법 중 하나입니다. 이번 수업에서는 파일을 찾고 변경 과정을 따라가기 쉽도록 main으로 통합했습니다.


### Argo CD 화면에서 읽을 두 가지

| 표시 | 뜻 |
| --- | --- |
| `OutOfSync` | Git 설정과 서버 설정에 차이가 있음 |
| `Synced` | Git 설정이 서버에 적용됨 |
| `Progressing` | 새 Pod 등을 준비하는 중 |
| `Healthy` | 앱 리소스가 정상 상태 |

실습에서는 **Synced + Healthy**를 확인한 뒤 새 버전 화면과 health 응답까지 열어 봅니다.

[Argo CD 자동 동기화](https://argo-cd.readthedocs.io/en/stable/user-guide/auto_sync/) · [Image Updater의 Git 기록](https://argocd-image-updater.readthedocs.io/en/stable/basics/update-methods/)

## 4. GitHub workflow에서 읽을 부분

workflow는 GitHub가 자동으로 실행할 순서를 적은 파일입니다. main 배포 파일은 **.github/workflows/deploy.yaml**입니다.

[현재 main의 deploy.yaml 열기](https://github.com/MinQDU014/idea-support-server/blob/main/.github/workflows/deploy.yaml)

| 설정 | 읽는 방법 |
| --- | --- |
| `pull_request`, 대상 `main` | main으로 보낼 PR에서 먼저 검사 |
| `push`, 대상 `main` | main에 코드가 반영되면 실행 |
| `paths-ignore` | 배포 YAML·문서만 바뀐 커밋에서는 이미지 빌드 생략 |
| `test` | MySQL을 준비하고 코드 검사·테스트 |
| `needs: test` | 테스트가 성공해야 다음 작업 시작 |
| `if: github.event_name == 'push'` | PR에서는 검사하고, 반영된 코드로 이미지 업로드 |
| `configure-aws-credentials` | GitHub Secrets의 키로 ECR에 연결 |
| `./gradlew jib ...` | 실행할 이미지를 만들어 ECR에 업로드 |

**파일:** `.github/workflows/deploy.yaml` · **브랜치:** `main` · **위치:** `jobs.build_and_push.steps`의 `Build and Push Image with Jib` 단계입니다. 아래 명령은 백엔드 프로젝트 최상위, 즉 `gradlew`가 있는 폴더에서 실행합니다.

```bash
./gradlew jib -PprojectDataImageTargetEnv=prod
```

현재 파일에는 여기에 Git 커밋 번호도 이미지 태그와 라벨로 남기도록 설정돼 있습니다. **GitHub Actions에서 이미지 업로드를 보고, Argo CD와 Lens에서 서버 교체를 봅니다.**

## 5. 실습 연결하기 — team 예제

### ① GitHub에 배포용 키 등록하기

저장소의 **Settings → Secrets and variables → Actions → New repository secret**에서 두 항목을 등록합니다.

| 이름 | 넣을 값 |
| --- | --- |
| `AWS_ACCESS_KEY_ID` | 이미지 업로드용으로 전달받은 Access Key ID |
| `AWS_SECRET_ACCESS_KEY` | 그 키의 Secret Access Key |

`deploy.yaml`의 리전은 `ap-southeast-2`, ECR 저장소 이름은 `idea-support-server`입니다. `team` 예제에서는 이 ECR과 공통 예제 저장소를 한 세트로 연결합니다. 팀별 배포는 한 번에 한 팀씩 순서대로 진행합니다.

GitHub에 등록하는 업로드용 키와 아래의 Lens 조회용 키는 역할이 다릅니다. 키는 각각 안내받은 위치에 입력합니다.

### ② Lens에 EKS 등록하기

PC에 **AWS CLI, kubectl, Lens**를 설치하고 PowerShell을 엽니다. **실행 위치: Windows PowerShell, 어느 폴더에서나 실행합니다.** 아래는 팀1의 예제입니다. 다른 팀은 profile 이름의 팀 번호를 바꾸세요.

```powershell
aws configure --profile classroom-team1
```

Access Key ID와 Secret Access Key에는 **자기 팀의 조회용 키**를 입력합니다. 기본 리전은 `ap-southeast-2`, 출력 형식은 `json`입니다.

```powershell
aws eks update-kubeconfig --region ap-southeast-2 --name classroom-main --alias classroom-team1 --profile classroom-team1
kubectl --context classroom-team1 get pods -n team
```

Lens에서 **Local Kubeconfigs → Add kubeconfig → Sync file(s)**를 선택하고 `%USERPROFILE%\.kube\config`를 등록합니다. `classroom-team1`에 연결한 뒤 namespace를 **team**으로 고릅니다.

**Lens에서 볼 공간을 고르기**

| namespace | Pods | Workloads → Deployments |
| --- | --- | --- |
| `team` | MySQL과 Spring | `spring` |
| `argocd` | Argo CD와 Image Updater | `argocd-server`, `argocd-repo-server`, `argocd-redis`, Image Updater 등 |
| 본인 `team1`~`team8` | 아직 앱을 올리지 않은 공간 | 비어 있음 |

`argocd-application-controller`는 **StatefulSets**에서 볼 수 있습니다. 사용하지 않는 `argocd-applicationset-controller`는 Pod 수가 0입니다. 학생 IAM `team1`~`team8`은 같은 수업 조회 권한을 사용합니다. 권한이 반영되기 전부터 Lens를 열어 두었다면 연결을 끊었다가 다시 연결하고 namespace를 다시 선택하세요.


**Workloads → Pods**에서 `mysql-0`과 `spring-...`이 보이면 연결된 것입니다. 배포 전 Spring Pod 이름을 적어 두세요.

### ③ Lens로 Argo CD 열고 로그인하기

**접속 주소: https://localhost:18080/**

이 주소는 각자 PC에서 여는 주소입니다. 같은 번호를 사용해도 학생마다 자기 PC의 포트로 연결됩니다. Lens에 연결한 `classroom-team1`과 Argo CD 로그인 계정은 서로 다른 로그인입니다.

1. Lens에서 자기 `classroom-team1` 클러스터를 엽니다. 다른 팀은 자기 팀 번호를 사용합니다.
2. **Workloads → Pods**에서 namespace를 **argocd**로 고릅니다.
3. 이름이 **argocd-server-…**인 Pod를 열고 **Running, Ready 1/1**인지 확인합니다. Pod 이름 뒤의 번호는 서버가 교체되면 달라집니다.
4. 오른쪽 상세 패널의 **Containers → server → Ports**로 내려갑니다.
5. **server:8080/TCP** 줄 옆의 **Forward…**를 누릅니다. `metrics:8083/TCP`는 상태 수집용 포트입니다.
6. 아래 표대로 입력한 뒤 **Start**를 누릅니다.

| Lens 항목 | 입력·선택 |
| --- | --- |
| 대상 Pod | `argocd-server-…` |
| 대상 컨테이너 포트 | `server:8080/TCP` |
| Local port to forward from | `18080` |
| https | 선택 |
| Open in Browser | 선택 |

브라우저 주소창에서 **https://localhost:18080/**를 확인합니다. `Random`을 그대로 두거나 `http://localhost:0/` 주소를 사용하지 않습니다.

Argo CD는 수업 서버에서 만든 자체 서명 인증서를 사용합니다. Chrome에서 인증서 안내가 나오면 수업 서버에 연결한 `https://localhost:18080/` 주소인지 확인한 뒤 안내에 따라 직접 진행합니다.

Lens에서 **Config → Secrets**를 열고 namespace를 **argocd-login**으로 고릅니다. `argocd-admin-credentials`를 열어 `username`, `password` 값을 표시합니다. `team1`~`team8` 모두 자기 IAM 연결에서 확인할 수 있습니다. 목록이 비어 있으면 namespace가 `argocd-login`인지 확인하고 수업 클러스터를 다시 연결합니다.

Argo CD 로그인 화면에 확인한 값을 입력하고 **SIGN IN**을 누릅니다.

| 항목 | 입력할 값 |
| --- | --- |
| Username | `admin` |
| Password | Lens의 `argocd-login/argocd-admin-credentials`에서 확인한 `password` |

로그인하면 **Applications → classroom-team**을 엽니다. **Synced + Healthy**와 리소스 트리의 `spring`, `mysql`을 확인합니다. 이번 실습은 main에 코드를 반영한 뒤 이 화면에서 새 Pod가 준비되고 기존 Pod가 종료되는 과정을 관찰합니다.

| Application 항목 | team 예제 |
| --- | --- |
| Repository | `MinQDU014/idea-support-server` |
| 배포 설정 브랜치 | `main` |
| Path | `deploy/classroom-eks/apps/team` |
| Destination namespace | `team` |

**연결이 안 될 때 확인하기**

- `404 page not found`: Lens의 대상 포트가 `server:8080/TCP`인지 확인합니다.
- 포트 연결 시작 오류: 기존 `18080` 연결을 Stop/Remove한 뒤 다시 시작합니다. 포트가 필요한 다른 프로그램을 사용 중이면 다른 로컬 포트를 지정하고 주소의 번호도 함께 바꿉니다.
- 서버 Pod가 바뀐 뒤 접속 종료: 새 `argocd-server-…` Pod를 열어 다시 연결합니다. Lens가 이전 Pod 이름을 계속 보여 주면 해당 수업 클러스터를 Disconnect한 뒤 다시 연결합니다.
- 로그인 실패: Username은 `admin`, Password는 Lens에서 확인한 Argo CD용 비밀번호인지 확인합니다.

Lens를 닫거나 해당 포트 연결을 중지하면 이 주소의 연결도 끝납니다.

### ④ 내 PC에서 health 응답 열기

**실행 위치: Windows PowerShell, 어느 폴더에서나 실행합니다.** 이 창은 health를 확인하는 동안 켜 둡니다.

```powershell
kubectl --context classroom-team1 proxy --port=8001
```

브라우저에서 아래 주소를 열고 `status: "ok"`, `database: "up"`을 확인합니다.

**main health:** http://127.0.0.1:8001/api/v1/namespaces/team/services/spring:http/proxy/common/health

Argo CD 화면은 Lens의 `https://localhost:18080/`, health 응답은 위의 `8001` 주소를 사용합니다. health는 Service를 통해 연결하므로 Spring Pod가 교체되는 동안에도 같은 주소를 사용합니다.

## 6. 직접 배포해 보기

### ① 새 버전 표시 만들기

아래 파일을 추가합니다. 응답에 버전과 실행 중인 Pod 이름을 넣어 배포 전후를 구분해 봅시다.

**새로 만들 파일:** `src/main/kotlin/com/ideasupport/main/common/health/DeployDemoController.kt` · **작업 브랜치:** `dev`. 아래 코드가 이 파일의 전체 내용입니다.

```kotlin
package com.ideasupport.main.common.health

import org.springframework.web.bind.annotation.GetMapping
import org.springframework.web.bind.annotation.RestController

@RestController
class DeployDemoController {
	@GetMapping("/common/deploy-demo")
	fun version(): Map<String, String> =
		mapOf(
			"version" to "team-v1",
			"pod" to (System.getenv("HOSTNAME") ?: "local"),
		)
}
```

변경 내용을 dev에 반영합니다. **Actions → Dev Registry**가 성공하면 아래 주소를 엽니다.

**dev 버전 확인:** https://daelim.minq.live/example/common/deploy-demo

`version: "team-v1"`이 보이면 main에 반영할 준비가 됐습니다.

### ② 배포 전 화면 나란히 열기

**1. GitHub Actions** — 이번 커밋의 실행 결과
**2. Argo CD → classroom-team** — 배포 상태와 리소스 트리
**3. Lens → team → Pods** — Pod 이름, 생성 시간, Ready
**4. health 응답 창** — 배포 중에도 요청이 이어지는지 확인

**실행 위치: 새 Windows PowerShell 창, 어느 폴더에서나 실행합니다.** 아래 코드 전체를 붙여넣어 health 응답을 계속 확인합니다. `Ctrl+C`로 끝냅니다.

```powershell
$healthUrl = 'http://127.0.0.1:8001/api/v1/namespaces/team/services/spring:http/proxy/common/health'
while ($true) {
  try {
    $r = Invoke-RestMethod $healthUrl -TimeoutSec 3
    '{0}  status={1}  database={2}' -f (Get-Date -Format HH:mm:ss), $r.status, $r.database
  } catch {
    '{0}  응답 실패: {1}' -f (Get-Date -Format HH:mm:ss), $_.Exception.Message
  }
  Start-Sleep -Seconds 1
}
```

### ③ dev에서 main으로 반영하기

GitHub에서 **base: main / compare: dev**로 PR을 만듭니다. 검사 결과를 확인한 뒤 Merge합니다.

**Actions → Deploy**에서 `Lint and Test`와 `Build and Push Docker Image`가 차례로 성공하는지 봅니다. 이때 Argo CD와 Lens도 계속 열어 둡니다.

### ④ 새 Pod가 기존 Pod를 이어받는 순간 보기

Argo CD에서 `spring` Deployment 아래를 펼칩니다. 새 ReplicaSet과 새 Pod가 나타납니다. ReplicaSet은 같은 버전의 Pod를 묶어 관리하는 단위입니다.

Lens에서도 새 Pod 이름이 추가됩니다. **새 Pod의 Logs**를 열어 Spring이 시작되는 과정을 보고, Ready가 **0/1 → 1/1**로 바뀌는지 확인합니다.

새 Pod가 준비되는 동안 기존 Pod는 계속 응답합니다. 새 Pod가 Ready로 10초 유지되면 기존 Pod가 종료되기 시작합니다. 종료 처리가 끝나면 Spring Pod는 다시 1개가 됩니다.

| 내가 볼 순서 | 적어 둘 것 |
| --- | --- |
| 배포 전 | 기존 Spring Pod 이름 |
| 새 Pod 생성 | 새 Pod 이름, 생성 시간 |
| 새 Pod 준비 완료 | Ready 1/1이 된 시각 |
| 기존 Pod 종료 | Terminating이 보인 시각 |
| 배포 완료 | Argo CD의 Synced + Healthy |
| 서비스 확인 | 배포 중 health 응답, 새 버전과 Pod 이름 |

### ⑤ 같은 주소에서 새 버전 확인하기

아래 주소를 열고 `version: "team-v1"`이 표시되는지 확인합니다. `pod` 값은 Lens에 남아 있는 새 Spring Pod 이름과 비교합니다.

**main 버전 확인:** http://127.0.0.1:8001/api/v1/namespaces/team/services/spring:http/proxy/common/deploy-demo

한 번 더 배포해 봅시다. 코드의 `team-v1`을 `team-v2`로 바꾸고 같은 순서로 dev와 main에 반영합니다. 같은 주소의 version과 pod 값이 함께 바뀌는지 확인합니다.

health 기록에서도 기존 Pod가 사라지는 시간에 `status=ok`, `database=up`이 이어졌는지 확인합니다.

이번 접속은 **Service를 통해 요청**합니다. 특정 Pod에 연결을 고정하지 않아 새 Pod로 교체되는 동안 같은 주소를 사용합니다.

## 7. 배포가 끝난 뒤 설명해 보기

옆 사람에게 화면을 가리키며 다음 세 가지를 설명해 봅시다.

1. main에 Merge한 뒤 새 Pod가 생기기까지 어떤 순서로 움직였나요?
2. Pod를 하나만 쓰는데 배포 중에는 왜 두 개가 보였나요?
3. 기존 Pod가 내려가는 동안 누가 요청을 받았고, health 기록은 어땠나요?

## 8. dev부터 main까지 전체 구조

개발한 내용은 dev에서 먼저 실행해 보고, 확인한 코드를 main에 반영합니다. **이미지를 만드는 길**, **배포 설정이 바뀌는 길**, **사용자 요청이 들어가는 길**을 나눠 따라가 보세요.

[diagrams.net에서 시스템 아키텍처 열기 · 편집하기](https://app.diagrams.net/?splash=0#Uhttps%3A%2F%2Fraw.githubusercontent.com%2FMinQDU014%2Fidea-support-server%2Fcodex%2Fclassroom-eks-preparation%2Fdocs%2Farchitecture%2Fclassroom-system-architecture.drawio)

[편집 원본 .drawio](https://github.com/MinQDU014/idea-support-server/blob/codex/classroom-eks-preparation/docs/architecture/classroom-system-architecture.drawio) · [전체 구조 이미지 크게 보기](https://raw.githubusercontent.com/MinQDU014/idea-support-server/283d25f950c250598cb33b1a2ab32149bce4f544/docs/architecture/classroom-system-overview.png)

### dev · main 전체 시스템

![dev와 main 전체 시스템 아키텍처](https://raw.githubusercontent.com/MinQDU014/idea-support-server/283d25f950c250598cb33b1a2ab32149bce4f544/docs/architecture/classroom-system-overview.png)

### 배포 중 Pod가 교체되는 순서

![Spring Pod 1개에서 2개, 다시 1개가 되는 롤링 업데이트](https://raw.githubusercontent.com/MinQDU014/idea-support-server/283d25f950c250598cb33b1a2ab32149bce4f544/docs/architecture/classroom-rolling-update.png)

새 Pod의 health 응답과 Ready 상태를 확인한 뒤 기존 Pod가 종료됩니다. MySQL Pod와 EBS 데이터는 유지됩니다.

[그림 파일과 공식 아이콘 출처](https://github.com/MinQDU014/idea-support-server/blob/codex/classroom-eks-preparation/docs/architecture/README.md)

**코드를 확인하는 곳은 dev, 확인한 코드를 반영하는 곳은 main입니다. main의 새 버전은 기존 Pod가 응답하는 동안 준비되고, 준비된 새 Pod가 서비스를 이어받습니다.**
