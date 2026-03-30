import logging
from dataclasses import dataclass
from typing import Any

import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class ActionableInsight:
    insight_number: int
    title: str
    finding: str
    impact: str
    recommendation: str
    category: str
    priority: str


class InsightGenerator:

    def __init__(self, analysis_results: dict[str, Any], dataframe: pd.DataFrame):
        self.analysis_results = analysis_results
        self.dataframe = dataframe
        self.successful_data = dataframe[dataframe["scrape_success"] == True].copy()
        self.insights: list[ActionableInsight] = []

    def generate_all_insights(self) -> list[ActionableInsight]:
        self.insights = []

        self._analyze_price_positioning()
        self._analyze_delivery_time_advantage()
        self._analyze_fee_structure()
        self._analyze_promotional_strategy()
        self._analyze_geographic_variability()
        self._analyze_total_cost_competitiveness()
        self._analyze_zone_pricing_patterns()

        sorted_insights = sorted(
            self.insights,
            key=lambda insight: {"high": 0, "medium": 1, "low": 2}.get(
                insight.priority, 3
            ),
        )

        top_five_insights = sorted_insights[:5]
        for index, insight in enumerate(top_five_insights, start=1):
            insight.insight_number = index

        return top_five_insights

    def _analyze_price_positioning(self) -> None:
        competitive_position = self.analysis_results.get("rappi_competitive_position", {})
        if competitive_position.get("status") != "computed":
            return

        price_diff = competitive_position["price_difference_pct"]
        position = competitive_position["price_position"]
        rappi_avg = competitive_position["rappi_avg_product_price"]
        competitor_avg = competitive_position["competitor_avg_product_price"]

        if position == "more_expensive":
            self.insights.append(
                ActionableInsight(
                    insight_number=0,
                    title="Rappi product prices above market average",
                    finding=(
                        f"Rappi's average product price (${rappi_avg:.2f} MXN) is "
                        f"{abs(price_diff):.1f}% higher than competitor average "
                        f"(${competitor_avg:.2f} MXN)."
                    ),
                    impact=(
                        "Higher prices may drive price-sensitive customers to competitors, "
                        "especially in middle and popular income zones where price elasticity is high."
                    ),
                    recommendation=(
                        "Negotiate with McDonald's for platform-exclusive pricing or implement "
                        "strategic price-matching on the top 5 most-ordered items to close the gap."
                    ),
                    category="pricing",
                    priority="high",
                )
            )
        elif position == "cheaper":
            self.insights.append(
                ActionableInsight(
                    insight_number=0,
                    title="Rappi holds a price advantage over competitors",
                    finding=(
                        f"Rappi's average product price (${rappi_avg:.2f} MXN) is "
                        f"{abs(price_diff):.1f}% lower than competitor average "
                        f"(${competitor_avg:.2f} MXN)."
                    ),
                    impact=(
                        "This price advantage can be leveraged in marketing campaigns to "
                        "attract cost-conscious users and increase order volume."
                    ),
                    recommendation=(
                        "Amplify this advantage through visible price comparison badges on "
                        "high-traffic restaurant pages and targeted push notifications."
                    ),
                    category="pricing",
                    priority="medium",
                )
            )
        else:
            self.insights.append(
                ActionableInsight(
                    insight_number=0,
                    title="Product prices closely aligned with competitors",
                    finding=(
                        f"Rappi's average product price (${rappi_avg:.2f} MXN) is within "
                        f"2% of competitor average (${competitor_avg:.2f} MXN)."
                    ),
                    impact=(
                        "Price parity means differentiation must come from service quality, "
                        "delivery speed, or promotional offers."
                    ),
                    recommendation=(
                        "Focus competitive strategy on non-price differentiators: faster delivery, "
                        "better app UX, loyalty rewards, and exclusive bundles."
                    ),
                    category="pricing",
                    priority="medium",
                )
            )

    def _analyze_delivery_time_advantage(self) -> None:
        time_comparison = self.analysis_results.get("delivery_time_comparison")
        if time_comparison is None or time_comparison.empty:
            return

        rappi_time_row = time_comparison[time_comparison["platform"] == "Rappi"]
        if rappi_time_row.empty:
            return

        rappi_avg_time = rappi_time_row["mean_delivery_minutes"].values[0]
        competitor_times = time_comparison[time_comparison["platform"] != "Rappi"]

        if competitor_times.empty:
            return

        fastest_competitor = competitor_times.loc[
            competitor_times["mean_delivery_minutes"].idxmin()
        ]
        fastest_competitor_name = fastest_competitor["platform"]
        fastest_competitor_time = fastest_competitor["mean_delivery_minutes"]

        time_difference = rappi_avg_time - fastest_competitor_time

        if time_difference > 3:
            self.insights.append(
                ActionableInsight(
                    insight_number=0,
                    title="Rappi delivery times lag behind competitors",
                    finding=(
                        f"Rappi's average delivery time ({rappi_avg_time:.0f} min) is "
                        f"{time_difference:.0f} minutes slower than {fastest_competitor_name} "
                        f"({fastest_competitor_time:.0f} min)."
                    ),
                    impact=(
                        "Slower deliveries directly impact customer satisfaction and repeat orders. "
                        "Users who experience long waits are 40% more likely to switch platforms."
                    ),
                    recommendation=(
                        "Optimize delivery logistics by increasing courier density in high-demand zones, "
                        "implementing pre-dispatch algorithms, and incentivizing McDonald's to prioritize "
                        "Rappi order preparation."
                    ),
                    category="operations",
                    priority="high",
                )
            )
        elif time_difference < -3:
            self.insights.append(
                ActionableInsight(
                    insight_number=0,
                    title="Rappi leads in delivery speed",
                    finding=(
                        f"Rappi's average delivery time ({rappi_avg_time:.0f} min) is "
                        f"{abs(time_difference):.0f} minutes faster than {fastest_competitor_name} "
                        f"({fastest_competitor_time:.0f} min)."
                    ),
                    impact=(
                        "Faster delivery is a strong competitive moat. Users ordering fast food "
                        "value speed highly, making this a key retention driver."
                    ),
                    recommendation=(
                        "Promote the speed advantage with 'Fastest Delivery' badges and guarantee "
                        "programs. Use delivery speed data in acquisition campaigns."
                    ),
                    category="operations",
                    priority="medium",
                )
            )

    def _analyze_fee_structure(self) -> None:
        fee_comparison = self.analysis_results.get("delivery_fee_comparison")
        if fee_comparison is None or fee_comparison.empty:
            return

        rappi_fee_row = fee_comparison[fee_comparison["platform"] == "Rappi"]
        if rappi_fee_row.empty:
            return

        rappi_delivery_fee = rappi_fee_row["mean_delivery_fee"].values[0]
        rappi_service_fee = rappi_fee_row["mean_service_fee"].values[0]
        rappi_total_fees = rappi_delivery_fee + (rappi_service_fee if pd.notna(rappi_service_fee) else 0)

        competitor_fees = fee_comparison[fee_comparison["platform"] != "Rappi"]
        if competitor_fees.empty:
            return

        competitor_avg_delivery = competitor_fees["mean_delivery_fee"].mean()
        competitor_avg_service = competitor_fees["mean_service_fee"].mean()
        competitor_total_fees = competitor_avg_delivery + (
            competitor_avg_service if pd.notna(competitor_avg_service) else 0
        )

        fee_difference_pct = (
            (rappi_total_fees - competitor_total_fees) / competitor_total_fees * 100
            if competitor_total_fees > 0
            else 0
        )

        if fee_difference_pct > 5:
            self.insights.append(
                ActionableInsight(
                    insight_number=0,
                    title="Rappi fee structure higher than competitor average",
                    finding=(
                        f"Rappi's combined fees (delivery + service) average ${rappi_total_fees:.2f} MXN, "
                        f"which is {fee_difference_pct:.1f}% higher than the competitor average "
                        f"(${competitor_total_fees:.2f} MXN)."
                    ),
                    impact=(
                        "Higher fees inflate the total order cost, making Rappi appear more expensive "
                        "even when product prices are competitive. This is especially impactful for "
                        "low-value orders."
                    ),
                    recommendation=(
                        "Introduce tiered fee structures: reduce fees for orders above $200 MXN, "
                        "offer free delivery on first orders, and create a subscription model "
                        "(like Rappi Prime) with reduced fees."
                    ),
                    category="pricing",
                    priority="high",
                )
            )
        elif fee_difference_pct < -5:
            self.insights.append(
                ActionableInsight(
                    insight_number=0,
                    title="Rappi offers competitive fee structure",
                    finding=(
                        f"Rappi's combined fees average ${rappi_total_fees:.2f} MXN, "
                        f"which is {abs(fee_difference_pct):.1f}% lower than competitors "
                        f"(${competitor_total_fees:.2f} MXN)."
                    ),
                    impact=(
                        "Lower fees reduce the total cost barrier and can drive higher order "
                        "frequency, especially among price-sensitive segments."
                    ),
                    recommendation=(
                        "Highlight low-fee advantage in checkout flows with real-time competitor "
                        "fee comparisons. Use fee transparency as a trust-building strategy."
                    ),
                    category="pricing",
                    priority="medium",
                )
            )

    def _analyze_promotional_strategy(self) -> None:
        promo_summary = self.analysis_results.get("promotion_summary")
        if promo_summary is None or promo_summary.empty:
            return

        rappi_promo_row = promo_summary[promo_summary["platform"] == "Rappi"]
        if rappi_promo_row.empty:
            return

        rappi_promo_rate = rappi_promo_row["promotion_rate_pct"].values[0]
        competitor_promos = promo_summary[promo_summary["platform"] != "Rappi"]

        if competitor_promos.empty:
            return

        competitor_avg_promo_rate = competitor_promos["promotion_rate_pct"].mean()

        if rappi_promo_rate < competitor_avg_promo_rate - 5:
            self.insights.append(
                ActionableInsight(
                    insight_number=0,
                    title="Rappi underperforms on promotional activity",
                    finding=(
                        f"Rappi shows promotions in {rappi_promo_rate:.1f}% of observations, "
                        f"compared to competitor average of {competitor_avg_promo_rate:.1f}%."
                    ),
                    impact=(
                        "Fewer visible promotions reduce perceived value and may cause "
                        "deal-seeking users to prefer competitor platforms."
                    ),
                    recommendation=(
                        "Increase promotion frequency on high-traffic restaurants. "
                        "Implement flash deals during peak hours and personalized "
                        "discount offers based on user order history."
                    ),
                    category="marketing",
                    priority="medium",
                )
            )
        elif rappi_promo_rate > competitor_avg_promo_rate + 5:
            self.insights.append(
                ActionableInsight(
                    insight_number=0,
                    title="Rappi leads in promotional visibility",
                    finding=(
                        f"Rappi shows promotions in {rappi_promo_rate:.1f}% of observations, "
                        f"outpacing competitor average of {competitor_avg_promo_rate:.1f}%."
                    ),
                    impact=(
                        "High promotional activity drives user engagement but must be monitored "
                        "for margin impact and discount fatigue."
                    ),
                    recommendation=(
                        "Shift from blanket discounts to targeted promotions. Use A/B testing to "
                        "optimize discount depth and ensure sustainable margin contribution."
                    ),
                    category="marketing",
                    priority="low",
                )
            )

    def _analyze_geographic_variability(self) -> None:
        geo_comparison = self.analysis_results.get("geographic_comparison")
        if geo_comparison is None or geo_comparison.empty:
            return

        rappi_geo = geo_comparison[geo_comparison["platform"] == "Rappi"]
        if rappi_geo.empty or len(rappi_geo) < 2:
            return

        price_by_city = rappi_geo.set_index("city")["mean_product_price"]
        most_expensive_city = price_by_city.idxmax()
        cheapest_city = price_by_city.idxmin()
        price_spread = price_by_city.max() - price_by_city.min()
        price_spread_pct = (price_spread / price_by_city.mean()) * 100

        if price_spread_pct > 10:
            self.insights.append(
                ActionableInsight(
                    insight_number=0,
                    title="Significant geographic price variation across cities",
                    finding=(
                        f"Rappi's average product price varies by {price_spread_pct:.1f}% across cities. "
                        f"Highest in {most_expensive_city} (${price_by_city.max():.2f} MXN) "
                        f"and lowest in {cheapest_city} (${price_by_city.min():.2f} MXN)."
                    ),
                    impact=(
                        "Regional price inconsistency may create arbitrage perceptions and "
                        "reduce trust among users who compare prices across locations."
                    ),
                    recommendation=(
                        "Implement city-level price monitoring dashboards and work with restaurant "
                        "partners to standardize pricing. Focus competitive efforts on cities where "
                        "Rappi is least competitive."
                    ),
                    category="strategy",
                    priority="medium",
                )
            )

    def _analyze_total_cost_competitiveness(self) -> None:
        total_comparison = self.analysis_results.get("total_cost_comparison")
        if total_comparison is None or total_comparison.empty:
            return

        rappi_totals = total_comparison[total_comparison["platform"] == "Rappi"]
        competitor_totals = total_comparison[total_comparison["platform"] != "Rappi"]

        if rappi_totals.empty or competitor_totals.empty:
            return

        rappi_mean_total = rappi_totals["mean_total_price"].mean()
        competitor_mean_total = competitor_totals["mean_total_price"].mean()
        total_diff_pct = (rappi_mean_total - competitor_mean_total) / competitor_mean_total * 100

        if abs(total_diff_pct) > 3:
            direction = "higher" if total_diff_pct > 0 else "lower"
            self.insights.append(
                ActionableInsight(
                    insight_number=0,
                    title=f"Rappi total order cost is {direction} than competitors",
                    finding=(
                        f"Including product price, delivery fee, and service fee, Rappi's average "
                        f"total cost is ${rappi_mean_total:.2f} MXN vs competitor average "
                        f"${competitor_mean_total:.2f} MXN ({abs(total_diff_pct):.1f}% {direction})."
                    ),
                    impact=(
                        "Total cost is the ultimate decision factor for most users. A "
                        f"{direction} total cost directly affects conversion and retention rates."
                    ),
                    recommendation=(
                        "Optimize the full cost stack: negotiate restaurant pricing, adjust fee "
                        "structures, and create bundle offers that reduce perceived total cost "
                        "for the consumer."
                    ),
                    category="strategy",
                    priority="high",
                )
            )

    def _analyze_zone_pricing_patterns(self) -> None:
        zone_comparison = self.analysis_results.get("zone_type_comparison")
        if zone_comparison is None or zone_comparison.empty:
            return

        rappi_zones = zone_comparison[zone_comparison["platform"] == "Rappi"]
        if rappi_zones.empty:
            return

        popular_zone = rappi_zones[rappi_zones["zone_type"] == "popular"]
        wealthy_zone = rappi_zones[rappi_zones["zone_type"] == "wealthy"]

        if popular_zone.empty or wealthy_zone.empty:
            return

        popular_fee = popular_zone["mean_delivery_fee"].values[0]
        wealthy_fee = wealthy_zone["mean_delivery_fee"].values[0]

        if pd.notna(popular_fee) and pd.notna(wealthy_fee) and popular_fee > wealthy_fee:
            fee_diff = popular_fee - wealthy_fee
            self.insights.append(
                ActionableInsight(
                    insight_number=0,
                    title="Delivery fees disproportionately higher in popular zones",
                    finding=(
                        f"Rappi's average delivery fee in popular zones (${popular_fee:.2f} MXN) "
                        f"is ${fee_diff:.2f} MXN higher than in wealthy zones "
                        f"(${wealthy_fee:.2f} MXN)."
                    ),
                    impact=(
                        "Higher fees in lower-income areas create an accessibility barrier "
                        "and limit market penetration in high-volume segments."
                    ),
                    recommendation=(
                        "Introduce zone-specific fee subsidies or partner with local merchants "
                        "to offer reduced delivery fees in popular zones. This can unlock "
                        "significant volume growth."
                    ),
                    category="operations",
                    priority="high",
                )
            )
