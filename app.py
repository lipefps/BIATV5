import os
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import pdfplumber
from typing import Tuple, List, Dict

class DashboardConfig:
    PAGE_TITLE = "Business Intelligence | Atividade 5"
    LAYOUT = "wide"
    SIDEBAR_STATE = "expanded"
    DATA_PATH = "dados-vendas.xlsx.pdf"
    
    COL_FILIAL = "Filial_Loja"
    COL_CATEGORIA = "Categoria Produto"
    COL_VALOR = "Valor_Total_Venda"
    COL_IDADE = "Idade_Cliente"
    COL_DATA = "Data_Compra"

class DataLoader:
    @staticmethod
    @st.cache_data(show_spinner="Processando base de dados...")
    def execute_pipeline(file_path: str) -> pd.DataFrame:
        raw_data = DataLoader._extract_from_pdf(file_path)
        if not raw_data:
            return pd.DataFrame()
            
        df = DataLoader._build_dataframe(raw_data)
        df = DataLoader._clean_columns(df)
        df = DataLoader._apply_data_types(df)
        df = DataLoader._create_business_features(df)
        
        return df

    @staticmethod
    def _extract_from_pdf(file_path: str) -> List[List[str]]:
        if not os.path.exists(file_path):
            st.error(f"Arquivo não localizado: {file_path}")
            return []
            
        extracted_rows = []
        try:
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    table = page.extract_table()
                    if table:
                        extracted_rows.extend(table)
        except Exception as e:
            st.error(f"Falha na leitura do documento: {str(e)}")
            
        return extracted_rows

    @staticmethod
    def _build_dataframe(raw_data: List[List[str]]) -> pd.DataFrame:
        header = raw_data[0]
        data = raw_data[1:]
        df = pd.DataFrame(data, columns=header)
        df = df[df[header[0]] != header[0]]
        return df

    @staticmethod
    def _clean_columns(df: pd.DataFrame) -> pd.DataFrame:
        df.columns = df.columns.str.replace('\n', ' ').str.strip()
        return df

    @staticmethod
    def _apply_data_types(df: pd.DataFrame) -> pd.DataFrame:
        if DashboardConfig.COL_VALOR in df.columns:
            df[DashboardConfig.COL_VALOR] = (
                df[DashboardConfig.COL_VALOR]
                .astype(str)
                .str.replace(',', '.')
                .astype(float)
            )
        
        if DashboardConfig.COL_IDADE in df.columns:
            df[DashboardConfig.COL_IDADE] = pd.to_numeric(
                df[DashboardConfig.COL_IDADE], 
                errors='coerce'
            )
            
        if DashboardConfig.COL_DATA in df.columns:
            df[DashboardConfig.COL_DATA] = pd.to_datetime(
                df[DashboardConfig.COL_DATA], 
                errors='coerce'
            )
            
        return df

    @staticmethod
    def _create_business_features(df: pd.DataFrame) -> pd.DataFrame:
        if DashboardConfig.COL_IDADE in df.columns:
            bins = [0, 25, 40, 60, 100]
            labels = ['Até 25 anos', '26 a 40 anos', '41 a 60 anos', '60+ anos']
            df['Faixa_Etaria'] = pd.cut(df[DashboardConfig.COL_IDADE], bins=bins, labels=labels)
        return df

class SalesEngine:
    def __init__(self, df: pd.DataFrame):
        self._df = df

    def apply_filters(self, filiais: List[str], categorias: List[str]) -> pd.DataFrame:
        df_filtered = self._df.copy()
        
        target_filial = self._resolve_column_name('Filial', DashboardConfig.COL_FILIAL)
        target_cat = self._resolve_column_name('Categoria', DashboardConfig.COL_CATEGORIA)
        
        if filiais and target_filial in df_filtered.columns:
            df_filtered = df_filtered[df_filtered[target_filial].isin(filiais)]
            
        if categorias and target_cat in df_filtered.columns:
            df_filtered = df_filtered[df_filtered[target_cat].isin(categorias)]
            
        return df_filtered

    def generate_kpis(self) -> Dict[str, float]:
        faturamento = self._df[DashboardConfig.COL_VALOR].sum() if DashboardConfig.COL_VALOR in self._df.columns else 0.0
        transacoes = len(self._df)
        ticket_medio = faturamento / transacoes if transacoes > 0 else 0.0
        
        return {
            "faturamento": float(faturamento),
            "transacoes": float(transacoes),
            "ticket_medio": float(ticket_medio)
        }

    def _resolve_column_name(self, keyword: str, default: str) -> str:
        return next((c for c in self._df.columns if keyword in c), default)

class UIRenderer:
    @staticmethod
    def render_page_setup():
        st.set_page_config(
            page_title=DashboardConfig.PAGE_TITLE,
            layout=DashboardConfig.LAYOUT,
            initial_sidebar_state=DashboardConfig.SIDEBAR_STATE
        )

    @staticmethod
    def render_header():
        st.title(":material/dashboard: Dashboard - ATV 5 - Supermercado")
        st.markdown("Monitoramento de performance e inteligência de vendas")
        st.divider()

    @staticmethod
    def render_sidebar(df: pd.DataFrame) -> Tuple[List[str], List[str]]:
        st.sidebar.header(":material/filter_alt: Filtros Dinâmicos")
        
        col_filial = next((c for c in df.columns if 'Filial' in c), DashboardConfig.COL_FILIAL)
        col_cat = next((c for c in df.columns if 'Categoria' in c), DashboardConfig.COL_CATEGORIA)
        
        filiais_disp = df[col_filial].dropna().unique().tolist() if col_filial in df.columns else []
        categorias_disp = df[col_cat].dropna().unique().tolist() if col_cat in df.columns else []
        
        selecao_filiais = st.sidebar.multiselect("Filial:", filiais_disp, default=filiais_disp)
        selecao_categorias = st.sidebar.multiselect("Categoria:", categorias_disp, default=categorias_disp)
        
        st.sidebar.divider()
        st.sidebar.info("As seleções alteram as métricas em tempo real.")
        
        return selecao_filiais, selecao_categorias

    @staticmethod
    def render_kpi_cards(kpis: Dict[str, float]):
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Faturamento Global", f"R$ {kpis['faturamento']:,.2f}", delta="Total")
        with col2:
            st.metric("Volume de Transações", int(kpis['transacoes']), delta="Vendas", delta_color="off")
        with col3:
            st.metric("Ticket Médio", f"R$ {kpis['ticket_medio']:,.2f}", delta="Por Cliente")
        st.write("") 

    @staticmethod
    def render_charts(df: pd.DataFrame):
        col1, col2 = st.columns([1, 1])
        
        col_filial = next((c for c in df.columns if 'Filial' in c), DashboardConfig.COL_FILIAL)
        col_cat = next((c for c in df.columns if 'Categoria' in c), DashboardConfig.COL_CATEGORIA)

        with col1:
            if col_filial in df.columns and DashboardConfig.COL_VALOR in df.columns:
                df_filial = df.groupby(col_filial, as_index=False)[DashboardConfig.COL_VALOR].sum()
                fig_filial = px.bar(
                    df_filial, 
                    x=col_filial, 
                    y=DashboardConfig.COL_VALOR,
                    color=col_filial,
                    text_auto='.2f',
                    title="Receita por Unidade",
                    color_discrete_sequence=px.colors.qualitative.Bold
                )
                fig_filial.update_layout(showlegend=False, xaxis_title="", yaxis_title="Receita (R$)")
                st.plotly_chart(fig_filial, use_container_width=True)

        with col2:
            if col_cat in df.columns and DashboardConfig.COL_VALOR in df.columns:
                df_cat = df.groupby(col_cat, as_index=False)[DashboardConfig.COL_VALOR].sum()
                fig_cat = go.Figure(data=[go.Pie(
                    labels=df_cat[col_cat], 
                    values=df_cat[DashboardConfig.COL_VALOR], 
                    hole=.4,
                    marker=dict(colors=px.colors.qualitative.Pastel)
                )])
                fig_cat.update_layout(title_text="Distribuição por Categoria")
                st.plotly_chart(fig_cat, use_container_width=True)

        if 'Faixa_Etaria' in df.columns and DashboardConfig.COL_VALOR in df.columns:
            df_idade = df.groupby('Faixa_Etaria', observed=True, as_index=False)[DashboardConfig.COL_VALOR].sum()
            fig_idade = px.area(
                df_idade, 
                x='Faixa_Etaria', 
                y=DashboardConfig.COL_VALOR, 
                markers=True,
                title="Receita por Perfil Demográfico",
                color_discrete_sequence=['#00b4d8']
            )
            fig_idade.update_layout(xaxis_title="Faixa Etária", yaxis_title="Receita (R$)")
            st.plotly_chart(fig_idade, use_container_width=True)

    @staticmethod
    def render_data_table(df: pd.DataFrame):
        with st.expander("Visualizar base de dados"):
            st.dataframe(df, use_container_width=True)
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label=":material/download: Exportar CSV",
                data=csv,
                file_name='extracao_vendas.csv',
                mime='text/csv',
            )

class Application:
    def __init__(self):
        UIRenderer.render_page_setup()
        self.raw_data = DataLoader.execute_pipeline(DashboardConfig.DATA_PATH)

    def run(self):
        UIRenderer.render_header()
        
        if self.raw_data.empty:
            st.warning("A aplicação foi interrompida pois não há dados disponíveis.")
            return

        filiais, categorias = UIRenderer.render_sidebar(self.raw_data)
        
        engine = SalesEngine(self.raw_data)
        filtered_data = engine.apply_filters(filiais, categorias)
        
        if filtered_data.empty:
            st.warning("Nenhum registro corresponde aos filtros aplicados.")
            return

        filtered_engine = SalesEngine(filtered_data)
        kpis = filtered_engine.generate_kpis()
        
        UIRenderer.render_kpi_cards(kpis)
        UIRenderer.render_charts(filtered_data)
        UIRenderer.render_data_table(filtered_data)

if __name__ == "__main__":
    app = Application()
    app.run()
