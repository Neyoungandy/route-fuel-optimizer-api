from django.core.management.base import BaseCommand

from planner.services.stations import get_station_index, load_stations
from django.conf import settings


class Command(BaseCommand):
    help = "Load the fuel-price CSV and print catalog statistics."

    def handle(self, *args, **options):
        stations = load_stations(settings.FUEL_PRICES_CSV, settings.US_CITIES_CSV)
        index = get_station_index()
        states = sorted({s.state for s in stations})
        self.stdout.write(f"stations={len(index.stations)} states={len(states)}")
        self.stdout.write(f"price_min={min(s.retail_price for s in stations):.3f}")
        self.stdout.write(f"price_max={max(s.retail_price for s in stations):.3f}")
