import pandas as pd
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib.units import cm
from datetime import datetime
from models import NotaFiscal, ResultadoValidacao
from typing import List
import io


class GeradorRelatorios:
    """Gerador de relatórios gerenciais e fiscais"""
    
    def __init__(self):
        self.styles = getSampleStyleSheet()
        self._criar_estilos_customizados()
    
    def _criar_estilos_customizados(self):
        """Cria estilos customizados para o PDF"""
        self.styles.add(ParagraphStyle(
            name='TituloCustom',
            parent=self.styles['Heading1'],
            fontSize=16,
            textColor=colors.HexColor('#1a237e'),
            spaceAfter=12
        ))
        
        self.styles.add(ParagraphStyle(
            name='SubtituloCustom',
            parent=self.styles['Heading2'],
            fontSize=12,
            textColor=colors.HexColor('#303f9f'),
            spaceAfter=8
        ))
    
    def gerar_dataframe_produtos(self, nota: NotaFiscal) -> pd.DataFrame:
        """Gera DataFrame com produtos da nota"""
        dados = []
        for p in nota.produtos:
            dados.append({
                'Código': p.codigo,
                'Descrição': p.descricao,
                'NCM': p.ncm,
                'CFOP': p.cfop,
                'Qtd': float(p.quantidade),
                'Valor Unit.': float(p.valor_unitario),
                'Valor Total': float(p.valor_total),
                'ICMS': float(p.impostos.icms_valor),
                'IPI': float(p.impostos.ipi_valor)
            })
        return pd.DataFrame(dados)
    
    def gerar_excel(self, notas: List[NotaFiscal]) -> bytes:
        """Gera arquivo Excel com múltiplas notas"""
        output = io.BytesIO()
        
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            # Aba: Resumo Geral
            resumo_data = []
            for nota in notas:
                resumo_data.append({
                    'Nota': nota.numero,
                    'Data': nota.data_emissao.strftime('%d/%m/%Y'),
                    'Emitente': nota.emitente.razao_social,
                    'CNPJ Emitente': nota.emitente.cnpj,
                    'Destinatário': nota.destinatario.nome,
                    'Valor Produtos': float(nota.totalizadores.valor_produtos),
                    'ICMS': float(nota.totalizadores.valor_icms),
                    'IPI': float(nota.totalizadores.valor_ipi),
                    'Valor Total': float(nota.totalizadores.valor_total_nota)
                })
            
            df_resumo = pd.DataFrame(resumo_data)
            df_resumo.to_excel(writer, sheet_name='Resumo', index=False)
            
            # Aba: Detalhamento (primeira nota como exemplo)
            if notas:
                df_produtos = self.gerar_dataframe_produtos(notas[0])
                df_produtos.to_excel(writer, sheet_name='Produtos', index=False)
            
            # Aba: Totalizadores
            totais_data = []
            for nota in notas:
                totais_data.append({
                    'Nota': nota.numero,
                    'Base ICMS': float(nota.totalizadores.base_calculo_icms),
                    'ICMS': float(nota.totalizadores.valor_icms),
                    'IPI': float(nota.totalizadores.valor_ipi),
                    'PIS': float(nota.totalizadores.valor_pis),
                    'COFINS': float(nota.totalizadores.valor_cofins),
                    'Frete': float(nota.totalizadores.valor_frete),
                    'Seguro': float(nota.totalizadores.valor_seguro),
                    'Desconto': float(nota.totalizadores.valor_desconto)
                })
            
            df_totais = pd.DataFrame(totais_data)
            df_totais.to_excel(writer, sheet_name='Impostos', index=False)
        
        output.seek(0)
        return output.read()
    
    def gerar_pdf_relatorio(
        self, 
        nota: NotaFiscal, 
        validacao: ResultadoValidacao
    ) -> bytes:
        """Gera relatório PDF completo"""
        output = io.BytesIO()
        doc = SimpleDocTemplate(output, pagesize=A4)
        elementos = []
        
        # Título
        titulo = Paragraph(
            f"Relatório de Análise Fiscal - NF-e {nota.numero}",
            self.styles['TituloCustom']
        )
        elementos.append(titulo)
        elementos.append(Spacer(1, 0.5*cm))
        
        # Dados da Nota
        elementos.append(Paragraph("1. DADOS DA NOTA FISCAL", self.styles['SubtituloCustom']))
        
        dados_nota = [
            ['Chave de Acesso:', nota.chave_acesso],
            ['Número:', nota.numero],
            ['Série:', nota.serie],
            ['Data de Emissão:', nota.data_emissao.strftime('%d/%m/%Y %H:%M:%S')],
        ]
        
        tabela_dados = Table(dados_nota, colWidths=[5*cm, 12*cm])
        tabela_dados.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#e3f2fd')),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        elementos.append(tabela_dados)
        elementos.append(Spacer(1, 0.5*cm))
        
        # Emitente e Destinatário
        elementos.append(Paragraph("2. PARTES ENVOLVIDAS", self.styles['SubtituloCustom']))
        
        partes = [
            ['EMITENTE', 'DESTINATÁRIO'],
            [
                f"{nota.emitente.razao_social}\nCNPJ: {nota.emitente.cnpj}\n{nota.emitente.endereco.municipio}/{nota.emitente.endereco.uf}",
                f"{nota.destinatario.nome}\nDoc: {nota.destinatario.cpf_cnpj}\n{nota.destinatario.endereco.municipio}/{nota.destinatario.endereco.uf}"
            ]
        ]
        
        tabela_partes = Table(partes, colWidths=[8.5*cm, 8.5*cm])
        tabela_partes.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a237e')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        elementos.append(tabela_partes)
        elementos.append(Spacer(1, 0.5*cm))
        
        # Totalizadores
        elementos.append(Paragraph("3. VALORES E IMPOSTOS", self.styles['SubtituloCustom']))
        
        valores = [
            ['Descrição', 'Valor (R$)'],
            ['Valor dos Produtos', f"{nota.totalizadores.valor_produtos:,.2f}"],
            ['Base Cálculo ICMS', f"{nota.totalizadores.base_calculo_icms:,.2f}"],
            ['ICMS', f"{nota.totalizadores.valor_icms:,.2f}"],
            ['IPI', f"{nota.totalizadores.valor_ipi:,.2f}"],
            ['PIS', f"{nota.totalizadores.valor_pis:,.2f}"],
            ['COFINS', f"{nota.totalizadores.valor_cofins:,.2f}"],
            ['Frete', f"{nota.totalizadores.valor_frete:,.2f}"],
            ['Desconto', f"{nota.totalizadores.valor_desconto:,.2f}"],
            ['VALOR TOTAL', f"{nota.totalizadores.valor_total_nota:,.2f}"],
        ]
        
        tabela_valores = Table(valores, colWidths=[12*cm, 5*cm])
        tabela_valores.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a237e')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#ffd54f')),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('ALIGN', (1, 1), (-1, -1), 'RIGHT'),
        ]))
        elementos.append(tabela_valores)
        elementos.append(Spacer(1, 0.5*cm))
        
        # Resultado da Validação
        elementos.append(Paragraph("4. RESULTADO DA VALIDAÇÃO", self.styles['SubtituloCustom']))
        
        status_color = colors.HexColor('#4caf50') if validacao.valido else colors.HexColor('#f44336')
        status_text = "✓ APROVADA" if validacao.valido else "✗ COM PENDÊNCIAS"
        
        validacao_info = [
            ['Status:', status_text],
            ['Score de Confiança:', f"{validacao.score_confianca * 100:.1f}%"],
            ['Inconsistências:', str(len(validacao.inconsistencias))],
            ['Alertas:', str(len(validacao.alertas))],
        ]
        
        tabela_validacao = Table(validacao_info, colWidths=[5*cm, 12*cm])
        tabela_validacao.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#e3f2fd')),
            ('BACKGROUND', (1, 0), (1, 0), status_color),
            ('TEXTCOLOR', (1, 0), (1, 0), colors.whitesmoke),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 0), (1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
        ]))
        elementos.append(tabela_validacao)
        elementos.append(Spacer(1, 0.5*cm))
        
        # Inconsistências
        if validacao.inconsistencias:
            elementos.append(Paragraph("⚠️ INCONSISTÊNCIAS ENCONTRADAS:", self.styles['SubtituloCustom']))
            for inc in validacao.inconsistencias:
                elementos.append(Paragraph(f"• {inc}", self.styles['Normal']))
            elementos.append(Spacer(1, 0.3*cm))
        
        # Alertas
        if validacao.alertas:
            elementos.append(Paragraph("📌 ALERTAS:", self.styles['SubtituloCustom']))
            for alerta in validacao.alertas:
                elementos.append(Paragraph(f"• {alerta}", self.styles['Normal']))
            elementos.append(Spacer(1, 0.3*cm))
        
        # Recomendações
        if validacao.recomendacoes:
            elementos.append(Paragraph("💡 RECOMENDAÇÕES:", self.styles['SubtituloCustom']))
            for rec in validacao.recomendacoes:
                elementos.append(Paragraph(f"• {rec}", self.styles['Normal']))
            elementos.append(Spacer(1, 0.5*cm))
        
        # Análise da IA
        if validacao.analise_ia:
            elementos.append(PageBreak())
            elementos.append(Paragraph("5. ANÁLISE INTELIGENTE (IA)", self.styles['SubtituloCustom']))
            
            # Divide análise em parágrafos
            for paragrafo in validacao.analise_ia.split('\n\n'):
                if paragrafo.strip():
                    elementos.append(Paragraph(paragrafo.strip(), self.styles['Normal']))
                    elementos.append(Spacer(1, 0.3*cm))
        
        # Rodapé
        elementos.append(Spacer(1, 1*cm))
        rodape = Paragraph(
            f"Relatório gerado em {datetime.now().strftime('%d/%m/%Y às %H:%M:%S')} | "
            f"Agente Fiscal IA - Sistema de Análise Automatizada",
            self.styles['Normal']
        )
        elementos.append(rodape)
        
        # Gera PDF
        doc.build(elementos)
        output.seek(0)
        return output.read()