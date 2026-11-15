# EKS CI 연결 기록

2026-11-15. 사용자가 기존 ECR과 같은 시드니 리전에서 classroom-main EKS와 Argo CD GitOps를 구축하도록 요청했다.

- 기존 deploy.yaml의 테스트 → Jib 업로드 두 job과 시드니 ECR 주소를 유지한다. 앱 코드·DB 구성은 변경하지 않는다.
- 같은 브랜치의 이전 실행은 취소해 늦게 끝난 과거 커밋이 latest를 되돌리는 일을 줄인다.
- latest와 함께 전체 Git SHA 태그를 남기고 OCI revision 라벨에도 SHA를 넣어 어떤 코드의 이미지인지 추적한다.
- Kubernetes 변경은 CI에서 실행하지 않는다. ECR을 읽는 Image Updater가 codex/classroom-gitops의 digest를 커밋하고 Argo CD가 배포한다.
- 실제 자격 증명은 기존 GitHub Secrets에서 읽는다. AWS 키·관리자 kubeconfig·GitOps 개인 키를 workflow에 추가하지 않는다.
- 같은 앱을 대상으로 로컬 ktlintCheck와 백엔드 테스트 189개가 통과했다. 이 PR의 Actions 결과와 main 병합 후 ECR→Git→Argo→Pod 검증은 이어 기록한다.

업데이트 위치: main의 .github/workflows/deploy.yaml, GitOps 브랜치의 deploy/classroom-eks/apps/team/kustomization.yaml, 준비 브랜치의 deploy/classroom-eks/WORK_LOG.md 및 Notion CD-2 강의.
