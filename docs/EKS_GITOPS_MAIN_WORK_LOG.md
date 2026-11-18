# 수업 배포 설정 main 통합 기록

## 2026-11-18 Lens에서 Argo CD 로그인 확인 진행

- Lens의 로컬 18080 접속과 학생 로그인까지 확인한다. 이전 작업은 TCP 연결과 HTTP 307 응답까지만 확인했다.
- 현재 server.basehref가 Kubernetes Service proxy 경로여서 직접 포트 연결의 UI 경로와 맞지 않는다. 기본 경로 /로 바꾸고 Argo CD 서버에 적용한다.
- Argo CD 서버가 재생성되면 현재 서버 Pod에 한정한 학생 포트 연결 권한을 갱신한다. Spring·MySQL Pod와 PVC는 전후 상태를 대조한다.
- 최종 접속 주소, Lens의 서버 포트 선택과 로그인 순서를 실제 화면으로 확인한 뒤 학생 강의에 반영한다.

## 2026-11-18 변경

- 학생이 main에서 실제 배포 파일을 찾아 배포 동작을 추적하도록 앱 정의와 설치 구성, 연결 설정을 main에 모은다.
- Argo Application → Kustomize → Kubernetes API → Deployment·ReplicaSet → Pod의 동작을 강의에 추가한다. Spring 프로그램과 GitHub가 임의의 YAML을 자동 실행하는 것으로 설명하지 않는다.
- 앱 source·이미지·DB 설정을 유지한 채 GitOps 읽기·쓰기 브랜치를 main으로 전환한다.
- CI의 경로 제외 조건으로 매니페스트·문서만 변경된 커밋의 이미지 빌드를 막는다.

## 확인할 것

- 기존 GitOps 정의와 main의 앱 정의를 kustomize로 렌더했을 때 동일한지.
- 코드 변경은 CI 대상, 배포 정의·문서만 변경한 경우는 제외되는지.
- live Application과 Image Updater가 main을 사용하고 Synced·Healthy인지.
- Spring·MySQL Pod UID와 PVC가 전환 전후 유지되는지.

업데이트 위치: main의 deploy/classroom-eks/apps/team, argocd, .github/workflows/deploy.yaml, docs/WEEK12_EKS_GITOPS.md 및 프로젝트관리지원기술 Notion CD-2.

## 2026-11-18 적용 결과

- PR #4로 배포 정의·연결 설정·설치 파일·학생 설명을 main에 통합했다.
- live Argo Application의 읽기 브랜치와 Image Updater의 Git 기록 브랜치를 main으로 전환했다. Synced·Healthy와 Image Updater Ready를 확인했다.
- 전환 전후 Spring·MySQL Pod와 PVC의 식별자가 유지됐다. 앱 이미지와 DB 설정은 변경하지 않았다.
- 기존 정의와 main 정의의 Kustomize 결과가 같은 4개 리소스임을 확인했다. 앱 변경과 배포 정의·문서 변경에 대한 CI 경로 조건을 확인했다.
- 학생 IAM team1~team8의 EKS Access Entry가 각 classroom:teamN 그룹에 연결됨을 확인했다.
- argocd namespace의 관찰용 Role과 8개 그룹의 RoleBinding을 적용했다. 실제 team1 인증으로 Pod·Deployment 조회를 확인했고, 8개 그룹별로 Pod·Deployment·로그 허용 및 Secret·삭제 거부를 확인했다.
- 권한 정의는 templates/platform/argocd-observer.yaml에 보관한다. AWS 관리자 정책이나 공용 관리자 키는 추가하지 않았다.
- 세부 실행 결과는 로컬·비공개 설치 부록에서 관리한다.

## 2026-11-18 Lens 포트 연결

- 사용자가 학생 8개 계정의 Argo CD 서버 Pod 포트 연결을 명시적으로 승인했다.
- grant-argocd-portforward.py는 현재 Argo CD 서버 Pod 이름을 찾아 해당 Pod의 get/create pods/portforward만 허용한다. 다른 Pod와 DB는 포함하지 않는다.
- 갱신한 수업 관리자 세션으로 Role과 RoleBinding을 적용했다. 8개 그룹의 인가 확인과 실제 team1 인증의 로컬 18080 연결을 통과했다. Argo CD 서버의 HTTP 307 HTTPS 응답을 확인했다.
- 기존 8080 포트 점유도 발견했다. 다른 프로세스를 종료하지 않고 18080을 사용했다.
- 전체 namespace의 workload 조회 제안은 자동 승인 검토에서 차단되어 적용하지 않았다. 실제 배포 정의는 존재하며 namespace별 조회는 허용돼 있다.

## 2026-11-18 Lens 전체 배포 목록 조회 승인·적용

- 앞서 차단된 전체 namespace 조회에 대해 사용자가 team1~team8의 Deployment·StatefulSet·ReplicaSet·DaemonSet 조회를 명시적으로 승인했다.
- platform/workload-catalog.yaml을 적용했다. get/list/watch만 있으며 Secret·생성·수정·삭제 규칙은 없다.
- 실제 team1 인증으로 전체 Deployment·StatefulSet 목록을 확인했다. Lens의 argocd 필터에서도 Argo CD Deployment 5개가 표시됐다. Spring은 team의 Deployment이고 MySQL·Argo application-controller는 StatefulSet이다.
- Notion 본문은 main의 실제 파일 연결과 YAML → Kubernetes API → 컨트롤러 → Pod 과정을 설명하도록 다시 저장했다. 기존 아키텍처 이미지 두 개를 보존하고 중복 섹션이 없음을 다시 읽어 확인했다.

## 2026-11-18 직접 접속 경로 수정 결과

- Argo CD Helm chart 10.18.0을 같은 버전으로 갱신했다. 아래 후속 점검에서 실행 명령의 점 포함 키가 중첩 키로 전달되어 실제 ConfigMap에는 이전 경로가 남았음을 확인했다.
- Argo CD 구성요소 갱신 후 현재 서버 Pod 이름으로 기존 승인된 학생 포트 연결 Role을 갱신했다. Spring·MySQL Pod 및 PVC의 UID는 전후 동일했다.
- 실제 team1 AWS 인증의 임시 18081 연결에서 서버 인증서를 신뢰 대상으로 검증했다. / 화면과 JavaScript 파일은 HTTP 200, students 로그인과 classroom-team 조회도 성공했고 Synced·Healthy였다.
- 임시 연결은 종료했다. 비밀번호·JWT는 출력하거나 평문 파일로 보관하지 않았다.
- Windows 창 활성화·화면 캡처가 실패해 Lens 18080과 실제 브라우저 로그인은 아직 대기 중이다. API 점검과 UI 검증을 구분한다. 학생 안내는 실제 UI 결과를 확인한 뒤 Notion에 반영한다.

## 2026-11-18 웹 파일 경로 수정·관리자 Secret 정리

- 브라우저 오류에 남은 Service proxy 경로와 live ConfigMap·Helm 값을 대조했다. 이전 명령은 점을 포함한 `server.basehref` 대신 중첩된 `server.basehref` 구조를 생성했다. 기본 HTML과 일부 파일의 응답만으로 정상이라고 판단했던 검증을 정정한다.
- 기존 Helm 설정을 보존하고 `configs.params`의 리터럴 키 `server.basehref`를 `/`로 적용했다. 잘못 생성된 중첩 `server` 키를 제거하고 ConfigMap과 Helm 저장값을 각각 확인했다. 서버 교체 후 기존 승인 범위의 학생 포트 연결 권한을 새 서버 Pod로 갱신했다.
- 사용자가 데스크톱 제어 중단을 요청해 화면·마우스·키보드를 조작하지 않았다. 사용 중인 로컬 주소를 유지하도록 학생 인증의 백그라운드 Service 포트 연결을 열었다. 이 연결은 Lens UI에서 생성한 연결로 기록하지 않는다.
- 브라우저와 같은 요청 헤더로 받은 HTML에 이전 경로가 없는지 확인했다. runtime·vendors·main·extensions JavaScript 및 fonts.css가 모두 200과 올바른 Content-Type을 반환했다. 관리자 세션 생성·사용자 확인·앱 조회·Deployment/StatefulSet 리소스 트리 조회를 통과했고 앱은 Synced·Healthy였다. 실제 브라우저 화면 조작 검증은 수행하지 않았다.
- 사용자 요청에 따라 관리자 보관용 Secret의 `username=admin`과 `password` 키를 확인하고 학생 보관용 Secret을 삭제했다. 학생 로그인 계정과 로그인 검증용 해시는 유지했다. 설치 스크립트도 관리자 보관용 Secret만 생성하도록 수정했다.
- 기본 kubeconfig에 `classroom-main-admin`과 namespace `argocd`를 추가했다. 기존 현재 연결은 바꾸지 않았고 관리자 연결로 해당 Secret 조회가 되는지 확인했다. 학생의 Secret 권한은 추가하지 않았다.
- 접속 절 교체안은 로컬에 준비했다. Notion 연결 도구가 대상 페이지에 404를 반환하며, 데스크톱 제어 중단 요청에 따라 브라우저 편집을 하지 않았다. Notion 저장은 미완료다. 비밀번호·JWT·세부 검증 파일은 공개 저장소에 포함하지 않는다.

업데이트 위치: main의 deploy/classroom-eks/templates/argocd/values.yaml, bootstrap-secrets.py, README.md 및 docs/WEEK12_EKS_GITOPS.md. Notion 프로젝트관리지원기술 12주차 CD-2의 접속 절은 추가 반영이 필요하다.
