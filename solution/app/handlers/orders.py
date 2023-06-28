import time
from collections import defaultdict
from datetime import timezone, date, datetime, time
from itertools import groupby
from operator import itemgetter
from typing import List
from fastapi import APIRouter
from starlette import status
from starlette.responses import JSONResponse
from app.schemas.orders import OrderOut, CompleteInfo, AssignedOrders, OrdersPost
from app.db.db import sql_pool
from app.config import courier_types, c_max_weight, c_max_orders, c_max_regions, c_first_order_dur, c_other_orders_dur

router = APIRouter(
    prefix="/orders",
    tags=["order-controller"]
)


def db_order_to_dict(order_id, db_weight, db_region, db_deliver_from, db_deliver_till, db_cost, db_cmpltd_time=None):
    """Функция переводит данные курьера полученные из БД в словарь"""
    order = {
        "order_id": order_id,
        "weight": db_weight,
        "regions": db_region,
        "delivery_hours": (db_deliver_from, db_deliver_till),
        "cost": db_cost,
        "completed_time": db_cmpltd_time.replace(tzinfo=None) if db_cmpltd_time else None
    }
    return order


@router.get("", name='Выдача информации о заказах', status_code=status.HTTP_200_OK)
async def send_all_orders_data(limit: int = 1, offset: int = 0) -> List[OrderOut]:
    if limit <= 0 or offset < 0:  # Если вдруг выводить ничего не нужно, сразу выводим ошибку
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content={})

    conn = sql_pool.getconn()
    cur = conn.cursor()
    cur.execute(f"""
    SELECT id, region, cost, weight, deliver_from, deliver_till, completed_time 
    FROM orders WHERE id > {offset} ORDER BY id ASC LIMIT {limit};
    """)
    orders_db_data = cur.fetchall()

    orders_list = []
    for db_order in orders_db_data:
        db_id, db_region, db_cost, db_weight, db_deliver_from, db_deliver_till, db_comp_time = db_order
        order = db_order_to_dict(db_id, db_weight, db_region, db_deliver_from, db_deliver_till, db_cost, db_comp_time)
        orders_list.append(order)

    cur.close()
    sql_pool.putconn(conn)
    return orders_list


@router.post("", name='Получение информации о заказах', status_code=status.HTTP_200_OK,
             responses={400: {"description": {}}})
async def add_orders(orders: OrdersPost) -> List[OrderOut]:
    conn = sql_pool.getconn()
    cur = conn.cursor()
    orders_data_output = []
    for order in orders.orders:
        order = order.dict()
        regions = order['regions']
        cost = order['cost']
        weight = order['weight']
        deliver_from = order['delivery_hours'][0]
        deliver_till = order['delivery_hours'][1]

        cur.execute(
            f"""INSERT INTO orders (region, cost, weight, deliver_from, deliver_till) 
                VALUES ({regions}, {cost}, {weight}, '{deliver_from}', '{deliver_till}') 
                RETURNING id""")

        order_id = cur.fetchone()[0]
        order['order_id'] = order_id
        orders_data_output.append(order)
    conn.commit()
    cur.close()
    sql_pool.putconn(conn)
    return orders_data_output


@router.post("/complete", name='Отмечаем выполненный заказ', status_code=status.HTTP_200_OK)
async def set_order_complete(complete_info: CompleteInfo) -> List[OrderOut]:
    conn = sql_pool.getconn()
    cur = conn.cursor()

    orders_data_output = []
    for orders_info in complete_info:
        for order in orders_info[1]:
            order = order.dict()
            courier_id = order["courier_id"]
            order_id = order["order_id"]
            complete_time = order["complete_time"]

            cur.execute(f"SELECT courier_id, completed_time, region, cost, weight, deliver_from, deliver_till "
                        f"FROM orders WHERE id = {order_id}")
            db_courier_time = cur.fetchone()

            def close_all(connection, cursor, connection_pool):
                connection.rollback()
                cursor.close()
                connection_pool.putconn(connection)
                return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content={})

            if db_courier_time is not None:  # Значит такой order_id есть в таблице
                db_courier_id, db_completed_time, db_region, db_cost, db_weight, db_deliver_from, \
                    db_deliver_till = db_courier_time

                if db_courier_id != courier_id and db_courier_id is not None:  # Нет или не совпадают courier_id
                    return close_all(conn, cur, sql_pool)

                if db_completed_time is None:  # Значит у этого order_id поле completed_time == Null
                    cur.execute(f"UPDATE orders SET completed_time = '{complete_time}' WHERE id = {order_id}")
                elif db_completed_time.replace(tzinfo=timezone.utc) == complete_time:
                    pass
                else:
                    return close_all(conn, cur, sql_pool)

                del order['courier_id']
                order = db_order_to_dict(order_id, db_weight, db_region, db_deliver_from,
                                         db_deliver_till, db_cost, complete_time)
                orders_data_output.append(order)
            else:
                return close_all(conn, cur, sql_pool)
    conn.commit()
    cur.close()
    sql_pool.putconn(conn)
    return orders_data_output


@router.post("/assign", name='Распределение заказов по курьерам', status_code=status.HTTP_201_CREATED)
def bruteforce_not_optimal_orders_assign(date: date = datetime.today().strftime('%Y-%m-%d')) -> List[AssignedOrders]:
    """Решение - не самый неоптимальный брутфорс. Логика следующая:
    1. Обрабатываем циклами все working_hours. Сначала для FOOT, затем BIKE, затем AUTO.
        Чтобы по возможности распределять заказы сначала для дешевых типов курьеров.
        Проблема - могут остаться дорогие заказы, которые будут распределяться на дорогих курьеров

    """
    """транзакции"""
    conn = sql_pool.getconn()
    conn.autocommit = False
    cur = conn.cursor()
    cur.execute("LOCK TABLE working_hours, couriers, orders IN ACCESS EXCLUSIVE MODE")

    db_working_hours = {}  # Список рабочих часов конкретного типа курьеров (FOOT|BIKE|AUTO)
    for c_type in courier_types:
        cur.execute(
            f"""SELECT working_hours.id, working_hours.work_from, working_hours.work_till, 
                        couriers.id FROM working_hours
                        INNER JOIN couriers ON working_hours.courier_id = couriers.id WHERE couriers.type = '{c_type}'
                        ORDER BY working_hours.work_till ASC, working_hours.work_from ASC"""
        )
        db_working_hours[c_type] = cur.fetchall()

    cur.execute(
        f"""SELECT id, region, cost, weight, deliver_from, deliver_till
            FROM orders WHERE batch_id IS NULL ORDER BY region ASC"""
    )
    db_orders = cur.fetchall()  # Список кортежей с данными о заказах
    orders_assigned = set()  # Множество id заказов, которые были распределены

    def orders_from_most_costed_region(orders: list, courier_type: str) -> list:
        """Из доступного списка заказов выбираем заказы из региона в котором максимльная сумма стоимостей заказов
            Это неоптимально с позиции алгоритмичной сложности решения, но позволяет сделать так, чтобы дешевые
            типы курьеров сначала обрабатывали дорогие заказы. Плюс мы сразу учитываем ограничение на количество
            регионов, которые может посетить курьер, чтобы иметь возможность объединить в один батч максимальное
            количество заказов
            Структура возвращаемого списка кортежей заказов:
            [(order_id, region, cost, weight, deliver_from, deliver_till), ...]
            """
        if orders is None:
            return []
        # Группируем заказы по региону и суммируем цены
        regions_cost = [(region, sum(i[2] for i in group)) for region, group in groupby(orders, key=itemgetter(1))]
        # Сортируем регионы по сумме цен, находим регионы с которых нужно начать распределять заказы
        regions_cost.sort(key=itemgetter(1), reverse=True)
        regions = set()  # Итоговые номера регионов из которых будем делать выборку заказов
        for num in range(min(c_max_regions[courier_type], len(regions_cost))):
            regions.add(regions_cost[num][0])
        orders_to_batch = [order for order in orders if order[1] in regions]  # Список заказов из дорогих регионов
        orders_to_batch.sort(key=itemgetter(5))  # Сразу сортируем по времени завершения заказа по возрастанию
        return orders_to_batch

    batches = defaultdict(list)
    """Итоговый список батчей, вносим в него батчи по ключу working_hours_id"""

    def time_to_minutes(t: time) -> int:
        return t.hour * 60 + t.minute

    def minutes_to_time(minutes: int) -> time:
        return time(minutes // 60, minutes % 60)

    def form_batch(time_from: time, time_till: time, batch: list, courier_id: int):
        """Формирует батчи заказов для данных каждого временного окна.
        На выходе: список батчей в формате: [[wh_id, start_time, fin_time, weight, [order_id`s]], ...]
        """
        free_weight = c_max_weight[c_type]  # Объявляем доступный вес заказа
        single_delivery_dur = c_first_order_dur[c_type]  # Объявляем длительность доставки 1 заказа
        if len(batches[wh_id]) > 0:  # Если батч не пустой
            time_from = batches[wh_id][-1][2]  # Обновляется время с которой начинается доставка
            single_delivery_dur = c_other_orders_dur[c_type]  # Обновляем длительность доставки
            free_weight = c_max_weight[c_type] - batches[wh_id][-1][3]  # Обновляем доступный вес
            """Если времени в интервале недостаточно для доставки - выход, отдаем список заказов батча"""
            if time_to_minutes(time_till) - time_to_minutes(time_from) < c_first_order_dur[c_type]:
                return None

        time_of_delivery = minutes_to_time(time_to_minutes(time_from) + single_delivery_dur)
        """Определяем время начиная с которого может быть выполнена ближайшая доставка"""

        orders = [order for order in db_orders
                  if order[3] <= free_weight  # Хватает веса
                  and order[5] > time_of_delivery  # Время исполнения больше чем мин время доставки
                  and time_of_delivery >= order[4] < time_till  # Время начала исполнения входит в интервал работы
                  and order[0] not in orders_assigned]  # Заказ еще не был назначен
        """Список нераспределенных заказов, которые подходят по времени и весу"""

        if orders:
            orders_to_batch = orders_from_most_costed_region(orders, c_type)
        else:
            return None
        """Список заказов из самых дорогих регионов"""

        def create_new_batch():
            start_time = max(del_from, time_of_delivery)
            fin_time = minutes_to_time(time_to_minutes(start_time) + single_delivery_dur)
            batch_temp = [wh_id, start_time, fin_time, o_weight, [order_id], courier_id]
            orders_assigned.add(order_id)
            return batch_temp

        def create_extra_batch():
            start_time = max(del_new_batch_time, del_from)
            fin_time = minutes_to_time(time_to_minutes(start_time) + single_delivery_dur)
            batch_temp = [wh_id, start_time, fin_time, o_weight, [order_id], courier_id]
            orders_assigned.add(order_id)
            return batch_temp

        for order in orders_to_batch:
            o_weight = order[3]
            del_from = order[4]
            del_till = order[5]
            order_id = order[0]
            if not batch:
                batch.append(create_new_batch())
            elif batch:
                free_weight = c_max_weight[c_type] - batch[-1][3]
                del_time = minutes_to_time(time_to_minutes(batch[-1][2]) + c_other_orders_dur[c_type])
                del_new_batch_time = minutes_to_time(time_to_minutes(batch[-1][2]) + c_first_order_dur[c_type])
                if (len(batch[-1][4]) < c_max_orders[c_type] and o_weight <= free_weight
                        and del_from < del_time < del_till):
                    batch[-1][3] += o_weight
                    batch[-1][2] = del_time
                    orders_assigned.add(order_id)
                    batch[-1][4].append(order_id)
                elif del_from < del_new_batch_time < del_till and del_new_batch_time < wh_till:
                    temp_batch = []
                    extra_batch = form_batch(del_new_batch_time, wh_till, temp_batch, courier_id)
                    if extra_batch:
                        for element in extra_batch:
                            batch.append(element)
                    break
                else:
                    return batch

        return batch

    wh_batch = []  # Итоговый список всех батчей в доставке
    for c_type in courier_types:
        for period in db_working_hours[c_type]:
            wh_id, wh_from, wh_till, c_id = period
            if time_to_minutes(wh_till) - time_to_minutes(wh_from) < c_first_order_dur[c_type]:
                pass
            temp_batch = []
            batch = form_batch(wh_from, wh_till, temp_batch, c_id)
            if batch:
                for element in batch:
                    wh_batch.append(element)

    couriers_batches = defaultdict(list)
    for batch in wh_batch:
        working_hours_id, start_deliver_time, end_deliver_time, total_weight, orders, courier_id = batch
        cur.execute(f"""INSERT INTO batches 
                        (date, start_deliver_time, courier_id, working_hours_id, total_orders, total_weight) 
                         VALUES ('{date}', '{start_deliver_time}', {courier_id}, 
                            {working_hours_id}, {len(orders)}, {total_weight}) 
                        RETURNING id""")
        batch_id = cur.fetchone()[0]
        orders_data = {"group_order_id": batch_id, "orders": []}
        order_pos = 0
        for order_id in orders:
            order_pos += 1
            cur.execute(f"""UPDATE orders 
                            SET batch_id = {batch_id}, courier_id = {courier_id}, position_in_batch = {order_pos} 
                            WHERE id = {order_id}
                            RETURNING weight, region, deliver_from, deliver_till, cost, completed_time""")
            order_data = cur.fetchone()
            weight, regions, del_from, del_till, cost, completed_time = order_data
            order = db_order_to_dict(order_id, weight, regions, del_from, del_till, cost, completed_time)
            orders_data["orders"].append(order)
        couriers_batches[courier_id].append(orders_data)

    couriers = []
    for key in couriers_batches.keys():
        couriers.append({"courier_id": key, "orders": couriers_batches[key]})

    conn.commit()
    cur.close()
    sql_pool.putconn(conn)
    response = [{"date": date, "couriers": couriers}]
    return response


@router.get("/{order_id}", name='Получение информации о заказе', status_code=status.HTTP_200_OK)
async def order_info(order_id: int) -> OrderOut:
    conn = sql_pool.getconn()
    cur = conn.cursor()

    cur.execute(f"""SELECT completed_time, region, cost, weight, deliver_from, deliver_till 
                    FROM orders WHERE id = {order_id}""")
    db_order = cur.fetchone()

    cur.close()
    sql_pool.putconn(conn)

    if db_order is None:
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={})

    db_completed_time, db_region, db_cost, db_weight, db_deliver_from, db_deliver_till = db_order
    order = db_order_to_dict(order_id, db_weight, db_region, db_deliver_from,
                             db_deliver_till, db_cost, db_completed_time)
    return order
