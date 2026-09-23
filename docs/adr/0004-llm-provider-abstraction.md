# 0004 — Providers

Status: aceita. Protocolo Python `SynthesisProvider`, entrada com fontes/evidências, saída estruturada com IDs. Implementações: síntese extrativa sem LLM e Ollama local opcional. Nenhuma chamada paga por padrão. Extensão futura para OpenAI, Anthropic, Gemini, Groq, OpenRouter e endpoints compatíveis sem tipos proprietários no domínio.

Modelo local deve ser previamente instalado pelo operador; não baixar modelos automaticamente. Registrar provider, modelo, parâmetros, prompt e hashes. Saída LLM é rascunho não verificado; IDs inexistentes são rejeitados. A checagem de citações não valida significado. Falhas mantêm resultado extrativo e evento de degradação. Credenciais futuras via ambiente; nunca persistir segredos em provenance.
