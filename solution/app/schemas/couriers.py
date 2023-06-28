from datetime import datetime
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, conlist, validator


class CourierType(str, Enum):
    foot = "FOOT"
    bike = "BIKE"
    auto = "AUTO"


class Courier(BaseModel):
    courier_type: CourierType
    regions: conlist(int, min_items=1)
    working_hours: conlist(str, min_items=1)

    @validator('regions', each_item=True)
    def check_positive(cls, v):
        if v < 1:
            raise ValueError('')
        return v

    @validator('working_hours', each_item=True)
    def change_times(cls, v):
        start_time = datetime.strptime(v[0:5], '%H:%M')
        end_time = datetime.strptime(v[6:11], '%H:%M')
        start_time = datetime.time(start_time)
        end_time = datetime.time(end_time)
        working_hours_tuple = (start_time, end_time)
        return working_hours_tuple

    class Config:
        schema_extra = {
            "example": {
                "courier_type": "FOOT",
                "regions": [1,2,3],
                "working_hours": ["10:00-12:00", "15:00-17:00"]
            }
        }


class CourierPost(BaseModel):
    couriers: List[Courier]


class CourierOutput(BaseModel):
    courier_id: int
    courier_type: CourierType
    regions: conlist(int, min_items=1)
    working_hours: conlist(tuple, min_items=1)

    @validator('working_hours', each_item=True)
    def change_times(cls, v):
        start_mins = v[0].strftime('%H:%M')
        end_mins = v[1].strftime('%H:%M')
        working_hours = start_mins + '-' + end_mins
        return working_hours


class PostedCouriersOut(BaseModel):
    couriers: List[CourierOutput]


class AllCouriersOut(BaseModel):
    couriers: List[CourierOutput]
    limit: int
    offset: int


class CourierMetaData(BaseModel):
    courier_id: int
    courier_type: CourierType
    regions: conlist(int, min_items=1)
    working_hours: conlist(tuple, min_items=1)
    rating: Optional[int]
    earnings: Optional[int]

    @validator('working_hours', each_item=True)
    def change_times(cls, v):
        start_mins = v[0].strftime('%H:%M')
        end_mins = v[1].strftime('%H:%M')
        working_hours = start_mins + '-' + end_mins
        return working_hours
