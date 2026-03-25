from pydantic import BaseModel
from typing import Optional, List

class EntityBase(BaseModel):
    id: str

class Customer(EntityBase):
    name: Optional[str] = None
    industry: Optional[str] = None

class Product(EntityBase):
    description: Optional[str] = None
    product_type: Optional[str] = None
    product_group: Optional[str] = None

class SalesOrder(EntityBase):
    creation_date: Optional[str] = None
    total_net_amount: Optional[float] = None
    currency: Optional[str] = None
