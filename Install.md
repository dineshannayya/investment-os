

git clone https://github.com/dineshannayya/investment-os.git
cd investment-os
docker compose up -d

Then access:


| URL             | Purpose        |
| --------------- | -------------- |
| localhost:3000  | Next.js UI     |
| localhost:8000  | FastAPI API    |
| localhost:5432  | PostgreSQL     |
| localhost:9000  | MinIO (later)  |
| localhost:11434 | Ollama (later) |


# Step 1 - Repository Structure

investment-os/
│
├── backend/
│   ├── app/
│   ├── requirements/
│   ├── alembic/
│   ├── tests/
│   └── Dockerfile
│
├── frontend/
│   ├── app/
│   ├── public/
│   ├── components/
│   └── Dockerfile
│
├── docker/
│   ├── postgres/
│   ├── redis/
│   └── scripts/
│
├── docs/
├── scripts/
├── .github/
├── docker-compose.yml
├── .env.example
├── Makefile
├── README.md
└── LICENSE
