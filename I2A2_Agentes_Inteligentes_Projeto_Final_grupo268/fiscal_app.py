import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime
import pandas as pd
from extractor import NFeExtractor
from validator import ValidadorInteligente
from reporter import GeradorRelatorios
from models import NotaFiscal


# Configuração da página
st.set_page_config(
    page_title="Agente Fiscal IA",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estilo customizado
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #1a237e;
        font-weight: bold;
        text-align: center;
        margin-bottom: 1rem;
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1rem;
        border-radius: 10px;
        color: white;
    }
    .success-box {
        background-color: #d4edda;
        border-left: 5px solid #28a745;
        padding: 1rem;
        border-radius: 5px;
        margin: 1rem 0;
    }
    .error-box {
        background-color: #f8d7da;
        border-left: 5px solid #dc3545;
        padding: 1rem;
        border-radius: 5px;
        margin: 1rem 0;
    }
    .warning-box {
        background-color: #fff3cd;
        border-left: 5px solid #ffc107;
        padding: 1rem;
        border-radius: 5px;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)


def inicializar_sessao():
    """Inicializa variáveis de sessão"""
    if 'notas_processadas' not in st.session_state:
        st.session_state.notas_processadas = []
    if 'validacoes' not in st.session_state:
        st.session_state.validacoes = []


def criar_graficos_dashboard(notas):
    """Cria gráficos para o dashboard"""
    if not notas:
        return None, None, None
    
    # Gráfico 1: Valores por Nota
    fig_valores = go.Figure()
    fig_valores.add_trace(go.Bar(
        x=[f"NF-e {n.numero}" for n in notas],
        y=[float(n.totalizadores.valor_total_nota) for n in notas],
        name='Valor Total',
        marker_color='#1a237e'
    ))
    fig_valores.update_layout(
        title="Valor Total por Nota Fiscal",
        xaxis_title="Nota Fiscal",
        yaxis_title="Valor (R$)",
        height=400
    )
    
    # Gráfico 2: Distribuição de Impostos
    if notas:
        nota_exemplo = notas[0]
        impostos_data = {
            'Imposto': ['ICMS', 'IPI', 'PIS', 'COFINS'],
            'Valor': [
                float(nota_exemplo.totalizadores.valor_icms),
                float(nota_exemplo.totalizadores.valor_ipi),
                float(nota_exemplo.totalizadores.valor_pis),
                float(nota_exemplo.totalizadores.valor_cofins)
            ]
        }
        fig_impostos = px.pie(
            impostos_data,
            values='Valor',
            names='Imposto',
            title='Distribuição de Impostos (Primeira Nota)',
            color_discrete_sequence=px.colors.sequential.Blues_r
        )
    else:
        fig_impostos = None
    
    # Gráfico 3: Timeline de Emissões
    datas = [n.data_emissao for n in notas]
    valores = [float(n.totalizadores.valor_total_nota) for n in notas]
    
    fig_timeline = go.Figure()
    fig_timeline.add_trace(go.Scatter(
        x=datas,
        y=valores,
        mode='lines+markers',
        name='Valor',
        line=dict(color='#667eea', width=3),
        marker=dict(size=10)
    ))
    fig_timeline.update_layout(
        title="Timeline de Emissões",
        xaxis_title="Data",
        yaxis_title="Valor (R$)",
        height=400
    )
    
    return fig_valores, fig_impostos, fig_timeline


def main():
    """Função principal da aplicação"""
    inicializar_sessao()
    
    # Header
    st.markdown('<p class="main-header">🤖 Agente Fiscal IA</p>', unsafe_allow_html=True)
    st.markdown(
        "<p style='text-align: center; color: #666;'>Sistema Inteligente de Processamento e Análise de Documentos Fiscais</p>",
        unsafe_allow_html=True
    )
    
    # Sidebar - Configurações
    with st.sidebar:
        st.header("⚙️ Configurações")
        
        api_key = st.text_input(
            "API Key do Gemini",
            type="password",
            help="Insira sua chave de API do Google Gemini"
        )
        
        st.markdown("---")
        st.markdown("### 📋 Menu")
        pagina = st.radio(
            "Selecione:",
            ["📤 Upload e Processamento", "📊 Dashboard", "📈 Relatórios"],
            label_visibility="collapsed"
        )
        
        st.markdown("---")
        st.markdown("### 📚 Sobre")
        st.info(
            """
            **Agente Fiscal IA v1.0**
            
            Sistema desenvolvido para:
            - Extração automática de dados
            - Validação inteligente
            - Geração de relatórios
            
            Tecnologias:
            - Python + Streamlit
            - Google Gemini AI
            - LangChain
            """
        )
    
    # Página: Upload e Processamento
    if pagina == "📤 Upload e Processamento":
        st.header("📤 Upload e Processamento de NF-e")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            uploaded_files = st.file_uploader(
                "Carregar arquivos XML de NF-e",
                type=['xml'],
                accept_multiple_files=True,
                help="Selecione um ou mais arquivos XML de Nota Fiscal Eletrônica"
            )
        
        with col2:
            st.markdown("### 📝 Instruções")
            st.markdown("""
            1. Configure sua API Key do Gemini
            2. Faça upload dos XMLs de NF-e
            3. Clique em processar
            4. Visualize os resultados
            """)
        
        if uploaded_files and api_key:
            if st.button("🚀 Processar Notas Fiscais", type="primary", use_container_width=True):
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                extractor = NFeExtractor()
                validador = ValidadorInteligente(api_key)
                
                total_files = len(uploaded_files)
                
                for idx, uploaded_file in enumerate(uploaded_files):
                    try:
                        status_text.text(f"Processando {uploaded_file.name}...")
                        progress_bar.progress((idx + 1) / total_files)
                        
                        # Extração
                        xml_content = uploaded_file.read()
                        extractor.carregar_xml(xml_content)
                        nota = extractor.extrair_nota_fiscal()
                        
                        # Validação
                        validacao = validador.validar_nota(nota)
                        
                        # Armazena resultados
                        st.session_state.notas_processadas.append(nota)
                        st.session_state.validacoes.append(validacao)
                        
                    except Exception as e:
                        st.error(f"Erro ao processar {uploaded_file.name}: {str(e)}")
                
                status_text.text("✅ Processamento concluído!")
                st.success(f"**{total_files} nota(s) processada(s) com sucesso!**")
                st.balloons()
        
        # Exibe resultados
        if st.session_state.notas_processadas:
            st.markdown("---")
            st.subheader("📋 Notas Processadas")
            
            for idx, (nota, validacao) in enumerate(zip(
                st.session_state.notas_processadas,
                st.session_state.validacoes
            )):
                with st.expander(f"NF-e {nota.numero} - {nota.emitente.razao_social}"):
                    col1, col2, col3, col4 = st.columns(4)
                    
                    with col1:
                        st.metric("Número", nota.numero)
                    with col2:
                        st.metric("Valor Total", f"R$ {nota.totalizadores.valor_total_nota:,.2f}")
                    with col3:
                        status = "✅ Válida" if validacao.valido else "⚠️ Pendente"
                        st.metric("Status", status)
                    with col4:
                        st.metric("Confiança", f"{validacao.score_confianca * 100:.1f}%")
                    
                    # Detalhes
                    tab1, tab2, tab3 = st.tabs(["📄 Dados", "✓ Validação", "🤖 Análise IA"])
                    
                    with tab1:
                        st.markdown("**Emitente:**")
                        st.text(f"{nota.emitente.razao_social} - CNPJ: {nota.emitente.cnpj}")
                        
                        st.markdown("**Destinatário:**")
                        st.text(f"{nota.destinatario.nome} - Doc: {nota.destinatario.cpf_cnpj}")
                        
                        st.markdown("**Produtos:**")
                        df_produtos = pd.DataFrame([
                            {
                                'Código': p.codigo,
                                'Descrição': p.descricao[:40] + '...' if len(p.descricao) > 40 else p.descricao,
                                'Qtd': float(p.quantidade),
                                'Valor Unit.': f"R$ {float(p.valor_unitario):.2f}",
                                'Total': f"R$ {float(p.valor_total):.2f}"
                            }
                            for p in nota.produtos
                        ])
                        st.dataframe(df_produtos, use_container_width=True)
                    
                    with tab2:
                        if validacao.inconsistencias:
                            st.markdown('<div class="error-box">', unsafe_allow_html=True)
                            st.markdown("**❌ Inconsistências:**")
                            for inc in validacao.inconsistencias:
                                st.markdown(f"- {inc}")
                            st.markdown('</div>', unsafe_allow_html=True)
                        
                        if validacao.alertas:
                            st.markdown('<div class="warning-box">', unsafe_allow_html=True)
                            st.markdown("**⚠️ Alertas:**")
                            for alerta in validacao.alertas:
                                st.markdown(f"- {alerta}")
                            st.markdown('</div>', unsafe_allow_html=True)
                        
                        if validacao.recomendacoes:
                            st.info("**💡 Recomendações:**\n" + "\n".join(f"- {r}" for r in validacao.recomendacoes))
                        
                        if not validacao.inconsistencias and not validacao.alertas:
                            st.markdown('<div class="success-box">', unsafe_allow_html=True)
                            st.markdown("✅ **Nenhuma inconsistência encontrada!**")
                            st.markdown('</div>', unsafe_allow_html=True)
                    
                    with tab3:
                        if validacao.analise_ia:
                            st.markdown(validacao.analise_ia)
                        else:
                            st.info("Análise de IA não disponível")
    
    # Página: Dashboard
    elif pagina == "📊 Dashboard":
        st.header("📊 Dashboard Gerencial")
        
        if not st.session_state.notas_processadas:
            st.warning("⚠️ Nenhuma nota processada. Faça upload de arquivos XML na página de Processamento.")
        else:
            notas = st.session_state.notas_processadas
            validacoes = st.session_state.validacoes
            
            # Métricas principais
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric(
                    "Total de Notas",
                    len(notas),
                    help="Quantidade de notas processadas"
                )
            
            with col2:
                valor_total = sum(float(n.totalizadores.valor_total_nota) for n in notas)
                st.metric(
                    "Valor Total",
                    f"R$ {valor_total:,.2f}",
                    help="Soma do valor de todas as notas"
                )
            
            with col3:
                impostos_total = sum(
                    float(n.totalizadores.valor_icms + n.totalizadores.valor_ipi +
                          n.totalizadores.valor_pis + n.totalizadores.valor_cofins)
                    for n in notas
                )
                st.metric(
                    "Total de Impostos",
                    f"R$ {impostos_total:,.2f}",
                    help="Soma de todos os impostos"
                )
            
            with col4:
                notas_validas = sum(1 for v in validacoes if v.valido)
                st.metric(
                    "Notas Válidas",
                    f"{notas_validas}/{len(notas)}",
                    help="Notas sem inconsistências"
                )
            
            # Gráficos
            st.markdown("---")
            fig_valores, fig_impostos, fig_timeline = criar_graficos_dashboard(notas)
            
            col1, col2 = st.columns(2)
            with col1:
                if fig_valores:
                    st.plotly_chart(fig_valores, use_container_width=True)
            with col2:
                if fig_impostos:
                    st.plotly_chart(fig_impostos, use_container_width=True)
            
            if fig_timeline:
                st.plotly_chart(fig_timeline, use_container_width=True)
    
    # Página: Relatórios
    elif pagina == "📈 Relatórios":
        st.header("📈 Geração de Relatórios")
        
        if not st.session_state.notas_processadas:
            st.warning("⚠️ Nenhuma nota processada. Faça upload de arquivos XML na página de Processamento.")
        else:
            st.info("Selecione o tipo de relatório que deseja gerar:")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("📊 Relatório Excel")
                st.markdown("""
                - Resumo de todas as notas
                - Detalhamento de produtos
                - Análise de impostos
                """)
                
                if st.button("📥 Gerar Excel", use_container_width=True):
                    gerador = GeradorRelatorios()
                    excel_data = gerador.gerar_excel(st.session_state.notas_processadas)
                    
                    st.download_button(
                        label="⬇️ Download Excel",
                        data=excel_data,
                        file_name=f"relatorio_fiscal_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True
                    )
            
            with col2:
                st.subheader("📄 Relatório PDF")
                st.markdown("""
                - Análise detalhada
                - Validações realizadas
                - Insights de IA
                """)
                
                nota_selecionada = st.selectbox(
                    "Selecione a nota:",
                    range(len(st.session_state.notas_processadas)),
                    format_func=lambda x: f"NF-e {st.session_state.notas_processadas[x].numero}"
                )
                
                if st.button("📥 Gerar PDF", use_container_width=True):
                    gerador = GeradorRelatorios()
                    nota = st.session_state.notas_processadas[nota_selecionada]
                    validacao = st.session_state.validacoes[nota_selecionada]
                    
                    pdf_data = gerador.gerar_pdf_relatorio(nota, validacao)
                    
                    st.download_button(
                        label="⬇️ Download PDF",
                        data=pdf_data,
                        file_name=f"analise_nfe_{nota.numero}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                        mime="application/pdf",
                        use_container_width=True
                    )
    
    # Footer
    st.markdown("---")
    st.markdown(
        "<p style='text-align: center; color: #999; font-size: 0.9rem;'>"
        "Agente Fiscal IA - Desenvolvido para fins educacionais | "
        f"© {datetime.now().year}"
        "</p>",
        unsafe_allow_html=True
    )


if __name__ == "__main__":
    main()