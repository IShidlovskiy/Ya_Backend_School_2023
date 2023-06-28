import pytest
from httpx import AsyncClient
from app.main import app

couriers = [{
    "courier_id": 1,
    "type": "FOOT",
    "region": [
      1,
      2,
      3
    ],
    "working_hours": [
      "10:00-12:00",
      "15:00-17:00"
    ]
  },
{
    "courier_id": 2,
    "type": "BIKE",
    "region": [
      1,
      2,
      3
    ],
    "working_hours": [
      "10:00-12:00",
      "15:00-17:00"
    ]
  },
{
    "courier_id": 3,
    "type": "AUTO",
    "region": [
      1,
      2,
      3
    ],
    "working_hours": [
      "10:00-12:00",
      "15:00-17:00"
    ]
  },
]

wrong_couriers_time = [{
    "courier_id": 3,
    "type": "AUTO",
    "region": [
      1,
      2,
      3
    ],
    "working_hours": [
      "1000-12:00",
      "15:00-17:00"
    ]
  },
]
wrong_couriers_id = [{
    "courier_id": 'Saruman',
    "type": "AUTO",
    "region": [
      1,
      2,
      3
    ],
    "working_hours": [
      "10:00-12:00",
      "15:00-17:00"
    ]
  },
]
wrong_couriers_type = [{
    "courier_id": 3,
    "type": "RUNNING",
    "region": [
      1,
      2,
      3
    ],
    "working_hours": [
      "10:00-12:00",
      "15:00-17:00"
    ]
  },
]
wrong_couriers_region_str = [{
    "courier_id": 3,
    "type": "AUTO",
    "region": [
      'Mordor'
    ],
    "working_hours": [
      "10:00-12:00",
      "15:00-17:00"
    ]
  },
]
wrong_couriers_region_less_than1 = [{
    "courier_id": 3,
    "type": "AUTO",
    "region": [
      -1, 0
    ],
    "working_hours": [
      "10:00-12:00",
      "15:00-17:00"
    ]
  },
]
@pytest.mark.asyncio
async def test_import_couriers():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.post("/couriers", json=couriers)
    assert response.status_code == 200, "Валидный JSON не принят"


@pytest.mark.asyncio
async def test_import_couriers_no_data():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.post("/couriers")
    assert response.status_code == 400, "Неверный ответ сервера"


@pytest.mark.asyncio
async def test_import_couriers_wrong_time():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.post("/couriers", json=wrong_couriers_time)
    assert response.status_code == 400, "Неверный ответ сервера"


@pytest.mark.asyncio
async def test_import_couriers_wrong_id():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.post("/couriers", json=wrong_couriers_id)
    assert response.status_code == 400, "Неверный ответ сервера"


@pytest.mark.asyncio
async def test_import_couriers_wrong_type():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.post("/couriers", json=wrong_couriers_type)
    assert response.status_code == 400, "Неверный ответ сервера"


@pytest.mark.asyncio
async def test_import_couriers_wrong_region_str():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.post("/couriers", json=wrong_couriers_region_str)
    assert response.status_code == 400, "Неверный ответ сервера"


@pytest.mark.asyncio
async def test_import_couriers_wrong_region_2_less_than1():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.post("/couriers", json=wrong_couriers_region_less_than1)
    assert response.status_code == 400, "Неверный ответ сервера"


@pytest.mark.asyncio
async def test_get_one_courier():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/couriers")
    assert response.status_code == 200, "Неверный ответ сервера"
    assert response.json() == {"couriers": [couriers[0]], 'limit': 1, 'offset': 0}, "Неверная выдача"


@pytest.mark.asyncio
async def test_get_all_couriers():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/couriers?limit=3&offset=0")
    assert response.status_code == 200, "Server error"
    assert response.json() == {"couriers": couriers, 'limit': 3, 'offset': 0}, "Неверная выдача"

