import logging
import re
from typing import Any, Optional

from playwright.async_api import Page

from config import GeoAddress
from scrapers.base_scraper import BaseScraper
from utils.browser_manager import BrowserManager
from utils.rate_limiter import RateLimiter

logger = logging.getLogger(__name__)


class RappiScraper(BaseScraper):

    def __init__(self, browser_manager: BrowserManager, rate_limiter: RateLimiter):
        super().__init__(
            platform_name="Rappi",
            base_url="https://www.rappi.com.mx",
            browser_manager=browser_manager,
            rate_limiter=rate_limiter,
        )

    async def set_delivery_address(self, page: Page, address: GeoAddress) -> bool:
        try:
            await page.wait_for_load_state("domcontentloaded")
            await page.wait_for_timeout(2000)

            address_input_selectors = [
                "input[placeholder*='direcci']",
                "input[placeholder*='address']",
                "input[placeholder*='Busca tu direcci']",
                "input[data-qa='address-input']",
                "[data-testid='address-input'] input",
                "input[type='text'][class*='address']",
                ".address-input input",
            ]

            address_input = None
            for selector in address_input_selectors:
                try:
                    candidate = page.locator(selector).first
                    if await candidate.is_visible(timeout=2000):
                        address_input = candidate
                        break
                except Exception:
                    continue

            if address_input is None:
                address_trigger_selectors = [
                    "[data-qa='address-picker']",
                    "[class*='address'][class*='trigger']",
                    "[class*='location'][class*='picker']",
                    "button:has-text('direcci')",
                    "span:has-text('direcci')",
                ]
                for selector in address_trigger_selectors:
                    try:
                        trigger = page.locator(selector).first
                        if await trigger.is_visible(timeout=2000):
                            await trigger.click()
                            await page.wait_for_timeout(1500)
                            break
                    except Exception:
                        continue

                for selector in address_input_selectors:
                    try:
                        candidate = page.locator(selector).first
                        if await candidate.is_visible(timeout=2000):
                            address_input = candidate
                            break
                    except Exception:
                        continue

            if address_input is None:
                self.logger.warning("Could not find address input on Rappi")
                await self.take_screenshot(page, f"no_address_input_{address.label}")
                return False

            await address_input.click()
            await address_input.fill("")
            await address_input.type(address.address, delay=50)
            await page.wait_for_timeout(2000)

            suggestion_selectors = [
                "[data-qa='address-suggestion']",
                "[class*='suggestion']",
                "[class*='autocomplete'] li",
                "[class*='dropdown'] [class*='item']",
                "[role='option']",
                "[class*='result'] [class*='item']",
            ]

            for selector in suggestion_selectors:
                try:
                    first_suggestion = page.locator(selector).first
                    if await first_suggestion.is_visible(timeout=3000):
                        await first_suggestion.click()
                        await page.wait_for_timeout(2000)
                        self.logger.info("Address set on Rappi: %s", address.label)
                        return True
                except Exception:
                    continue

            await page.keyboard.press("Enter")
            await page.wait_for_timeout(2000)
            self.logger.info("Address submitted via Enter on Rappi: %s", address.label)
            return True

        except Exception as address_error:
            self.logger.error("Error setting Rappi address: %s", address_error)
            await self.take_screenshot(page, f"address_error_{address.label}")
            return False

    async def navigate_to_restaurant(self, page: Page, restaurant_name: str) -> bool:
        try:
            await self.dismiss_popups(page)

            search_url = f"{self.base_url}/restaurants/search?query={restaurant_name}"
            await page.goto(search_url, wait_until="domcontentloaded")
            await page.wait_for_timeout(3000)

            search_selectors = [
                "input[placeholder*='Busca']",
                "input[data-qa='search-input']",
                "input[type='search']",
                "input[placeholder*='Search']",
                "[data-testid='search-input'] input",
            ]

            for selector in search_selectors:
                try:
                    search_box = page.locator(selector).first
                    if await search_box.is_visible(timeout=2000):
                        await search_box.click()
                        await search_box.fill("")
                        await search_box.type(restaurant_name, delay=50)
                        await page.wait_for_timeout(2000)
                        break
                except Exception:
                    continue

            restaurant_link_selectors = [
                f"a:has-text('{restaurant_name}')",
                f"[data-qa='store-card']:has-text('{restaurant_name}')",
                f"[class*='restaurant']:has-text('{restaurant_name}')",
                f"[class*='store']:has-text('{restaurant_name}')",
                "[data-qa='store-card']",
                "[class*='RestaurantCard']",
            ]

            for selector in restaurant_link_selectors:
                try:
                    restaurant_element = page.locator(selector).first
                    if await restaurant_element.is_visible(timeout=3000):
                        await restaurant_element.click()
                        await page.wait_for_timeout(3000)
                        self.logger.info("Navigated to %s on Rappi", restaurant_name)
                        return True
                except Exception:
                    continue

            self.logger.warning("Could not find %s on Rappi", restaurant_name)
            return False

        except Exception as nav_error:
            self.logger.error("Error navigating to restaurant on Rappi: %s", nav_error)
            return False

    async def extract_product_data(
        self, page: Page, product_id: str, product_name: str
    ) -> dict[str, Any]:
        result = {
            "product_price": None,
            "active_promotions": None,
            "restaurant_name": "McDonald's",
            "error_message": None,
        }

        try:
            product_selectors = [
                f"[class*='product']:has-text('{product_name}')",
                f"[data-qa='product-item']:has-text('{product_name}')",
                f"[class*='ProductItem']:has-text('{product_name}')",
                f"span:has-text('{product_name}')",
            ]

            product_element = None
            for selector in product_selectors:
                try:
                    candidate = page.locator(selector).first
                    if await candidate.is_visible(timeout=2000):
                        product_element = candidate
                        break
                except Exception:
                    continue

            if product_element is None:
                result["error_message"] = f"Product '{product_name}' not found on page"
                return result

            price_selectors = [
                "[class*='price']",
                "[data-qa='product-price']",
                "span:has-text('$')",
            ]

            for price_selector in price_selectors:
                try:
                    price_element = product_element.locator(price_selector).first
                    if await price_element.is_visible(timeout=1500):
                        price_text = await price_element.text_content()
                        extracted_price = self._parse_price(price_text)
                        if extracted_price is not None:
                            result["product_price"] = extracted_price
                            break
                except Exception:
                    continue

            try:
                promo_selectors = [
                    "[class*='promo']",
                    "[class*='discount']",
                    "[class*='offer']",
                    "[class*='sale']",
                ]
                for promo_selector in promo_selectors:
                    try:
                        promo_element = product_element.locator(promo_selector).first
                        if await promo_element.is_visible(timeout=1000):
                            result["active_promotions"] = await promo_element.text_content()
                            break
                    except Exception:
                        continue
            except Exception:
                pass

        except Exception as extraction_error:
            result["error_message"] = str(extraction_error)

        return result

    async def extract_delivery_info(self, page: Page) -> dict[str, Any]:
        result = {
            "delivery_fee": None,
            "service_fee": None,
            "estimated_delivery_minutes": None,
        }

        try:
            delivery_time_selectors = [
                "[class*='delivery'][class*='time']",
                "[data-qa='delivery-time']",
                "span:has-text('min')",
                "[class*='eta']",
            ]

            for selector in delivery_time_selectors:
                try:
                    time_element = page.locator(selector).first
                    if await time_element.is_visible(timeout=2000):
                        time_text = await time_element.text_content()
                        parsed_minutes = self._parse_delivery_time(time_text)
                        if parsed_minutes is not None:
                            result["estimated_delivery_minutes"] = parsed_minutes
                            break
                except Exception:
                    continue

            fee_selectors = [
                "[class*='delivery'][class*='fee']",
                "[data-qa='delivery-fee']",
                "span:has-text('Env'):has-text('$')",
                "[class*='shipping']",
            ]

            for selector in fee_selectors:
                try:
                    fee_element = page.locator(selector).first
                    if await fee_element.is_visible(timeout=2000):
                        fee_text = await fee_element.text_content()
                        if "gratis" in fee_text.lower() or "free" in fee_text.lower():
                            result["delivery_fee"] = 0.0
                        else:
                            parsed_fee = self._parse_price(fee_text)
                            if parsed_fee is not None:
                                result["delivery_fee"] = parsed_fee
                        break
                except Exception:
                    continue

        except Exception as delivery_error:
            self.logger.warning("Error extracting delivery info from Rappi: %s", delivery_error)

        return result

    @staticmethod
    def _parse_price(price_text: Optional[str]) -> Optional[float]:
        if not price_text:
            return None
        cleaned_text = price_text.replace(",", "").replace(" ", "")
        price_match = re.search(r"\$?(\d+\.?\d*)", cleaned_text)
        if price_match:
            return float(price_match.group(1))
        return None

    @staticmethod
    def _parse_delivery_time(time_text: Optional[str]) -> Optional[int]:
        if not time_text:
            return None
        range_match = re.search(r"(\d+)\s*-\s*(\d+)", time_text)
        if range_match:
            low = int(range_match.group(1))
            high = int(range_match.group(2))
            return (low + high) // 2
        single_match = re.search(r"(\d+)", time_text)
        if single_match:
            return int(single_match.group(1))
        return None
