# 0002 — Backend

Status: aceita. Python >=3.10, FastAPI, Pydantic 2, HTTPX, SQLite da biblioteca padrão e Uvicorn. Python disponível localmente é 3.10; manter compatibilidade enquanto houver suporte das dependências. FastAPI fornece contratos e OpenAPI sem estrutura adicional. Django seria útil com administração e autenticação multiusuário; não é necessário neste marco. SQLite evita serviço externo; snapshots versionados não substituem migrações relacionais futuras. Uma instância local, sem promessa de escala horizontal.
