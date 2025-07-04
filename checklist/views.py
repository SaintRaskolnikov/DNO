import json
import os
from urllib.parse import quote
from django.http import HttpResponseNotFound, JsonResponse
from django.shortcuts import render
from checklist.utils import load_disease_data
from urllib.parse import unquote
from django.utils.text import slugify
from dno import settings

STEPS_JSON_PATH = os.path.join(settings.BASE_DIR, 'checklist', 'data', 'steps', 'steps.json')

def landing(request):
    """
    Render the landing page with a list of diseases.
    Filter diseases by search query if present.
    """
    diseases_dir = os.path.join(settings.BASE_DIR, 'checklist', 'data', 'diseases')

    try:
        all_files = os.listdir(diseases_dir)
    except FileNotFoundError:
        all_files = []

    # Remove .json and extract disease names
    diseases = [f.replace(".json", "") for f in all_files if f.endswith(".json")]

    query = request.GET.get('default-search', '').strip()
    print(f"Search query: {query}")

    # Filtra resultados
    if query:
        filtered = [d for d in diseases if query.lower() in d.lower()]
    else:
        filtered = diseases

    # Gera (nome, url_segura) para cada doença
    results = [(d, f"/checklist/{quote(d)}") for d in filtered]

    return render(request, 'landing.html', {'results': results, 'query': query})




def checklist_view(request, dno):
    try:
        with open(STEPS_JSON_PATH, encoding='utf-8') as f:
            steps = json.load(f)
    except FileNotFoundError:
        # fallback para lista vazia ou erro controlado
        steps = []
    except json.JSONDecodeError:
        # lidar com erro de parsing
        steps = []

    dno_decoded = unquote(dno)  # Decodifica %C3%A7 etc.
    selected_disease = dno_decoded.strip()

    criteria = load_disease_data(selected_disease)
    if not criteria:
        return HttpResponseNotFound(f"Critérios para a doença '{selected_disease}' não encontrados.")


    # Extract criteria
    criterios_clinicos_raw = criteria.get("criterios_clinicos", {})
    criterios_laboratoriais_raw = criteria.get("criterios_laboratoriais", {})
    criterios_epidemiologicos = criteria.get("criterios_epidemiologicos", {})
    classificacoes = criteria.get("classificacao_caso", {})

    # Format clinical keys for display (e.g., snake_case → Capitalized Title)
    criterios_clinicos = {}
    for key, value in criterios_clinicos_raw.items():
        formatted_key = key.replace("_", " ").capitalize()
        criterios_clinicos[formatted_key] = value


    criterios_laboratoriais = {}
    for key, value in criterios_laboratoriais_raw.items():
        formatted_key = key.replace("_", " ").capitalize()
        criterios_laboratoriais[formatted_key] = value


    classificacao_atual = None

    if request.method == "POST":
        post_data = request.POST
        print("Received POST data:", post_data)

        def count_checked(prefix):
            return len([k for k in post_data.keys() if k.startswith(prefix)])

        # CLINICAL
        cli_count = count_checked("cli_")
        epi_count = count_checked("epi_")

        # LAB
        criterios_laboratoriais_items = list(criterios_laboratoriais.items())  # lista de (doenca_nome, dados)

        lab_conf_count = 0
        lab_prov_count = 0

        for key in request.POST.keys():
            if key.startswith("lab_"):
                # Esperamos formato: lab_{disease_index}_{group}_{item_index}
                parts = key.split("_")
                if len(parts) == 4:
                    _, disease_idx_str, group_name, item_idx_str = parts
                    try:
                        disease_idx = int(disease_idx_str)
                        item_idx = int(item_idx_str)
                    except ValueError:
                        continue  # não é formato esperado

                    if disease_idx < len(criterios_laboratoriais_items):
                        doenca_nome, doenca_dados = criterios_laboratoriais_items[disease_idx]
                        grupos = doenca_dados.get("grupos", {})
                        grupo_itens = grupos.get(group_name, {})
                        # Só conta se o item existir mesmo na estrutura
                        if str(item_idx) in grupo_itens:
                            if group_name == "confirmado":
                                lab_conf_count += 1
                            elif group_name == "provavel":
                                lab_prov_count += 1

        # Now evaluate classification
        classificacoes = criteria.get("classificacao_caso", {})
        print("Classificações disponíveis:", classificacoes)
        classificacao_atual = ""

        # Order matters: check 'confirmado' first
        prioridade = ["confirmado", "provavel", "possivel"]
        classificacoes_ordenadas = sorted(classificacoes.items(), key=lambda x: prioridade.index(x[0]))

        for nome, valores in classificacoes_ordenadas:
            if (
                (valores.get("cli", 0) == 0 or cli_count >= valores["cli"]) and
                (valores.get("epi", 0) == 0 or epi_count >= valores["epi"]) and
                (valores.get("lab_conf", 0) == 0 or lab_conf_count >= valores["lab_conf"]) and
                (valores.get("lab_prov", 0) == 0 or lab_prov_count >= valores["lab_prov"])
            ):
                classificacao_atual = nome
                break
        if classificacao_atual:
            if classificacao_atual == "confirmado":
                classificacao_atual = "Confirmado"
            elif classificacao_atual == "provavel":
                classificacao_atual = "Provável"
            elif classificacao_atual =="possivel":
                classificacao_atual = "Possível"
            else:
                pass
            

        # Handle AJAX POST
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            print(f"AJAX POST classification {classificacao_atual}")
            return JsonResponse({"classificacao_atual": classificacao_atual})
        print("EPI count:", epi_count)
        print("LAB CONF count:", lab_conf_count)
        print("LAB PROV count:", lab_prov_count)

    context = {
        "selected_disease": selected_disease.capitalize(),
        "dno":selected_disease,
        "criterios_clinicos": criterios_clinicos,
        "criterios_laboratoriais": criterios_laboratoriais,
        "criterios_epidemiologicos": criterios_epidemiologicos,
        "classificacao_do_caso": classificacoes,
        "classificacao_atual": classificacao_atual,
        "steps": steps
    }

    return render(request, 'checklist.html', context)




