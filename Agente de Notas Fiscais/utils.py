import os
import pandas as pd
import zipfile
from pydantic import BaseModel, ValidationError
from typing import List

def descompactar_arquivos(zip_path='dados/arquivos.zip', destino='dados/extraidos'):
    os.makedirs(destino, exist_ok=True)
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(destino)
    return destino

class NotaFiscal(BaseModel):
    CHAVE_DE_ACESSO: str
    MODELO: str
    SÉRIE: str
    NÚMERO: str
    NATUREZA_DA_OPERAÇÃO: str
    DATA_EMISSÃO: str
    EVENTO_MAIS_RECENTE: str = None
    DATA_HORA_EVENTO_MAIS_RECENTE: str = None
    CPF_CNPJ_Emitente: str
    RAZÃO_SOCIAL_EMITENTE: str
    INSCRIÇÃO_ESTADUAL_EMITENTE: str
    UF_EMITENTE: str
    MUNICÍPIO_EMITENTE: str
    CNPJ_DESTINATÁRIO: str
    NOME_DESTINATÁRIO: str
    UF_DESTINATÁRIO: str
    INDICADOR_IE_DESTINATÁRIO: str
    DESTINO_DA_OPERAÇÃO: str
    CONSUMIDOR_FINAL: str
    PRESENÇA_DO_COMPRADOR: str
    VALOR_NOTA_FISCAL: float

class ProdutoNotaFiscal(BaseModel):
    CHAVE_DE_ACESSO: str
    MODELO: str
    SÉRIE: str
    NÚMERO: str
    NATUREZA_DA_OPERAÇÃO: str
    DATA_EMISSÃO: str
    CPF_CNPJ_Emitente: str
    RAZÃO_SOCIAL_EMITENTE: str
    INSCRIÇÃO_ESTADUAL_EMITENTE: str
    UF_EMITENTE: str
    MUNICÍPIO_EMITENTE: str
    CNPJ_DESTINATÁRIO: str
    NOME_DESTINATÁRIO: str
    UF_DESTINATÁRIO: str
    INDICADOR_IE_DESTINATÁRIO: str
    DESTINO_DA_OPERAÇÃO: str
    CONSUMIDOR_FINAL: str
    PRESENÇA_DO_COMPRADOR: str
    NÚMERO_PRODUTO: str
    DESCRIÇÃO_DO_PRODUTO_SERVIÇO: str
    CÓDIGO_NCM_SH: str
    NCM_SH_TIPO_DE_PRODUTO: str
    CFOP: str
    QUANTIDADE: float
    UNIDADE: str
    VALOR_UNITÁRIO: float
    VALOR_TOTAL: float

def carregar_csvs_de_zip(caminho_pasta):
    arquivos = [f for f in os.listdir(caminho_pasta) if f.endswith('.csv')]
    if not arquivos:
        raise FileNotFoundError("Nenhum arquivo CSV encontrado na pasta extraída.")

    dfs = []
    for arquivo in arquivos:
        caminho = os.path.join(caminho_pasta, arquivo)
        df = pd.read_csv(caminho, sep=None, engine='python')
        dfs.append(df)

    return pd.concat(dfs, ignore_index=True)

def validar_dados(df):
    erros = []
    for idx, row in df.iterrows():
        try:
            NotaFiscal(**row.dropna().to_dict())
        except ValidationError as e:
            erros.append((idx, e))
    return erros
