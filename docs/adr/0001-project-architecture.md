# 0001 — Arquitetura modular local

Status: aceita para o marco inicial. Data: 2026-09-23.

Monólito modular: API → planejamento → conector → seleção → extração → verificação estrutural → síntese → persistência. Contratos Pydantic entre etapas. SQLite guarda pesquisas e eventos; JSON versionado facilita inspeção e futura migração. Sem microserviços, vector store ou orquestrador multiagente agora. Reviewer e cético entram quando houver avaliação de ganho funcional. Sem acoplamento a Maya/ELASTUS.

Alternativa: LangGraph e múltiplos agentes. Adiada por custo, depuração e ausência de ganho demonstrado. Toda afirmação aponta para evidências existentes; conteúdo externo é dado não confiável, nunca instrução.
