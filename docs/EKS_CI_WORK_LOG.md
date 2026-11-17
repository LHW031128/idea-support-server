# EKS CI 연결 기록

2026-11-15. 사용자가 기존 ECR과 같은 시드니 리전에서 classroom-main EKS와 Argo CD GitOps를 구축하도록 요청했다.

- 기존 deploy.yaml의 테스트 → Jib 업로드 두 job과 시드니 ECR 주소를 유지한다. 앱 코드·DB 구성은 변경하지 않는다.
- 같은 브랜치의 이전 실행은 취소해 늦게 끝난 과거 커밋이 latest를 되돌리는 일을 줄인다.
- latest와 함께 전체 Git SHA 태그를 남기고 OCI revision 라벨에도 SHA를 넣어 어떤 코드의 이미지인지 추적한다.
- Kubernetes 변경은 CI에서 실행하지 않는다. ECR을 읽는 Image Updater가 codex/classroom-gitops의 digest를 커밋하고 Argo CD가 배포한다.
- 실제 자격 증명은 기존 GitHub Secrets에서 읽는다. AWS 키·관리자 kubeconfig·GitOps 개인 키를 workflow에 추가하지 않는다.
- 같은 앱을 대상으로 로컬 ktlintCheck와 백엔드 테스트 189개가 통과했다. 이 PR의 Actions 결과와 main 병합 후 ECR→Git→Argo→Pod 검증은 이어 기록한다.

업데이트 위치: main의 .github/workflows/deploy.yaml, GitOps 브랜치의 deploy/classroom-eks/apps/team/kustomization.yaml, 준비 브랜치의 deploy/classroom-eks/WORK_LOG.md 및 Notion CD-2 강의.

## 2026-11-16 실제 완료

- PR #3 검사 통과 후 main에 병합했다. 실제 이미지 소스 커밋은 50f307ae35934a788d4e16b2d45d5d49659128f3이다.
- Actions 43726492461에서 테스트 189개·ECR 업로드가 성공했다. latest와 전체 SHA 태그의 digest는 sha256:f62e5ac2a10482483121adfc00257d4fc2a7c34bc6bed9347994ec1a5d666ab9다.
- Image Updater가 codex/classroom-gitops에 5f5cd1bdb98b44675db2862c392e0f55942f1c50을 자동 기록했고 Argo CD가 새 Spring Pod로 동기화했다. Synced·Healthy, 실제 API 200과 기존 DB 데이터 유지를 확인했다.
- 기존 team1 IAM 키로 EKS·Lens에서 team의 MySQL·Spring을 확인했고 다른 팀·Secret은 거절됐다. Argo 관리자와 학생 로그인은 성공했으며 학생 Sync 요청은 403이다.
- 공개 설치 구성·일반 강의 원본은 codex/classroom-eks-preparation에 있다. 실제 운영 검증 JSON은 사용자 승인에 따라 비공개 Notion 설치 부록 https://app.notion.com/p/419b4057395f81dab0d4d4246cc762b9 에만 첨부한다.
- 이 완료 기록은 skip ci 문서 커밋이다. 후속 문서 SHA를 실제 배포 이미지 소스 50f307a…와 혼동하지 않는다.


## 2026-11-18 main에 배포 정의 통합

- 배포 파일을 찾기 쉽도록 main의 deploy/classroom-eks/apps/team으로 통합하고, Application의 읽기 브랜치와 Image Updater의 쓰기 브랜치도 main에 맞춘다.
- deploy.yaml의 push·pull_request 경로 제외 조건에 deploy/classroom-eks/**와 docs/**를 추가한다. 배포 digest 자동 커밋에서 앱 이미지를 다시 만드는 순환을 끊는다.
- 기존 2026-11-16 검증 이력은 당시 별도 브랜치 구성의 기록으로 보존한다. 현재 구성의 설명과 갱신 위치는 main의 docs/WEEK12_EKS_GITOPS.md와 deploy/classroom-eks/README.md다.
