from sqlalchemy import Column, Integer, String, ForeignKey, Numeric
from sqlalchemy.orm import relationship
from database import Base

class User(Base):
    __tablename__ = "users"
    id= Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True,nullable=False,index=True)
    hashed_password = Column(String(255),nullable=False)
    #items table과 관계를 맺는다, 이 테이블이 부모가 되는 관계
    #user을 꺼냈을 때 내가 등록할 목록들을 list로 꺼내올 수 있도록 함
    items = relationship("Item",back_populates="owner", cascade="all, delete-orphan")

class Item(Base):
    __tablename__="items"
    id= Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    price = Column(Numeric(10,2), nullable=False)
    is_offer = Column(String(5), nullable=True)  # "true" / None (간단화)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    #해당 item을 가져왔을 때 소유주 1개의 데이터도 가져올 수 있도록 함
    owner = relationship("User", back_populates="items")