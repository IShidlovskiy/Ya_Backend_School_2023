from sqlalchemy import MetaData, Table, Column, Integer, Enum, ForeignKey, Time, DateTime, Float, Date, Numeric

metadata = MetaData()

# Restriction on available courier types
courier_type = Enum("FOOT", "BIKE", "AUTO", name="courier_type")

# DB tables structure
couriers = Table(
    "couriers",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("type", courier_type, nullable=False)
)

orders = Table(
    "orders",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("region", Integer, nullable=False),
    Column("cost", Integer),
    Column("weight", Numeric(asdecimal=False)),
    Column("deliver_from", Time, nullable=False),
    Column("deliver_till", Time, nullable=False),
    Column("completed_time", DateTime, nullable=True),
    Column("courier_id", Integer, ForeignKey("couriers.id"), nullable=True),
    Column("batch_id", Integer, ForeignKey("batches.id"),nullable=True),  # В какой партии доставлялся заказ
    Column("position_in_batch", Integer, nullable=True),  # Для учета заработка курьера (0,8 для не первых заказов)
)

working_hours = Table(
    "working_hours",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("courier_id", Integer, ForeignKey("couriers.id")),
    Column("work_from", Time, nullable=False),
    Column("work_till", Time, nullable=False),
    Column("num_orders_delivering", Integer, nullable=True),
)

regions = Table(
    "regions",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("region", Integer, nullable=False),
    Column("courier_id", Integer, ForeignKey("couriers.id"))
)

batches = Table(
    "batches",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("date", Date, nullable=True),
    Column("start_deliver_time", Time, nullable=False),
    Column("courier_id", Integer, ForeignKey("couriers.id"), nullable=False),
    Column("working_hours_id", Integer, ForeignKey("working_hours.id"), nullable=False),
    Column("total_orders", Integer, nullable=False),
    Column("total_weight", Numeric(asdecimal=False), nullable=True)
)
