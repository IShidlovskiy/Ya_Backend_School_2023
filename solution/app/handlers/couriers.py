from collections import defaultdict
from datetime import date, time, datetime
from typing import List
from fastapi import APIRouter
from starlette import status
from starlette.responses import JSONResponse

from app.handlers.orders import db_order_to_dict
from app.schemas.couriers import CourierOutput, AllCouriersOut, CourierMetaData, PostedCouriersOut, CourierPost
from app.db.db import sql_pool
from app.schemas.orders import AssignedOrders

router = APIRouter(
    prefix="/couriers",
    tags=["courier-controller"]
)


def db_courier_to_dict(courier_id, db_type, db_regions, db_working_hours):
    """Функция переводит данные курьера полученные из БД в словарь"""
    working_hours = []
    for work_period in db_working_hours.strip('{}').split('","'):
        work_from, work_till = work_period.strip('()"').split(',')
        work_from = time.fromisoformat(work_from)
        work_till = time.fromisoformat(work_till)
        working_hours.append((work_from, work_till))

    courier = {
        "courier_id": courier_id,
        "courier_type": db_type,
        "regions": db_regions,
        "working_hours": working_hours
    }
    return courier


@router.get("", name='Выдача информации о курьерах', status_code=status.HTTP_200_OK)
async def send_all_couriers_data(offset: int = 0, limit: int = 1) -> AllCouriersOut:
    if limit <= 0 or offset < 0:
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content={})

    conn = sql_pool.getconn()
    cur = conn.cursor()

    cur.execute(f"""
        SELECT c.id, c.type, 
        ARRAY_AGG(DISTINCT r.region) AS regions,
        ARRAY_AGG(DISTINCT (wh.work_from, wh.work_till)) AS working_hours
        FROM (
            SELECT * FROM couriers WHERE id > {offset} ORDER BY id ASC LIMIT {limit}
        ) c
        JOIN regions r ON c.id = r.courier_id
        JOIN working_hours wh ON c.id = wh.courier_id
        GROUP BY c.id, c.type
        ORDER BY c.id ASC
    """)

    db_couriers = cur.fetchall()
    conn.commit()
    cur.close()
    sql_pool.putconn(conn)

    all_couriers = []
    for courier in db_couriers:
        db_courier_id, db_type, db_regions, db_working_hours = courier
        courier = db_courier_to_dict(db_courier_id, db_type, db_regions, db_working_hours)
        all_couriers.append(courier)

    response = {"couriers": all_couriers, "limit": limit, "offset": offset}
    return response


@router.post("", name='Получение информации о курьерах', status_code=status.HTTP_200_OK)
async def add_couriers(couriers: CourierPost) -> PostedCouriersOut:
    conn = sql_pool.getconn()
    cur = conn.cursor()
    couriers_data_output = []
    for courier in couriers.couriers:
        courier = courier.dict()
        courier_type = courier['courier_type']

        cur.execute(
            f"""INSERT INTO couriers (type) 
                VALUES ('{courier_type}')
                RETURNING id""")
        courier_id = cur.fetchone()[0]
        courier['courier_id'] = courier_id

        for region in courier['regions']:
            cur.execute(f"INSERT INTO regions (region, courier_id) "
                        f"VALUES ({region}, {courier_id})")

        for work_from, work_till in courier['working_hours']:
            cur.execute(
                f"INSERT INTO working_hours (courier_id, work_from, work_till) "
                f"VALUES ({courier_id}, '{work_from}', '{work_till}')")

        couriers_data_output.append(courier)
    conn.commit()
    cur.close()
    sql_pool.putconn(conn)
    return {"couriers": couriers_data_output}


@router.get("/assignments", name='Список распределенных заказов', status_code=status.HTTP_200_OK)
async def assigned_orders_out(date: date = datetime.today().strftime('%Y-%m-%d'),
                              courier_id: int = None) -> List[AssignedOrders]:
    conn = sql_pool.getconn()
    cur = conn.cursor()
    if courier_id:
        cur.execute(
            f"""SELECT o.courier_id, o.batch_id, o.id as order_id, o.weight, o.region, 
                            o.deliver_from, o.deliver_till, o.cost, o.completed_time
                        FROM orders o
                        INNER JOIN batches b ON o.batch_id = b.id
                        WHERE b.date = '{date}' AND o.batch_id IS NOT NULL AND o.courier_id = {courier_id}"""
        )
    else:
        cur.execute(
            f"""SELECT o.courier_id, o.batch_id, o.id as order_id, o.weight, o.region, 
                    o.deliver_from, o.deliver_till, o.cost, o.completed_time
                FROM orders o
                INNER JOIN batches b ON o.batch_id = b.id
                WHERE b.date = '{date}' AND o.batch_id IS NOT NULL"""
        )

    db_orders = cur.fetchall()
    if not db_orders:
        response = [{"date": date, "couriers": []}]
        return response

    conn.commit()
    cur.close()
    sql_pool.putconn(conn)

    batches = defaultdict(list)
    couriers_data = defaultdict(set)
    for db_order in db_orders:
        db_courier_id, db_batch_id, db_order_id, db_weight, db_region, \
            db_deliver_from, db_deliver_till, db_cost, db_completed_time = db_order
        order = db_order_to_dict(db_order_id, db_weight, db_region, db_deliver_from,
                                 db_deliver_till, db_cost, db_completed_time)

        batches[db_batch_id].append(order)
        couriers_data[db_courier_id].add(db_batch_id)

    couriers = []
    for key in couriers_data.keys():
        orders = []
        for batch_id in couriers_data[key]:
            orders.append({"group_order_id": batch_id, "orders": batches[batch_id]})
        couriers.append({"courier_id": key, "orders": orders})
    response = [{"date": date, "couriers": couriers}]

    return response


@router.get("/{courier_id}", name='Получение информации о курьере', status_code=status.HTTP_200_OK)
async def courier_info(courier_id: int) -> CourierOutput:
    conn = sql_pool.getconn()
    cur = conn.cursor()
    cur.execute(f"""
            SELECT c.id, c.type, 
            ARRAY_AGG(DISTINCT r.region) AS regions,
            ARRAY_AGG(DISTINCT (wh.work_from, wh.work_till)) AS working_hours
            FROM couriers c
            JOIN regions r ON c.id = r.courier_id
            JOIN working_hours wh ON c.id = wh.courier_id
            WHERE c.id = {courier_id}
            GROUP BY c.id
        """)
    db_courier = cur.fetchone()
    cur.close()
    sql_pool.putconn(conn)

    if not db_courier:
        return JSONResponse(status_code=404, content={})

    db_courier_id, db_type, db_regions, db_working_hours = db_courier
    return db_courier_to_dict(db_courier_id, db_type, db_regions, db_working_hours)


@router.get("/meta-info/{courier_id}", name='Получение зарплаты и рейтинга курьера', status_code=status.HTTP_200_OK)
async def courier_meta_info(courier_id: int, startDate: date, endDate: date) -> CourierMetaData:
    conn = sql_pool.getconn()
    cur = conn.cursor()

    cur.execute(f"""
                SELECT c.id, c.type, 
                ARRAY_AGG(DISTINCT r.region) AS regions,
                ARRAY_AGG(DISTINCT (wh.work_from, wh.work_till)) AS working_hours
                FROM couriers c
                JOIN regions r ON c.id = r.courier_id
                JOIN working_hours wh ON c.id = wh.courier_id
                WHERE c.id = {courier_id}
                GROUP BY c.id
            """)
    db_courier = cur.fetchone()
    if db_courier is None:
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={})

    courier_id, db_type, db_regions, db_working_hours = db_courier
    courier = db_courier_to_dict(courier_id, db_type, db_regions, db_working_hours)

    cur.execute(f"""
        WITH orders_filtered AS (
            SELECT o.cost, o.position_in_batch, c.type
            FROM orders o
            JOIN couriers c ON o.courier_id = c.id
            WHERE o.courier_id = {courier_id}
            AND o.completed_time >= TIMESTAMP '{startDate}'
            AND o.completed_time < TIMESTAMP '{endDate}'
        ),
        orders_earnings AS (
            SELECT 
                SUM(CASE 
                    WHEN position_in_batch = 1 THEN cost
                    WHEN position_in_batch > 1 THEN cost * 0.8
                    ELSE 0 
                    END) AS earnings, 
                COUNT(*) AS num_orders, 
                type
            FROM orders_filtered
            GROUP BY type
        ),
        courier_data AS (
            SELECT
                earnings * 
                CASE type 
                    WHEN 'FOOT' THEN 2
                    WHEN 'BIKE' THEN 3
                    WHEN 'AUTO' THEN 4
                    ELSE 0
                END AS total_earnings,
                num_orders / 
                (EXTRACT(EPOCH FROM (TIMESTAMP '{endDate}' - TIMESTAMP '{startDate}')) / 3600) *
                CASE type 
                    WHEN 'FOOT' THEN 3
                    WHEN 'BIKE' THEN 2
                    WHEN 'AUTO' THEN 1
                    ELSE 0
                END AS rating
            FROM orders_earnings
        )
        SELECT total_earnings, rating
        FROM courier_data
    """)
    db_courier_metadata = cur.fetchone()

    if not db_courier_metadata:
        return courier

    db_earnings, db_rating = db_courier_metadata
    cur.close()
    sql_pool.putconn(conn)

    courier |= {"rating": int(db_rating), "earnings": db_earnings}
    return courier
