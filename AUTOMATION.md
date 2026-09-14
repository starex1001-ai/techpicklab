# 자동발행 연결

기존 글·디자인·주소를 보존한 자동발행 지원 버전입니다. 원래 README의 미구현 안내는 이 파일과 중앙 자동발행 안내로 보완됩니다.

`python build.py`를 실행하면 `dist`가 생성됩니다. 중앙 자동발행기는 본문과 dist를 함께 GitHub에 커밋합니다. Cloudflare 기존 Worker의 Git 연결에서 빌드 명령은 비우고 배포 명령은 `npx wrangler deploy`를 사용하세요. 자산 경로는 `./dist`입니다.

기존 글은 자동발행으로 수정하지 않습니다. 기존 URL과 충돌하는 행은 오류로 남깁니다. Google 인증 파일 등 추가 정적 파일은 public에 저장하세요. dist는 생성물입니다. 인증키를 이 저장소에 넣지 마세요.

테크픽랩은 public에 원본 사이트 전체를 보존합니다. 다른 4개 사이트는 content/legacy-posts에 원본 글 HTML을 보존합니다. 디자인 파일은 원본과 같습니다. 새 글은 content/posts.json의 body_html과 선택 image_url/image_alt를 사용합니다.
