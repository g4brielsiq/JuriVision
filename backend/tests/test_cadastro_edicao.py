"""
Testes do Cadastro e Edição Manual de Processos (RF-08 / RN-01).
- CT-10: POST /api/v1/processos cria processo (201) com partes e resumo anonimizados.
- CT-11: Validações de entrada (422) e número CNJ duplicado (409).
- CT-12: PUT /api/v1/processos/{id} edita o processo, preserva máscaras e reaplica a barreira LGPD.
- CT-13: PUT em processo inexistente (404) e PUT com número CNJ de outro processo (409).
"""
from typing import Iterator
import uuid

from fastapi.testclient import TestClient
import pytest

from app.main import app, init_db_and_seed


@pytest.fixture(scope="module")
def client() -> Iterator[TestClient]:
    init_db_and_seed()
    with TestClient(app) as test_client:
        yield test_client


def _numero_cnj_unico() -> str:
    """Gera um número CNJ válido e único para não colidir com dados existentes no banco."""
    seq = uuid.uuid4().int % 10_000_000
    return f"{seq:07d}-{uuid.uuid4().int % 100:02d}.2025.8.02.0001"


def _payload(**overrides) -> dict:
    base = {
        "numero_processo": _numero_cnj_unico(),
        "tema": "Dano Moral",
        "magistrado": "Dr. Rafael De Amorim",
        "comarca": "1ª Vara Cível de Maceió",
        "autor": "Maria Aparecida Santos",
        "reu": "Banco do Brasil S.A.",
        "resumo": "Autora: Maria Aparecida Santos, CPF 123.456.789-00, teve o nome negativado indevidamente.",
        "resultado": "Procedente",
        "data_julgamento": "2025-08-15",
    }
    base.update(overrides)
    return base


def test_ct10_cadastro_manual_anonimiza_partes_e_resumo(client: TestClient):
    payload = _payload()
    resp = client.post("/api/v1/processos", json=payload)
    assert resp.status_code == 201, resp.text
    body = resp.json()

    meta = body["metadados_extraidos"]
    assert body["id_processo"].startswith("proc-")
    assert meta["numero_processo"] == payload["numero_processo"]
    assert meta["tema"] == "Dano Moral"
    # RN-01: pessoa física mascarada, pessoa jurídica preservada
    assert "Maria Aparecida Santos" not in meta["partes_anonimizadas"]["autor"]
    assert "***" in meta["partes_anonimizadas"]["autor"]
    assert meta["partes_anonimizadas"]["reu"] == "Banco do Brasil S.A."
    # RN-01: resumo sem CPF nem nome completo
    assert "123.456.789-00" not in body["resumo_nlp"]
    assert "Maria Aparecida Santos" not in body["resumo_nlp"]
    assert body["auditoria_lgpd"]["total_cpfs_mascarados"] >= 1
    assert 0.0 <= body["analise_preditiva"]["probabilidade_deferimento"] <= 1.0

    # O processo cadastrado aparece na consulta e no detalhe
    lista = client.get("/api/v1/processos", params={"busca": payload["numero_processo"]}).json()
    assert lista["total"] == 1
    detalhe = client.get(f"/api/v1/processos/{body['id_processo']}")
    assert detalhe.status_code == 200


@pytest.mark.parametrize(
    "campo, valor",
    [
        ("numero_processo", "123"),          # fora do formato CNJ
        ("resultado", "Ganhou"),             # fora dos valores permitidos
        ("tema", ""),                        # obrigatório
        ("resumo", "curto"),                 # mínimo de 10 caracteres
        ("data_julgamento", "15/08/2025"),   # formato de data inválido
    ],
)
def test_ct11_cadastro_validacoes_retorna_422(client: TestClient, campo: str, valor: str):
    resp = client.post("/api/v1/processos", json=_payload(**{campo: valor}))
    assert resp.status_code == 422


def test_ct11_cadastro_numero_duplicado_retorna_409(client: TestClient):
    payload = _payload()
    assert client.post("/api/v1/processos", json=payload).status_code == 201
    resp = client.post("/api/v1/processos", json=_payload(numero_processo=payload["numero_processo"]))
    assert resp.status_code == 409


def test_ct12_edicao_atualiza_campos_e_reaplica_lgpd(client: TestClient):
    criado = client.post("/api/v1/processos", json=_payload(resultado="Em Analise")).json()
    id_proc = criado["id_processo"]
    meta = criado["metadados_extraidos"]

    # Simula o formulário de edição: reenvia os nomes já mascarados e troca outros campos
    edicao = _payload(
        numero_processo=meta["numero_processo"],
        tema="Direito do Consumidor",
        comarca="2ª Vara Cível de Arapiraca",
        autor=meta["partes_anonimizadas"]["autor"],
        reu="José Carlos Pereira",
        resumo="Requerente alega cobrança indevida. RG: 1234567 informado na inicial.",
        resultado="Improcedente",
    )
    resp = client.put(f"/api/v1/processos/{id_proc}", json=edicao)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    novo_meta = body["metadados_extraidos"]

    assert body["id_processo"] == id_proc
    assert novo_meta["tema"] == "Direito do Consumidor"
    assert novo_meta["comarca"] == "2ª Vara Cível de Arapiraca"
    assert novo_meta["partes_anonimizadas"]["autor"] == meta["partes_anonimizadas"]["autor"]  # máscara preservada
    assert "José Carlos Pereira" not in novo_meta["partes_anonimizadas"]["reu"]
    assert "1234567" not in body["resumo_nlp"]

    item = client.get("/api/v1/processos", params={"busca": meta["numero_processo"]}).json()["itens"][0]
    assert item["resultado"] == "Improcedente"


def test_ct13_edicao_inexistente_404_e_numero_de_outro_processo_409(client: TestClient):
    assert client.put("/api/v1/processos/proc-nao-existe", json=_payload()).status_code == 404

    primeiro = client.post("/api/v1/processos", json=_payload()).json()
    segundo = client.post("/api/v1/processos", json=_payload()).json()
    numero_do_primeiro = primeiro["metadados_extraidos"]["numero_processo"]

    resp = client.put(f"/api/v1/processos/{segundo['id_processo']}", json=_payload(numero_processo=numero_do_primeiro))
    assert resp.status_code == 409
