import os
import pandas as pd
from pydantic import BaseModel, ValidationError
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_experimental.agents import create_pandas_dataframe_agent
from typing import Optional

# --------- Padronização das colunas ------------
def padronizar_colunas(df: pd.DataFrame) -> pd.DataFrame:
    df.columns = [
        col.strip()
           .upper()
           .replace(' ', '_')
           .replace('/', '_')
           .replace('Ç', 'C')
           .replace('Á', 'A')
           .replace('É', 'E')
           .replace('Í', 'I')
           .replace('Ó', 'O')
           .replace('Ú', 'U')
           .replace('Â', 'A')
           .replace('Ê', 'E')
           .replace('Ô', 'O')
        for col in df.columns
    ]
    return df

# --------- Modelos Pydantic para validação ---------
class NotaFiscal(BaseModel):
    CHAVE_DE_ACESSO: str
    MODELO: str
    SERIE: str
    NUMERO: str
    NATUREZA_DA_OPERACAO: str
    DATA_EMISSAO: str
    EVENTO_MAIS_RECENTE: Optional[str] = None
    DATA_HORA_EVENTO_MAIS_RECENTE: Optional[str] = None
    CPF_CNPJ_EMITENTE: str
    RAZAO_SOCIAL_EMITENTE: str
    INSCRICAO_ESTADUAL_EMITENTE: Optional[str] = None
    UF_EMITENTE: str
    MUNICIPIO_EMITENTE: Optional[str] = None
    CNPJ_DESTINATARIO: Optional[str] = None
    NOME_DESTINATARIO: Optional[str] = None
    UF_DESTINATARIO: Optional[str] = None
    INDICADOR_IE_DESTINATARIO: Optional[str] = None
    DESTINO_DA_OPERACAO: Optional[str] = None
    CONSUMIDOR_FINAL: Optional[str] = None
    PRESENCA_DO_COMPRADOR: Optional[str] = None
    VALOR_NOTA_FISCAL: Optional[float] = 0.0

class ProdutoNotaFiscal(BaseModel):
    CHAVE_DE_ACESSO: str
    MODELO: str
    SERIE: str
    NUMERO: str
    NATUREZA_DA_OPERACAO: str
    DATA_EMISSAO: str
    CPF_CNPJ_EMITENTE: str
    RAZAO_SOCIAL_EMITENTE: str
    INSCRICAO_ESTADUAL_EMITENTE: Optional[str] = None
    UF_EMITENTE: str
    MUNICIPIO_EMITENTE: Optional[str] = None
    CNPJ_DESTINATARIO: Optional[str] = None
    NOME_DESTINATARIO: Optional[str] = None
    UF_DESTINATARIO: Optional[str] = None
    INDICADOR_IE_DESTINATARIO: Optional[str] = None
    DESTINO_DA_OPERACAO: Optional[str] = None
    CONSUMIDOR_FINAL: Optional[str] = None
    PRESENCA_DO_COMPRADOR: Optional[str] = None
    NUMERO_PRODUTO: Optional[str] = None
    DESCRICAO_DO_PRODUTO_SERVICO: Optional[str] = None
    CODIGO_NCM_SH: Optional[str] = None
    NCM_SH_TIPO_DE_PRODUTO: Optional[str] = None
    CFOP: Optional[str] = None
    QUANTIDADE: Optional[float] = 0.0
    UNIDADE: Optional[str] = None
    VALOR_UNITARIO: Optional[float] = 0.0
    VALOR_TOTAL: Optional[float] = 0.0

# --------- Função para validar dados com Pydantic --------------
def validar_dados(df: pd.DataFrame, modelo: BaseModel) -> pd.DataFrame:
    registros_validos = []
    erros = []
    for i, row in df.iterrows():
        dados = row.to_dict()
        try:
            registro = modelo(**dados)
            registros_validos.append(registro.dict())
        except ValidationError as e:
            erros.append((i, e.errors()))
    if erros:
        print(f"Erros de validação encontrados em {len(erros)} registros.")
        # Para debug, descomente abaixo:
        # for idx, err in erros:
        #     print(f"Registro {idx}: {err}")
    return pd.DataFrame(registros_validos)

# --------- Função para carregar e combinar os CSVs ----------
def carregar_csvs_de_zip(caminho_pasta: str) -> pd.DataFrame:
    arquivos_csv = [f for f in os.listdir(caminho_pasta) if f.endswith('.csv')]
    if len(arquivos_csv) < 2:
        raise ValueError("Esperado pelo menos 2 arquivos CSV na pasta para notas fiscais e produtos.")

    # Leitura
    df_nf = pd.read_csv(os.path.join(caminho_pasta, arquivos_csv[0]))
    df_prod = pd.read_csv(os.path.join(caminho_pasta, arquivos_csv[1]))

    # Log colunas
    print("Colunas brutas df_nf:", df_nf.columns.tolist())
    print("Colunas brutas df_prod:", df_prod.columns.tolist())

    # Padronização
    df_nf = padronizar_colunas(df_nf)
    df_prod = padronizar_colunas(df_prod)

    print("Colunas padronizadas df_nf:", df_nf.columns.tolist())
    print("Colunas padronizadas df_prod:", df_prod.columns.tolist())

 # 🚨 Diagnóstico individual dos registros de df_nf
    df_nf_dicts = df_nf.to_dict(orient='records')
    for i, registro in enumerate(df_nf_dicts):
        try:
            NotaFiscal(**registro)
        except Exception as e:
            print(f"Erro na linha {i}: {e}")

    # Validação
    df_nf_validado = df_nf
    #df_nf_validado = validar_dados(df_nf, NotaFiscal)
    df_prod_validado = df_prod #validar_dados(df_prod, ProdutoNotaFiscal)

    if df_nf_validado.empty:
        raise ValueError("Nenhum registro válido encontrado no DataFrame de Notas Fiscais após validação.")
    if df_prod_validado.empty:
        raise ValueError("Nenhum registro válido encontrado no DataFrame de Produtos após validação.")

    # Confere chave
    if 'CHAVE_DE_ACESSO' not in df_nf_validado.columns:
        raise KeyError("Coluna 'CHAVE_DE_ACESSO' não encontrada no DataFrame de Notas Fiscais após validação.")
    if 'CHAVE_DE_ACESSO' not in df_prod_validado.columns:
        raise KeyError("Coluna 'CHAVE_DE_ACESSO' não encontrada no DataFrame de Produtos após validação.")

    # Merge
    df_completo = pd.merge(
        df_nf_validado, df_prod_validado,
        on="CHAVE_DE_ACESSO",
        how="outer",
        suffixes=('_NF','_PROD')
    )
    return df_completo
# --------- Função para criar o agente LangChain com HuggingFace -----
def criar_agente(df: pd.DataFrame):
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise EnvironmentError("Variável de ambiente GOOGLE_API_KEY não definida. Configure sua chave API do Google.")

    llm = ChatGoogleGenerativeAI(
        model="gemini-1.5-flash",
        temperature=0,
        streaming=False
    )

    agente = create_pandas_dataframe_agent(
        llm=llm,
        df=df,
        verbose=True,
        agent_type="openai-tools",
        allow_dangerous_code=True,
        prefix = "Você é um especialista em análise de dados e deve responder em português de forma clara, objetiva e direta, sem escrever código.",
    )
    return agente