# Решение вступительного задания по направлению Python

## Основные особенности

- Реализованы все эндпоинты задания и допзаданий.
- Схема таблиц базы данных прописана в /app/db/schemas.py
- Верификация всех входящих и выходящих данных происходит с использованием pydentic. Валидируемые классы находятся в каталоге /app/schemas/
- Эндпоинты разнесены по типу (для courier и для order) и находятся в каталоге /app/handlers/
- Для того чтобы заместить стандартную для FastApi генерацию ответа при ошибке 422 ValidationError, используется функция из /app/extra/error_handler.py. Решение о замещении принято на основе JSON схемы задания, в которой не предполагается отправка кода 422.
- Ограничение количества запросов в 10 RPS сделано с использованием slowapi

### Отдельно нужно обратить внимание на логику работы эндпоинта "POST /orders/assign":
- При выгрузке данных о рабочих часах он не учитывает уже сформированные партии заказов на текущую дату.
- Из-за этого, при использовании этой функции больше одного раза за день (например, если в середине дня поступил новый заказ и его попробовали распределить) - заказ будет распределен, но время доставки с огромной вероятностью наложится на уже другую существующую доставку.
- Эту недоработку можно исправить, но сейчас не хватило времени. Кроме того, в ReadMe файле задания было указано, что данный эндпоинт используется только перед началом рабочего дня.
- Итог: при получении кода 200 в ответе для назначения заказов, все последующие обращения к эндпоинту приведут к наложению доставок друг на друга.
- Отдельно: решение - брутфорс, с очень высоким значением Time Complexity. Потенциально, задача может быть решена с использованием типовых алгоритмов для подобных задач, либо используя пакеты нелинейной или бинарной оптимизации. Для реализации такого решения нужно больше времени. Как потенциальный ориентир - Scheduling Algorithms by Peter Brucker.
- Текущая логика следующая: самые дорогие заказы распределяем на самых дешевых исполнителей для минимизации затрат на оплату труда. Но при этом именно дорогие заказы выгружаем в первую очередь, чтобы они по возможности были точно выполнены.


## Команды для запуска вне Docker-файла:
Для создания миграции:

```alembic -c app/alembic.ini revision --autogenerate -m "DB creation"```

Для приведения таблиц в БД в соответствие со схемой:

```alembic -c app/alembic.ini upgrade head ```

Для запуска приложения:

```uvicorn app.main:app --host '0.0.0.0'--port 8080 --reload```

## Тестирование:
Тесты в папке с заданием уже утратили свою актуальность (не были актуализированы после первого формирования и прогонов).

Однако после запуска приложения, по адресу ip:8080/docs доступна интерактивная JSON схема, которая позволяет проверять работу эндпоинтов. При этом нужно учитывать, что приложение должно быть подключено к тестовой базе данных.