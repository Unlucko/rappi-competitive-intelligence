import json
import os
import sys

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from analysis.comparative_analyzer import ComparativeAnalyzer
from analysis.insight_generator import InsightGenerator
from analysis.report_builder import PLATFORM_COLOR_MAP, ReportBuilder

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(BASE_DIR, "output")


def load_scraped_data() -> pd.DataFrame:
    scraped_data_path = os.path.join(OUTPUT_DIR, "scraped_data.json")
    sample_data_path = os.path.join(OUTPUT_DIR, "sample_data.json")

    data_path = None
    if os.path.exists(scraped_data_path):
        data_path = scraped_data_path
    elif os.path.exists(sample_data_path):
        data_path = sample_data_path

    if data_path is None:
        st.error("No se encontraron datos. Ejecuta run_scraper.py primero.")
        return pd.DataFrame()

    with open(data_path, "r", encoding="utf-8") as data_file:
        raw_data = json.load(data_file)

    return pd.DataFrame(raw_data)


def render_executive_summary(competitive_position: dict) -> None:
    if competitive_position.get("status") != "computed":
        st.warning("Datos insuficientes para generar el resumen ejecutivo.")
        return

    column_one, column_two, column_three = st.columns(3)

    with column_one:
        st.metric(
            label="Precio Promedio Rappi",
            value=f"${competitive_position['rappi_avg_product_price']:.2f}",
            delta=f"{competitive_position['price_difference_pct']:+.1f}% vs competencia",
            delta_color="inverse",
        )

    with column_two:
        st.metric(
            label="Tiempo Entrega Rappi",
            value=f"{competitive_position['rappi_avg_delivery_minutes']:.0f} min",
            delta=f"{competitive_position['rappi_avg_delivery_minutes'] - competitive_position['competitor_avg_delivery_minutes']:+.0f} min vs competencia",
            delta_color="inverse",
        )

    with column_three:
        st.metric(
            label="Costo Total Rappi",
            value=f"${competitive_position['rappi_avg_total_price']:.2f}",
            delta=f"${competitive_position['rappi_avg_total_price'] - competitive_position['competitor_avg_total_price']:+.2f} vs competencia",
            delta_color="inverse",
        )

    st.divider()

    column_four, column_five, column_six = st.columns(3)

    rappi_fee = competitive_position.get("rappi_avg_delivery_fee", 0)
    comp_fee = competitive_position.get("competitor_avg_delivery_fee", 0)

    with column_four:
        fee_display = f"${rappi_fee:.2f}" if rappi_fee > 0 else "No disponible"
        st.metric(label="Tarifa Envio Rappi", value=fee_display)

    with column_five:
        fee_display = f"${comp_fee:.2f}" if comp_fee > 0 else "No disponible"
        st.metric(label="Tarifa Envio Competencia", value=fee_display)

    with column_six:
        position_label_map = {
            "cheaper": "Mas barato",
            "more_expensive": "Mas caro",
            "similar": "Similar",
        }
        position_text = position_label_map.get(
            competitive_position.get("price_position", ""), "N/A"
        )
        st.metric(label="Posicion de Precio", value=position_text)


def render_insight_cards(insights: list) -> None:
    for insight in insights:
        priority_color_map = {
            "high": "red",
            "medium": "orange",
            "low": "green",
        }
        border_color = priority_color_map.get(insight.priority, "gray")

        st.markdown(
            f"""
            <div style="
                border-left: 5px solid {border_color};
                padding: 15px;
                margin: 10px 0;
                background-color: #f8f9fa;
                border-radius: 5px;
            ">
                <h4>Insight #{insight.insight_number}: {insight.title}</h4>
                <p><strong>Hallazgo:</strong> {insight.finding}</p>
                <p><strong>Impacto:</strong> {insight.impact}</p>
                <p><strong>Recomendacion:</strong> {insight.recommendation}</p>
                <p style="font-size: 0.8em; color: gray;">
                    Categoria: {insight.category.upper()} | Prioridad: {insight.priority.upper()}
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )


def main() -> None:
    st.set_page_config(
        page_title="Competitive Intelligence - Rappi",
        page_icon="",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    st.title("Sistema de Competitive Intelligence para Rappi")
    st.caption("Analisis comparativo: Rappi vs Uber Eats vs DiDi Food en Mexico")

    dataframe = load_scraped_data()

    if dataframe.empty:
        st.stop()

    with st.sidebar:
        st.header("Filtros")

        available_platforms = sorted(dataframe["platform"].unique().tolist())
        selected_platforms = st.multiselect(
            "Plataformas",
            options=available_platforms,
            default=available_platforms,
        )

        available_cities = sorted(dataframe["city"].unique().tolist())
        selected_cities = st.multiselect(
            "Ciudades",
            options=available_cities,
            default=available_cities,
        )

        available_products = sorted(dataframe["product_name"].unique().tolist())
        selected_products = st.multiselect(
            "Productos",
            options=available_products,
            default=available_products,
        )

        available_zone_types = sorted(dataframe["zone_type"].unique().tolist())
        zone_type_labels = {"wealthy": "Alta", "middle": "Media", "popular": "Popular"}
        selected_zone_types = st.multiselect(
            "Tipo de Zona",
            options=available_zone_types,
            default=available_zone_types,
            format_func=lambda zone: zone_type_labels.get(zone, zone),
        )

    filtered_dataframe = dataframe[
        (dataframe["platform"].isin(selected_platforms))
        & (dataframe["city"].isin(selected_cities))
        & (dataframe["product_name"].isin(selected_products))
        & (dataframe["zone_type"].isin(selected_zone_types))
    ].copy()

    if filtered_dataframe.empty:
        st.warning("No hay datos con los filtros seleccionados.")
        st.stop()

    successful_data = filtered_dataframe[filtered_dataframe["scrape_success"] == True]

    sidebar_col1, sidebar_col2, sidebar_col3 = st.columns(3)
    with sidebar_col1:
        st.metric("Registros totales", len(filtered_dataframe))
    with sidebar_col2:
        st.metric("Registros exitosos", len(successful_data))
    with sidebar_col3:
        success_rate = (
            len(successful_data) / len(filtered_dataframe) * 100
            if len(filtered_dataframe) > 0
            else 0
        )
        st.metric("Tasa de exito", f"{success_rate:.0f}%")

    analyzer = ComparativeAnalyzer(filtered_dataframe)
    analysis_results = analyzer.generate_full_analysis()

    tab_summary, tab_prices, tab_fees, tab_time, tab_geo, tab_insights, tab_data = st.tabs([
        "Resumen Ejecutivo",
        "Precios",
        "Tarifas",
        "Tiempos de Entrega",
        "Analisis Geografico",
        "Insights",
        "Datos Crudos",
    ])

    with tab_summary:
        st.header("Resumen Ejecutivo")
        render_executive_summary(analysis_results["rappi_competitive_position"])

    with tab_prices:
        st.header("Comparacion de Precios")

        price_data = analysis_results["price_comparison_by_platform"]
        if not price_data.empty:
            price_chart = px.bar(
                price_data,
                x="product_name",
                y="mean_price",
                color="platform",
                barmode="group",
                title="Precio Promedio por Producto y Plataforma",
                labels={
                    "product_name": "Producto",
                    "mean_price": "Precio Promedio (MXN)",
                    "platform": "Plataforma",
                },
                color_discrete_map=PLATFORM_COLOR_MAP,
            )
            price_chart.update_layout(template="plotly_white")
            st.plotly_chart(price_chart, use_container_width=True)

            st.subheader("Tabla de Precios Detallada")
            st.dataframe(
                price_data.rename(columns={
                    "platform": "Plataforma",
                    "product_name": "Producto",
                    "mean_price": "Precio Promedio",
                    "median_price": "Precio Mediana",
                    "min_price": "Precio Min",
                    "max_price": "Precio Max",
                    "sample_count": "Muestras",
                }),
                use_container_width=True,
                hide_index=True,
            )

        total_cost_data = analysis_results["total_cost_comparison"]
        if not total_cost_data.empty:
            total_chart = px.bar(
                total_cost_data,
                x="product_name",
                y="mean_total_price",
                color="platform",
                barmode="group",
                title="Costo Total Promedio (Producto + Envio + Servicio)",
                labels={
                    "product_name": "Producto",
                    "mean_total_price": "Costo Total (MXN)",
                    "platform": "Plataforma",
                },
                color_discrete_map=PLATFORM_COLOR_MAP,
            )
            total_chart.update_layout(template="plotly_white")
            st.plotly_chart(total_chart, use_container_width=True)

    with tab_fees:
        st.header("Estructura de Tarifas")

        fee_data = analysis_results["delivery_fee_comparison"]
        has_fee_data = not fee_data.empty and fee_data["mean_delivery_fee"].notna().any()

        if has_fee_data:
            fee_chart_col1, fee_chart_col2 = st.columns(2)

            with fee_chart_col1:
                delivery_fee_chart = px.bar(
                    fee_data,
                    x="platform",
                    y="mean_delivery_fee",
                    color="platform",
                    title="Tarifa de Envio Promedio",
                    labels={
                        "platform": "Plataforma",
                        "mean_delivery_fee": "Tarifa Envio (MXN)",
                    },
                    color_discrete_map=PLATFORM_COLOR_MAP,
                )
                delivery_fee_chart.update_layout(template="plotly_white", showlegend=False)
                st.plotly_chart(delivery_fee_chart, use_container_width=True)

            with fee_chart_col2:
                service_fee_chart = px.bar(
                    fee_data,
                    x="platform",
                    y="mean_service_fee",
                    color="platform",
                    title="Tarifa de Servicio Promedio",
                    labels={
                        "platform": "Plataforma",
                        "mean_service_fee": "Tarifa Servicio (MXN)",
                    },
                    color_discrete_map=PLATFORM_COLOR_MAP,
                )
                service_fee_chart.update_layout(template="plotly_white", showlegend=False)
                st.plotly_chart(service_fee_chart, use_container_width=True)

            st.subheader("Tabla de Tarifas Detallada")
            st.dataframe(
                fee_data.rename(columns={
                    "platform": "Plataforma",
                    "mean_delivery_fee": "Envio Promedio",
                    "median_delivery_fee": "Envio Mediana",
                    "min_delivery_fee": "Envio Min",
                    "max_delivery_fee": "Envio Max",
                    "mean_service_fee": "Servicio Promedio",
                    "sample_count": "Muestras",
                }),
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.warning("Las tarifas de envio y servicio no pudieron ser extraidas automaticamente.")
            st.markdown(
                "Ambas plataformas (Rappi y Uber Eats) ocultan las tarifas exactas de envio "
                "y servicio detras de componentes dinamicos que requieren autenticacion o "
                "interaccion avanzada con la interfaz."
            )
            st.subheader("Observaciones manuales de los screenshots capturados")

            obs_data = pd.DataFrame([
                {
                    "Plataforma": "Rappi",
                    "Observacion": (
                        'Promocion activa: "Envio gratis en tu pedido" y '
                        '"15 dias de entrega gratis" para nuevos usuarios. '
                        'Tarifa base no visible sin autenticacion.'
                    ),
                },
                {
                    "Plataforma": "Uber Eats",
                    "Observacion": (
                        'Texto visible: "Costo de envio a MXN$..." (valor truncado). '
                        'Requiere cuenta para ver el monto completo. '
                        'Estimado $19-$49 MXN segun zona.'
                    ),
                },
            ])
            st.dataframe(obs_data, use_container_width=True, hide_index=True)

            st.markdown(
                "**Recomendacion:** Para obtener tarifas exactas se requiere ejecutar el "
                "scraper con cuentas autenticadas en cada plataforma. Esto permitiria "
                "capturar las tarifas reales por direccion y generar la comparacion completa."
            )

    with tab_time:
        st.header("Tiempos de Entrega")

        time_data = analysis_results["delivery_time_comparison"]
        if not time_data.empty:
            time_chart = px.bar(
                time_data,
                x="platform",
                y="mean_delivery_minutes",
                color="platform",
                title="Tiempo de Entrega Estimado Promedio",
                labels={
                    "platform": "Plataforma",
                    "mean_delivery_minutes": "Minutos",
                },
                color_discrete_map=PLATFORM_COLOR_MAP,
                text="mean_delivery_minutes",
            )
            time_chart.update_traces(texttemplate="%{text:.0f} min", textposition="outside")
            time_chart.update_layout(template="plotly_white", showlegend=False)
            st.plotly_chart(time_chart, use_container_width=True)

            st.subheader("Tabla de Tiempos Detallada")
            st.dataframe(
                time_data.rename(columns={
                    "platform": "Plataforma",
                    "mean_delivery_minutes": "Promedio (min)",
                    "median_delivery_minutes": "Mediana (min)",
                    "min_delivery_minutes": "Min (min)",
                    "max_delivery_minutes": "Max (min)",
                    "sample_count": "Muestras",
                }),
                use_container_width=True,
                hide_index=True,
            )

    with tab_geo:
        st.header("Analisis Geografico")

        geo_data = analysis_results["geographic_comparison"]
        if not geo_data.empty:
            geo_price_chart = px.bar(
                geo_data,
                x="city",
                y="mean_total_price",
                color="platform",
                barmode="group",
                title="Costo Total Promedio por Ciudad",
                labels={
                    "city": "Ciudad",
                    "mean_total_price": "Costo Total (MXN)",
                    "platform": "Plataforma",
                },
                color_discrete_map=PLATFORM_COLOR_MAP,
            )
            geo_price_chart.update_layout(template="plotly_white")
            st.plotly_chart(geo_price_chart, use_container_width=True)

            pivot_data = geo_data.pivot_table(
                values="mean_total_price",
                index="city",
                columns="platform",
                aggfunc="mean",
            ).round(2)

            heatmap = go.Figure(
                data=go.Heatmap(
                    z=pivot_data.values,
                    x=pivot_data.columns.tolist(),
                    y=pivot_data.index.tolist(),
                    colorscale="RdYlGn_r",
                    text=pivot_data.values.round(2),
                    texttemplate="%{text}",
                    textfont={"size": 12},
                )
            )
            heatmap.update_layout(
                title="Mapa de Calor: Costo Total por Ciudad y Plataforma",
                template="plotly_white",
            )
            st.plotly_chart(heatmap, use_container_width=True)

        zone_data = analysis_results["zone_type_comparison"]
        if not zone_data.empty:
            zone_labels = {"Wealthy": "Alta", "Middle": "Media", "Popular": "Popular"}
            zone_display = zone_data.copy()
            zone_display["zone_label"] = zone_display["zone_type"].map(zone_labels).fillna(zone_display["zone_type"])

            has_zone_fee_data = zone_display["mean_delivery_fee"].notna().any() and (zone_display["mean_delivery_fee"] > 0).any()

            if has_zone_fee_data:
                zone_chart = px.bar(
                    zone_display,
                    x="zone_label",
                    y="mean_delivery_fee",
                    color="platform",
                    barmode="group",
                    title="Tarifa de Envio por Tipo de Zona Socioeconomica",
                    labels={
                        "zone_label": "Tipo de Zona",
                        "mean_delivery_fee": "Tarifa Envio (MXN)",
                        "platform": "Plataforma",
                    },
                    color_discrete_map=PLATFORM_COLOR_MAP,
                )
                zone_chart.update_layout(template="plotly_white")
                st.plotly_chart(zone_chart, use_container_width=True)

            has_zone_price_data = "mean_product_price" in zone_display.columns and zone_display["mean_product_price"].notna().any()
            if has_zone_price_data:
                zone_price_chart = px.bar(
                    zone_display,
                    x="zone_label",
                    y="mean_product_price",
                    color="platform",
                    barmode="group",
                    title="Precio Promedio de Producto por Tipo de Zona Socioeconomica",
                    labels={
                        "zone_label": "Tipo de Zona",
                        "mean_product_price": "Precio Producto (MXN)",
                        "platform": "Plataforma",
                    },
                    color_discrete_map=PLATFORM_COLOR_MAP,
                )
                zone_price_chart.update_layout(template="plotly_white")
                st.plotly_chart(zone_price_chart, use_container_width=True)

    with tab_insights:
        st.header("Top 5 Insights Accionables")

        insight_generator = InsightGenerator(analysis_results, filtered_dataframe)
        insights = insight_generator.generate_all_insights()

        if insights:
            render_insight_cards(insights)
        else:
            st.info("No se generaron insights con los datos actuales.")

        promo_data = analysis_results["promotion_summary"]
        if not promo_data.empty:
            st.subheader("Tasa de Promociones por Plataforma")
            promo_chart = px.bar(
                promo_data,
                x="platform",
                y="promotion_rate_pct",
                color="platform",
                title="Porcentaje de Observaciones con Promocion Activa",
                labels={
                    "platform": "Plataforma",
                    "promotion_rate_pct": "Tasa de Promocion (%)",
                },
                color_discrete_map=PLATFORM_COLOR_MAP,
                text="promotion_rate_pct",
            )
            promo_chart.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
            promo_chart.update_layout(
                template="plotly_white",
                showlegend=False,
                yaxis=dict(range=[0, 100]),
            )
            st.plotly_chart(promo_chart, use_container_width=True)

    with tab_data:
        st.header("Datos Crudos")

        st.dataframe(filtered_dataframe, use_container_width=True, hide_index=True)

        csv_content = filtered_dataframe.to_csv(index=False)
        st.download_button(
            label="Descargar datos como CSV",
            data=csv_content,
            file_name="competitive_intelligence_data.csv",
            mime="text/csv",
        )

        json_content = filtered_dataframe.to_json(orient="records", indent=2, force_ascii=False)
        st.download_button(
            label="Descargar datos como JSON",
            data=json_content,
            file_name="competitive_intelligence_data.json",
            mime="application/json",
        )


if __name__ == "__main__":
    main()
