# 0005 — Modelo de evidência

Status: aceita. Schema 0.1.0. Source guarda documento e identificadores; Evidence guarda trecho e campos clínicos opcionais; Claim guarda texto e evidence_ids. Relações validadas no servidor. Campos desconhecidos são nulos, não inferidos do país da revista nem da afiliação. Tamanho amostral positivo quando disponível; natureza documental e estudo distinguíveis.

Estados separados: metadado recuperado, trecho conferido, suporte semântico não avaliado. Não atribuir GRADE automaticamente. Suporte, oposição e contexto são relações explícitas, inicialmente contexto. Ampliações incompatíveis exigem nova versão/migração. Primeira extração é de trechos de abstracts; extração clínica estruturada e classificação detalhada ficam para próxima fase.
