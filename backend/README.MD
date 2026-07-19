backend/

app/
│
├── main.py
│
├── core/
│   ├── config.py
│   ├── logging.py
│   ├── security.py
│   ├── dependencies.py
│   ├── constants.py
│   └── enums.py
│
├── db/
│   ├── base.py
│   ├── session.py
│   ├── database.py
│   ├── models/
│   └── migrations/
│
├── common/
│   ├── exceptions.py
│   ├── responses.py
│   ├── pagination.py
│   ├── filters.py
│   ├── validators.py
│   └── utils.py
│
├── api/
│   └── v1/
│       ├── router.py
│       ├── health.py
│       └── startup.py
│
├── startup/
│   ├── models.py
│   ├── schemas.py
│   ├── repository.py
│   ├── service.py
│   └── routes.py
│
└── tests/
