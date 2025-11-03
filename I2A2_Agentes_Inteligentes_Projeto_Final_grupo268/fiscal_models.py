from pydantic import BaseModel, Field, validator
from typing import List, Optional
from datetime import datetime
from decimal import Decimal


class Endereco(BaseModel):
    """Modelo de endereço"""
    logradouro: str
    numero: str
    bairro: str
    municipio: str
    uf: str
    cep: str
    
    
class Emitente(BaseModel):
    """Modelo do emitente da NF-e"""
    cnpj: str
    razao_social: str
    nome_fantasia: Optional[str] = None
    endereco: Endereco
    inscricao_estadual: Optional[str] = None
    
    @validator('cnpj')
    def validar_cnpj(cls, v):
        # Remove caracteres não numéricos
        cnpj = ''.join(filter(str.isdigit, v))
        if len(cnpj) != 14:
            raise ValueError('CNPJ deve ter 14 dígitos')
        return cnpj


class Destinatario(BaseModel):
    """Modelo do destinatário da NF-e"""
    cpf_cnpj: str
    nome: str
    endereco: Endereco
    inscricao_estadual: Optional[str] = None
    
    @validator('cpf_cnpj')
    def validar_cpf_cnpj(cls, v):
        doc = ''.join(filter(str.isdigit, v))
        if len(doc) not in [11, 14]:
            raise ValueError('CPF deve ter 11 dígitos ou CNPJ 14 dígitos')
        return doc


class Imposto(BaseModel):
    """Modelo de impostos"""
    icms_base_calculo: Decimal = Field(default=Decimal('0.00'))
    icms_valor: Decimal = Field(default=Decimal('0.00'))
    ipi_valor: Decimal = Field(default=Decimal('0.00'))
    pis_valor: Decimal = Field(default=Decimal('0.00'))
    cofins_valor: Decimal = Field(default=Decimal('0.00'))
    
    class Config:
        json_encoders = {
            Decimal: lambda v: float(v)
        }


class Produto(BaseModel):
    """Modelo de produto da NF-e"""
    codigo: str
    descricao: str
    ncm: str
    cfop: str
    unidade: str
    quantidade: Decimal
    valor_unitario: Decimal
    valor_total: Decimal
    impostos: Imposto
    
    class Config:
        json_encoders = {
            Decimal: lambda v: float(v)
        }


class Totalizadores(BaseModel):
    """Totalizadores da NF-e"""
    base_calculo_icms: Decimal
    valor_icms: Decimal
    valor_ipi: Decimal
    valor_pis: Decimal
    valor_cofins: Decimal
    valor_produtos: Decimal
    valor_frete: Decimal = Field(default=Decimal('0.00'))
    valor_seguro: Decimal = Field(default=Decimal('0.00'))
    valor_desconto: Decimal = Field(default=Decimal('0.00'))
    valor_total_nota: Decimal
    
    class Config:
        json_encoders = {
            Decimal: lambda v: float(v)
        }


class NotaFiscal(BaseModel):
    """Modelo completo da Nota Fiscal Eletrônica"""
    chave_acesso: str
    numero: str
    serie: str
    data_emissao: datetime
    emitente: Emitente
    destinatario: Destinatario
    produtos: List[Produto]
    totalizadores: Totalizadores
    informacoes_adicionais: Optional[str] = None
    
    @validator('chave_acesso')
    def validar_chave(cls, v):
        chave = ''.join(filter(str.isdigit, v))
        if len(chave) != 44:
            raise ValueError('Chave de acesso deve ter 44 dígitos')
        return chave
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            Decimal: lambda v: float(v)
        }


class ResultadoValidacao(BaseModel):
    """Resultado da validação inteligente"""
    valido: bool
    score_confianca: float = Field(ge=0.0, le=1.0)
    inconsistencias: List[str] = Field(default_factory=list)
    alertas: List[str] = Field(default_factory=list)
    recomendacoes: List[str] = Field(default_factory=list)
    analise_ia: Optional[str] = None