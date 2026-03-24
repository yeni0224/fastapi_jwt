# (JWT & 비밀번호 해시 + 쿠키 유틸)
from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import jwt, JWTError
from passlib.context import CryptContext
from fastapi import Request

SECRET_KEY = "change-this-to-very-secret" #원래 SECRET_KEY는 코드에 두지 않는다
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

#네이버 로그인-----------------------------------
import httpx
import os
from dotenv import load_dotenv

NAVER_CLIENT_ID = os.getenv('NAVER_CLIENT_ID')
NAVER_CLIENT_SECRET = os.getenv('NAVER_CLIENT_SECRET')
#-----------------------------------------------------

#비크립트 : 비밀번호를 안전하게 해시(Hash)로 변환하는 알고리즘, 최초 로그인 시 비밀번호 검증 도구
#salt : 해시 전에 비밀번호에 랜덤 값을 섞은 랜덤문자열, 같은 비밀번호라도 매번 다른 해시값 발생
#       bcrypt는 내부에서 자동으로 salt 관리, 해시과정에 포함
#크립트 컨텍스트 : 어떤 방식으로 비밀번호를 해시할지 설정을 묶어놓은 객체
    #schemes:어떤 해시 알고리즘을 쓸지 목록 정하기
    #deprecatd:구식으로 처리할것인가, auto:첫번째것만 최신으로 나머지는 자동으로 구식처리
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)

#로그인 성공시 토큰 생성
def create_access_token(sub: str) -> str:
    #유효시간 설정
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": sub, "exp": expire}
            #헤더 + 정보 + 시그니처가 합쳐진 토큰이 만들어진다
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

#쿠키에 담긴 코드 디코딩
def decode_token(token: str) -> Optional[dict]:
    try:        
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return None

# 쿠키에서 bearer 토큰 꺼내기 (dev 용, HttpOnly)
COOKIE_NAME = "access_token"

def get_token_from_request(request: Request) -> Optional[str]:
    #요청에 담긴 쿠키 중 access_token 키의 값을 꺼냄. 없으면 None반환
    token = request.cookies.get(COOKIE_NAME)
    # "Bearer xxx" 형태로 저장했다면 접두어 제거
    if token and token.lower().startswith("bearer "):
        #같은 문자열을 공백 기준으로 **최대 1번만** 나눠서 뒤쪽 순수 토큰값만 반환
        return token.split(" ", 1)[1]
    #접두어가 없는 경우, 토큰을 그대로 반환. 순수 토큰값만 쿠키에 저장한 경우를 처리
    return token

#네이버 로그인 -----------------------------------------------------
#네이버인증 url
def get_naver_auth_url():
    return(
        "https://nid.naver.com/oauth2.0/authorize"
        "?response_type=code"
        f"&client_id={NAVER_CLIENT_ID}"
        "&redirect_uri=http://localhost:8000/callback"
        "&state={state}"
    )

async def get_naver_token(code:str):
    token_url = "https://nid.naver.com/oauth2.0/token"
    headers = {"Content-Type":"application/x-www-form-urlencoded"}
    params = {
        "grant_type": "authorization_code",
        "client_id": NAVER_CLIENT_ID,
        "client_secret": NAVER_CLIENT_SECRET,
        "code": code,
        "state": "{state}"
    }
    async with httpx.AsyncClient() as client:
        response = await client.post(token_url, headers=headers, data=params)
        response.raise_for_status()
        return response.json()
    
async def get_naver_user_info(access_token: str):
    user_info_url = "https://openapi.naver.com/v1/nid/me"
    headers = {
        "Authorization": f"Bearer {access_token}"
    }
    async with httpx.AsyncClient() as client:
        response = await client.get(user_info_url, headers=headers)
        response.raise_for_status()
        return response.json()