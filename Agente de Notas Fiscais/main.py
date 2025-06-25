import streamlit as st
from dotenv import load_dotenv
from utils import descompactar_arquivos  # Sua função para extrair zip
from agent import carregar_csvs_de_zip, criar_agente

load_dotenv()

st.title("📊 Agente Inteligente - Análise de Notas Fiscais")

# Extrair arquivos zip para pasta temporária
pasta_csv = descompactar_arquivos()

# Carregar e validar CSVs, retornar DataFrame completo
df = carregar_csvs_de_zip(pasta_csv)

st.write("✅ Dados carregados com sucesso:")
st.dataframe(df.head())
if df.empty:
    st.error("❌ Erro: DataFrame está vazio. Verifique os arquivos CSV.")

# Criar agente com LLM
agente = criar_agente(df)

# Pergunta do usuário
pergunta = st.text_input("Digite sua pergunta sobre os dados:")

if pergunta:
    with st.spinner("🧠 Processando a resposta..."):
        try:
            resposta = agente.invoke({"input": pergunta})
            st.success("Resposta:")
            st.write(resposta["output"] if isinstance(resposta, dict) else resposta)
        except StopIteration:
            st.error("Erro interno: modelo retornou resposta incompleta ou vazia.")
        except Exception as e:
            st.error(f"Erro ao processar a pergunta: {e}")