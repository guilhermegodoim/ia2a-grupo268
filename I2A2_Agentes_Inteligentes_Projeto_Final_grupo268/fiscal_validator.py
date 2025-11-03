import google.generativeai as genai
from decimal import Decimal
from models import NotaFiscal, ResultadoValidacao
from typing import List
import json


class ValidadorInteligente:
    """Validador de NF-e com IA (Gemini)"""
    
    def __init__(self, api_key: str):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-1.5-flash')
    
    def validar_cnpj(self, cnpj: str) -> bool:
        """Valida dígitos verificadores do CNPJ"""
        cnpj = ''.join(filter(str.isdigit, cnpj))
        if len(cnpj) != 14:
            return False
        
        # Validação dos dígitos verificadores
        def calcular_digito(cnpj_base, pesos):
            soma = sum(int(cnpj_base[i]) * pesos[i] for i in range(len(pesos)))
            resto = soma % 11
            return 0 if resto < 2 else 11 - resto
        
        # Primeiro dígito
        pesos1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
        digito1 = calcular_digito(cnpj[:12], pesos1)
        
        # Segundo dígito
        pesos2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
        digito2 = calcular_digito(cnpj[:13], pesos2)
        
        return cnpj[-2:] == f"{digito1}{digito2}"
    
    def validar_cpf(self, cpf: str) -> bool:
        """Valida dígitos verificadores do CPF"""
        cpf = ''.join(filter(str.isdigit, cpf))
        if len(cpf) != 11:
            return False
        
        # Verifica sequências inválidas
        if cpf == cpf[0] * 11:
            return False
        
        # Calcula primeiro dígito
        soma = sum(int(cpf[i]) * (10 - i) for i in range(9))
        digito1 = 0 if soma % 11 < 2 else 11 - (soma % 11)
        
        # Calcula segundo dígito
        soma = sum(int(cpf[i]) * (11 - i) for i in range(10))
        digito2 = 0 if soma % 11 < 2 else 11 - (soma % 11)
        
        return cpf[-2:] == f"{digito1}{digito2}"
    
    def validar_chave_acesso(self, chave: str) -> bool:
        """Valida chave de acesso da NF-e (44 dígitos + DV)"""
        chave = ''.join(filter(str.isdigit, chave))
        if len(chave) != 44:
            return False
        
        # Valida dígito verificador (último dígito)
        chave_base = chave[:43]
        soma = 0
        multiplicador = 2
        
        for i in range(len(chave_base) - 1, -1, -1):
            soma += int(chave_base[i]) * multiplicador
            multiplicador = 9 if multiplicador == 2 else multiplicador - 1
        
        resto = soma % 11
        dv_calculado = 0 if resto in [0, 1] else 11 - resto
        
        return int(chave[-1]) == dv_calculado
    
    def validar_calculos(self, nota: NotaFiscal) -> List[str]:
        """Valida cálculos matemáticos da nota"""
        inconsistencias = []
        
        # Valida soma dos produtos
        soma_produtos = sum(p.valor_total for p in nota.produtos)
        if abs(soma_produtos - nota.totalizadores.valor_produtos) > Decimal('0.10'):
            inconsistencias.append(
                f"Divergência na soma de produtos: calculado {soma_produtos}, "
                f"declarado {nota.totalizadores.valor_produtos}"
            )
        
        # Valida valor total da nota
        valor_calculado = (
            nota.totalizadores.valor_produtos +
            nota.totalizadores.valor_frete +
            nota.totalizadores.valor_seguro +
            nota.totalizadores.valor_ipi -
            nota.totalizadores.valor_desconto
        )
        
        if abs(valor_calculado - nota.totalizadores.valor_total_nota) > Decimal('0.10'):
            inconsistencias.append(
                f"Divergência no valor total: calculado {valor_calculado}, "
                f"declarado {nota.totalizadores.valor_total_nota}"
            )
        
        # Valida impostos por produto
        for idx, produto in enumerate(nota.produtos):
            valor_esperado = produto.quantidade * produto.valor_unitario
            if abs(valor_esperado - produto.valor_total) > Decimal('0.01'):
                inconsistencias.append(
                    f"Produto {idx+1} ({produto.descricao}): divergência no cálculo - "
                    f"esperado {valor_esperado}, declarado {produto.valor_total}"
                )
        
        return inconsistencias
    
    def validar_com_ia(self, nota: NotaFiscal) -> str:
        """Usa Gemini para análise inteligente da nota"""
        try:
            # Prepara dados para a IA
            dados_nota = {
                "numero": nota.numero,
                "data": nota.data_emissao.strftime("%d/%m/%Y"),
                "emitente": {
                    "nome": nota.emitente.razao_social,
                    "cnpj": nota.emitente.cnpj
                },
                "destinatario": {
                    "nome": nota.destinatario.nome,
                    "documento": nota.destinatario.cpf_cnpj
                },
                "produtos": [
                    {
                        "descricao": p.descricao,
                        "quantidade": float(p.quantidade),
                        "valor_unitario": float(p.valor_unitario),
                        "valor_total": float(p.valor_total),
                        "ncm": p.ncm,
                        "cfop": p.cfop
                    }
                    for p in nota.produtos[:5]  # Limita a 5 produtos
                ],
                "totais": {
                    "produtos": float(nota.totalizadores.valor_produtos),
                    "icms": float(nota.totalizadores.valor_icms),
                    "ipi": float(nota.totalizadores.valor_ipi),
                    "total": float(nota.totalizadores.valor_total_nota)
                }
            }
            
            prompt = f"""Você é um contador especialista em análise fiscal. Analise esta Nota Fiscal Eletrônica (NF-e) e forneça:

1. Verificação de conformidade fiscal (CFOP, NCM, impostos)
2. Identificação de possíveis irregularidades ou alertas
3. Recomendações para o destinatário
4. Análise de risco fiscal (baixo/médio/alto)

Dados da NF-e:
{json.dumps(dados_nota, indent=2, ensure_ascii=False)}

Forneça uma análise detalhada mas concisa (máximo 500 palavras)."""

            response = self.model.generate_content(prompt)
            return response.text
            
        except Exception as e:
            return f"Erro na análise de IA: {str(e)}"
    
    def validar_nota(self, nota: NotaFiscal) -> ResultadoValidacao:
        """Executa validação completa da nota"""
        inconsistencias = []
        alertas = []
        recomendacoes = []
        
        # Validação de documentos
        if not self.validar_cnpj(nota.emitente.cnpj):
            inconsistencias.append(f"CNPJ do emitente inválido: {nota.emitente.cnpj}")
        
        doc_dest = nota.destinatario.cpf_cnpj
        if len(''.join(filter(str.isdigit, doc_dest))) == 14:
            if not self.validar_cnpj(doc_dest):
                inconsistencias.append(f"CNPJ do destinatário inválido: {doc_dest}")
        elif len(''.join(filter(str.isdigit, doc_dest))) == 11:
            if not self.validar_cpf(doc_dest):
                inconsistencias.append(f"CPF do destinatário inválido: {doc_dest}")
        
        # Validação da chave de acesso
        if not self.validar_chave_acesso(nota.chave_acesso):
            inconsistencias.append("Chave de acesso com dígito verificador inválido")
        
        # Validação de cálculos
        inconsistencias.extend(self.validar_calculos(nota))
        
        # Alertas gerais
        if nota.totalizadores.valor_total_nota > Decimal('100000'):
            alertas.append("Valor elevado da nota - verificar necessidade de garantias")
        
        if len(nota.produtos) > 50:
            alertas.append("Nota com muitos itens - atenção ao prazo de conferência")
        
        # Recomendações
        if nota.totalizadores.valor_desconto > Decimal('0'):
            recomendacoes.append("Verificar condições comerciais do desconto concedido")
        
        if nota.totalizadores.valor_icms == Decimal('0'):
            recomendacoes.append("ICMS zerado - confirmar regime tributário ou benefício fiscal")
        
        # Análise com IA
        analise_ia = self.validar_com_ia(nota)
        
        # Calcula score de confiança
        total_verificacoes = 5 + len(nota.produtos)
        erros_graves = len(inconsistencias)
        score = max(0.0, 1.0 - (erros_graves * 0.2))
        
        return ResultadoValidacao(
            valido=len(inconsistencias) == 0,
            score_confianca=score,
            inconsistencias=inconsistencias,
            alertas=alertas,
            recomendacoes=recomendacoes,
            analise_ia=analise_ia
        )