from fastapi import FastAPI, Depends, Request, HTTPException, status, Response
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from database import Base, engine, SessionLocal
import models
from schemas import UserCreate, ItemCreate, ItemOut, SaveMessage
import auth
from fastapi.responses import RedirectResponse

#websockets--------------------------------------------------
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from typing import List
from datetime import datetime
#------------------------------------------------------------

#mongodb--------------------------------------------------
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime

# MongoDB 연결 (기본 로컬 주소)
MONGO_DETAILS = "mongodb://localhost:27017"
client = AsyncIOMotorClient(MONGO_DETAILS)
database = client.chat_db
message_collection = database.get_collection("messages_history")
#------------------------------------------------------------

app = FastAPI()

# --- CORS 설정 (React 연동 필수) ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"], # React 개발 서버 주소
    allow_credentials=True, # 쿠키(인증 정보) 포함 허용
    allow_methods=["*"],
    allow_headers=["*"],
)

Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# 토큰 안의 정보에서 유저 정보 꺼내옴
def get_current_user(request: Request, db: Session = Depends(get_db)) -> models.User:
    token = auth.get_token_from_request(request)
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    payload = auth.decode_token(token)
    if not payload or "sub" not in payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    user = db.query(models.User).filter(models.User.id == int(payload["sub"])).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user

# --- API 라우터 ---

#회원가입
@app.post("/api/register")
def register(user_data: UserCreate, db: Session = Depends(get_db)):
    exists = db.query(models.User).filter(models.User.username == user_data.username).first()
    if exists:
        raise HTTPException(status_code=400, detail="이미 존재하는 사용자명입니다.")
    #유저 정보가 담긴 모델 생성
    user = models.User(username=user_data.username, hashed_password=auth.hash_password(user_data.password))
    db.add(user)
    db.commit()
    return {"message": "회원가입 성공"}

@app.post("/api/login")
def login(response: Response, user_data: UserCreate, db: Session = Depends(get_db)):
    #username이 일치하는 record 찾기
    user = db.query(models.User).filter(models.User.username == user_data.username).first()
    #db에 저장된 비밀번호를 대조함. 실패하면 에러 발생
    if not user or not auth.verify_password(user_data.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="아이디 또는 비밀번호가 올바르지 않습니다.")
    
    #로그인 성공시 response의 토큰이 만들어지고, 토큰에 쿠키의 값 세팅
    token = auth.create_access_token(str(user.id))
    #response 객체를 통해 서버에서 클라로 들어옴
    response.set_cookie(
        key=auth.COOKIE_NAME,#같은 도메인이면 쿠키 이름이 넘어갈 것
        value=f"Bearer {token}",#토큰이 헤더,정보,서명 뒤에 붙을 것
        httponly=True,#수업 한정 사용, 실무는 https 프로토콜을 사용,이 쿠키는 javascript에서 접근 불가
        secure=False, #http프로토콜도 쿠키 전송(실무에서 True)
        samesite="lax", # react->FastAPI 내에서 요청은 정상작동, 외부 사이트 공격은 차단
        max_age=60 * 60, # 유효시간 60분
        path='/'
    )
    return {"message": "로그인 성공", "username": user.username}

@app.post("/api/logout")
def logout(response: Response):
    response.delete_cookie(auth.COOKIE_NAME)
    return {"message": "로그아웃 성공"}

@app.get("/api/me")
def check_auth(user: models.User = Depends(get_current_user)):
    return {"username": user.username}

#리턴될 때 itemOut으로 변환될 것이다.
@app.get("/api/items", response_model=list[ItemOut])
def get_items(db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    return db.query(models.Item).filter(models.Item.owner_id == user.id).order_by(models.Item.id.desc()).all()

@app.post("/api/items", response_model=ItemOut)
def create_item(item_data: ItemCreate, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    item = models.Item(
        name=item_data.name,
        price=item_data.price,
        is_offer=item_data.is_offer,
        owner_id=user.id,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item

#네이버 로그인 ---------------------------------------------
@app.get("/")
async def root():
    auth_url = auth.get_naver_auth_url()
    return RedirectResponse(auth_url)

@app.get("/callback")
async def callback(request: Request, response: Response):
    code = request.query_params.get("code")
    state = request.query_params.get("state")

    # 네이버에서 토큰 받아오기
    token_response = await auth.get_naver_token(code)
    access_token = token_response.get("access_token")

    # 사용자 정보 가져오기
    user_info = await auth.get_naver_user_info(access_token)

    # JWT 발급
    jwt_token = auth.create_access_token({"sub": user_info["id"]})

    # HttpOnly 쿠키에 저장
    response.set_cookie(
        key="access_token",
        value=jwt_token,
        httponly=True,
        samesite="lax"
    )

    # 프론트엔드로 리다이렉트
    return RedirectResponse(url="http://localhost:5173/items")

#websocket-------------------------------------------------------
class ConnectionManager:
    def __init__(self):
        #현재 접속중인 웹소켓 연결 객체 저장리스트
        self.active_connections: List[WebSocket] = []

    #새로운 클라이언트가 처음 접속하면
    async def connect(self, websocket: WebSocket):
        #접속 요청 수락(accept)
        await websocket.accept()
        #연결된 소켓 객체 리스트에 추가
        self.active_connections.append(websocket)

    #클라이언트가 접속 종료시
    def disconnect(self, websocket: WebSocket):
        #해당 소켓 객체 리스트에서 제거
        self.active_connections.remove(websocket)

    #클라이언트가 메세지 send시
    async def broadcast(self, message: dict):
        #리스트에 저장된 모든 소켓 객체를 하나씩 꺼내서
        for connection in self.active_connections:
            #클라이언트에게 json형식으로 메세지 전송
            await connection.send_json(message)
 
manager = ConnectionManager()
 
@app.websocket("/ws-chat")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
 
    try:
        #연결이 유지되는 동안 무한 반복하면서 클라이언트 메세지 기다림
        while True:
            #await사용해 json 데이터 올때까지(작업 완료될 때까지) 클라 메세지 기다리다가 메세지 받아 저장
            data = await websocket.receive_json()
            #받은 데이터로 메세지 형식 구성
            message = {
                "sender": data.get("sender", "Anonymous"),
                "content": data.get("content", ""),
                "type": data.get("type", "CHAT"),
                "timestamp": datetime.now().isoformat()
            }
 
            # JOIN 처리 : 제일 처음 접속한 상태일 때
            if message["type"] == "JOIN":
                #content 내용 설정
                message["content"] = f"{message['sender']} joined the chat"
            
            await manager.broadcast(message)
 
    except WebSocketDisconnect:
        #사용자가 브라우저 닫거나 연결을 끊으면 예외 발생
        manager.disconnect(websocket)

#채팅 내용 저장시 nosql 사용을 추천(mongodb)

@app.post("/api/save-message")
async def save_message(msg: SaveMessage):

    #mongodb(단일 채팅 기능에 추가)----------------------------------
    #기존 내용 출력(20개만)
    history = msg.content[-20:]
    
    for msg in history:
        # MongoDB의 _id(ObjectId)는 JSON 직렬화가 안되므로 문자열로 변환하거나 제외.
        await message_collection.insert_one({
            "sender": msg["sender"],
            "content": msg["content"],
            "type": msg.get("type", "CHAT"),
            "timestamp": datetime.now().isoformat()
        })
        
        #단일 저장
        # await message_collection.insert_one({
        #     "sender": msg.sender,
        #     "content": msg.content,
        #     "type": "CHAT",
        #     "timestamp": datetime.now().isoformat()
        #})
    #------------------------------------------------------------
    return {"message": "저장 완료"}

#websocket-------------------------------------------------------