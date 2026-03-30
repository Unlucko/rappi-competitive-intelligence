import asyncio
import json
import logging
import os
import sys
from datetime import datetime

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import (
    ADDRESSES,
    LOGGING_CONFIG,
    OUTPUT_DIR,
    PLATFORM_CONFIGS,
    REFERENCE_PRODUCTS,
    SCRAPING_CONFIG,
)
from scrapers.base_scraper import ScrapingResult
from scrapers.rappi_scraper import RappiScraper
from scrapers.ubereats_scraper import UberEatsScraper
from scrapers.didifood_scraper import DidiFoodScraper
from utils.browser_manager import BrowserManager
from utils.rate_limiter import RateLimiter
from analysis.report_builder import ReportBuilder


def setup_logging() -> None:
    logging.basicConfig(
        level=getattr(logging, LOGGING_CONFIG["level"]),
        format=LOGGING_CONFIG["format"],
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(LOGGING_CONFIG["log_file"], encoding="utf-8"),
        ],
    )


def load_fallback_sample_data() -> list[dict]:
    sample_data_path = os.path.join(OUTPUT_DIR, "sample_data.json")
    if os.path.exists(sample_data_path):
        with open(sample_data_path, "r", encoding="utf-8") as sample_file:
            return json.load(sample_file)
    return []


def save_combined_results(all_results: list[dict], filename: str = "scraped_data.json") -> str:
    output_path = os.path.join(OUTPUT_DIR, filename)
    with open(output_path, "w", encoding="utf-8") as output_file:
        json.dump(all_results, output_file, indent=2, ensure_ascii=False)
    return output_path


def save_results_to_csv(all_results: list[dict], filename: str = "scraped_data.csv") -> str:
    output_path = os.path.join(OUTPUT_DIR, filename)
    dataframe = pd.DataFrame(all_results)
    dataframe.to_csv(output_path, index=False, encoding="utf-8")
    return output_path


async def run_scraper_for_platform(
    scraper_instance,
    addresses_to_scrape,
    products_to_scrape,
    max_addresses: int = 5,
) -> list[dict]:
    logger = logging.getLogger(__name__)
    all_platform_results = []

    selected_addresses = addresses_to_scrape[:max_addresses]

    for address in selected_addresses:
        logger.info(
            "Scraping %s at %s...",
            scraper_instance.platform_name,
            address.label,
        )
        try:
            address_results = await scraper_instance.scrape_address(
                address=address,
                products=products_to_scrape,
            )
            for result in address_results:
                all_platform_results.append(result.to_dict())
        except Exception as scrape_error:
            logger.error(
                "Error scraping %s at %s: %s",
                scraper_instance.platform_name,
                address.label,
                scrape_error,
            )

    return all_platform_results


async def run_all_scrapers(
    max_addresses_per_platform: int = 3,
    use_sample_on_failure: bool = True,
) -> list[dict]:
    logger = logging.getLogger(__name__)
    combined_results = []

    browser_manager = BrowserManager(
        headless=SCRAPING_CONFIG["headless"],
        user_agents=SCRAPING_CONFIG["user_agents"],
        navigation_timeout_ms=SCRAPING_CONFIG["navigation_timeout_ms"],
    )

    rate_limiter = RateLimiter(
        min_delay=SCRAPING_CONFIG["min_delay_seconds"],
        max_delay=SCRAPING_CONFIG["max_delay_seconds"],
        max_retries=SCRAPING_CONFIG["max_retries"],
        backoff_base=SCRAPING_CONFIG["backoff_base_seconds"],
    )

    scrapers = []

    if PLATFORM_CONFIGS["rappi"].enabled:
        scrapers.append(RappiScraper(browser_manager, rate_limiter))

    if PLATFORM_CONFIGS["ubereats"].enabled:
        scrapers.append(UberEatsScraper(browser_manager, rate_limiter))

    if PLATFORM_CONFIGS["didifood"].enabled:
        scrapers.append(DidiFoodScraper(browser_manager, rate_limiter))

    try:
        await browser_manager.start()

        for scraper in scrapers:
            logger.info("Starting scrape for platform: %s", scraper.platform_name)
            try:
                platform_results = await run_scraper_for_platform(
                    scraper_instance=scraper,
                    addresses_to_scrape=ADDRESSES,
                    products_to_scrape=REFERENCE_PRODUCTS,
                    max_addresses=max_addresses_per_platform,
                )
                combined_results.extend(platform_results)
                scraper.save_results_to_json()
                logger.info(
                    "Completed %s: %d results collected",
                    scraper.platform_name,
                    len(platform_results),
                )
            except Exception as platform_error:
                logger.error(
                    "Failed to scrape %s: %s",
                    scraper.platform_name,
                    platform_error,
                )

    finally:
        await browser_manager.stop()

    successful_count = sum(1 for r in combined_results if r.get("scrape_success"))

    if successful_count == 0 and use_sample_on_failure:
        logger.warning(
            "No successful scraping results. Loading fallback sample data."
        )
        combined_results = load_fallback_sample_data()

    return combined_results


def generate_reports(results_data: list[dict]) -> None:
    logger = logging.getLogger(__name__)

    if not results_data:
        logger.error("No data available for report generation.")
        return

    dataframe = pd.DataFrame(results_data)

    logger.info("Generating competitive intelligence reports...")
    report_builder = ReportBuilder(dataframe)

    html_report_path = report_builder.generate_html_report()
    logger.info("HTML report generated: %s", html_report_path)

    markdown_report_path = report_builder.generate_markdown_report()
    logger.info("Markdown report generated: %s", markdown_report_path)

    chart_paths = report_builder.save_charts_as_html()
    logger.info("Charts saved: %d files", len(chart_paths))

    for insight in report_builder.insights:
        logger.info(
            "Insight #%d [%s]: %s",
            insight.insight_number,
            insight.priority.upper(),
            insight.title,
        )


async def main() -> None:
    setup_logging()
    logger = logging.getLogger(__name__)

    logger.info("=" * 60)
    logger.info("Competitive Intelligence Scraper - Starting")
    logger.info("Timestamp: %s", datetime.now().isoformat())
    logger.info("=" * 60)

    use_sample_only = "--sample-only" in sys.argv
    max_addresses = 3

    for arg in sys.argv[1:]:
        if arg.startswith("--max-addresses="):
            try:
                max_addresses = int(arg.split("=")[1])
            except ValueError:
                pass

    if use_sample_only:
        logger.info("Running in sample-only mode (no live scraping)")
        results_data = load_fallback_sample_data()
    else:
        logger.info("Running live scraping with max %d addresses per platform", max_addresses)
        results_data = await run_all_scrapers(
            max_addresses_per_platform=max_addresses,
            use_sample_on_failure=True,
        )

    json_output_path = save_combined_results(results_data)
    logger.info("Combined results saved to: %s", json_output_path)

    csv_output_path = save_results_to_csv(results_data)
    logger.info("CSV results saved to: %s", csv_output_path)

    generate_reports(results_data)

    logger.info("=" * 60)
    logger.info("Competitive Intelligence Scraper - Completed")
    logger.info("Total records: %d", len(results_data))
    logger.info("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
