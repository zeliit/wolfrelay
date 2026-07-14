# wolfrelay

`wftoon###.com` 계열 사이트를 Mihon에서 열기 위한 간단한 릴레이 서버입니다.

## 핵심

- Mihon이 직접 접속할 때 `Connection reset`이 나는 경우 사용
- `wolfrelay`가 HTML/이미지를 대신 받아 Mihon에 전달
- `docker compose up -d --build` 한 번이면 `wolfrelay`와 `FlareSolverr`가 같이 올라옵니다

## Mihon 설정

```text
도메인: https://wftoon111.com
Relay URL: https://wf.example.com
```

주의:

- Mihon에는 공개 주소만 넣습니다
- `172.17.0.1:8911`, `host.docker.internal:8191` 같은 내부 주소는 넣지 않습니다

## 실행

```powershell
cd C:\worker\source_code\python_code\wolfrelay
docker compose up -d --build
```

## 확인

로컬 헬스체크:

```powershell
curl.exe -sS http://127.0.0.1:8911/health
```

정상 응답:

```json
{"status":"ok"}
```

컨테이너 확인:

```powershell
docker compose ps
```

여기서 `wolfrelay`, `flaresolverr` 두 컨테이너가 모두 떠 있어야 합니다.

## Reverse Proxy

예시 공개 주소:

- `https://wf.example.com`

Reverse Proxy는 이 공개 주소를 내부 `wolfrelay:8911` 또는 호스트 `8911`로 넘기면 됩니다.

중요:

- 사용자 앱에는 공개 주소 `https://wf.example.com` 을 넣습니다
- `host.docker.internal:8191` 는 사용자용 주소가 아니라, 예전 서버 내부 우회용 주소였습니다

## 엔드포인트

- `/health`
- `/html?url=...&referer=...`
- `/binary?url=...&referer=...`

제한:

- `/html` 은 `wftoon###.com`만 허용
- `/binary` 는 공인 이미지 호스트만 허용

## 지금 보고된 에러의 뜻

아래 에러:

```text
HTTPConnectionPool(host='host.docker.internal', port=8191) ...
Failed to establish a new connection: [Errno 111] Connection refused
```

의미:

- `wolfrelay`가 HTML 우회 처리를 위해 FlareSolverr에 붙으려 했음
- 그런데 배포한 사람 서버에는 `8191`에서 받는 FlareSolverr가 없었음

즉, 배포 환경이 불완전했던 것입니다.

이제는 기본 `docker-compose.yml` 이 FlareSolverr를 같이 띄우므로, 배포자는 아래만 다시 하면 됩니다:

```powershell
docker compose down
docker compose up -d --build
```
