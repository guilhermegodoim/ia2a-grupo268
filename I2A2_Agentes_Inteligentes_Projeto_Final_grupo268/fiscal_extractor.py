from lxml import etree
from decimal import Decimal
from datetime import datetime
from models import (
    NotaFiscal, Emitente, Destinatario, Endereco,
    Produto, Imposto, Totalizadores
)
from typing import Optional


class NFeExtractor:
    """Extrator de dados de XML de NF-e"""
    
    # Namespace padrão da NF-e
    NS = {'nfe': 'http://www.portalfiscal.inf.br/nfe'}
    
    def __init__(self):
        self.tree = None
        self.root = None
    
    def carregar_xml(self, xml_content: bytes) -> bool:
        """Carrega o XML da NF-e"""
        try:
            self.tree = etree.fromstring(xml_content)
            self.root = self.tree
            return True
        except Exception as e:
            raise ValueError(f"Erro ao carregar XML: {str(e)}")
    
    def _get_text(self, xpath: str, default: str = "") -> str:
        """Extrai texto de um elemento XML"""
        try:
            elem = self.root.xpath(xpath, namespaces=self.NS)
            return elem[0].text if elem and elem[0].text else default
        except:
            return default
    
    def _get_decimal(self, xpath: str, default: float = 0.0) -> Decimal:
        """Extrai valor decimal de um elemento XML"""
        try:
            valor = self._get_text(xpath, str(default))
            return Decimal(valor)
        except:
            return Decimal(str(default))
    
    def extrair_endereco(self, base_xpath: str) -> Endereco:
        """Extrai dados de endereço"""
        return Endereco(
            logradouro=self._get_text(f"{base_xpath}/nfe:xLgr"),
            numero=self._get_text(f"{base_xpath}/nfe:nro"),
            bairro=self._get_text(f"{base_xpath}/nfe:xBairro"),
            municipio=self._get_text(f"{base_xpath}/nfe:xMun"),
            uf=self._get_text(f"{base_xpath}/nfe:UF"),
            cep=self._get_text(f"{base_xpath}/nfe:CEP")
        )
    
    def extrair_emitente(self) -> Emitente:
        """Extrai dados do emitente"""
        base = ".//nfe:emit"
        return Emitente(
            cnpj=self._get_text(f"{base}/nfe:CNPJ"),
            razao_social=self._get_text(f"{base}/nfe:xNome"),
            nome_fantasia=self._get_text(f"{base}/nfe:xFant"),
            endereco=self.extrair_endereco(f"{base}/nfe:enderEmit"),
            inscricao_estadual=self._get_text(f"{base}/nfe:IE")
        )
    
    def extrair_destinatario(self) -> Destinatario:
        """Extrai dados do destinatário"""
        base = ".//nfe:dest"
        
        # Tenta CNPJ primeiro, depois CPF
        cpf_cnpj = self._get_text(f"{base}/nfe:CNPJ")
        if not cpf_cnpj:
            cpf_cnpj = self._get_text(f"{base}/nfe:CPF")
        
        return Destinatario(
            cpf_cnpj=cpf_cnpj,
            nome=self._get_text(f"{base}/nfe:xNome"),
            endereco=self.extrair_endereco(f"{base}/nfe:enderDest"),
            inscricao_estadual=self._get_text(f"{base}/nfe:IE")
        )
    
    def extrair_produtos(self) -> list[Produto]:
        """Extrai lista de produtos"""
        produtos = []
        items = self.root.xpath(".//nfe:det", namespaces=self.NS)
        
        for item in items:
            base = "nfe:prod"
            imposto_base = "nfe:imposto"
            
            # Extrai impostos
            impostos = Imposto(
                icms_base_calculo=self._extrair_imposto_valor(item, f"{imposto_base}/nfe:ICMS//nfe:vBC"),
                icms_valor=self._extrair_imposto_valor(item, f"{imposto_base}/nfe:ICMS//nfe:vICMS"),
                ipi_valor=self._extrair_imposto_valor(item, f"{imposto_base}/nfe:IPI//nfe:vIPI"),
                pis_valor=self._extrair_imposto_valor(item, f"{imposto_base}/nfe:PIS//nfe:vPIS"),
                cofins_valor=self._extrair_imposto_valor(item, f"{imposto_base}/nfe:COFINS//nfe:vCOFINS")
            )
            
            # Cria produto
            produto = Produto(
                codigo=self._get_text_from_elem(item, f"{base}/nfe:cProd"),
                descricao=self._get_text_from_elem(item, f"{base}/nfe:xProd"),
                ncm=self._get_text_from_elem(item, f"{base}/nfe:NCM"),
                cfop=self._get_text_from_elem(item, f"{base}/nfe:CFOP"),
                unidade=self._get_text_from_elem(item, f"{base}/nfe:uCom"),
                quantidade=self._get_decimal_from_elem(item, f"{base}/nfe:qCom"),
                valor_unitario=self._get_decimal_from_elem(item, f"{base}/nfe:vUnCom"),
                valor_total=self._get_decimal_from_elem(item, f"{base}/nfe:vProd"),
                impostos=impostos
            )
            produtos.append(produto)
        
        return produtos
    
    def _get_text_from_elem(self, elem, xpath: str) -> str:
        """Extrai texto de subelemento"""
        try:
            result = elem.xpath(xpath, namespaces=self.NS)
            return result[0].text if result and result[0].text else ""
        except:
            return ""
    
    def _get_decimal_from_elem(self, elem, xpath: str) -> Decimal:
        """Extrai decimal de subelemento"""
        try:
            valor = self._get_text_from_elem(elem, xpath)
            return Decimal(valor) if valor else Decimal('0.00')
        except:
            return Decimal('0.00')
    
    def _extrair_imposto_valor(self, elem, xpath: str) -> Decimal:
        """Extrai valor de imposto"""
        return self._get_decimal_from_elem(elem, xpath)
    
    def extrair_totalizadores(self) -> Totalizadores:
        """Extrai totalizadores da nota"""
        base = ".//nfe:total/nfe:ICMSTot"
        
        return Totalizadores(
            base_calculo_icms=self._get_decimal(f"{base}/nfe:vBC"),
            valor_icms=self._get_decimal(f"{base}/nfe:vICMS"),
            valor_ipi=self._get_decimal(f"{base}/nfe:vIPI"),
            valor_pis=self._get_decimal(f"{base}/nfe:vPIS"),
            valor_cofins=self._get_decimal(f"{base}/nfe:vCOFINS"),
            valor_produtos=self._get_decimal(f"{base}/nfe:vProd"),
            valor_frete=self._get_decimal(f"{base}/nfe:vFrete"),
            valor_seguro=self._get_decimal(f"{base}/nfe:vSeg"),
            valor_desconto=self._get_decimal(f"{base}/nfe:vDesc"),
            valor_total_nota=self._get_decimal(f"{base}/nfe:vNF")
        )
    
    def extrair_nota_fiscal(self) -> NotaFiscal:
        """Extrai todos os dados da NF-e"""
        try:
            # Extrai chave de acesso
            chave = self._get_text(".//nfe:infNFe/@Id")
            chave = chave.replace("NFe", "") if chave else ""
            
            # Data de emissão
            data_str = self._get_text(".//nfe:ide/nfe:dhEmi")
            if not data_str:
                data_str = self._get_text(".//nfe:ide/nfe:dEmi")
            
            # Converte data
            try:
                data_emissao = datetime.fromisoformat(data_str.replace('Z', '+00:00'))
            except:
                data_emissao = datetime.now()
            
            # Cria objeto NotaFiscal
            nota = NotaFiscal(
                chave_acesso=chave,
                numero=self._get_text(".//nfe:ide/nfe:nNF"),
                serie=self._get_text(".//nfe:ide/nfe:serie"),
                data_emissao=data_emissao,
                emitente=self.extrair_emitente(),
                destinatario=self.extrair_destinatario(),
                produtos=self.extrair_produtos(),
                totalizadores=self.extrair_totalizadores(),
                informacoes_adicionais=self._get_text(".//nfe:infAdic/nfe:infCpl")
            )
            
            return nota
        except Exception as e:
            raise ValueError(f"Erro ao extrair dados da NF-e: {str(e)}")