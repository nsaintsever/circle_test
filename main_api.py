import datetime
import json
import hashlib
from fastapi import FastAPI, HTTPException, Depends
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import IntegrityError
from pydantic import BaseModel, Field
from typing import Dict, Any, List

# Assuming database_setup.py is in the same directory and defines Base, Order, OrderHistory, engine
from database_setup import Base, Order, OrderHistory, engine, DATABASE_URL

# Create database tables if they don't exist (idempotent)
Base.metadata.create_all(bind=engine)

app = FastAPI(title="CIRCLE Language Order API", version="0.1.0")

# SQLAlchemy session dependency
def get_db():
    db = sessionmaker(autocommit=False, autoflush=False, bind=engine)()
    try:
        yield db
    finally:
        db.close()

# --- Pydantic Models for Request/Response ---
class CircleOrderData(BaseModel):
    # Using Dict[str, Any] to represent the flexible 80 CIRCLE fields
    # In a more mature system, each C-field could be explicitly typed
    # For C10 (Product), C11 (Vintage) specifically, as they are key for CLE
    C10: str = Field(..., description="Product Code (e.g., C10_products.csv)")
    C11: str = Field(..., description="Vintage (Year, e.g., C11_vintages.csv)")
    # The rest of the fields, up to 80. Using a generic Dict for now.
    # It's expected that the frontend sends all available fields.
    circle_data: Dict[str, Any] = Field(..., description="Key-value pairs for all CIRCLE fields C0-C80")
    sender_id: str = Field(..., description="Identifier for the actor sending/creating the order")
    receiver_id: str = Field(..., description="Identifier for the actor intended to receive the order next")


class OrderResponse(BaseModel):
    cle: str
    data: Dict[str, Any] # Will parse the JSON string from DB
    current_actor: str
    status: str
    last_updated: datetime.datetime
    created_at: datetime.datetime
    sender: str | None
    receiver: str | None

    class Config:
        from_attributes = True # Use this for Pydantic v2 (orm_mode is deprecated)


class OrderHistoryResponse(BaseModel):
    history_id: int
    cle: str
    timestamp: datetime.datetime
    actor: str
    action: str
    changed_data: Dict[str, Any] | None # Will parse JSON

    class Config:
        from_attributes = True

class OrderWithHistoryResponse(OrderResponse):
    history: List[OrderHistoryResponse] = []

class OrderUpdateRequest(BaseModel):
    updated_data: Dict[str, Any] = Field(..., description="The full set of CIRCLE fields with updates.")
    sender_id: str = Field(..., description="Identifier for the actor sending the update.")
    new_current_actor: str = Field(..., description="Identifier for the actor who should act next.")
    new_status: str = Field(..., description="The new status of the order (e.g., 'AmendedByCastle', 'Accepted').")
    action_description: str = Field(..., description="Description of the action taken (e.g., 'Castle Amended Fields', 'Merchant Accepted Order').")


# --- CLE Generation ---
def generate_cle(order_input_data: CircleOrderData) -> str:
    """
    Generates a CLE by hashing key fields from the order data.
    """
    timestamp_str = datetime.datetime.now(datetime.timezone.utc).isoformat()

    # Key fields for CLE: Product Code (C10), Vintage (C11), Sender ID, Receiver ID, and Timestamp.
    concatenated_string = f"{order_input_data.C10}|{order_input_data.C11}|{order_input_data.sender_id}|{order_input_data.receiver_id}|{timestamp_str}"

    cle_hash = hashlib.sha256(concatenated_string.encode('utf-8')).hexdigest()
    return cle_hash

# --- API Endpoints ---

@app.post("/order", response_model=OrderResponse, status_code=201)
def create_order(order_input: CircleOrderData, db: Session = Depends(get_db)):
    """
    Create a new wine order.
    The CLE (unique key) will be generated based on key input fields.
    """
    cle = generate_cle(order_input)

    full_circle_data = order_input.circle_data.copy()
    full_circle_data['C10'] = order_input.C10 # Ensure C10 from dedicated field is in main data
    full_circle_data['C11'] = order_input.C11 # Ensure C11 from dedicated field is in main data
    if 'C0' not in full_circle_data: # Add default C0 if not provided
        full_circle_data['C0'] = "11"

    db_order = Order(
        cle=cle,
        data=json.dumps(full_circle_data),
        current_actor=order_input.receiver_id,
        status="New",
        sender=order_input.sender_id,
        receiver=order_input.receiver_id
    )

    db_history = OrderHistory(
        cle=cle,
        actor=order_input.sender_id,
        action="Created",
        changed_data=json.dumps(full_circle_data)
    )

    try:
        db.add(db_order)
        db.add(db_history)
        db.commit()
        db.refresh(db_order)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Order with this CLE already exists or other integrity error.")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")

    response_data_dict = json.loads(db_order.data)
    return OrderResponse(
        cle=db_order.cle,
        data=response_data_dict,
        current_actor=db_order.current_actor,
        status=db_order.status,
        last_updated=db_order.last_updated,
        created_at=db_order.created_at,
        sender=db_order.sender,
        receiver=db_order.receiver
    )


@app.get("/order/{cle}", response_model=OrderWithHistoryResponse)
def get_order(cle: str, db: Session = Depends(get_db)):
    """
    Retrieve a specific order by its CLE, including its history.
    """
    db_order = db.query(Order).options(joinedload(Order.history_entries)).filter(Order.cle == cle).first()
    if db_order is None:
        raise HTTPException(status_code=404, detail="Order not found")

    order_data_dict = json.loads(db_order.data)

    history_list = []
    if db_order.history_entries: # Check if history_entries is not None
        for entry in db_order.history_entries:
            history_entry_data = json.loads(entry.changed_data) if entry.changed_data else None
            history_list.append(OrderHistoryResponse(
                history_id=entry.history_id,
                cle=entry.cle,
                timestamp=entry.timestamp,
                actor=entry.actor,
                action=entry.action,
                changed_data=history_entry_data
            ))

    return OrderWithHistoryResponse(
        cle=db_order.cle,
        data=order_data_dict,
        current_actor=db_order.current_actor,
        status=db_order.status,
        last_updated=db_order.last_updated,
        created_at=db_order.created_at,
        sender=db_order.sender,
        receiver=db_order.receiver,
        history=history_list
    )


@app.put("/order/{cle}", response_model=OrderResponse)
def update_order(cle: str, update_data: OrderUpdateRequest, db: Session = Depends(get_db)):
    """
    Update an existing order. This is used when an actor amends data,
    accepts an order, or sends it to the next actor in the workflow.
    """
    db_order = db.query(Order).filter(Order.cle == cle).first()
    if db_order is None:
        raise HTTPException(status_code=404, detail="Order not found to update.")

    # Update the order fields
    db_order.data = json.dumps(update_data.updated_data)
    db_order.current_actor = update_data.new_current_actor
    db_order.status = update_data.new_status
    db_order.sender = update_data.sender_id
    db_order.receiver = update_data.new_current_actor
    # last_updated is handled by server_default/onupdate in DB model

    # Create a history entry
    db_history = OrderHistory(
        cle=cle,
        actor=update_data.sender_id,
        action=update_data.action_description,
        changed_data=json.dumps(update_data.updated_data)
    )

    try:
        db.add(db_order) # SQLAlchemy handles this as an update since db_order is tracked
        db.add(db_history)
        db.commit()
        db.refresh(db_order)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred during update: {str(e)}")

    response_data_dict = json.loads(db_order.data)
    return OrderResponse(
        cle=db_order.cle,
        data=response_data_dict,
        current_actor=db_order.current_actor,
        status=db_order.status,
        last_updated=db_order.last_updated,
        created_at=db_order.created_at,
        sender=db_order.sender,
        receiver=db_order.receiver
    )


@app.get("/orders/actor/{actor_name}", response_model=List[OrderResponse])
def get_orders_for_actor(actor_name: str, db: Session = Depends(get_db)):
    """
    Retrieve orders relevant to a specific actor (i.e., where they are the current_actor).
    """
    db_orders = db.query(Order).filter(Order.current_actor == actor_name).order_by(Order.last_updated.desc()).all()

    if not db_orders:
        return []

    response_list = []
    for db_order_item in db_orders: # renamed db_order to db_order_item to avoid conflict
        order_data_dict = json.loads(db_order_item.data)
        response_list.append(OrderResponse(
            cle=db_order_item.cle,
            data=order_data_dict,
            current_actor=db_order_item.current_actor,
            status=db_order_item.status,
            last_updated=db_order_item.last_updated,
            created_at=db_order_item.created_at,
            sender=db_order_item.sender,
            receiver=db_order_item.receiver
        ))
    return response_list


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
