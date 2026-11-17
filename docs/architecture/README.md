# dev · main 수업 시스템 아키텍처

[diagrams.net에서 열기](https://app.diagrams.net/?splash=0#Uhttps%3A%2F%2Fraw.githubusercontent.com%2FMinQDU014%2Fidea-support-server%2Fcodex%2Fclassroom-eks-preparation%2Fdocs%2Farchitecture%2Fclassroom-system-architecture.drawio)

[프로젝트관리지원기술 12주차 CD-2](https://app.notion.com/p/project-2026-01/12-CD-2-EKS-Argo-CD-GitOps-62b9fa2a819d820da707017163701676)

## 그림

- `classroom-system-architecture.drawio`: diagrams.net에서 편집하는 원본. 전체 구조와 롤링 업데이트, 두 페이지가 들어 있다.
- `classroom-system-overview.png`: 전체 구조. diagrams.net에서 200% 배율로 내보낸 3684 × 2846 이미지.
- `classroom-rolling-update.png`: Spring Pod 1개 → 2개 → 1개 교체 순서. 3288 × 1578 이미지.

dev는 GitHub Actions → EC2의 Distribution Registry → Lightsail의 Docker Compose로 연결된다. main은 GitHub Actions → Amazon ECR → Argo CD Image Updater → GitOps 브랜치 커밋 → Argo CD → Amazon EKS로 연결된다. 파란색은 배포 설정, 주황색은 이미지, 초록색은 요청과 DB 연결, 회색 점선은 화면 조회를 뜻한다.

EKS는 ECR과 같은 시드니 리전의 `classroom-main`이다. `team`에서 Spring Deployment와 MySQL StatefulSet을 실행하고, MySQL 데이터는 EBS 볼륨과 PVC에 보관한다. Argo CD와 Image Updater는 `argocd` namespace에 있다. `team1`~`team8` namespace도 별도로 존재한다.

## 아이콘 출처

공식 배포 자산을 원본 비율로 넣었으며, 원본 파일에 이미지를 포함해 편집할 때도 표시된다.

- [AWS Architecture Icons](https://aws.amazon.com/architecture/icons/): 2026년 7월 패키지의 Amazon EC2, Amazon Lightsail, Amazon ECR, Amazon EKS, Amazon EBS, AWS IAM SVG.
- [CNCF Artwork](https://github.com/cncf/artwork): Argo, Kubernetes, Distribution 로고.
- [Kubernetes Community Icons](https://github.com/kubernetes/community/tree/main/icons): Pod, Service, Deployment 리소스 아이콘.
- [GitHub 공식 로고](https://github.githubassets.com/images/modules/logos_page/GitHub-Mark.png), [GitHub Actions 공식 조직 아이콘](https://avatars.githubusercontent.com/u/44036562?v=4).
- [Docker 공식 로고 패키지](https://www.docker.com/static/Docker-Logos-1.zip): docker-mark-ocean-blue.svg.
- [Spring Initializr 공식 아이콘](https://raw.githubusercontent.com/spring-io/start.spring.io/main/start-client/static/images/icon.svg).
- [MySQL 공식 로고](https://www.mysql.com/common/logos/logo-mysql-170x115.png).
- [Lens 공식 저장소 로고](https://raw.githubusercontent.com/lensapp/lens/master/docs/img/lens-logo-icon.svg).
- [Caddy 공식 로고](https://caddyserver.com/resources/images/logo-light.svg).
- [Lucide monitor](https://raw.githubusercontent.com/lucide-icons/lucide/main/icons/monitor.svg): 웹 브라우저를 보는 PC.

## 수정 위치

1. diagrams.net에서 원본을 열어 도형·아이콘·연결선을 수정한다.
2. 두 페이지를 각각 PNG, 배율 200%, 현재 페이지로 내보낸다.
3. 이 폴더의 `.drawio`와 두 PNG를 함께 갱신한다.
4. Notion CD-2의 마지막 `8. dev부터 main까지 전체 구조`에서 편집 링크와 이미지를 갱신한다.

## 작업 기록

- 2026-11-17: 강의의 Mermaid 구조도를 공식 제품 아이콘을 포함한 diagrams.net 원본으로 교체했다. 전체 구조와 Pod 교체 순서를 두 페이지로 나눴다. 실제 diagrams.net에서 두 페이지를 열고 PNG로 내보내 글자와 화살표를 확인했다.
- 공개 그림에는 비밀번호, AWS 키, 계정 번호, IAM ARN, 실제 배포 digest와 운영 증거 파일을 포함하지 않았다.
