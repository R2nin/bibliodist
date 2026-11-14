"""
Testes da aba Revisão PRISMA.

Os registros abaixo seguem exatamente o formato devolvido pela API do Acervo
Digital da FEMA (os dois primeiros são reais, com resumo encurtado; os demais
são fictícios para cobrir os casos de exclusão). Nenhum teste acessa a internet.
"""
from unittest import mock

from django.core.cache import cache
from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from .prisma import acervo_fema
from .prisma.consulta import ErroConsulta, normalizar_texto, parse
from .prisma.pipeline import Criterios, executar

REG_BLOCKCHAIN_DOCS = {
    "id": 26405, "tombo_inicial": "6344", "tipo": "TCC",
    "titulo": "SISTEMA DE GERENCIAMENTO DE DOCUMENTOS EDUCACIONAIS BASEADO EM BLOCKCHAIN",
    "editora": "IMESA", "exemplares": 1, "classificacao": "TCC 2111600150",
    "participantes": ["Orientador: GUILHERME DE CLEVA FARTO",
                      "Orientado: FELIPE ARAÚJO DE ALMEIDA ( 2111600150 )"],
    "curso": "BCC",
    "palavras_chave": "SISTEMA DE GERENCIAMENTO DE DOCUMENTOS EDUCACIONAIS BASEADO EM BLOCKCHAIN; "
                      "BLOCKCHAIN, ENSINO, DOCUMENTOS;GUILHERME DE CLEVA FARTO; FELIPE ARAÚJO DE ALMEIDA; 2024",
    "resumo": "A gestão de documentos estudantis é um desafio constante para instituições de ensino,\r\n"
              "especialmente quando se trata de garantir a autenticidade e a segurança desses\r\ndocumentos.",
    "uuid_arquivo": "uSwXEhVQgb9ZRSl8", "ano": "2024", "busca": "...",
    "referencia_bibliografica": None, "podeReservar": False,
}
REG_BLOCKCHAIN_PUBLICO = {
    **REG_BLOCKCHAIN_DOCS, "id": 25657, "ano": "2022",
    "titulo": "O USO DE BLOCKCHAIN E POTENCIAIS PRÁTICAS NO SETOR PÚBLICO BRASILEIRO",
    "participantes": ["Orientador: FULANO ORIENTADOR", "Orientado: CICLANO ALUNO ( 1 )"],
    "palavras_chave": "O USO DE BLOCKCHAIN...; BLOCKCHAIN, SETOR PÚBLICO, CONTRATO INTELIGENTE; X; Y; 2022",
    "resumo": "Estudo sobre contratos inteligentes e blockchain na administração pública brasileira, "
              "com foco em transparência.",
}
REG_SEM_PDF = {**REG_BLOCKCHAIN_DOCS, "id": 1, "ano": "2019", "uuid_arquivo": "",
               "titulo": "BLOCKCHAIN APLICADO A LOGISTICA"}
REG_ANTIGO = {**REG_BLOCKCHAIN_DOCS, "id": 2, "ano": "2010", "titulo": "CRIPTOMOEDAS E BLOCKCHAIN"}
REG_BITCOIN = {**REG_BLOCKCHAIN_DOCS, "id": 3, "ano": "2021", "titulo": "MINERAÇÃO DE BITCOIN COM BLOCKCHAIN",
               "palavras_chave": "T; BITCOIN, BLOCKCHAIN; O; A; 2021", "resumo": ""}
REG_IA = {**REG_BLOCKCHAIN_DOCS, "id": 4, "ano": "2025", "titulo": "INTELIGÊNCIA ARTIFICIAL NA SAÚDE",
          "palavras_chave": "T; INTELIGÊNCIA ARTIFICIAL, SAÚDE; O; A; 2025",
          "resumo": "Uso de redes neurais; menciona blockchain apenas no resumo para rastrear prontuários."}

POR_TERMO = {
    "blockchain": [REG_BLOCKCHAIN_DOCS, REG_BLOCKCHAIN_PUBLICO, REG_SEM_PDF, REG_ANTIGO, REG_BITCOIN],
    "contrato inteligente": [REG_BLOCKCHAIN_PUBLICO],
    "": [REG_BLOCKCHAIN_DOCS, REG_BLOCKCHAIN_PUBLICO, REG_SEM_PDF, REG_ANTIGO, REG_BITCOIN, REG_IA],
}


def buscar_falso(termo, tipo="TCC", curso="BCC"):
    return [acervo_fema.normalizar(r) for r in POR_TERMO.get(termo.lower(), [])]


class ConsultaBooleanaTests(SimpleTestCase):
    def avalia(self, expr, texto):
        return parse(expr).avaliar(normalizar_texto(texto))

    def test_ignora_acentos_e_maiusculas(self):
        self.assertTrue(self.avalia("inteligencia", "INTELIGÊNCIA Artificial"))

    def test_precedencia_and_sobre_or(self):
        self.assertTrue(self.avalia("a OR b AND c", "a"))
        self.assertFalse(self.avalia("(a OR b) AND c", "a"))

    def test_not_e_and_implicito(self):
        self.assertTrue(self.avalia("blockchain NOT bitcoin", "blockchain e saude"))
        self.assertFalse(self.avalia("blockchain NOT bitcoin", "blockchain e bitcoin"))
        self.assertTrue(self.avalia("redes neurais", "uso de neurais em redes"))

    def test_frase_e_prefixo(self):
        self.assertTrue(self.avalia('"contrato inteligente"', "um contrato inteligente"))
        self.assertFalse(self.avalia('"contrato inteligente"', "contrato muito inteligente"))
        self.assertTrue(self.avalia("educa*", "plataforma educacional"))

    def test_palavra_inteira(self):
        self.assertFalse(self.avalia("rede", "redes"))

    def test_operadores_em_portugues(self):
        self.assertTrue(self.avalia("ia OU blockchain E NAO bitcoin", "blockchain"))

    def test_termos_positivos(self):
        self.assertEqual(parse('a OR ("b c" AND NOT d)').termos_positivos(), ["a", "b c"])

    def test_erros(self):
        for ruim in ["", "(a OR b", "NOT a", "a OR", "a )"]:
            with self.assertRaises(ErroConsulta, msg=ruim):
                parse(ruim)


class NormalizacaoTests(SimpleTestCase):
    def test_campos_extraidos(self):
        t = acervo_fema.normalizar(REG_BLOCKCHAIN_DOCS)
        self.assertEqual(t.autores, ["Felipe Araújo De Almeida"])
        self.assertEqual(t.orientadores, ["Guilherme De Cleva Farto"])
        self.assertEqual(t.palavras_chave, ["Blockchain", "Ensino", "Documentos"])
        self.assertNotIn("\r", t.resumo)
        self.assertTrue(t.url_pdf.endswith("/download/14/uSwXEhVQgb9ZRSl8"))

    def test_ano_invalido(self):
        self.assertIsNone(acervo_fema.normalizar({**REG_ANTIGO, "ano": "206"}).ano_int)


class PipelineTests(SimpleTestCase):
    def test_fluxo_completo(self):
        crit = Criterios(expressao='(blockchain OR "contrato inteligente") NOT bitcoin',
                         ano_inicio=2015, exigir_pdf=True)
        res = executar(crit, buscar=buscar_falso)

        self.assertEqual(res.consultas, {"blockchain": 5, "contrato inteligente": 1})
        self.assertEqual(res.identificados, 6)
        self.assertEqual(res.duplicados, 1)          # 25657 veio nas duas buscas
        self.assertEqual(res.triados, 5)
        self.assertEqual(res.excl_triagem_expressao, 1)   # bitcoin
        self.assertEqual(res.excl_triagem_periodo, 1)     # 2010
        self.assertEqual(res.excl_sem_pdf, 1)
        self.assertEqual([t.id for t in res.incluidos], [26405, 25657])   # mais recente primeiro
        # a soma fecha: triados = excluídos + incluídos
        self.assertEqual(res.triados, len(res.excluidos) + res.total_incluidos)

    def test_modo_amplo_acha_termo_so_no_resumo(self):
        normal = executar(Criterios(expressao="prontuarios"), buscar=buscar_falso)
        amplo = executar(Criterios(expressao="prontuarios", modo_amplo=True), buscar=buscar_falso)
        self.assertEqual(normal.total_incluidos, 0)
        self.assertEqual([t.id for t in amplo.incluidos], [4])

    def test_exigir_resumo(self):
        res = executar(Criterios(expressao="bitcoin", modo_amplo=True, exigir_resumo=True),
                       buscar=buscar_falso)
        self.assertEqual(res.excl_sem_resumo, 1)
        self.assertEqual(res.total_incluidos, 0)


class BuscaPaginadaTests(SimpleTestCase):
    def setUp(self):
        cache.clear()

    @mock.patch("biblioteca.prisma.acervo_fema.requests.get")
    def test_pagina_ate_lote_incompleto_e_usa_cache(self, get):
        cheio = [{**REG_ANTIGO, "id": i} for i in range(acervo_fema.PAGE_SIZE)]
        get.return_value.json.side_effect = [cheio, [REG_BLOCKCHAIN_DOCS]]
        r = acervo_fema.buscar("x")
        self.assertEqual(len(r), acervo_fema.PAGE_SIZE + 1)
        self.assertEqual(get.call_count, 2)
        self.assertEqual(get.call_args_list[1].kwargs["params"]["page"], 1)
        acervo_fema.buscar("X")                       # mesma busca -> cache
        self.assertEqual(get.call_count, 2)

    @mock.patch("biblioteca.prisma.acervo_fema.requests.get")
    def test_erro_de_rede(self, get):
        get.side_effect = acervo_fema.requests.ConnectionError("offline")
        with self.assertRaises(acervo_fema.AcervoIndisponivel):
            acervo_fema.buscar("x")
        self.assertEqual(acervo_fema.listar_cursos(), acervo_fema.CURSOS_FALLBACK)


@mock.patch("biblioteca.prisma.acervo_fema.listar_tipos", return_value=["TCC"])
@mock.patch("biblioteca.prisma.acervo_fema.listar_cursos", return_value=["BCC", "ADS"])
@mock.patch("biblioteca.prisma.acervo_fema.buscar", side_effect=buscar_falso)
class PrismaViewTests(TestCase):
    def test_formulario_vazio(self, *_):
        r = self.client.get(reverse("prisma_busca"))
        self.assertContains(r, "Protocolo de busca")
        self.assertNotContains(r, "Fluxograma PRISMA")

    def test_resultado(self, *_):
        r = self.client.get(reverse("prisma_busca"), {"q": "blockchain", "exigir_pdf": "on"})
        self.assertContains(r, "Fluxograma PRISMA")
        self.assertContains(r, "DOCUMENTOS EDUCACIONAIS BASEADO EM BLOCKCHAIN")
        self.assertContains(r, "Texto completo (PDF) indisponível")

    def test_expressao_invalida(self, *_):
        r = self.client.get(reverse("prisma_busca"), {"q": "(blockchain"})
        self.assertContains(r, "Expressão inválida")

    def test_csv(self, *_):
        r = self.client.get(reverse("prisma_exportar_csv"), {"q": "blockchain", "exigir_pdf": "on"})
        self.assertEqual(r["Content-Type"], "text/csv; charset=utf-8")
        linhas = r.content.decode("utf-8-sig").strip().splitlines()
        self.assertTrue(linhas[0].startswith("situacao;etapa;motivo"))
        self.assertEqual(len(linhas), 1 + 5)


# ─── Empréstimos em atraso: renovação e cobrança ─────────────────────────────

import datetime as _dt

from django.contrib.auth.models import User
from django.core import mail
from django.test import override_settings
from django.utils import timezone

from .models import Emprestimo, Leitor, Livro, LogOperacao, Notificacao


@mock.patch("biblioteca.mq_publisher._publicar", side_effect=ConnectionError("mq offline"))
class EmprestimoAtrasadoTests(TestCase):
    def setUp(self):
        self.staff = User.objects.create_user("bib", password="x", is_staff=True)
        self.client.force_login(self.staff)
        self.hoje = timezone.now().date()
        leitor = Leitor.objects.create(nome="Ana", email="ana@example.com", matricula="123")
        livro = Livro.objects.create(titulo="Dom Casmurro")
        self.emp = Emprestimo.objects.create(
            livro=livro, leitor=leitor,
            data_emprestimo=self.hoje - _dt.timedelta(days=20),
            data_prevista=self.hoje - _dt.timedelta(days=3),
        )

    def test_lista_mostra_acoes_para_atrasado(self, _):
        r = self.client.get(reverse("emprestimo_list"))
        self.emp.refresh_from_db()
        self.assertEqual(self.emp.status, "atrasado")
        self.assertContains(r, reverse("emprestimo_renovar", args=[self.emp.pk]))
        self.assertContains(r, reverse("emprestimo_cobrar", args=[self.emp.pk]))
        self.assertContains(r, reverse("emprestimo_devolver", args=[self.emp.pk]))

    def test_renovar_ate_nova_data(self, _):
        nova = self.hoje + _dt.timedelta(days=10)
        r = self.client.post(reverse("emprestimo_renovar", args=[self.emp.pk]),
                             {"nova_data": nova.isoformat()})
        self.assertRedirects(r, reverse("emprestimo_list"), fetch_redirect_response=False)
        self.emp.refresh_from_db()
        self.assertEqual(self.emp.status, "ativo")
        self.assertEqual(self.emp.data_prevista, nova)
        self.assertTrue(LogOperacao.objects.filter(tipo="renovacao").exists())
        self.assertTrue(Notificacao.objects.filter(tipo="renovacao", emprestimo=self.emp).exists())

    def test_renovar_rejeita_data_passada(self, _):
        r = self.client.post(reverse("emprestimo_renovar", args=[self.emp.pk]),
                             {"nova_data": self.hoje.isoformat()})
        self.assertEqual(r.status_code, 200)
        self.emp.refresh_from_db()
        self.assertEqual(self.emp.status, "atrasado")

    @override_settings(EMAIL_HOST="smtp.example.com")
    def test_cobrar_envia_email(self, _):
        self.client.get(reverse("emprestimo_list"))  # marca como atrasado
        r = self.client.get(reverse("emprestimo_cobrar", args=[self.emp.pk]))
        self.assertContains(r, "3 dias de atraso")
        r = self.client.post(reverse("emprestimo_cobrar", args=[self.emp.pk]),
                             {"assunto": "Atraso", "corpo": "Devolva, por favor."})
        self.assertRedirects(r, reverse("emprestimo_list"), fetch_redirect_response=False)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["ana@example.com"])
        self.assertEqual(mail.outbox[0].body, "Devolva, por favor.")
        self.assertTrue(LogOperacao.objects.filter(tipo="cobranca").exists())
        self.assertTrue(Notificacao.objects.filter(tipo="atraso", emprestimo=self.emp).exists())

    def test_contador_de_cobrancas(self, _):
        self.client.get(reverse("emprestimo_list"))
        url = reverse("emprestimo_cobrar", args=[self.emp.pk])
        for _i in range(2):
            self.client.post(url, {"assunto": "Atraso", "corpo": "Devolva."})
        self.emp.refresh_from_db()
        self.assertEqual(self.emp.cobrancas, 2)
        self.assertIsNotNone(self.emp.ultima_cobranca)
        self.assertContains(self.client.get(reverse("emprestimo_list")), "Cobrado 2 vezes")
        self.assertContains(self.client.get(url), "Cobrado <strong>2 vezes</strong>")
        self.assertTrue(LogOperacao.objects.filter(descricao__contains="2ª cobrança").exists())

    def test_devolver_atrasado(self, _):
        self.client.get(reverse("emprestimo_list"))
        self.client.post(reverse("emprestimo_devolver", args=[self.emp.pk]))
        self.emp.refresh_from_db()
        self.assertEqual(self.emp.status, "devolvido")

    def test_acoes_bloqueadas_para_ativo(self, _):
        self.emp.data_prevista = self.hoje + _dt.timedelta(days=5)
        self.emp.save()
        for nome in ("emprestimo_renovar", "emprestimo_cobrar"):
            r = self.client.post(reverse(nome, args=[self.emp.pk]), {"nova_data": "2099-01-01"})
            self.assertRedirects(r, reverse("emprestimo_list"), fetch_redirect_response=False)
        self.assertEqual(len(mail.outbox), 0)

    def test_leitor_comum_sem_acesso(self, _):
        comum = User.objects.create_user("leitor", password="x")
        self.client.force_login(comum)
        r = self.client.get(reverse("emprestimo_cobrar", args=[self.emp.pk]))
        self.assertEqual(r.status_code, 403)


@override_settings(STORAGES={
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
})
class PermissoesAdminTests(TestCase):
    def setUp(self):
        self.super = User.objects.create_superuser("root", password="x")
        self.admin = User.objects.create_user("adm", password="x", is_staff=True)
        self.comum = User.objects.create_user("leitor", password="x")
        self.client.force_login(self.admin)

    def test_admin_acessa_usuarios_e_cria_conta(self):
        self.assertEqual(self.client.get(reverse("usuario_list")).status_code, 200)
        self.assertContains(self.client.get(reverse("home")), reverse("usuario_list"))
        self.client.post(reverse("usuario_create"), {
            "username": "novo", "senha": "senhaforte1", "senha2": "senhaforte1", "papel": "admin"})
        self.assertTrue(User.objects.get(username="novo").is_staff)

    def test_admin_reseta_senha_de_comum_mas_nao_de_superadmin(self):
        url = lambda u: reverse("usuario_reset_senha", args=[u.pk])
        r = self.client.post(url(self.comum), {"senha": "outrasenha1", "senha2": "outrasenha1"})
        self.assertRedirects(r, reverse("usuario_list"), fetch_redirect_response=False)
        self.assertEqual(self.client.get(url(self.super)).status_code, 403)

    def test_admin_tem_todas_as_permissoes_no_django_admin(self):
        self.assertTrue(self.admin.has_perm("biblioteca.delete_livro"))
        self.assertTrue(self.admin.has_perm("auth.change_user"))
        self.assertFalse(self.comum.has_perm("biblioteca.delete_livro"))
        self.assertEqual(self.client.get("/admin/biblioteca/livro/").status_code, 200)

    def test_admin_nao_ve_nem_edita_superadmin_no_django_admin(self):
        r = self.client.get("/admin/auth/user/")
        self.assertNotContains(r, ">root<")
        self.assertNotEqual(self.client.get(f"/admin/auth/user/{self.super.pk}/change/").status_code, 200)
        r = self.client.get(f"/admin/auth/user/{self.admin.pk}/change/")
        self.assertNotContains(r, 'name="is_superuser"')

    def test_usuario_comum_continua_sem_acesso(self):
        self.client.force_login(self.comum)
        self.assertEqual(self.client.get(reverse("usuario_list")).status_code, 403)


class PaginacaoTests(TestCase):
    def setUp(self):
        self.client.force_login(User.objects.create_user("bib2", password="x", is_staff=True))
        Livro.objects.bulk_create([Livro(titulo=f"Livro {i:03d}") for i in range(35)])

    def test_campo_de_pagina_e_links_preservam_busca(self):
        r = self.client.get(reverse("livro_list"), {"q": "Livro", "page": 2})
        html = r.content.decode()
        self.assertIn('name="page"', html)
        self.assertIn('value="2"', html)
        self.assertIn('max="4"', html)
        self.assertIn('<input type="hidden" name="q" value="Livro">', html)
        self.assertIn("?q=Livro&amp;page=4", html)   # última página
        self.assertIn("?q=Livro&amp;page=1", html)   # primeira página

    def test_pagina_fora_do_intervalo_vai_para_a_ultima(self):
        r = self.client.get(reverse("livro_list"), {"page": 999})
        self.assertEqual(r.context["page_obj"].number, 4)


# ─── Busca por ISBN (Google Books + Open Library) ───────────────────────────

from . import isbn as isbn_lookup


class _Resp:
    def __init__(self, status=200, dados=None):
        self.status_code, self._dados = status, dados or {}

    def json(self):
        return self._dados

    def raise_for_status(self):
        if self.status_code >= 400:
            raise Exception(self.status_code)


def _fake_http(google=None, google_status=200, ol=None, ol_obra=None, ol_nota=None, capa_ok=False):
    def get(url, params=None, timeout=None):
        if "googleapis" in url:
            return _Resp(google_status, {"items": [{"volumeInfo": google}]} if google else {})
        if "api/books" in url:
            return _Resp(200, {f"ISBN:{params['bibkeys'][5:]}": ol} if ol else {})
        if "/isbn/" in url:
            return _Resp(200, ol_obra) if ol_obra else _Resp(404)
        if "ratings.json" in url:
            return _Resp(200, {"summary": ol_nota or {}})
        return _Resp(404)

    def head(url, timeout=None, allow_redirects=None):
        return _Resp(200 if capa_ok else 404)

    return mock.patch.multiple(isbn_lookup.requests, get=mock.Mock(side_effect=get),
                               head=mock.Mock(side_effect=head))


GOOGLE = {
    "title": "Código Limpo", "authors": ["Robert C. Martin"], "publishedDate": "2009-08-14",
    "publisher": "Alta Books", "description": "Habilidades práticas", "averageRating": 4.5,
    "ratingsCount": 12, "imageLinks": {"thumbnail": "http://books.google.com/x?id=1&edge=curl"},
}


class BuscaIsbnTests(TestCase):
    def test_normaliza_e_converte_isbn10(self):
        self.assertEqual(isbn_lookup.normalizar_isbn("85-359-0277-5"), "8535902775")
        self.assertEqual(isbn_lookup.isbn10_para_13("8535902775"), "9788535902778")
        self.assertEqual(isbn_lookup.isbn10_para_13("0132350882"), "9780132350884")

    def test_google_completo(self):
        with _fake_http(google=GOOGLE):
            d = isbn_lookup.buscar("978-85-7608-267-5")
        self.assertEqual(d["titulo"], "Código Limpo")
        self.assertEqual(d["autores"], "Robert C. Martin")
        self.assertEqual(d["ano"], "2009")
        self.assertEqual(d["data_publicacao"], "14/08/2009")
        self.assertEqual(d["nota"], 4.5)
        self.assertEqual(d["nota_qtd"], 12)
        self.assertEqual(d["capa_url"], "https://books.google.com/x?id=1")
        self.assertTrue(d["fonte"].startswith("Google Books"))

    def test_cota_google_esgotada_usa_open_library(self):
        ol = {"title": "Clean Code", "authors": [{"name": "Robert Martin"}], "publish_date": "Aug 1, 2008",
              "publishers": [{"name": "Prentice Hall"}], "cover": {"large": "http://covers.openlibrary.org/b/1-L.jpg"}}
        with _fake_http(google_status=429, ol=ol, ol_obra={"works": [{"key": "/works/OL1W"}]},
                        ol_nota={"average": 4.236, "count": 50}):
            d = isbn_lookup.buscar("9780132350884")
        self.assertEqual(d["titulo"], "Clean Code")
        self.assertEqual(d["ano"], "2008")
        self.assertEqual(d["data_publicacao"], "01/08/2008")
        self.assertEqual(d["editora"], "Prentice Hall")
        self.assertEqual(d["capa_url"], "https://covers.openlibrary.org/b/1-L.jpg")
        self.assertEqual((d["nota"], d["nota_qtd"]), (4.24, 50))
        self.assertEqual(d["fonte"], "Open Library")

    def test_open_library_completa_capa_que_falta_no_google(self):
        g = dict(GOOGLE, imageLinks={}, averageRating=None, ratingsCount=None)
        with _fake_http(google=g, ol={"title": "Clean", "cover": {"medium": "https://c/x.jpg"}}):
            d = isbn_lookup.buscar("9788576082675")
        self.assertEqual(d["titulo"], "Código Limpo")  # Google tem prioridade
        self.assertEqual(d["capa_url"], "https://c/x.jpg")
        self.assertIsNone(d["nota"])
        self.assertEqual(d["fonte"], "Google Books + Open Library")

    def test_nada_encontrado(self):
        with _fake_http():
            self.assertIsNone(isbn_lookup.buscar("9788576082675"))
        self.assertIsNone(isbn_lookup.buscar("123"))


class LivroIsbnViewTests(TestCase):
    def setUp(self):
        self.client.force_login(User.objects.create_user("bib3", password="x", is_staff=True))

    def test_view_buscar_isbn(self):
        with _fake_http(google=GOOGLE):
            r = self.client.get(reverse("livro_buscar_isbn"), {"isbn": "9788576082675"})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["nota"], 4.5)
        r = self.client.get(reverse("livro_buscar_isbn"), {"isbn": "12ab"})
        self.assertEqual(r.status_code, 400)

    def test_criar_e_editar_salva_metadados(self):
        self.client.post(reverse("livro_create"), {
            "titulo": "Código Limpo", "isbn": "9788576082675", "total_exemplares": "1",
            "editora": "Alta Books", "data_publicacao": "2009-08-14",
            "capa_url": "https://books.google.com/x?id=1", "nota": "4,5", "nota_qtd": "12",
        })
        livro = Livro.objects.get(isbn="9788576082675")
        self.assertEqual(str(livro.nota), "4.50")
        self.assertEqual(livro.nota_qtd, 12)
        self.assertEqual(livro.editora, "Alta Books")
        r = self.client.get(reverse("livro_detail", args=[livro.pk]))
        self.assertContains(r, "https://books.google.com/x?id=1")
        self.assertContains(r, "bi-star-half")
        # URL não http(s) e nota fora da faixa são descartadas
        self.client.post(reverse("livro_edit", args=[livro.pk]), {
            "titulo": "Código Limpo", "isbn": "9788576082675", "capa_url": "javascript:alert(1)", "nota": "9",
        })
        livro.refresh_from_db()
        self.assertEqual(livro.capa_url, "")
        self.assertIsNone(livro.nota)
