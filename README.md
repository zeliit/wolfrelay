# wolfrelay

`wftoon###.com` 계열 사이트를 Mihon에서 읽기 위한 간단한 릴레이 서버다.

## 용도

- Mihon에서 직접 접속하면 `Connection reset`이 나는 경우 사용
- 서버가 대신 HTML/이미지를 받아서 Mihon에 전달

## 사용자가 Mihon에 넣는 값

```text
도메인: https://wftoon111.com
Relay URL: https://wf.example.com
```

주의:

- 사용자는 `172.17.0.1:8911` 같은 내부 주소를 넣지 않는다.
- 최신 확장에서는 `프록시 URL`을 쓰지 않는다.

## 서버 구조

- 공개 주소: `https://wf.example.com`
- 내부 wolfrelay: `http://172.17.0.1:8911` 또는 같은 Docker network의 서비스명

즉:

- Mihon은 `https://wf.example.com`에 붙음
- Reverse Proxy는 내부적으로 `http://172.17.0.1:8911`에 붙음

## 실행

```powershell
cd C:\worker\source_code\python_code\wolfrelay
docker compose up -d --build
```

## 확인

헬스체크:

```powershell
curl.exe -sS http://127.0.0.1:8911/health
```

공개 주소 확인:

```powershell
curl.exe -sS https://wf.example.com/health
```

정상 응답:

```json
{"status":"ok"}
```

## Reverse Proxy 설정

### 1. 공개 도메인 준비

- 예: `wf.example.com`
- 이 도메인이 wolfrelay 서버를 가리키도록 DNS 설정

### 2. Proxy Host 생성

- Domain Names: `wf.example.com`
- Scheme: `http`
- Forward Port: `8911`

Forward Hostname/IP는 환경에 따라 다르다.

### 3. 업스트림 주소

Reverse Proxy가 서버에서 직접 8911에 붙을 수 있으면:

- `127.0.0.1`
- 또는 서버 공인 IP

Reverse Proxy가 Docker 컨테이너면:

- `172.17.0.1`

중요:

- `172.17.0.1`는 사용자용 주소가 아니다.
- NPM 컨테이너가 자기 호스트로 붙을 때 쓰는 내부 주소다.

## 엔드포인트

- `/health`
- `/html?url=...&referer=...`
- `/binary?url=...&referer=...`

정책:

- `/html`은 `wftoon###.com`만 허용
- `/binary`는 공인 외부 이미지 호스트 허용
- `/binary`의 `referer`는 `wftoon###.com` 계열이어야 함

## 문제 생기면 체크할 것

1. `https://wf.example.com/health`가 열리는지
2. Reverse Proxy 업스트림이 실제로 `8911`에 붙는지
3. Mihon 설정이 아래처럼 들어갔는지

```text
도메인: https://wftoon218.com
Relay URL: https://wf.example.com
```
