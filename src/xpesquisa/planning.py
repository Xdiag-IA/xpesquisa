import re
import unicodedata
from urllib.parse import urlencode

from .models import Plan, ResearchRequest, SearchTask


def normalized(text: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", text.lower()) if not unicodedata.combining(c))


def brazil_terms(question: str) -> str:
    text = normalized(question).replace("artifical", "artificial")
    topics = [(r"inteligencia artificial|\bia\b", "inteligência artificial"),
              (r"elastograf", "elastografia"), (r"esteatos|masld|gordura no figado", "esteatose"),
              (r"telemedicina", "telemedicina"), (r"publicidade", "publicidade médica"),
              (r"prontuario", "prontuário"), (r"hepatite", "hepatite"), (r"cirrose", "cirrose")]
    for pattern, terms in topics:
        if re.search(pattern, text):
            return terms
    stop = set("a as o os um uma uns umas e de da das do dos em no na nos nas por para sobre com como qual quais que se ao aos pelo pela medico medicos medicina brasil brasileira brasileiro uso lei leis define evidencia atual sociedade sociedades pesquisa pesquisar conselho federal regional".split())
    words = [w for w in re.findall(r"[\w-]+", question.lower()) if normalized(w) not in stop and len(w) > 2]
    return " ".join(words[:7]) or question.strip()


def plan_research(request: ResearchRequest) -> Plan:
    text = normalized(request.question)
    regulatory = bool(re.search(r"\b(lei|leis|legal|legais|cfm|crm|crms|resolucao|resolucoes|regulacao|regulamentacao|etica|norma|normas)\b", text))
    intent = request.scope if request.scope != "auto" else ("regulation" if regulatory else "brazil" if re.search(r"brasil|brasileir", text) else "literature")
    local_query = request.query or brazil_terms(request.question)
    if intent == "regulation":
        searches = [SearchTask(connector="cfm", label="CFM e CRMs — normas", query=local_query,
                               reason="Pergunta normativa: pesquisar resoluções e pareceres na base dos conselhos.",
                               manual_url="https://portal.cfm.org.br/buscar-normas-cfm-e-crm/?" + urlencode([("texto", local_query), ("uf", request.uf or ""), ("tipo[]", "R"), ("tipo[]", "P")])),
                    SearchTask(connector="legislation_pending", label="Legislação federal / Diário Oficial", query=local_query,
                               reason="Normas profissionais não substituem leis federais. Integração automática pendente.",
                               manual_url="https://www.planalto.gov.br/ccivil_03/")]
        plan = Plan(interpretation="Pesquisar normas profissionais brasileiras; não tratar a pergunta como busca de artigos biomédicos.",
                    query=local_query, strategy="Roteamento normativo para CFM/CRMs; legislação federal indicada como lacuna.",
                    intent="regulation", searches=searches,
                    limitations=["Consulta inicial de resoluções e pareceres. A ementa não substitui a leitura integral da norma.",
                                 "Situação normativa é a declarada pela base consultada, não parecer jurídico ou verificação de vigência independente."])
    else:
        plan = literature_plan(request, text)
        plan.intent = intent
        plan.searches = [SearchTask(connector="europe_pmc", label="Europe PMC", query=plan.query,
                                   reason="Literatura científica internacional; registros MED no exemplo hepático.")]
        if intent == "brazil":
            plan.searches.extend([
                SearchTask(connector="bvs_pending", label="BVS / LILACS", query=local_query,
                           reason="Literatura latino-americana; conector pendente, acesso automatizado bloqueado no diagnóstico inicial.",
                           manual_url="https://search.bvsalud.org/portal/?" + urlencode({"q": local_query})),
                SearchTask(connector="scielo_pending", label="SciELO", query=local_query,
                           reason="Coleções científicas brasileiras; integração automática ainda não implementada.",
                           manual_url="https://search.scielo.org/?" + urlencode({"q": local_query, "lang": "pt"}))])
    # Explicit international-only mode is available; auto still includes relevant Brazilian societies.
    if request.scope != "literature":
        if re.search(r"hepat|figado|esteatos|cirrose|masld", text):
            plan.searches.append(SearchTask(connector="sbh", label="Sociedade Brasileira de Hepatologia", query=local_query,
                                             reason="Tema hepático: consultar publicações institucionais da especialidade."))
        if re.search(r"radiolog|elastograf|ultrassom|ultrasson|diagnostico por imagem", text):
            plan.searches.append(SearchTask(connector="cbr", label="Colégio Brasileiro de Radiologia", query=local_query,
                                             reason="Tema de diagnóstico por imagem: consultar a sociedade da especialidade."))
    plan.limitations.append("Direcionamento por regras e vocabulário inicial, não compreensão universal. Catálogo de sociedades ainda limitado a SBH e CBR.")
    return plan


def literature_plan(request: ResearchRequest, text: str) -> Plan:
    if request.query:
        return Plan(interpretation=request.question, query=request.query, strategy="Query fornecida pelo usuário",
                    limitations=["Estratégia não validada por bibliotecário ou especialista."])
    if "elastograf" in text and any(w in text for w in ("hepat", "figado", "fibros")):
        return Plan(
            interpretation="Mapear literatura sobre elastografia hepática e avaliação de fibrose, sem restringir etiologia.",
            query='(elastography OR "liver stiffness") AND (liver OR hepatic) AND fibrosis AND SRC:MED',
            strategy="Vocabulário inicial explícito pt-BR → inglês; recorte de registros MED no Europe PMC",
            intervention="Elastografia hepática", outcome="Avaliação de fibrose hepática",
            limitations=["População e comparador não definidos; busca exploratória, não revisão sistemática.",
                         "Ordenação por relevância da fonte, sem garantia de exaustividade ou atualização clínica."])
    if re.search(r"esteatos|masld|gordura no figado", text):
        query = '("hepatic steatosis" OR "fatty liver" OR MASLD OR NAFLD)'
        if "prevalencia" in text:
            query += " AND prevalence"
        if re.search(r"brasil|brasileir", text):
            query += " AND (Brazil OR Brazilian)"
        return Plan(interpretation=request.question, query=query + " AND SRC:MED",
                    strategy="Vocabulário explícito pt-BR → inglês para esteatose; Brasil como termo, não prova do país da população.",
                    limitations=["Busca lexical inicial; não identifica automaticamente a população ou sintetiza prevalência."])
    return Plan(interpretation=request.question, query=request.question,
                strategy="Pergunta literal; revise a estratégia em inglês no campo de busca",
                limitations=["Tradução automática e decomposição PICO geral ainda não implementadas."])
