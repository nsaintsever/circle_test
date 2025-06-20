import datetime
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from sqlalchemy.sql import func

DATABASE_URL = "sqlite:///./circle_orders.db"

Base = declarative_base()

class Order(Base):
    __tablename__ = "orders"

    cle = Column(String, primary_key=True, index=True)
    data = Column(Text)  # JSON string of CIRCLE fields
    current_actor = Column(String, index=True) # Broker, Castle, Merchant, Warehouse
    status = Column(String, index=True) # New, PendingCastle, AmendedByCastle, etc.
    last_updated = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    sender = Column(String, nullable=True) # Actor ID who last sent
    receiver = Column(String, nullable=True) # Actor ID intended to receive

    history_entries = relationship("OrderHistory", back_populates="order")

    def __repr__(self):
        return f"<Order(cle='{self.cle}', status='{self.status}', current_actor='{self.current_actor}')>"

class OrderHistory(Base):
    __tablename__ = "order_history"

    history_id = Column(Integer, primary_key=True, autoincrement=True)
    cle = Column(String, ForeignKey("orders.cle"), index=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    actor = Column(String) # Who made the change
    action = Column(String) # e.g., 'Created', 'Amended', 'Sent to Merchant'
    changed_data = Column(Text, nullable=True) # JSON string of changed fields, or full data

    order = relationship("Order", back_populates="history_entries")

    def __repr__(self):
        return f"<OrderHistory(cle='{self.cle}', actor='{self.actor}', action='{self.action}')>"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False}) # check_same_thread for FastAPI/Streamlit

# Function to create tables
def create_db_and_tables():
    Base.metadata.create_all(bind=engine)
    print("Database and tables created successfully.")

if __name__ == "__main__":
    create_db_and_tables()
    # Example of how to add data (optional, for testing setup)
    # SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    # db = SessionLocal()
    # example_order_data = {
    #     "C0": "11", "C1": "A0", "C10": "TESTPROD", "C11": "2023",
    #     # ... other fields up to 80
    # }
    # import json
    # new_order = Order(
    #     cle="TESTCLE123",
    #     data=json.dumps(example_order_data),
    #     current_actor="Broker",
    #     status="New",
    #     sender="Broker_ID_1",
    #     receiver="Castle_ID_1"
    # )
    # db.add(new_order)
    # new_history = OrderHistory(
    #     cle="TESTCLE123",
    #     actor="Broker_ID_1",
    #     action="Created",
    #     changed_data=json.dumps(example_order_data)
    # )
    # db.add(new_history)
    # db.commit()
    # print("Example order added.")
    # db.close()
