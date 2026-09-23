import unicodedata

from .models import Plan, ResearchRequest


def plan_research(request: ResearchRequest) -> Plan:
    normalized = "".join(c for c in unicodedata.normalize("NFKD", request.question.lower()) if not unicodedata.combining(c))
    if request.query:
        return Plan(interpretation=request.question, query=request.query, strategy="Query fornecida pelo usuário",
                    limitations=["Estratégia não validada por bibliotecário ou especialista."])
    if "elastograf" in normalized and any(w in normalized for w in ("hepat", "figado", "fibros")):
        return Plan(
            interpretation="Mapear literatura sobre elastografia hepática e avaliação de fibrose, sem restringir etiologia.",
            query='(elastography OR "liver stiffness") AND (liver OR hepatic) AND fibrosis AND SRC:MED',
            strategy="Vocabulário inicial explícito pt-BR → inglês; recorte de registros MED no Europe PMC",
            intervention="Elastografia hepática", outcome="Avaliação de fibrose hepática",
            limitations=["População e comparador não definidos; busca exploratória, não revisão sistemática.",
                         "Ordenação por relevância da fonte, sem garantia de exaustividade ou atualização clínica."])
    return Plan(interpretation=request.question, query=request.question,
                strategy="Pergunta literal; revise a estratégia em inglês no campo de busca",
                limitations=["Tradução automática e decomposição PICO geral ainda não implementadas."])
