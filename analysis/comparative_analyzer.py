import logging
from typing import Any, Optional

import pandas as pd

logger = logging.getLogger(__name__)


class ComparativeAnalyzer:

    def __init__(self, dataframe: pd.DataFrame):
        self.dataframe = dataframe.copy()
        self.successful_records = self.dataframe[
            self.dataframe["scrape_success"] == True
        ].copy()
        self.logger = logging.getLogger(__name__)

    def compute_price_comparison_by_platform(self) -> pd.DataFrame:
        if self.successful_records.empty:
            return pd.DataFrame()

        price_summary = (
            self.successful_records.groupby(["platform", "product_name"])
            .agg(
                mean_price=("product_price", "mean"),
                median_price=("product_price", "median"),
                min_price=("product_price", "min"),
                max_price=("product_price", "max"),
                sample_count=("product_price", "count"),
            )
            .reset_index()
            .round(2)
        )
        return price_summary

    def compute_delivery_fee_comparison(self) -> pd.DataFrame:
        if self.successful_records.empty:
            return pd.DataFrame()

        fee_data = self.successful_records.dropna(subset=["delivery_fee"])
        if fee_data.empty:
            return pd.DataFrame()

        fee_summary = (
            fee_data.groupby("platform")
            .agg(
                mean_delivery_fee=("delivery_fee", "mean"),
                median_delivery_fee=("delivery_fee", "median"),
                min_delivery_fee=("delivery_fee", "min"),
                max_delivery_fee=("delivery_fee", "max"),
                mean_service_fee=("service_fee", "mean"),
                sample_count=("delivery_fee", "count"),
            )
            .reset_index()
            .round(2)
        )
        return fee_summary

    def compute_delivery_time_comparison(self) -> pd.DataFrame:
        if self.successful_records.empty:
            return pd.DataFrame()

        time_data = self.successful_records.dropna(subset=["estimated_delivery_minutes"])
        if time_data.empty:
            return pd.DataFrame()

        time_summary = (
            time_data.groupby("platform")
            .agg(
                mean_delivery_minutes=("estimated_delivery_minutes", "mean"),
                median_delivery_minutes=("estimated_delivery_minutes", "median"),
                min_delivery_minutes=("estimated_delivery_minutes", "min"),
                max_delivery_minutes=("estimated_delivery_minutes", "max"),
                sample_count=("estimated_delivery_minutes", "count"),
            )
            .reset_index()
            .round(1)
        )
        return time_summary

    def compute_total_cost_comparison(self) -> pd.DataFrame:
        if self.successful_records.empty:
            return pd.DataFrame()

        total_data = self.successful_records.dropna(subset=["total_final_price"])
        if total_data.empty:
            return pd.DataFrame()

        total_summary = (
            total_data.groupby(["platform", "product_name"])
            .agg(
                mean_total_price=("total_final_price", "mean"),
                median_total_price=("total_final_price", "median"),
                sample_count=("total_final_price", "count"),
            )
            .reset_index()
            .round(2)
        )
        return total_summary

    def compute_geographic_comparison(self) -> pd.DataFrame:
        if self.successful_records.empty:
            return pd.DataFrame()

        geo_summary = (
            self.successful_records.groupby(["platform", "city"])
            .agg(
                mean_product_price=("product_price", "mean"),
                mean_delivery_fee=("delivery_fee", "mean"),
                mean_total_price=("total_final_price", "mean"),
                mean_delivery_minutes=("estimated_delivery_minutes", "mean"),
                sample_count=("product_price", "count"),
            )
            .reset_index()
            .round(2)
        )
        return geo_summary

    def compute_zone_type_comparison(self) -> pd.DataFrame:
        if self.successful_records.empty:
            return pd.DataFrame()

        zone_summary = (
            self.successful_records.groupby(["platform", "zone_type"])
            .agg(
                mean_product_price=("product_price", "mean"),
                mean_delivery_fee=("delivery_fee", "mean"),
                mean_total_price=("total_final_price", "mean"),
                mean_delivery_minutes=("estimated_delivery_minutes", "mean"),
                sample_count=("product_price", "count"),
            )
            .reset_index()
            .round(2)
        )
        return zone_summary

    def compute_promotion_summary(self) -> pd.DataFrame:
        if self.successful_records.empty:
            return pd.DataFrame()

        promo_data = self.successful_records.copy()
        promo_data["has_promotion"] = promo_data["active_promotions"].notna()

        promo_summary = (
            promo_data.groupby("platform")
            .agg(
                total_records=("has_promotion", "count"),
                records_with_promo=("has_promotion", "sum"),
            )
            .reset_index()
        )
        promo_summary["promotion_rate_pct"] = (
            promo_summary["records_with_promo"]
            / promo_summary["total_records"]
            * 100
        ).round(1)

        return promo_summary

    def compute_rappi_competitive_position(self) -> dict[str, Any]:
        if self.successful_records.empty:
            return {"status": "insufficient_data"}

        rappi_data = self.successful_records[
            self.successful_records["platform"] == "Rappi"
        ]
        competitors_data = self.successful_records[
            self.successful_records["platform"] != "Rappi"
        ]

        if rappi_data.empty or competitors_data.empty:
            return {"status": "insufficient_data"}

        rappi_avg_price = rappi_data["product_price"].mean()
        competitor_avg_price = competitors_data["product_price"].mean()
        price_difference_pct = (
            (rappi_avg_price - competitor_avg_price) / competitor_avg_price * 100
        )

        rappi_avg_delivery_fee = rappi_data["delivery_fee"].mean()
        competitor_avg_delivery_fee = competitors_data["delivery_fee"].mean()

        rappi_avg_time = rappi_data["estimated_delivery_minutes"].mean()
        competitor_avg_time = competitors_data["estimated_delivery_minutes"].mean()

        rappi_avg_total = rappi_data["total_final_price"].mean()
        competitor_avg_total = competitors_data["total_final_price"].mean()

        if price_difference_pct < -2:
            price_position = "cheaper"
        elif price_difference_pct > 2:
            price_position = "more_expensive"
        else:
            price_position = "similar"

        return {
            "status": "computed",
            "rappi_avg_product_price": round(rappi_avg_price, 2),
            "competitor_avg_product_price": round(competitor_avg_price, 2),
            "price_difference_pct": round(price_difference_pct, 1),
            "price_position": price_position,
            "rappi_avg_delivery_fee": round(rappi_avg_delivery_fee, 2),
            "competitor_avg_delivery_fee": round(competitor_avg_delivery_fee, 2),
            "rappi_avg_delivery_minutes": round(rappi_avg_time, 1),
            "competitor_avg_delivery_minutes": round(competitor_avg_time, 1),
            "rappi_avg_total_price": round(rappi_avg_total, 2),
            "competitor_avg_total_price": round(competitor_avg_total, 2),
        }

    def generate_full_analysis(self) -> dict[str, Any]:
        self.logger.info("Generating full comparative analysis...")

        return {
            "price_comparison_by_platform": self.compute_price_comparison_by_platform(),
            "delivery_fee_comparison": self.compute_delivery_fee_comparison(),
            "delivery_time_comparison": self.compute_delivery_time_comparison(),
            "total_cost_comparison": self.compute_total_cost_comparison(),
            "geographic_comparison": self.compute_geographic_comparison(),
            "zone_type_comparison": self.compute_zone_type_comparison(),
            "promotion_summary": self.compute_promotion_summary(),
            "rappi_competitive_position": self.compute_rappi_competitive_position(),
        }
