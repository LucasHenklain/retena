# -*- coding: utf-8 -*-
"""
exportar_para_object_storage.py - exporta os eventos do LMS para CSV gzip e envia ao OCI Object Storage,
no formato que sql/08_dbms_cloud_ingestao.sql espera (DBMS_CLOUD.COPY_DATA -> EVENTOS_LMS).

Fonte dos dados (--fonte auto, padrao):
  1) tabela EVENTOS_LMS via python-oracledb (conexao resolvida por conexao.py: Free local ou Autonomous);
  2) fallback: ..\\..\\08_Dados\\logs_lms.parquet (mesma origem usada por scripts/carregar_eventos.py).

Formato do CSV (casa com o "format" do 08_dbms_cloud_ingestao.sql):
  UTF-8 | cabecalho (skipheaders=1) | delimitador "," | campos entre aspas duplas quando necessario
  (aspas internas dobradas) | TS_EVENTO em YYYY-MM-DD HH24:MI:SS | gzip | colunas fisicas de EVENTOS_LMS:
  FASE, TS_EVENTO, NOME, USUARIO_AFETADO, CONTEXTO, COMPONENTE, EVENTO, DESCRICAO, ORIGEM
  (ID_EVENTO e IDENTITY; NUM_FASE/CAPITULO/FLG_ALUNO sao colunas virtuais - o banco calcula.)

Upload: SDK oci lendo ~/.oci/config (perfil OCI_CONFIG_PROFILE), UploadManager (multipart automatico).
--dry-run: gera apenas o arquivo local em %TEMP% e imprime tamanho, linhas e SHA-256 (nao toca na OCI).

Adaptado do EduRetain (equipe Retena): oci_storage.py (_get_client via oci.config.from_file, listagem
paginada com next_start_with) - aqui no sentido inverso: o banco/parquet e a origem e o bucket e o destino.

Uso:
  python exportar_para_object_storage.py --dry-run
  python exportar_para_object_storage.py --dry-run --fonte parquet
  python exportar_para_object_storage.py --desde 2026-08-01              # incremental (TS_EVENTO >= data)
  python exportar_para_object_storage.py --criar-bucket                  # cria o bucket se nao existir e envia
  python exportar_para_object_storage.py --listar                        # lista objetos do prefixo no bucket
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import gzip
import hashlib
import io
import os
import sys
import tempfile
import time
from pathlib import Path

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))
from conexao import carregar_env, descrever, get_connection  # noqa: E402

PARQUET_PADRAO = (AQUI.parent.parent / "08_Dados" / "logs_lms.parquet").resolve()
COLUNAS = ["FASE", "TS_EVENTO", "NOME", "USUARIO_AFETADO", "CONTEXTO", "COMPONENTE", "EVENTO", "DESCRICAO", "ORIGEM"]
FORMATO_TS = "%Y-%m-%d %H:%M:%S"  # = dateformat 'YYYY-MM-DD HH24:MI:SS' no COPY_DATA


def _env(nome: str, padrao: str = "") -> str:
    return os.environ.get(nome, padrao).strip()


def _limpar(v):
    """Remove quebras de linha (o loader do DBMS_CLOUD e orientado a linha); None vira campo vazio."""
    if v is None:
        return ""
    if isinstance(v, str):
        return v.replace("\r\n", " ").replace("\n", " ").replace("\r", " ")
    return v


# --------------------------------------------------------------------------- fontes
def linhas_oracle(desde: str | None):
    """Gera tuplas a partir de EVENTOS_LMS (arraysize alto: ~685 mil linhas em poucos segundos)."""
    sql = ("SELECT FASE, TO_CHAR(TS_EVENTO, 'YYYY-MM-DD HH24:MI:SS'), NOME, USUARIO_AFETADO, CONTEXTO, "
           "COMPONENTE, EVENTO, DESCRICAO, ORIGEM FROM EVENTOS_LMS")
    binds = {}
    if desde:
        sql += " WHERE TS_EVENTO >= TO_DATE(:desde, 'YYYY-MM-DD')"
        binds["desde"] = desde
    sql += " ORDER BY ID_EVENTO"
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.arraysize = 20_000
        cur.prefetchrows = 20_001
        cur.execute(sql, binds)
        for r in cur:
            yield r
    finally:
        conn.close()


def linhas_parquet(caminho: Path, desde: str | None):
    """Fallback: mesmo preparo de scripts/carregar_eventos.py ("dd/mm/yyyy HH:MM" -> datetime)."""
    import pandas as pd

    df = pd.read_parquet(caminho)
    df["ts"] = pd.to_datetime(df["hora"], format="%d/%m/%Y %H:%M")
    if desde:
        df = df[df["ts"] >= pd.Timestamp(desde)]
    # mantem a ordem do parquet (= ordem de insercao/ID_EVENTO de carregar_eventos.py) para o CSV sair identico ao do banco
    cols = ["fase", "ts", "nome", "usuario_afetado", "contexto", "componente", "evento", "descricao", "origem"]
    for c in cols:
        if c != "ts":
            df[c] = df[c].astype("string").astype(object).where(df[c].notna(), None)  # pd.NA -> None -> campo vazio
    for r in df[cols].itertuples(index=False):
        yield (r.fase, r.ts.strftime(FORMATO_TS), r.nome, r.usuario_afetado, r.contexto, r.componente,
               r.evento, r.descricao, r.origem)


def escolher_fonte(fonte: str, parquet: Path, desde: str | None):
    if fonte in ("auto", "oracle"):
        try:
            gen = linhas_oracle(desde)
            primeira = next(gen)  # forca a conexao/consulta agora, para poder cair no fallback
            def encadeado():
                yield primeira
                yield from gen
            return "oracle:EVENTOS_LMS", encadeado()
        except StopIteration:
            return "oracle:EVENTOS_LMS (0 linhas)", iter(())
        except Exception as e:  # noqa: BLE001 - qualquer falha de conexao/consulta cai no parquet
            if fonte == "oracle":
                raise
            print(f"[fonte] Oracle indisponivel ({str(e).splitlines()[0]}) -> fallback parquet")
    if not parquet.is_file():
        raise SystemExit(f"[fonte] parquet nao encontrado: {parquet}")
    return f"parquet:{parquet}", linhas_parquet(parquet, desde)


# --------------------------------------------------------------------------- exportacao
def exportar_csv_gz(saida: Path, linhas) -> tuple[int, str]:
    """Escreve CSV gzip; retorna (qtd_linhas_de_dados, sha256)."""
    saida.parent.mkdir(parents=True, exist_ok=True)
    qtd = 0
    # mtime=0 no cabecalho gzip -> mesmo conteudo gera o mesmo SHA-256 em execucoes diferentes (evidencia reproduzivel)
    with open(saida, "wb") as bruto, gzip.GzipFile(filename="", mode="wb", fileobj=bruto, mtime=0, compresslevel=6) as gzb, \
            io.TextIOWrapper(gzb, encoding="utf-8", newline="") as gz:
        w = csv.writer(gz, delimiter=",", quotechar='"', quoting=csv.QUOTE_MINIMAL, lineterminator="\n")
        w.writerow(COLUNAS)
        for r in linhas:
            w.writerow([_limpar(v) for v in r])
            qtd += 1
    h = hashlib.sha256()
    with open(saida, "rb") as f:
        for bloco in iter(lambda: f.read(1 << 20), b""):
            h.update(bloco)
    return qtd, h.hexdigest()


def contar_linhas(saida: Path) -> int:
    """Releitura independente do arquivo (confere que o gzip esta integro e o total de linhas de dados)."""
    with gzip.open(saida, "rt", encoding="utf-8", newline="") as gz:
        return sum(1 for _ in csv.reader(gz)) - 1


# --------------------------------------------------------------------------- OCI
def cliente_oci():
    import oci  # importado aqui: o --dry-run nao exige SDK/config

    perfil = _env("OCI_CONFIG_PROFILE", "DEFAULT")
    cfg = oci.config.from_file(profile_name=perfil)  # ~/.oci/config (ConfigFileNotFound se ausente)
    oci.config.validate_config(cfg)
    return oci, cfg, oci.object_storage.ObjectStorageClient(cfg)


def garantir_bucket(oci, cfg, client, ns: str, bucket: str) -> None:
    try:
        client.get_bucket(ns, bucket)
        print(f"[oci] bucket '{bucket}' ja existe")
    except oci.exceptions.ServiceError as e:
        if e.status != 404:
            raise
        comp = _env("OCI_COMPARTMENT_OCID") or cfg["tenancy"]
        det = oci.object_storage.models.CreateBucketDetails(
            name=bucket, compartment_id=comp, storage_tier="Standard", public_access_type="NoPublicAccess")
        client.create_bucket(ns, det)
        print(f"[oci] bucket '{bucket}' criado no compartment {comp[:40]}...")


def upload(arquivo: Path, bucket: str, prefixo: str, criar_bucket: bool) -> str:
    oci, cfg, client = cliente_oci()
    ns = _env("OCI_NAMESPACE") or client.get_namespace().data
    if criar_bucket:
        garantir_bucket(oci, cfg, client, ns, bucket)
    objeto = f"{prefixo}{arquivo.name}"
    um = oci.object_storage.UploadManager(client, allow_parallel_uploads=True, parallel_process_count=3)
    t0 = time.time()
    resp = um.upload_file(ns, bucket, objeto, str(arquivo), content_type="application/gzip",
                          metadata={"origem": "retena-exportar_para_object_storage", "tabela": "EVENTOS_LMS"})
    head = client.head_object(ns, bucket, objeto)
    print(f"[oci] upload ok em {time.time() - t0:.1f}s | etag={resp.headers.get('etag')} | "
          f"content-length={head.headers.get('content-length')} | md5={head.headers.get('content-md5')}")
    uri = f"https://objectstorage.{cfg['region']}.oraclecloud.com/n/{ns}/b/{bucket}/o/{objeto}"
    print(f"[oci] URI para DBMS_CLOUD: {uri}")
    return uri


def listar(bucket: str, prefixo: str) -> None:
    """Listagem paginada (padrao oci_storage.list_csv_objects do EduRetain)."""
    oci, cfg, client = cliente_oci()
    ns = _env("OCI_NAMESPACE") or client.get_namespace().data
    inicio, total = None, 0
    while True:
        resp = client.list_objects(ns, bucket, prefix=prefixo or None, start=inicio, fields="name,size,timeModified")
        for o in resp.data.objects:
            total += 1
            print(f"  {o.time_modified:%Y-%m-%d %H:%M}  {o.size:>12,} B  {o.name}".replace(",", "."))
        inicio = resp.data.next_start_with
        if not inicio:
            break
    print(f"[oci] {total} objeto(s) em {bucket}/{prefixo}")


# --------------------------------------------------------------------------- main
def main() -> int:
    ap = argparse.ArgumentParser(description="Exporta EVENTOS_LMS -> CSV gzip -> OCI Object Storage")
    ap.add_argument("--dry-run", action="store_true", help="so gera o arquivo local (nao usa a OCI)")
    ap.add_argument("--fonte", choices=["auto", "oracle", "parquet"], default="auto")
    ap.add_argument("--parquet", default=str(PARQUET_PADRAO))
    ap.add_argument("--saida", help="arquivo .csv.gz de saida (padrao: %%TEMP%%\\retena_oci\\eventos_lms_<ts>.csv.gz)")
    ap.add_argument("--desde", help="incremental: apenas TS_EVENTO >= YYYY-MM-DD")
    ap.add_argument("--bucket", default=None, help="padrao: OCI_BUCKET_NAME (.env) ou retena-lms")
    ap.add_argument("--prefixo", default=None, help="padrao: OCI_OBJECT_PREFIX (.env) ou eventos_lms/")
    ap.add_argument("--criar-bucket", action="store_true")
    ap.add_argument("--listar", action="store_true", help="so lista os objetos do prefixo e sai")
    ap.add_argument("--env", help="caminho de um .env especifico")
    args = ap.parse_args()

    usado = carregar_env(args.env)
    bucket = args.bucket or _env("OCI_BUCKET_NAME", "retena-lms")
    prefixo = args.prefixo if args.prefixo is not None else _env("OCI_OBJECT_PREFIX", "eventos_lms/")
    print(f"[cfg] .env={usado or 'nenhum'} | {descrever()} | bucket={bucket} prefixo={prefixo}")

    if args.listar:
        listar(bucket, prefixo)
        return 0

    agora = dt.datetime.now()
    sufixo = f"_desde_{args.desde}" if args.desde else ""
    saida = Path(args.saida) if args.saida else Path(tempfile.gettempdir()) / "retena_oci" / f"eventos_lms{sufixo}_{agora:%Y%m%d_%H%M%S}.csv.gz"

    t0 = time.time()
    origem, linhas = escolher_fonte(args.fonte, Path(args.parquet), args.desde)
    print(f"[fonte] {origem}" + (f" | TS_EVENTO >= {args.desde}" if args.desde else ""))
    qtd, sha = exportar_csv_gz(saida, linhas)
    dur = time.time() - t0
    tam = saida.stat().st_size
    relidas = contar_linhas(saida)
    print(f"[csv] arquivo : {saida}")
    print(f"[csv] tamanho : {tam:,} bytes".replace(",", ".") + f" ({tam / 1_048_576:.2f} MiB, gzip)")
    print(f"[csv] linhas  : {qtd:,} de dados + 1 cabecalho | releitura: {relidas:,} (ok={relidas == qtd})".replace(",", "."))
    print(f"[csv] sha256  : {sha}")
    print(f"[csv] colunas : {','.join(COLUNAS)} | TS_EVENTO='{FORMATO_TS}' | gerado em {dur:.1f}s")

    if args.dry_run:
        print("[dry-run] nada enviado a OCI. Para enviar: remova --dry-run (exige ~/.oci/config).")
        return 0

    uri = upload(saida, bucket, prefixo, args.criar_bucket)
    print("\n-- cole no Autonomous (ver sql/08_dbms_cloud_ingestao.sql):")
    print("BEGIN DBMS_CLOUD.COPY_DATA(table_name => 'EVENTOS_LMS', credential_name => 'RETENA_OBJ_STORE_CRED',")
    print(f"  file_uri_list => '{uri}',")
    print("  field_list => 'FASE, TS_EVENTO DATE ''YYYY-MM-DD HH24:MI:SS'', NOME, USUARIO_AFETADO, CONTEXTO, COMPONENTE, EVENTO, DESCRICAO, ORIGEM',")
    print("  format => JSON_OBJECT('type' VALUE 'csv', 'delimiter' VALUE ',', 'skipheaders' VALUE 1, 'quote' VALUE '\"',")
    print("                        'dateformat' VALUE 'YYYY-MM-DD HH24:MI:SS', 'compression' VALUE 'gzip', 'blankasnull' VALUE true,")
    print("                        'trimspaces' VALUE 'lrtrim', 'rejectlimit' VALUE 1000, 'characterset' VALUE 'AL32UTF8')); END;")
    return 0


if __name__ == "__main__":
    sys.exit(main())
