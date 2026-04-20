import requests
import json
import os

# ==========================================
# 1. 사용자 환경 변수 세팅 (GitHub Actions 전용)
# ==========================================
# ⚠️ 실제 키를 삭제하고 깃허브 Secrets에서 불러오도록 수정했습니다.
REST_API_KEY = os.environ.get("REST_API_KEY")
REDIRECT_URI = "http://localhost:8000"
AUTHORIZE_CODE = os.environ.get("AUTH_CODE")
OPENWEATHER_API_KEY = os.environ.get("OPENWEATHER_KEY")

CITY_NAME = "Seoul"

# 토큰을 영구 저장할 파일 이름
TOKEN_FILE = "kakao_tokens.json"

# ==========================================
# 2. 토큰 관리 로직 (발급 및 자동 갱신)
# ==========================================
def get_tokens():
    # 파일이 있으면 (이미 한 번 성공했다면) 리프레시 토큰으로 자동 갱신
    if os.path.isfile(TOKEN_FILE):
        with open(TOKEN_FILE, "r") as fp:
            tokens = json.load(fp)

        print("⏳ 저장된 토큰을 발견했습니다. 액세스 토큰을 새로 갱신합니다...")
        refresh_url = "https://kauth.kakao.com/oauth/token"
        data = {
            "grant_type": "refresh_token",
            "client_id": REST_API_KEY,
            "refresh_token": tokens["refresh_token"]
        }
        res = requests.post(refresh_url, data=data)
        new_tokens = res.json()

        if "access_token" not in new_tokens:
            print("❌ 토큰 갱신 실패. 인가 코드를 처음부터 다시 발급받아야 합니다.")
            exit()

        # 기존 리프레시 토큰 유지, 새 액세스 토큰으로 업데이트
        tokens["access_token"] = new_tokens["access_token"]
        if "refresh_token" in new_tokens:
            tokens["refresh_token"] = new_tokens["refresh_token"]

        with open(TOKEN_FILE, "w") as fp:
            json.dump(tokens, fp)
        return tokens["access_token"]

    # 파일이 없으면 (최초 실행 시) 새로 발급 후 파일로 저장
    else:
        print("⏳ 최초 실행입니다. 카카오 토큰을 새로 발급받습니다...")
        token_url = "https://kauth.kakao.com/oauth/token"
        data = {
            "grant_type": "authorization_code",
            "client_id": REST_API_KEY,
            "redirect_uri": REDIRECT_URI,
            "code": AUTHORIZE_CODE
        }
        res = requests.post(token_url, data=data)
        tokens = res.json()

        if "access_token" not in tokens:
            print("❌ 토큰 발급 실패. 인가 코드가 만료되었는지 확인하세요.")
            print(tokens)
            exit()

        with open(TOKEN_FILE, "w") as fp:
            json.dump(tokens, fp)
        return tokens["access_token"]

# 토큰 획득 실행
access_token = get_tokens()
print("✅ 카카오 인증 완료!")

# ==========================================
# 3. OpenWeather API 날씨 데이터 추출
# ==========================================
print("⏳ 날씨 정보를 가져옵니다...")
weather_url = f"http://api.openweathermap.org/data/2.5/weather?q={CITY_NAME}&appid={OPENWEATHER_API_KEY}&units=metric&lang=kr"
weather_res = requests.get(weather_url)
weather_data = weather_res.json()

if weather_res.status_code != 200:
    print("❌ 날씨 가져오기 실패. (API 키가 아직 활성화되지 않았을 수 있습니다.)")
    print(weather_data)
    exit()

current_temp = weather_data["main"]["temp"]
weather_desc = weather_data["weather"][0]["description"]
humidity = weather_data["main"]["humidity"]
print(f"✅ 날씨 추출 완료! ({current_temp}°C, {weather_desc})")

# ==========================================
# 4. 카카오톡 전송
# ==========================================
print("⏳ 카카오톡으로 전송합니다...")
send_url = "https://kapi.kakao.com/v2/api/talk/memo/default/send"
headers = {"Authorization": f"Bearer {access_token}"}
message_text = f"🌤️ 오늘의 {CITY_NAME} 날씨입니다.\n\n- 기온: {current_temp}°C\n- 상태: {weather_desc}\n- 습도: {humidity}%"

template = {
    "object_type": "text",
    "text": message_text,
    "link": {"web_url": "https://weather.naver.com/"},
    "button_title": "상세 날씨 보기"
}

send_res = requests.post(send_url, headers=headers, data={"template_object": json.dumps(template)})

if send_res.status_code == 200:
    print("🎉 전송 성공! 스마트폰을 확인하세요.")
else:
    print(f"❌ 전송 실패 (HTTP {send_res.status_code}):", send_res.json())
