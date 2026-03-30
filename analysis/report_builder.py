import json
import logging
import os
from datetime import datetime
from typing import Any

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from analysis.comparative_analyzer import ComparativeAnalyzer
from analysis.insight_generator import ActionableInsight, InsightGenerator
from config import OUTPUT_DIR

logger = logging.getLogger(__name__)

PLATFORM_COLOR_MAP = {
    "Rappi": "#FF441F",
    "Uber Eats": "#06C167",
    "DiDi Food": "#FF8C00",
}


class ReportBuilder:

    def __init__(self, dataframe: pd.DataFrame):
        self.dataframe = dataframe
        self.analyzer = ComparativeAnalyzer(dataframe)
        self.analysis_results = self.analyzer.generate_full_analysis()
        self.insight_generator = InsightGenerator(self.analysis_results, dataframe)
        self.insights = self.insight_generator.generate_all_insights()
        self.figures: dict[str, go.Figure] = {}

    def build_all_charts(self) -> dict[str, go.Figure]:
        self.figures["price_comparison"] = self._build_price_comparison_chart()
        self.figures["delivery_fee_comparison"] = self._build_delivery_fee_chart()
        self.figures["delivery_time_comparison"] = self._build_delivery_time_chart()
        self.figures["total_cost_comparison"] = self._build_total_cost_chart()
        self.figures["geographic_heatmap"] = self._build_geographic_heatmap()
        self.figures["zone_comparison"] = self._build_zone_comparison_chart()
        self.figures["promotion_rates"] = self._build_promotion_rate_chart()
        return self.figures

    def _build_price_comparison_chart(self) -> go.Figure:
        price_data = self.analysis_results["price_comparison_by_platform"]
        if price_data.empty:
            return self._empty_figure("No hay datos de precios disponibles")

        figure = px.bar(
            price_data,
            x="product_name",
            y="mean_price",
            color="platform",
            barmode="group",
            title="Comparacion de Precios Promedio por Producto y Plataforma",
            labels={
                "product_name": "Producto",
                "mean_price": "Precio Promedio (MXN)",
                "platform": "Plataforma",
            },
            color_discrete_map=PLATFORM_COLOR_MAP,
        )
        figure.update_layout(
            template="plotly_white",
            font=dict(size=12),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        )
        return figure

    def _build_delivery_fee_chart(self) -> go.Figure:
        fee_data = self.analysis_results["delivery_fee_comparison"]
        if fee_data.empty:
            return self._empty_figure("No hay datos de tarifas de envio disponibles")

        figure = make_subplots(
            rows=1,
            cols=2,
            subplot_titles=("Tarifa de Envio Promedio", "Tarifa de Servicio Promedio"),
        )

        for _, row in fee_data.iterrows():
            platform_name = row["platform"]
            platform_color = PLATFORM_COLOR_MAP.get(platform_name, "#888888")

            figure.add_trace(
                go.Bar(
                    x=[platform_name],
                    y=[row["mean_delivery_fee"]],
                    name=f"{platform_name} - Envio",
                    marker_color=platform_color,
                    showlegend=True,
                ),
                row=1,
                col=1,
            )

            service_fee_value = row["mean_service_fee"] if pd.notna(row["mean_service_fee"]) else 0
            figure.add_trace(
                go.Bar(
                    x=[platform_name],
                    y=[service_fee_value],
                    name=f"{platform_name} - Servicio",
                    marker_color=platform_color,
                    opacity=0.7,
                    showlegend=False,
                ),
                row=1,
                col=2,
            )

        figure.update_layout(
            title="Comparacion de Estructura de Tarifas por Plataforma",
            template="plotly_white",
            font=dict(size=12),
        )
        figure.update_yaxes(title_text="MXN", row=1, col=1)
        figure.update_yaxes(title_text="MXN", row=1, col=2)
        return figure

    def _build_delivery_time_chart(self) -> go.Figure:
        time_data = self.analysis_results["delivery_time_comparison"]
        if time_data.empty:
            return self._empty_figure("No hay datos de tiempos de entrega disponibles")

        figure = go.Figure()

        for _, row in time_data.iterrows():
            platform_name = row["platform"]
            platform_color = PLATFORM_COLOR_MAP.get(platform_name, "#888888")

            figure.add_trace(
                go.Bar(
                    x=[platform_name],
                    y=[row["mean_delivery_minutes"]],
                    name=platform_name,
                    marker_color=platform_color,
                    error_y=dict(
                        type="data",
                        symmetric=False,
                        array=[row["max_delivery_minutes"] - row["mean_delivery_minutes"]],
                        arrayminus=[row["mean_delivery_minutes"] - row["min_delivery_minutes"]],
                    ),
                    text=[f"{row['mean_delivery_minutes']:.0f} min"],
                    textposition="outside",
                )
            )

        figure.update_layout(
            title="Comparacion de Tiempo de Entrega Estimado",
            yaxis_title="Minutos",
            template="plotly_white",
            font=dict(size=12),
            showlegend=True,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        )
        return figure

    def _build_total_cost_chart(self) -> go.Figure:
        total_data = self.analysis_results["total_cost_comparison"]
        if total_data.empty:
            return self._empty_figure("No hay datos de costo total disponibles")

        figure = px.bar(
            total_data,
            x="product_name",
            y="mean_total_price",
            color="platform",
            barmode="group",
            title="Costo Total Promedio (Producto + Envio + Servicio)",
            labels={
                "product_name": "Producto",
                "mean_total_price": "Costo Total Promedio (MXN)",
                "platform": "Plataforma",
            },
            color_discrete_map=PLATFORM_COLOR_MAP,
        )
        figure.update_layout(
            template="plotly_white",
            font=dict(size=12),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        )
        return figure

    def _build_geographic_heatmap(self) -> go.Figure:
        geo_data = self.analysis_results["geographic_comparison"]
        if geo_data.empty:
            return self._empty_figure("No hay datos geograficos disponibles")

        pivot_data = geo_data.pivot_table(
            values="mean_total_price",
            index="city",
            columns="platform",
            aggfunc="mean",
        ).round(2)

        figure = go.Figure(
            data=go.Heatmap(
                z=pivot_data.values,
                x=pivot_data.columns.tolist(),
                y=pivot_data.index.tolist(),
                colorscale="RdYlGn_r",
                text=pivot_data.values.round(2),
                texttemplate="%{text}",
                textfont={"size": 12},
                hovertemplate="Ciudad: %{y}<br>Plataforma: %{x}<br>Precio Total: $%{z:.2f} MXN<extra></extra>",
            )
        )

        figure.update_layout(
            title="Mapa de Calor: Costo Total Promedio por Ciudad y Plataforma",
            xaxis_title="Plataforma",
            yaxis_title="Ciudad",
            template="plotly_white",
            font=dict(size=12),
        )
        return figure

    def _build_zone_comparison_chart(self) -> go.Figure:
        zone_data = self.analysis_results["zone_type_comparison"]
        if zone_data.empty:
            return self._empty_figure("No hay datos por tipo de zona disponibles")

        zone_labels = {"wealthy": "Alta", "middle": "Media", "popular": "Popular"}
        zone_data_display = zone_data.copy()
        zone_data_display["zone_label"] = zone_data_display["zone_type"].map(zone_labels)

        figure = px.bar(
            zone_data_display,
            x="zone_label",
            y="mean_delivery_fee",
            color="platform",
            barmode="group",
            title="Tarifa de Envio Promedio por Tipo de Zona Socioeconomica",
            labels={
                "zone_label": "Tipo de Zona",
                "mean_delivery_fee": "Tarifa de Envio Promedio (MXN)",
                "platform": "Plataforma",
            },
            color_discrete_map=PLATFORM_COLOR_MAP,
        )
        figure.update_layout(
            template="plotly_white",
            font=dict(size=12),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        )
        return figure

    def _build_promotion_rate_chart(self) -> go.Figure:
        promo_data = self.analysis_results["promotion_summary"]
        if promo_data.empty:
            return self._empty_figure("No hay datos de promociones disponibles")

        colors = [
            PLATFORM_COLOR_MAP.get(platform, "#888888")
            for platform in promo_data["platform"]
        ]

        figure = go.Figure(
            data=go.Bar(
                x=promo_data["platform"],
                y=promo_data["promotion_rate_pct"],
                marker_color=colors,
                text=promo_data["promotion_rate_pct"].apply(lambda x: f"{x:.1f}%"),
                textposition="outside",
            )
        )

        figure.update_layout(
            title="Tasa de Promociones Activas por Plataforma",
            xaxis_title="Plataforma",
            yaxis_title="Porcentaje de Observaciones con Promocion (%)",
            template="plotly_white",
            font=dict(size=12),
            yaxis=dict(range=[0, 100]),
        )
        return figure

    @staticmethod
    def _empty_figure(message: str) -> go.Figure:
        figure = go.Figure()
        figure.add_annotation(
            text=message,
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            showarrow=False,
            font=dict(size=16),
        )
        figure.update_layout(template="plotly_white")
        return figure

    def generate_html_report(self, output_filename: str = "competitive_report.html") -> str:
        self.build_all_charts()

        competitive_position = self.analysis_results["rappi_competitive_position"]

        report_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        total_records = len(self.dataframe)
        successful_records = len(self.dataframe[self.dataframe["scrape_success"] == True])

        chart_html_sections = ""
        for chart_name, figure in self.figures.items():
            chart_html_sections += f'<div class="chart-container">{figure.to_html(full_html=False, include_plotlyjs=False)}</div>\n'

        insights_html_sections = ""
        for insight in self.insights:
            priority_class = f"priority-{insight.priority}"
            insights_html_sections += f"""
            <div class="insight-card {priority_class}">
                <h3>Insight #{insight.insight_number}: {insight.title}</h3>
                <div class="insight-detail">
                    <strong>Hallazgo:</strong> {insight.finding}
                </div>
                <div class="insight-detail">
                    <strong>Impacto:</strong> {insight.impact}
                </div>
                <div class="insight-detail">
                    <strong>Recomendacion:</strong> {insight.recommendation}
                </div>
                <div class="insight-meta">
                    Categoria: {insight.category.upper()} | Prioridad: {insight.priority.upper()}
                </div>
            </div>
            """

        position_status = competitive_position.get("status", "insufficient_data")
        position_html = ""
        if position_status == "computed":
            position_html = f"""
            <div class="summary-grid">
                <div class="summary-card">
                    <h4>Precio Promedio Rappi</h4>
                    <div class="summary-value">${competitive_position['rappi_avg_product_price']:.2f}</div>
                </div>
                <div class="summary-card">
                    <h4>Precio Promedio Competencia</h4>
                    <div class="summary-value">${competitive_position['competitor_avg_product_price']:.2f}</div>
                </div>
                <div class="summary-card">
                    <h4>Diferencia de Precio</h4>
                    <div class="summary-value">{competitive_position['price_difference_pct']:+.1f}%</div>
                </div>
                <div class="summary-card">
                    <h4>Tiempo Entrega Rappi</h4>
                    <div class="summary-value">{competitive_position['rappi_avg_delivery_minutes']:.0f} min</div>
                </div>
                <div class="summary-card">
                    <h4>Tiempo Entrega Competencia</h4>
                    <div class="summary-value">{competitive_position['competitor_avg_delivery_minutes']:.0f} min</div>
                </div>
                <div class="summary-card">
                    <h4>Costo Total Rappi</h4>
                    <div class="summary-value">${competitive_position['rappi_avg_total_price']:.2f}</div>
                </div>
            </div>
            """

        html_content = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Reporte de Inteligencia Competitiva - Rappi</title>
    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
            color: #333;
        }}
        .report-header {{
            background: linear-gradient(135deg, #FF441F, #FF6B4A);
            color: white;
            padding: 30px;
            border-radius: 10px;
            margin-bottom: 30px;
        }}
        .report-header h1 {{
            margin: 0 0 10px 0;
            font-size: 28px;
        }}
        .report-header p {{
            margin: 5px 0;
            opacity: 0.9;
        }}
        .section {{
            background: white;
            border-radius: 10px;
            padding: 25px;
            margin-bottom: 25px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.08);
        }}
        .section h2 {{
            color: #FF441F;
            border-bottom: 2px solid #FF441F;
            padding-bottom: 10px;
        }}
        .chart-container {{
            margin: 20px 0;
        }}
        .summary-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin: 20px 0;
        }}
        .summary-card {{
            background: #f8f9fa;
            border-radius: 8px;
            padding: 20px;
            text-align: center;
            border-left: 4px solid #FF441F;
        }}
        .summary-card h4 {{
            margin: 0 0 10px 0;
            color: #666;
            font-size: 14px;
        }}
        .summary-value {{
            font-size: 24px;
            font-weight: bold;
            color: #333;
        }}
        .insight-card {{
            background: #f8f9fa;
            border-radius: 8px;
            padding: 20px;
            margin: 15px 0;
            border-left: 5px solid #ccc;
        }}
        .insight-card.priority-high {{
            border-left-color: #dc3545;
        }}
        .insight-card.priority-medium {{
            border-left-color: #ffc107;
        }}
        .insight-card.priority-low {{
            border-left-color: #28a745;
        }}
        .insight-card h3 {{
            margin: 0 0 15px 0;
            color: #333;
        }}
        .insight-detail {{
            margin: 10px 0;
            line-height: 1.6;
        }}
        .insight-meta {{
            margin-top: 15px;
            font-size: 12px;
            color: #888;
            text-transform: uppercase;
        }}
        .footer {{
            text-align: center;
            padding: 20px;
            color: #888;
            font-size: 12px;
        }}
    </style>
</head>
<body>
    <div class="report-header">
        <h1>Reporte de Inteligencia Competitiva</h1>
        <p>Analisis comparativo: Rappi vs Uber Eats vs DiDi Food</p>
        <p>Generado: {report_timestamp} | Registros totales: {total_records} | Registros exitosos: {successful_records}</p>
    </div>

    <div class="section">
        <h2>Resumen Ejecutivo</h2>
        {position_html}
    </div>

    <div class="section">
        <h2>Top 5 Insights Accionables</h2>
        {insights_html_sections}
    </div>

    <div class="section">
        <h2>Analisis Visual</h2>
        {chart_html_sections}
    </div>

    <div class="footer">
        <p>Sistema de Competitive Intelligence para Rappi | Reporte generado automaticamente</p>
    </div>
</body>
</html>"""

        output_path = os.path.join(OUTPUT_DIR, output_filename)
        with open(output_path, "w", encoding="utf-8") as report_file:
            report_file.write(html_content)

        logger.info("HTML report saved to %s", output_path)
        return output_path

    def generate_markdown_report(self, output_filename: str = "competitive_report.md") -> str:
        competitive_position = self.analysis_results["rappi_competitive_position"]
        report_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        lines = [
            "# Reporte de Inteligencia Competitiva - Rappi",
            "",
            f"**Fecha de generacion:** {report_timestamp}",
            f"**Registros totales:** {len(self.dataframe)}",
            f"**Registros exitosos:** {len(self.dataframe[self.dataframe['scrape_success'] == True])}",
            "",
            "---",
            "",
            "## Resumen Ejecutivo",
            "",
        ]

        if competitive_position.get("status") == "computed":
            lines.extend([
                f"| Metrica | Rappi | Competencia | Diferencia |",
                f"|---------|-------|-------------|------------|",
                f"| Precio Promedio Producto | ${competitive_position['rappi_avg_product_price']:.2f} | ${competitive_position['competitor_avg_product_price']:.2f} | {competitive_position['price_difference_pct']:+.1f}% |",
                f"| Tarifa de Envio Promedio | ${competitive_position['rappi_avg_delivery_fee']:.2f} | ${competitive_position['competitor_avg_delivery_fee']:.2f} | - |",
                f"| Tiempo de Entrega (min) | {competitive_position['rappi_avg_delivery_minutes']:.0f} | {competitive_position['competitor_avg_delivery_minutes']:.0f} | - |",
                f"| Costo Total Promedio | ${competitive_position['rappi_avg_total_price']:.2f} | ${competitive_position['competitor_avg_total_price']:.2f} | - |",
                "",
            ])

        lines.extend([
            "---",
            "",
            "## Top 5 Insights Accionables",
            "",
        ])

        for insight in self.insights:
            lines.extend([
                f"### Insight #{insight.insight_number}: {insight.title}",
                "",
                f"**Hallazgo:** {insight.finding}",
                "",
                f"**Impacto:** {insight.impact}",
                "",
                f"**Recomendacion:** {insight.recommendation}",
                "",
                f"*Categoria: {insight.category.upper()} | Prioridad: {insight.priority.upper()}*",
                "",
                "---",
                "",
            ])

        output_path = os.path.join(OUTPUT_DIR, output_filename)
        with open(output_path, "w", encoding="utf-8") as report_file:
            report_file.write("\n".join(lines))

        logger.info("Markdown report saved to %s", output_path)
        return output_path

    def save_charts_as_html(self, output_subdir: str = "charts") -> list[str]:
        charts_dir = os.path.join(OUTPUT_DIR, output_subdir)
        os.makedirs(charts_dir, exist_ok=True)

        if not self.figures:
            self.build_all_charts()

        saved_paths = []
        for chart_name, figure in self.figures.items():
            chart_path = os.path.join(charts_dir, f"{chart_name}.html")
            figure.write_html(chart_path, include_plotlyjs="cdn")
            saved_paths.append(chart_path)

        logger.info("Saved %d charts to %s", len(saved_paths), charts_dir)
        return saved_paths
