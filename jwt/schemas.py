from pydantic import BaseModel
from typing import Optional, List

class UserCreate(BaseModel):
    #데이터 생성할 때 해당 정보가 반드시 들어와있는지 확인하도록
    username: str
    password: str

#여러 데이터를 한번에 받아놓을 수 있도록 형태를 저장해놓은 것
class ItemCreate(BaseModel):
    name: str
    price: float
    is_offer: Optional[str] = None #form에서 넘어온 데이터 변환->ItemCreate->Item

class ItemOut(BaseModel):
    #ORM 객체(DB 조회 결과)를 응답 형식으로 직렬화(변환)할 때 구조를 검증
    id: int
    name: str
    price: float
    is_offer: Optional[str] = None
    owner_id: int

    class Config:
        from_attributes = True #ORM모델을 검증모델로 변환

class NaverUser(BaseModel):
    id:str
    email:Optional[str] = None

class SaveMessage(BaseModel):
    sender : str
    content : List[dict]