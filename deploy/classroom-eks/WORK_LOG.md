# EKS · Argo CD · GitOps 작업 기록

## 2026-11-15 준비와 실행 재개

- 사용자 범위: 서울 수업 계정의 `classroom-main`, namespace `team` 및 `team1`~`team8`, 앱·MySQL은 `team`만. Argo CD 관리자 암호는 Kubernetes Secret에 보관. ECR→Git→Argo CD→Pod 흐름과 Lens 접속을 Notion에 설명.
- 기존 source의 최근 커밋과 변경 Markdown을 확인했다. 기존 `deploy/dev-registry/index.html` 수정은 보존한다. 기존 시드니 Lightsail·Registry·학생 DB는 이전·삭제하지 않는다.
- 설치 템플릿, 공개 설정 생성기, Secret 초기화, 학생 Access Entry 도구와 강의 원본을 준비했다. 준비 상태를 배포 성공이라고 표시하지 않는다.
- 사용자 로그인 후 AWS 프로젝트 상세에서 **Rubber Ducking = 950177940921**, 소유자 대학 Builder ID를 직접 확인했다. classic 루트 계정과 혼동하지 않는다.
- 카드 등록·유료 플랜 전환 후의 Billing 화면을 확인했다. 아직 고급 기능의 관리 계정 이메일 입력·인증이 남아 있고, 서울 EKS 조회는 Organizations SCP explicit deny로 거절됐다. 사용자의 완료 답변 뒤 설정 화면 새로고침·서울 EKS 조회로 이 상태를 재확인했다.
- 고급 기능은 지출 한도를 삭제하는 되돌릴 수 없는 변경이므로 사용자에게 해당 화면을 열어 직접 완료하도록 요청했다. 그동안 문서와 배포 파일 검증을 계속한다.
- 최신 AWS CLI를 공식 서명 확인 후 작업 공간 `.local/tools/awscli`에만 추출했다. 기존 시스템 AWS CLI와 운영 프로필은 변경하지 않는다. 수업 CLI 설정·임시 인증은 `.local/aws-login`에 격리한다.
- AWS CLI 로그인 성공 후 STS로 계정 950177940921·AccountFullAccessRole을 확인했다. 서울 EKS의 ListClusters·DescribeClusterVersions는 여전히 SCP explicit deny다. 시드니에서는 지원 버전 조회와 기존 ECR latest 메타데이터 조회가 가능했다.
- 시드니 ECR의 기존 latest는 코드 6a23785…의 이미지다. 이것을 현재 dev 패키지의 배포 성공으로 간주하지 않는다. 서울 ECR 준비와 실제 시작 이미지 검증은 권한 해제 뒤 진행한다.
- 기존 IAM team1~team8을 읽기 전용으로 감사했다. 모두 ECR PowerUser 정책만 있으며 inline 정책·IAM 그룹은 없었다. 새 키를 생성하지 않고 기존 팀 키를 Lens 인증에 재사용하도록 안내를 맞췄다. EKS Access Entry/RBAC는 아직 적용하지 않았다.
- 정적 검사: 9개 namespace, team 전용 4개 workload/service 선언, immutable digest 고정, 팀별 예시+자기 namespace RoleBinding, 학생 Secret/exec/write 금지, ImageUpdater 1.4.0 공식 CRD 스키마, 잘못된 계정/리전/전체 인터넷 CIDR/digest 입력 거절, Python 구문 검사 통과.
- Helm 공식 차트의 존재를 확인하고 Argo CD 10.18.0(앱 3.6.1) 45개 리소스·Image Updater 1.4.2(앱 1.4.0) 9개 리소스를 렌더링했다. updater의 전역 ClusterRole 미생성·ServiceAccount·1분 주기·ECR 인증 스크립트를 확인했다.
- eksctl 검증에서 EBS CSI Pod Identity association의 namespace 필수 누락을 찾아 kube-system으로 수정했다. 이후 실제 서울 버전 조회에서 SCP에 막혀 eksctl 전체 dry-run은 미완료다. 이것을 생성 성공으로 기록하지 않는다.
- Notion 개인 초안: 강의 본문 https://app.notion.com/p/419b4057395f817bb96ad48b1e87c6dd , 설치 부록 https://app.notion.com/p/419b4057395f81dab0d4d4246cc762b9 . 상호 링크를 넣고 재조회로 저장을 확인했다.
- 계정 ID·IAM 구성이 포함된 공개 GitHub 업로드가 자동 승인 검토에서 차단됐다. 사용자에게 공개 범위를 설명했고 명시적 승인 후 `codex/classroom-eks-preparation`에 4d397f3…을 push해 원격 SHA를 검증했다. 비밀번호·AWS 키·실제 Secret 값·kubeconfig는 포함하지 않았다.

## 완료 판정과 갱신 위치

- 클러스터: 서울 STS 계정 확인, control plane ACTIVE·노드 Ready·EBS CSI/Pod Identity add-on 확인.
- GitOps: 정확한 코드 브랜치·GitOps 브랜치, ECR digest·Git 기록·Argo revision·실제 Pod·API 결과.
- 데이터: MySQL PVC Bound와 DB 쓰기·재기동 후 데이터 유지 확인.
- 권한: 학생 본인의 인증으로 예시/자기 팀 조회 가능, 다른 팀·Secret·쓰기 거절, 실제 Lens 연결.
- 설명: `docs/WEEK12_EKS_GITOPS.md`, 이 폴더 `README.md`, 개인 Notion 초안과 설치 부록.
- 실제 생성·배포 결과와 남은 제한은 이 문서에 누적한다. 연결된 기기에 설치하는 검사는 사용자 지시에 따라 수행하지 않는다.
