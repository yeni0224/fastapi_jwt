from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

#MySQL 연결 정보
DATABASE_URL = "mysql+pymysql://madang:madang@localhost:3306/madangdb?charset=utf8mb4"
engine = create_engine(DATABASE_URL, echo=False, pool_pre_ping=True, 
                       future=True) # DB와 실제로 통신하는 객체
SessionLocal = sessionmaker(autoflush=False, bind=engine)
Base = declarative_base()