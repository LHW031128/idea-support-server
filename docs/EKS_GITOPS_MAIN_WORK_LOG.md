# 수업 배포 설정 main 통합 기록

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
