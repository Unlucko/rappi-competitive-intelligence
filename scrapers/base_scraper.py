import abc
import json
import logging
import os
from datetime import datetime, timezone
from typing import Any, Optional

from playwright.async_api import BrowserContext, Page

from config import (
    GeoAddress,
    OUTPUT_DIR,
    SCREENSHOTS_DIR,
    SCRAPING_CONFIG,
)
from utils.browser_manager import BrowserManager
from utils.rate_limiter import RateLimiter

logger = logging.getLogger(__name__)


class ScrapingResult:

    def __init__(
        self,
        platform: str,
        address_label: str,
        city: str,
        zone_type: str,
        product_id: str,
        product_name: str,
        product_price: Optional[float] = None,
        delivery_fee: Optional[float] = None,
        service_fee: Optional[float] = None,
        estimated_delivery_minutes: Optional[int] = None,
        active_promotions: Optional[str] = None,
        total_final_price: Optional[float] = None,
        restaurant_name: Optional[str] = None,
        scrape_timestamp: Optional[str] = None,
        scrape_success: bool = False,
        error_message: Optional[str] = None,
    ):
        self.platform = platform
        self.address_label = address_label
        self.city = city
        self.zone_type = zone_type
        self.product_id = product_id
        self.product_name = product_name
        self.product_price = product_price
        self.delivery_fee = delivery_fee
        self.service_fee = service_fee
        self.estimated_delivery_minutes = estimated_delivery_minutes
        self.active_promotions = active_promotions
        self.total_final_price = total_final_price
        self.restaurant_name = restaurant_name
        self.scrape_timestamp = scrape_timestamp or datetime.now(timezone.utc).isoformat()
        self.scrape_success = scrape_success
        self.error_message = error_message

    def to_dict(self) -> dict[str, Any]:
        return {
            "platform": self.platform,
            "address_label": self.address_label,
            "city": self.city,
            "zone_type": self.zone_type,
            "product_id": self.product_id,
            "product_name": self.product_name,
            "product_price": self.product_price,
            "delivery_fee": self.delivery_fee,
            "service_fee": self.service_fee,
            "estimated_delivery_minutes": self.estimated_delivery_minutes,
            "active_promotions": self.active_promotions,
            "total_final_price": self.total_final_price,
            "restaurant_name": self.restaurant_name,
            "scrape_timestamp": self.scrape_timestamp,
            "scrape_success": self.scrape_success,
            "error_message": self.error_message,
        }


class BaseScraper(abc.ABC):

    def __init__(
        self,
        platform_name: str,
        base_url: str,
        browser_manager: BrowserManager,
        rate_limiter: RateLimiter,
    ):
        self.platform_name = platform_name
        self.base_url = base_url
        self.browser_manager = browser_manager
        self.rate_limiter = rate_limiter
        self.logger = logging.getLogger(f"{__name__}.{platform_name}")
        self.results: list[ScrapingResult] = []

    @abc.abstractmethod
    async def set_delivery_address(self, page: Page, address: GeoAddress) -> bool:
        pass

    @abc.abstractmethod
    async def navigate_to_restaurant(self, page: Page, restaurant_name: str) -> bool:
        pass

    @abc.abstractmethod
    async def extract_product_data(
        self, page: Page, product_id: str, product_name: str
    ) -> dict[str, Any]:
        pass

    @abc.abstractmethod
    async def extract_delivery_info(self, page: Page) -> dict[str, Any]:
        pass

    async def take_screenshot(self, page: Page, label: str) -> Optional[str]:
        try:
            timestamp_suffix = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{self.platform_name}_{label}_{timestamp_suffix}.png"
            filepath = os.path.join(SCREENSHOTS_DIR, filename)
            await page.screenshot(path=filepath, full_page=False)
            self.logger.info("Screenshot saved: %s", filepath)
            return filepath
        except Exception as screenshot_error:
            self.logger.warning("Failed to take screenshot: %s", screenshot_error)
            return None

    async def dismiss_popups(self, page: Page) -> None:
        common_dismiss_selectors = [
            "[data-testid='close-button']",
            "button[aria-label='Close']",
            "button[aria-label='Cerrar']",
            ".cookie-banner button",
            "#onetrust-accept-btn-handler",
            "button:has-text('Aceptar')",
            "button:has-text('Accept')",
            "button:has-text('Entendido')",
            "button:has-text('Got it')",
            "button:has-text('OK')",
            "[class*='close'][class*='modal']",
            "[class*='dismiss']",
        ]

        for selector in common_dismiss_selectors:
            try:
                element = page.locator(selector).first
                if await element.is_visible(timeout=1000):
                    await element.click()
                    self.logger.debug("Dismissed popup with selector: %s", selector)
                    await page.wait_for_timeout(500)
            except Exception:
                pass

    async def scrape_address(
        self,
        address: GeoAddress,
        products: list[dict[str, str]],
        restaurant_name: str = "McDonald's",
    ) -> list[ScrapingResult]:
        address_results = []
        context = None

        try:
            context = await self.browser_manager.create_context()
            page = await self.browser_manager.create_page(context)

            self.logger.info(
                "Scraping %s for address: %s", self.platform_name, address.label
            )

            await self.rate_limiter.wait_between_requests()
            await page.goto(self.base_url, wait_until="domcontentloaded")
            await page.wait_for_timeout(2000)
            await self.dismiss_popups(page)

            address_set_successfully = await self.rate_limiter.execute_with_retry(
                self.set_delivery_address,
                page,
                address,
                operation_name=f"set_address_{address.label}",
            )

            if not address_set_successfully:
                self.logger.warning(
                    "Could not set address %s on %s", address.label, self.platform_name
                )
                for product in products:
                    address_results.append(
                        ScrapingResult(
                            platform=self.platform_name,
                            address_label=address.label,
                            city=address.city,
                            zone_type=address.zone_type,
                            product_id=product["product_id"],
                            product_name=product["product_name"],
                            scrape_success=False,
                            error_message="Failed to set delivery address",
                        )
                    )
                return address_results

            await self.dismiss_popups(page)

            restaurant_found = await self.rate_limiter.execute_with_retry(
                self.navigate_to_restaurant,
                page,
                restaurant_name,
                operation_name=f"find_restaurant_{address.label}",
            )

            if not restaurant_found:
                self.logger.warning(
                    "Could not find %s at %s on %s",
                    restaurant_name,
                    address.label,
                    self.platform_name,
                )
                await self.take_screenshot(page, f"no_restaurant_{address.label}")
                for product in products:
                    address_results.append(
                        ScrapingResult(
                            platform=self.platform_name,
                            address_label=address.label,
                            city=address.city,
                            zone_type=address.zone_type,
                            product_id=product["product_id"],
                            product_name=product["product_name"],
                            scrape_success=False,
                            error_message="Restaurant not found",
                        )
                    )
                return address_results

            await self.dismiss_popups(page)

            delivery_info = await self.rate_limiter.execute_with_retry(
                self.extract_delivery_info,
                page,
                operation_name=f"delivery_info_{address.label}",
            )
            delivery_info = delivery_info or {}

            for product in products:
                try:
                    product_data = await self.rate_limiter.execute_with_retry(
                        self.extract_product_data,
                        page,
                        product["product_id"],
                        product["product_name"],
                        operation_name=f"product_{product['product_id']}_{address.label}",
                    )
                    product_data = product_data or {}

                    product_price = product_data.get("product_price")
                    delivery_fee = delivery_info.get("delivery_fee")
                    service_fee = delivery_info.get("service_fee")

                    total_final_price = None
                    if product_price is not None:
                        total_final_price = product_price
                        if delivery_fee is not None:
                            total_final_price += delivery_fee
                        if service_fee is not None:
                            total_final_price += service_fee

                    result = ScrapingResult(
                        platform=self.platform_name,
                        address_label=address.label,
                        city=address.city,
                        zone_type=address.zone_type,
                        product_id=product["product_id"],
                        product_name=product["product_name"],
                        product_price=product_price,
                        delivery_fee=delivery_fee,
                        service_fee=service_fee,
                        estimated_delivery_minutes=delivery_info.get(
                            "estimated_delivery_minutes"
                        ),
                        active_promotions=product_data.get("active_promotions"),
                        total_final_price=total_final_price,
                        restaurant_name=product_data.get(
                            "restaurant_name", restaurant_name
                        ),
                        scrape_success=product_price is not None,
                        error_message=product_data.get("error_message"),
                    )
                    address_results.append(result)

                except Exception as product_error:
                    self.logger.error(
                        "Error extracting product %s: %s",
                        product["product_name"],
                        product_error,
                    )
                    address_results.append(
                        ScrapingResult(
                            platform=self.platform_name,
                            address_label=address.label,
                            city=address.city,
                            zone_type=address.zone_type,
                            product_id=product["product_id"],
                            product_name=product["product_name"],
                            scrape_success=False,
                            error_message=str(product_error),
                        )
                    )

            await self.take_screenshot(page, f"completed_{address.label}")

        except Exception as scrape_error:
            self.logger.error(
                "Critical error scraping %s at %s: %s",
                self.platform_name,
                address.label,
                scrape_error,
            )
            for product in products:
                address_results.append(
                    ScrapingResult(
                        platform=self.platform_name,
                        address_label=address.label,
                        city=address.city,
                        zone_type=address.zone_type,
                        product_id=product["product_id"],
                        product_name=product["product_name"],
                        scrape_success=False,
                        error_message=str(scrape_error),
                    )
                )

        finally:
            if context:
                await self.browser_manager.close_context(context)

        self.results.extend(address_results)
        return address_results

    def save_results_to_json(self, filename: Optional[str] = None) -> str:
        if filename is None:
            filename = f"{self.platform_name.lower().replace(' ', '_')}_results.json"

        filepath = os.path.join(OUTPUT_DIR, filename)
        serializable_results = [result.to_dict() for result in self.results]

        with open(filepath, "w", encoding="utf-8") as output_file:
            json.dump(serializable_results, output_file, indent=2, ensure_ascii=False)

        self.logger.info("Results saved to %s (%d records)", filepath, len(self.results))
        return filepath
