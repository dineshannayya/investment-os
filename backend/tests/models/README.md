tests/
├── models/
│   ├── test_base.py
│   ├── test_mixins.py
│   ├── test_enums.py
│   ├── test_startup.py
│   ├── test_founder.py
│   ├── test_opportunity.py
│   ├── test_document.py
│   ├── test_investment.py
│   └── test_model_relationships.py
│
├── fixtures.py
└── conftest.py

Implementation order


conftest.py (engine, session, fixtures)

test_enums.py

test_base.py

test_mixins.py

test_startup.py

test_founder.py

test_opportunity.py

test_document.py

test_investment.py

test_model_relationships.py


conftest.py
    FastAPI
    Client
    Settings

database.py
    Engine
    Session
    Transaction

fixtures.py
    Startup
    Founder
    Opportunity
    Document
    Investment
