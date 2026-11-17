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
