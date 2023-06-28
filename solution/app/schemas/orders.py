from datetime import datetime, date
from typing import List, Optional
from pydantic import BaseModel, validator


class Order(BaseModel):
    weight: float
    regions: int
    delivery_hours: List[str]
    cost: int

    @validator('regions')
    def check_positive(cls, v):
        if v < 1:
            raise ValueError('')
        return v

    @validator('weight', 'cost')
    def more_than_zero(cls, v):
        if v < 0:
            raise ValueError('')
        return v

    @validator('delivery_hours')
    def change_times(cls, v):
        if v is None:
            return None
        v = v[0]
        start_time = datetime.strptime(v[0:5], '%H:%M')
        end_time = datetime.strptime(v[6:11], '%H:%M')
        start_time = datetime.time(start_time)
        end_time = datetime.time(end_time)
        delivery_hours_tuple = (start_time, end_time)
        return delivery_hours_tuple

    class Config:
        schema_extra = {
            "example": {
                "weight": 1.5,
                "regions": 2,
                "delivery_hours": ["10:00-12:00"],
                "cost": 175
            }
        }


class OrdersPost(BaseModel):
    orders: List[Order]


class OrderComplete(BaseModel):
    courier_id: int
    order_id: int
    complete_time: datetime


class CompleteInfo(BaseModel):
    complete_info: list[OrderComplete]

    class Config:
        schema_extra = {
            "example": {
                "complete_info": [
                    {
                        "courier_id": 0,
                        "order_id": 0,
                        "complete_time": "2023-05-07T17:08:00.827Z"
                    }
                ]
            }
        }


class OrderOut(BaseModel):
    order_id: int
    weight: float
    regions: int
    delivery_hours: tuple
    cost: int
    completed_time: Optional[datetime]

    @validator('delivery_hours')
    def change_delivery_times(cls, v):
        start_mins = v[0].strftime('%H:%M')
        end_mins = v[1].strftime('%H:%M')
        delivery_hours = start_mins + '-' + end_mins
        return [delivery_hours]

    @validator('completed_time')
    def strip_completed_time(cls, v):
        if v is None:
            return ""
        formatted_ct = str(v.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z")
        return formatted_ct

    class Config:
        schema_extra = {
            "example": {
                "order_id": 200,
                "weight": 1.5,
                "region": 2,
                "delivery_hours": ["10:00-12:00"],
                "cost": 175,
                "completed_time": "2023-05-07T15:24:40.532Z"
            }
        }


class AllOrdersOut(BaseModel):
    orders: List[OrderOut]


class OrderBatches(BaseModel):
    group_order_id: int
    orders: List[OrderOut]


class AssignedCouriers(BaseModel):
    courier_id: int
    orders: List[OrderBatches]


class AssignedOrders(BaseModel):
    date: date
    couriers: List[AssignedCouriers]
